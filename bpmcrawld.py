import sys
import urllib.parse
import tempfile
import requests
import json

from gmusicapi.clients import Mobileclient

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *

# key-value database of all track's histograms ever found
tracks_histogram_db = 'data/histograms.db'

station_url = "https://play.google.com/music/r/m/Lw4jnysfpqteg7q7ojholkx2gbu?t=20__-"
playlist_url = "https://play.google.com/music/playlist/AMaBXyn-DcjON9b8u733BIoH1YLmRPJj13LHih-wzmTbslByRRVpAGT8Jph1nq2Y2Wxmw7hW8ZAp0wggan4jHYit5Le2jWstoQ%3D%3D"

api = None

def get_station_from_url(url):
    station_id_str = urllib.parse.unquote(url).rsplit("/", 1)[-1].split("?", 1)[0].split('#', 1)[0]
    stations = api.get_all_stations()
    for station in stations:
        if 'seed' in station and 'curatedStationId' in station['seed']:
            if station['seed']['curatedStationId'] == station_id_str:
                debug(f"{whoami()}: found station {station['id']}")
                return station
    raise ExBpmCrawlGeneric(f"Failed to find station by string {station_id_str} (from url {url})")


def get_cached_track(track_id):
    with SqliteDict(tracks_histogram_db, autocommit=True) as cache:
        try:
            return cache[track_id]
        except KeyError:
            return None


def save_cached_track(track_id, histogram):
    with SqliteDict(tracks_histogram_db, autocommit=True) as cache:
        cache[track_id] = histogram


def download_track(track_id):
    """Returns tempfile object (it will be deleted upon close!)"""
    file = tempfile.NamedTemporaryFile(mode='w+b', dir='data/tmp', prefix='track', suffix='.mp3')
    stream_url = api.get_stream_url(track_id, quality='low')
    with requests.get(stream_url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            # if chunk:
            file.write(chunk)
    file.flush()
    return file


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    oldloglevel = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    api = Mobileclient(debug_logging=False)
    logging.getLogger("gmusicapi.Mobileclient1").setLevel(logging.WARNING)
    if not api.oauth_login(gmusic_client_id):
        print(f"Please login to Google Music first (run gmusic-login.py)")
        sys.exit(1)
    logging.getLogger().setLevel(oldloglevel)
    debug("logged in")

    station = get_station_from_url(station_url)
    info(f"Now crawling on station {station['name']}")
    tracks_cache = []
    tracks = ["first_stub"]
    while len(tracks):
        tracks = api.get_station_tracks(station['id'], num_tracks=25, recently_played_ids=tracks_cache)
        found_new = False
        for track in tracks:
            track_id = track['storeId']
            if track_id not in tracks_cache:
                histogram = get_cached_track(track_id)
                if not histogram:
                    found_new = True
                    file = download_track(track_id)
                    debug(f"got track {track_id} to {file.name}")
                    tracks_cache.append(track_id)
                    histogram = calc_bpm_histogram(file.name)
                    file.close()
                    save_cached_track(track_id, histogram)
                    info(f"saved histogram for track {track_id}: {histogram}")
                    sys.exit(0)
                else:
                    info(f"already have cached histogram for track {track_id}: {histogram}")
                    sys.exit(0)
        if not found_new:
            debug(f"Probably we've seen all tracks now")
            sys.exit(0)
        debug(f"seen {len(tracks_cache)} tracks up to time")
