
__all__ = [
    "music_service_mapping",
    "MusicProviderGoogle",
    "MusicProviderSpotify",
    "MusicproviderYandexMusic",
]

from .provider_google import MusicProviderGoogle
from .provider_spotify import MusicProviderSpotify
from .provider_yandex import MusicproviderYandexMusic

music_service_mapping = {
    'gmusic': MusicProviderGoogle,
    'spotify': MusicProviderSpotify,
    'yandexmusic': MusicproviderYandexMusic,
}
