from .base import MusicproviderBase
from backend.log import *
from backend.exceptions import *
from backend.whoami import *

import os
import logging
import datetime
import tempfile

import yandex_music
import yandex_music.exceptions
from backend.calc_bpm import calc_file_bpm_histogram

# TODO: change this fixed temp_dir to something appropriate
temp_dir = 'data/tmp'


class MusicproviderYandexMusic(MusicproviderBase):

    class YMPlaylistLiked(WhoamiObject):
        client = None
        tracks = None

        def __init__(self, client):
            self.client = client
            track_ids = [x.id for x in self.client.users_likes_tracks()]
            self.tracks = self.client.tracks(track_ids)

    music_service = 'yandexmusic'
    token_env_var = 'YM_TOKEN'
    token = None
    client = None
    artist_pager = {}

    def __init__(self, music_service, music_service_config, provider_logging_level=CRITICAL):

        super(MusicproviderYandexMusic, self).__init__(music_service, music_service_config, provider_logging_level)
        try:
            self.token = music_service_config['token']
        except Exception:
            raise ExBpmcrawlGeneric(f"No yandex music token provided")

    def set_provider_logging_level(self, provider_logging_level):
        super(MusicproviderYandexMusic, self).set_provider_logging_level(provider_logging_level)
        logging.getLogger("yandex_music").setLevel(self.provider_logging_level)

    def login(self):
        try:
            self.client = yandex_music.Client(self.token).init()
        except yandex_music.exceptions.UnauthorizedError as e:
            raise ExBpmcrawlGeneric(
                f"Failed to log in to {self.music_service}: {e}\n"
                f"You may try to obtain another token.\n"
                f"For instructions, run the app with no {self.token_env_var} env set."
            )
        if not self.client.me.account.login:
            raise ExBpmcrawlGeneric(
                f"Internal error: it looks like login to {self.music_service} was performed as anonymous user."
            )

    def get_playlist(self, playlist_id_uri_name):
        """
        Get existing playlist by name (or id or uri if supported by specific provider's child class)
        :param playlist_id_uri_name: playlist id, uri or name
        :return: playlist
        """
        if playlist_id_uri_name == 'LIKED':  # special name: liked tracks
            return self.YMPlaylistLiked(self.client)
        elif playlist_id_uri_name == 'PLOD':  # special name: playlist of the day
            pers_blocks = self.client.landing(blocks=['personalplaylists']).blocks[0]
            playlist = next(
                x.data.data for x in pers_blocks.entities if x.data.data.generated_playlist_type == 'playlistOfTheDay'
            )
            # the "update" code is from example "paily_playlist_updater.py" but modified
            if playlist.modified:
                pl_modified = datetime.datetime.strptime(playlist.modified, "%Y-%m-%dT%H:%M:%S%z").date()
                if datetime.datetime.now().date() == pl_modified:
                    debug(f"playlist {playlist_id_uri_name} is updated today, {pl_modified}")
                    return playlist
                else:
                    debug(f"playlist {playlist_id_uri_name} is updated at {pl_modified}, will try to update")
            debug(f"trying to update playlist {playlist_id_uri_name}")
            updated_playlist = self.client.users_playlists(user_id=playlist.uid, kind=playlist.kind)
            if updated_playlist.modified:
                pl_modified = datetime.datetime.strptime(updated_playlist.modified, "%Y-%m-%dT%H:%M:%S%z").date()
                debug(f"tried to update playlist {playlist_id_uri_name}, update date now is {pl_modified}")
                return updated_playlist
            else:
                debug(f"tried to update playlist {playlist_id_uri_name} but failed")
                print(f"playlist before update: modified: %s, play_counter: %s" % (
                    playlist.modified, playlist.play_counter))
                print(f"playlist after  update: modified: %s, play_counter: %s" % (
                    updated_playlist.modified, updated_playlist.play_counter))
            return updated_playlist
        else:
            user_playlists = self.client.users_playlists_list()
            playlist = next((p for p in user_playlists if p.title == playlist_id_uri_name), None)
            if playlist == None:
                raise ExBpmcrawlPlaylistNotExists(f'playlist "{playlist_id_uri_name}" not found')
            return playlist
        #raise ExBpmcrawlGeneric(f"Internal error in {self.whoami()}: should not be here")

    def get_playlist_id(self, playlist):
        return playlist.kind

    def get_or_create_my_playlist(self, playlist_name):
        """
        Get existing playlist, or create user's playlist if it does not exist.
        :param playlist_name: Name of playlist (or, if supported by specific provider's API, uri or id of it)
        :return: playlist
        """
        try:
            playlist = self.get_playlist(playlist_name)
        except ExBpmcrawlPlaylistNotExists:
            playlist = self.client.users_playlists_create(playlist_name)
        return playlist

    def get_playlist_tracks(self, playlist):
        """
        Get all tracks of playlist
        :param playlist: playlist returned by get_or_create_my_playlist()
        :return: list of tracks
        """
        tracks = playlist.tracks if playlist.tracks else playlist.fetch_tracks()
        if len(tracks):
            if isinstance(tracks[0], yandex_music.TrackShort):
                # then, probably if we'll do fetch_tracks, they'll become Track objects, not TrackShort
                track_ids = [x.id for x in tracks]
                tracks = self.client.tracks(track_ids)
        return tracks

    def add_track_to_playlist(self, playlist, track_id):
        """
        Add track to existing playlist
        :param playlist: playlist returned by get_or_create_playlist()
        :param track_id: track id to add (not track object but track id)
        :return: True if added, false if not
        """
        tracks = self.client.tracks([track_id])
        if not tracks or not len(tracks):
            raise ExBpmcrawlGeneric(f"Failed to find track with id '{track_id}'")
        if len(tracks) != 1:
            raise ExBpmcrawlGeneric(f"Ambiguous track found for id '{track_id}': got {len(tracks)} tracks instead of 1")
        try:
            album_id = tracks[0].albums[0].id
        except Exception as e:
            raise ExBpmcrawlGeneric(f"Failed to get album id for track {track_id}")
        if playlist.insert_track(track_id, album_id):
            return True
        else:
            return False

    def get_track_id(self, track):
        """
        Get track id for given track. Track id is used to save track info to cache databse.
        :param track: track returned by station_get_next_track, or track of playlist
        :return: String with track id
        """
        return f"{track.id}"

    def download_track(self, track):
        """
        Download track to file and return Tempfile object.
        File will be deleted upon close!
        :param track: track returned by station_get_next_track, or track of playlist
        :return: tempfile object with track data
        """
        file = tempfile.NamedTemporaryFile(mode='w+b', dir=temp_dir, prefix='track', suffix='.mp3')
        try:
            try:
                track.download(file.name)
            except AttributeError:
                debug(f"{self.whoami()}: warning: probably got TrackShort object (normally I need to get a list of full track objects! say to author!), trying to get full Track object.")
                track = track.fetchTrack()
                track.download(file.name)
        except yandex_music.exceptions.UnauthorizedError:
            info(f"Yandex prohibited track download of '{track.title}'")
            return None
        return file

    def calc_bpm_histogram(self, track):
        """
        Calculate BPM histogram for track
        :param track: track returned by station_get_next_track, or track of playlist
        :return: histogram: { bpm1(float): bpm1_share, bpm2(float): bpm2_share }
        """
        file = self.download_track(track)
        if not file:
            return None
        debug(f"{self.whoami()}: got track {self.get_track_id(track)} to {file.name}")
        histogram = calc_file_bpm_histogram(file.name)
        file.close()
        return histogram

    def get_artist(self, artist_id):
        artists = self.client.artists(artist_id)
        if not artists or not len(artists):
            raise ExBpmcrawlGeneric(f"Artist not found for id {artist_id}")
        return artists[0]

    def artist_pager_init(self, artist):
        self.artist_pager_load_page(artist, 0)

    def artist_pager_load_page(self, artist, page_num=0):
        debug(f"loading artist {artist.id}'s tracks page {page_num}")
        self.artist_pager[artist.id] = {'page': page_num, 'idx': 0, 'tracks': []}
        self.artist_pager[artist.id]['tracks'] = artist.get_tracks(self.artist_pager[artist.id]['page'], 50)

    def artist_pager_get_next_track(self, artist):
        try:
            track = self.artist_pager[artist.id]['tracks'][self.artist_pager[artist.id]['idx']]
            self.artist_pager[artist.id]['idx'] += 1
            return track
        except IndexError:
            if self.artist_pager[artist.id]['idx'] == 0:
                return None
            else:
                self.artist_pager_load_page(artist, self.artist_pager[artist.id]['page']+1)
                return self.artist_pager_get_next_track(artist)
