#
# TODO: this code copied from original branch without checking that it works. It should. Probably.
# TODO: but certainly authentication needs to be rewritten:
#       need to get user music provider's identity from music_service_config
#

from .base import MusicproviderBase
from backend.log import *
from backend.exceptions import *
from backend.whoami import *
from backend.calc_bpm import calc_file_bpm_histogram

import logging
import re
import urllib
import requests
import tempfile

from gmusicapi.clients import Mobileclient
import gmusicapi.exceptions

# TODO: probably we should set it somehow elsewhere
gmusic_client_id = '3ae9278a98fd8efe'

# TODO: change this fixed temp_dir to something appropriate
temp_dir = 'data/tmp'

class MusicProviderGoogle(MusicproviderBase):
    music_service = 'gmusic'
    gmusic_client_id = gmusic_client_id
    api = None
    station_current = None  # current station
    station_recently_played = None  # list of tracks already seen from current station
    station_current_tracks = None  # list of tracks got last time from station
    station_current_unseen = None  # count of tracks in current tracks list that were unseen in this playback session
    station_now_playing = None  # index of 'currently playing' track (points to track returned by last station_get_next_track call)

    def login(self):
        # log in to google music suppressing it's debugging messages
        oldloglevel = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        self.api = Mobileclient(debug_logging=False)
        logging.getLogger("gmusicapi.Mobileclient1").setLevel(logging.WARNING)
        rv = self.api.oauth_login(self.gmusic_client_id)
        logging.getLogger().setLevel(oldloglevel)
        if not rv:
            raise ExBpmcrawlGeneric(f"Please login to Google Music first (run gmusic-login.py)")

    def get_playlist(self, playlist_id_uri_name):
        if re.match('^https?://', playlist_id_uri_name, re.I):
            # this is uri of shared playlist
            try:
                self.api.get_shared_playlist_contents(urllib.parse.unquote(playlist_id_uri_name))
            except Exception as e:
                debug(f"{self.whoami()}: got exception:", exc_info=True)
                raise ExBpmcrawlGeneric(f"failed to get shared playlist: {e}, enable debug for more")
        # find previously created playlist with specified name
        playlists = self.api.get_all_user_playlist_contents()
        playlist = None
        for pl in playlists:
            if pl["name"] == playlist_id_uri_name:
                playlist = pl
                break
        return playlist

    def get_or_create_my_playlist(self, playlist_name):
        playlist = self.get_playlist(playlist_name)
        if not playlist:
            debug(f"{whoami}: playlist {playlist_name} not found, creating it...")
            id = self.api.create_playlist(playlist_name)
            debug(f"{whoami}: created playlist, id {id}")
            playlists = self.api.get_all_playlists()
            for pl in playlists:
                if pl["id"] == id:
                    playlist = pl
                    break
        if not playlist:
            raise ExBpmcrawlGeneric(f"Failed to find or create playlist {playlist_name}")
        return playlist

    def get_playlist_tracks(self, playlist):
        # get track ids of playlist
        tracks_in_playlist = []
        if "tracks" in playlist:
            for track in playlist["tracks"]:
                if "track" in track:  # it is google play music's track, not some local crap
                    tracks_in_playlist.append(track["track"])
        return tracks_in_playlist

    def add_track_to_playlist(self, playlist, track_id):
        added = self.api.add_songs_to_playlist(playlist["id"], track_id)
        if len(added):
            return True
        else:
            return False

    def get_station_from_url(self, url):
        if url == "IFL":
            return {"id": "IFL", "name": "I'm Feeling Lucky"}
        station_id_str = urllib.parse.unquote(url).rsplit("/", 1)[-1].split("?", 1)[0].split('#', 1)[0]
        stations = self.api.get_all_stations()
        for station in stations:
            if 'seed' in station and 'curatedStationId' in station['seed']:
                if station['seed']['curatedStationId'] == station_id_str:
                    debug(f"{whoami()}: found station {station['id']}")
                    return station
        raise ExBpmcrawlGeneric(f"Failed to find station by string '{station_id_str}' (from url '{url}')")

    def get_station_name(self, station):
        return station['name']

    def station_prepare(self, station):
        self.station_recently_played = []
        self.station_current_tracks = None
        self.station_current_unseen = 0
        self.station_now_playing = None
        self.station_current = station

    def station_get_next_track(self):
        need_new_tracks = False
        if self.station_current_tracks is None:
            need_new_tracks = True
        else:
            while not need_new_tracks:
                self.station_now_playing += 1
                if self.station_now_playing >= len(self.station_current_tracks):
                    if self.station_current_unseen == 0:
                        # all played tracks already seen, so probably we've seen all tracks of station, let's stop it
                        debug(f"{self.whoami()}: all played tracks were already seen, stopping this playback cycle")
                        return None
                    else:
                        need_new_tracks = True
                else:
                    track = self.station_current_tracks[self.station_now_playing]
                    track_id = self.get_track_id(track)
                    if track_id in self.station_recently_played:
                        # try to get next track
                        debug(f"{self.whoami()}: (level 1) skipping already seen track {track_id}")
                        continue
                    else:
                        self.station_current_unseen += 1
                        self.station_recently_played.append(track_id)
                        debug(f"{self.whoami()}: (level 1) returning next track {track_id}, station_current_unseen=={self.station_current_unseen}")
                        return track
        # here we are only if we need more tracks from station
        debug(f"{self.whoami()}: getting new set of tracks")
        self.station_current_tracks = self.api.get_station_tracks(self.station_current['id'], num_tracks=25,
                                                                  recently_played_ids=self.station_recently_played)
        self.station_current_unseen = 0
        self.station_now_playing = 0
        if not self.station_current_tracks or len(self.station_current_tracks) == 0:
            debug(f"{self.whoami()}: got no tracks, stopping this playback cycle")
            return None
        debug(f"{self.whoami()}: got {len(self.station_current_tracks)} tracks")

        while not (self.station_now_playing >= len(self.station_current_tracks)):
            track = self.station_current_tracks[self.station_now_playing]
            track_id = self.get_track_id(track)
            if track_id in self.station_recently_played:
                # try to get next track
                debug(f"{self.whoami()}: (level 2) skipping already seen track {track_id}")
                self.station_now_playing += 1
                continue
            else:
                self.station_current_unseen += 1
                self.station_recently_played.append(track_id)
                debug(f"{self.whoami()}: (level 2) returning next track {track_id}, station_current_unseen=={self.station_current_unseen}")
                return track
        debug(f"{self.whoami()}: (level 2) reached end of list, stopping this playback cycle")
        return None

    def get_track_id(self, track):
        return track['storeId']

    def download_track(self, track):
        file = tempfile.NamedTemporaryFile(mode='w+b', dir=temp_dir, prefix='track', suffix='.mp3')
        stream_url = self.api.get_stream_url(self.get_track_id(track), quality='low')
        with requests.get(stream_url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                file.write(chunk)
        file.flush()
        return file

    def get_track_id(self, track):
        return track['storeId']

    def calc_bpm_histogram(self, track):
        file = self.download_track(track)
        debug(f"{self.whoami()}: got track {self.get_track_id(track)} to {file.name}")
        histogram = calc_file_bpm_histogram(file.name)
        file.close()
        return histogram
