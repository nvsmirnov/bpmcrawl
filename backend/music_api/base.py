from backend.music_api import music_service_mapping
from backend.exceptions import *
from backend.log import *
from backend.whoami import *


#def get_music_provider(music_service, provider_logging_level=CRITICAL):
#    if music_service not in music_service_mapping:
#        raise ExBpmcrawlGeneric(f"Unknown music service provider: '{music_service}'")
#    return music_service_mapping[music_service](music_service, provider_logging_level)


class MusicproviderBase(WhoamiObject):
    music_service = None
    provider_logging_level = None

    @classmethod
    def create(cls, music_service, music_service_config, provider_logging_level=CRITICAL):
        """
        Create music provider object of specified type.
        music_service_config may contain all services dict (then dict member for certain service will be used for it)
        or it may contain music service's config only.
        Do not use keys identical to services id in per-service configs.
        :param music_service: id of music service
        :param music_service_config: user's config of music service.
        :param provider_logging_level: log level for provider, default is CRITICAL
        :return: object of appropriate Musicprovider* class
        """
        msc = None
        if music_service in music_service_config:
            msc = music_service_config[music_service]
        else:
            msc = music_service_config
        return music_service_mapping[music_service](music_service, msc, provider_logging_level)

    def __str__(self):
        return self.__repr__()
    
    def __repr__(self):
        return f"{self.__class__.__name__}(music_service={self.music_service})"

    def __init__(self, music_service, music_service_config, provider_logging_level=CRITICAL):
        if self.music_service != music_service:
            raise ExBpmcrawlGeneric(f"Internal error: tried to init {self.__class__.__name__} with wrong service provider '{self.music_service}'")
        self.set_provider_logging_level(provider_logging_level)

    def set_provider_logging_level(self, provider_logging_level):
        self.provider_logging_level = provider_logging_level

    def login(self):
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_playlist(self, playlist_id_uri_name):
        """
        Get existing playlist by name (or id or uri if supported by specific provider's child class)
        :param playlist_id_uri_name: playlist id, uri or name
        :return: playlist
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_playlist_id(self, playlist):
        """
        Get id string of playlist
        :param playlist: playlist object
        :return: playlist id string
        """
        return playlist["id"]

    def get_or_create_my_playlist(self, playlist_name):
        """
        Get existing playlist, or create user's playlist if it does not exist.
        :param playlist_name: Name of playlist (or, if supported by specific provider's API, uri or id of it)
        :return: playlist
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_playlist_tracks(self, playlist):
        """
        Get all tracks of playlist
        :param playlist: playlist returned by get_or_create_my_playlist()
        :return: list of tracks
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def add_track_to_playlist(self, playlist, track_id):
        """
        Add track to existing playlist
        :param playlist: playlist returned by get_or_create_playlist()
        :return: True if added, false if not
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_station_from_url(self, url):
        """
        Get station object (in format of provider) from station name/URL
        :param url: name or url of radio station got from user
        :return: radio station id
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_station_name(self, station):
        """
        Get station name (probably human readable)
        :param station: station returned by get_station_from_url
        :return: Station name
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def station_prepare(self, station):
        """
        Prepare station for playback (i.e., clear 'recently played' cache to start with first track)
        It may be ok to do nothing for some of providers.
        For now it is guaranteed to work only for one station at a time.
        :param station: station returned by get_station_from_url
        :return: Nothing
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def station_get_next_track(self, station):
        """
        Get next track from station, exclude already seen tracks.
        For now it is guaranteed to work only for one station at a time.
        :param station: station returned by get_station_from_url
        :return: None if there is no unseen tracks to play
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_track_id(self, track):
        """
        Get track id for given track. Track id is used to save track info to cache databse.
        :param track: track returned by station_get_next_track, or track of playlist
        :return: String with track id
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def download_track(self, track):
        """
        Download track to file and return Tempfile object.
        File will be deleted upon close!
        :param track: track returned by station_get_next_track, or track of playlist
        :return: tempfile object with track data
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def calc_bpm_histogram(self, track):
        """
        Calculate BPM histogram for track
        :param track: track returned by station_get_next_track, or track of playlist
        :return: histogram: { bpm1(float): bpm1_share, bpm2(float): bpm2_share }
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def get_artist(self, artist_id):
        """
        Get artist object for given artist id
        :param artist_id: artist id
        :return: artist object
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def artist_pager_init(self, artist):
        """
        Init tracks pager for artist
        :param artist: artist object
        :return: Nothing
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def artist_pager_load_page(self, artist, page_num=0):
        """
        Get page of tracks for artist
        :param artist: artist object
        :param page_num: page number (default 0)
        :return: Nothing
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")

    def artist_pager_get_next_track(self, artist):
        """
        Get next track for previously initialized pager for artist.
        :param artist: artist object
        :return: Track object or None if end of list reached
        """
        raise ExBpmcrawlGeneric(f"Internal error: Method {self.whoami()} is not implemented")
