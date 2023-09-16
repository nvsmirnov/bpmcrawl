#
# TODO: this code copied from original branch without checking that it works. It should. Probably.
# TODO: but certainly authentication needs to be rewritten:
#       need to get user music provider's identity from music_service_config
#

from .base import MusicproviderBase
from backend.log import *
from backend.exceptions import *

import logging
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import *

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

    def set_provider_logging_level(self, provider_logging_level):
        super(MusicProviderSpotify, self).set_provider_logging_level(provider_logging_level)
        logging.getLogger("spotipy").setLevel(self.provider_logging_level)

    def login(self):
        logging.getLogger("spotipy").setLevel(CRITICAL)
        try:
            self.api = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False, scope=" ".join(self.spotify_scopes)))
            self.api.me()  # or else it will try to log in upon first request
            return self.api
        except Exception as e:
            debug(f"{self.whoami()}: got exception:", exc_info=True)
            raise ExBpmcrawlGeneric(f"Failed to log in to Spotify: {e} (enable debug for more)")

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
            raise ExBpmcrawlGeneric(str(e))
        else:
            return True

    def get_station_from_url(self, url):
        raise ExBpmcrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def get_station_name(self, station):
        raise ExBpmcrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def station_prepare(self, station):
        raise ExBpmcrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def station_get_next_track(self, station):
        raise ExBpmcrawlGeneric(f"Stations are not implemented (and not needed) for Spotify")

    def get_track_id(self, track):
        return track['track']['id']

    def download_track(self, track):
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

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

    def artist_pager_init(self, artist):
        self.artist_pager_load_page(artist, 0)
