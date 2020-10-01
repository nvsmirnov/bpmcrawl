import logging
import urllib
import requests
import tempfile
import time

from exceptions import *
from config import *
from calc_bpm import *

from gmusicapi.clients import Mobileclient
import gmusicapi.exceptions
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import *

music_service_mapping = None  # it is really initialized at the end of this file


def get_music_provider(music_service):
    if music_service not in music_service_mapping:
        raise ExBpmCrawlGeneric(f"Unknown music service provider: '{music_service}'")
    return music_service_mapping[music_service](music_service)


class MusicproviderBase(WhoamiObject):
    music_service = None

    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return f"{self.__class__.__name__}(music_service={self.music_service})"

    def __init__(self, music_service):
        if self.music_service != music_service:
            raise ExBpmCrawlGeneric(f"Internal error: tried to init {self.__class__.__name__} with wring service provider '{self.music_service}'")

    def login(self):
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_playlist(self, playlist_id_uri_name):
        """
        Get existing playlist by name (or id or uri if supported by specific provider's child class)
        :param playlist_id_uri_name: playlist id, uri or name
        :return: playlist
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_or_create_my_playlist(self, playlist_name):
        """
        Get existing playlist, or create user's playlist if it does not exist.
        :param playlist_name: Name of playlist (or, if supported by specific provider's API, uri or id of it)
        :return: playlist
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_playlist_tracks(self, playlist):
        """
        Get all tracks of playlist
        :param playlist: playlist returned by get_or_create_my_playlist()
        :return: list of tracks
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def add_track_to_playlist(self, playlist, track_id):
        """
        Add track to existing playlist
        :param playlist: playlist returned by get_or_create_playlist()
        :return: True if added, false if not
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_station_from_url(self, url):
        """
        Get station object (in format of provider) from station name/URL
        :param url: name or url of radio station got from user
        :return: radio station id
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_station_name(self, station):
        """
        Get station name (probably human readable)
        :param station: station returned by get_station_from_url
        :return: Station name
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def station_prepare(self, station):
        """
        Prepare station for playback (i.e., clear 'recently played' cache to start with first track)
        It may be ok to do nothing for some of providers.
        For now it is guaranteed to work only for one station at a time.
        :param station: station returned by get_station_from_url
        :return: Nothing
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def station_get_next_track(self, station):
        """
        Get next track from station, exclude already seen tracks.
        For now it is guaranteed to work only for one station at a time.
        :param station: station returned by get_station_from_url
        :return: None if there is no unseen tracks to play
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_track_id(self, track):
        """
        Get track id for given track. Track id is used to save track info to cache databse.
        :param track: track returned by station_get_next_track, or track of playlist
        :return: String with track id
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def download_track(self, track):
        """
        Download track to file and return Tempfile object.
        File will be deleted upon close!
        :param track: track returned by station_get_next_track, or track of playlist
        :return: tempfile object with track data
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def calc_bpm_histogram(self, track):
        """
        Calculate BPM histogram for track
        :param track: track returned by station_get_next_track, or track of playlist
        :return: histogram: { bpm1(float): bpm1_share, bpm2(float): bpm2_share }
        """
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")


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
            raise ExBpmCrawlGeneric(f"Please login to Google Music first (run gmusic-login.py)")

    def get_playlist(self, playlist_id_uri_name):
        if re.match('^https?://', playlist_id_uri_name, re.I):
            # this is uri of shared playlist
            try:
                self.api.get_shared_playlist_contents(urllib.parse.unquote(playlist_id_uri_name))
            except Exception as e:
                debug(f"{self.whoami()}: got exception:", exc_info=True)
                raise ExBpmCrawlGeneric(f"failed to get shared playlist: {e}, enable debug for more")
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
            raise ExBpmCrawlGeneric(f"Failed to find or create playlist {playlist_name}")
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
        raise ExBpmCrawlGeneric(f"Failed to find station by string '{station_id_str}' (from url '{url}')")

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


class MusicProviderSpotify(MusicproviderBase):
    music_service = 'spotify'
    api = None
    spotify_scopes = [
        "playlist-read-collaborative",
        "playlist-read-private",
        "playlist-modify-public",
        "playlist-modify-private",
        "user-library-read",
        "user-library-modify",
        "user-top-read",
        "user-follow-read",
        "user-read-recently-played",
    ]
    playlist_get_fields = ['id', 'name', 'uri']

    def login(self):
        logging.getLogger("spotipy").setLevel(logging.CRITICAL)
        try:
            self.api = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False, scope=" ".join(self.spotify_scopes)))
            self.api.me()  # or else it will try to log in upon first request
            return self.api
        except Exception as e:
            debug(f"{self.whoami()}: got exception:", exc_info=True)
            raise ExBpmCrawlGeneric(f"Failed to log in to Spotify: {e} (enable debug for more)")

    def get_playlist(self, playlist_id_uri_name):
        playlist = None
        try:
            playlist = self.api.playlist(playlist_id_uri_name, fields=",".join(self.playlist_get_fields))
        except SpotifyException as e:
            if e.http_status != 404:
                raise
        if not playlist:
            debug(f"{self.whoami()}: didn't get it by id, searching among my playlists by name '{playlist_id_uri_name}'")
            # the api's search doesn't fit, because we need only our playlists
            response = self.api.current_user_playlists()
            while response:
                for item in response['items']:
                    if playlist_id_uri_name.casefold() == item['name'].casefold():
                        playlist = {}
                        for field in self.playlist_get_fields:
                            try:
                                playlist[field] = item[field]
                            except KeyError:
                                warning(f"{self.whoami()}: failed to get field {field} of playlist '{playlist_id_uri_name}'")
                        break
                if response['next']:
                    debug(f"{self.whoami()}: next")
                    response = self.api.next(response)
                else:
                    response = None
        return playlist

    def get_or_create_my_playlist(self, playlist_name):
        debug(f"{self.whoami()}: trying to treat name '{playlist_name}' as id")
        playlist = self.get_playlist(playlist_name)
        if playlist is None:
            debug(f"{self.whoami()}: no playlist found, creating playlist with name '{playlist_name}'")
            item = self.api.user_playlist_create(self.api.me()['id'], playlist_name)
            playlist = {}
            for field in self.playlist_get_fields:
                try:
                    playlist[field] = item[field]
                except KeyError:
                    warning(f"{self.whoami()}: failed to get field {field} of playlist '{playlist_name}'")
        debug(f"{self.whoami()}: returning playlist {playlist}")
        return playlist

    def get_playlist_tracks(self, playlist):
        tracks = []
        result = self.api.playlist_items(playlist['id'], additional_types=['track'])
        tracks.extend(result['items'])
        while result['next']:
            result = self.api.next(result)
            tracks.extend(result['items'])
        return tracks

    def add_track_to_playlist(self, playlist, track_id):
        try:
            self.api.playlist_add_items(playlist['id'], [track_id])
        except Exception as e:
            debug(f"{self.whoami()}: got exception:", exc_info=True)
            raise ExBpmCrawlGeneric(str(e))
        else:
            return True

    def get_station_from_url(self, url):
        raise ExBpmCrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def get_station_name(self, station):
        raise ExBpmCrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def station_prepare(self, station):
        raise ExBpmCrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def station_get_next_track(self, station):
        raise ExBpmCrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def get_track_id(self, track):
        return track['track']['id']

    def download_track(self, track):
        raise ExBpmCrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def calc_bpm_histogram(self, track):
        track_id = self.get_track_id(track)
        debug(f"{self.whoami()}: getting audio analysis for {track_id}")
        try:
            histogram = {}
            try:
                analysis = self.api.audio_analysis(track_id)
            except Exception as e:
                # sometimes it is just good to wait and retry and it will magically appear
                # do this rather than immediately fall back to mp3 file analysis
                warning(f"failed to get audio analysis from spotify for {track_id}, will retry")
                time.sleep(10)
                analysis = self.api.audio_analysis(track_id)
            for section in analysis['sections']:
                if float(section['tempo_confidence']) > 0:
                    tempo = round(float(section['tempo']), 1)
                    share = round((float(section['duration']) / float(analysis['track']['duration'])), 2)
                    if tempo in histogram:
                        histogram[tempo] += share
                    else:
                        histogram[tempo] = share
        except Exception as e:
            histogram = None
            debug(f"{self.whoami()}: got exception", exc_info=True)
            error(f"{self.whoami()}: failed to get audio analysis for {track_id} ({e}), will try to analyze mp3 file...")
        # TODO: implement this
        #if histogram is None:
        #    file = self.download_track(track)
        #    debug(f"{self.whoami()}: got track {self.get_track_id(track)} to {file.name}")
        #    histogram = calc_file_bpm_histogram(file.name)
        #    file.close()
        debug(f"{self.whoami()}: histogram({track_id}): {histogram}")
        return histogram


music_service_mapping = {
    'gmusic': MusicProviderGoogle,
    'spotify': MusicProviderSpotify,
}
