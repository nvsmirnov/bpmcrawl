#!/usr/bin/env python

#
# If run without parameters, it will crawl on I'm Feeling Locky station
# If single parameter given - it will be treated as station URL
# If -p playlist given, playlist will be treated as own playlist name or as shared playlist url (if begins with http...)
#

# TODO: изменить хранение в db на json - чтобы можно было глазами в БД копаться при желании

import sys
import os
import urllib.parse
import tempfile
import requests
import time
import json

from gmusicapi.clients import Mobileclient

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *

station_url = "IFL"
playlist_name = None

api = None

def get_station_from_url(url):
    if url == "IFL":
        return {"id": "IFL", "name": "I'm Feeling Lucky"}
    station_id_str = urllib.parse.unquote(url).rsplit("/", 1)[-1].split("?", 1)[0].split('#', 1)[0]
    stations = api.get_all_stations()
    for station in stations:
        if 'seed' in station and 'curatedStationId' in station['seed']:
            if station['seed']['curatedStationId'] == station_id_str:
                debug(f"{whoami()}: found station {station['id']}")
                return station
    raise ExBpmCrawlGeneric(f"Failed to find station by string '{station_id_str}' (from url '{url}')")


def get_playlist_tracks_from_url(url):
    if url.lower().startswith('http'):
        # this is playlist url
        error(f"playlist by URL is not implemented yet")
        sys.exit(1)
    else:
        # this is local playlist name
        playlists = api.get_all_user_playlist_contents()
        # find prevously created playlist with our name
        playlist = None
        for pl in playlists:
            if pl["name"] == playlist_name:
                playlist = pl
                break
        tracks_in_playlist = {}
        tracks = []
        if "tracks" in playlist:
            for track in playlist["tracks"]:
                if "track" in track:  # it is play music's track
                    if track["track"]["storeId"] not in tracks_in_playlist:
                        tracks.append(track["track"])
                        tracks_in_playlist[track["track"]["storeId"]] = True
        return tracks


def get_cached_track(track_id):
    with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        try:
            cached = cache[track_id]
        except KeyError:
            return None
        try:
            return cached["histogram"]
        except KeyError:
            error(f"{whoami()}: internal error loading data from cache for track {track_id}")
            sys.exit(1)


def save_cached_track(track_id, histogram):
    """warning: for now, it will override all data saved for this track"""
    with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        cache[track_id] = {"histogram": histogram}


def download_track(track_id):
    """Returns tempfile object (it will be deleted upon close!)"""
    file = tempfile.NamedTemporaryFile(mode='w+b', dir=temp_dir, prefix='track', suffix='.mp3')
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

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(tracks_histogram_db), exist_ok=True)

    # oh, I know 'bout argparse, but... :-)
    if len(sys.argv) > 1:
        if len(sys.argv) == 2:
            station_url = sys.argv[1]
            info(f"using station url: {station_url}")
        elif sys.argv[1] == '-p':
            playlist_name = sys.argv[2]
            info(f"using playlist: {playlist_name}")
        else:
            error(f"parameters: station_url | -p playlist_name_or_shared_playlist_url")
            sys.exit(1)

    if not is_cache_version_ok():
        print(f"wrong cache version, convert or delete it ({tracks_histogram_db})", file=sys.stderr)
        sys.exit(1)

    oldloglevel = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    api = Mobileclient(debug_logging=False)
    logging.getLogger("gmusicapi.Mobileclient1").setLevel(logging.WARNING)
    if not api.oauth_login(gmusic_client_id):
        print(f"Please login to Google Music first (run gmusic-login.py)")
        sys.exit(1)
    logging.getLogger().setLevel(oldloglevel)
    debug("logged in")

    station = None

    stats = {"processed": 0, "new": 0}

    if not playlist_name:
        station = get_station_from_url(station_url)
        info(f"Now crawling on station {station['name']}")
    tracks_cache = []  # tracks for "recently played" list
    tracks = ["first_stub"]
    while len(tracks):
        if station:
            tracks = api.get_station_tracks(station['id'], num_tracks=25, recently_played_ids=tracks_cache)
        else:
            tracks = get_playlist_tracks_from_url(playlist_name)
            info(f"Got {len(tracks)} track(s) from {playlist_name}")
        found_new = False
        for track in tracks:
            track_id = track['storeId']
            if track_id not in tracks_cache:
                stats["processed"] += 1
                histogram = get_cached_track(track_id)
                if not histogram:
                    found_new = True
                    stats["new"] += 1
                    file = download_track(track_id)
                    debug(f"got track {track_id} to {file.name}")
                    tracks_cache.append(track_id)
                    histogram = calc_bpm_histogram(file.name)
                    file.close()
                    save_cached_track(track_id, histogram)
                    info(f"saved histogram for track {track_id}: {histogram}")
                else:
                    info(f"already have cached histogram for track {track_id}: {histogram}")
        if not station:
            break
        if not found_new:
            debug(f"Probably we've seen all tracks now ({len(tracks_cache)}), exiting")
            break
        debug(f"seen {len(tracks_cache)} tracks up to time")
        time.sleep(1)
    info(f"bpmcrawld exiting; stats: {stats}")
