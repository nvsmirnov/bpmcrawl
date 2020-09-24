#!/usr/bin/env python

#
# If run without parameters, it will crawl on I'm Feeling Locky station
# If single parameter given - it will be treated as station URL
# If -p playlist given, playlist will be treated as own playlist name or as shared playlist url (if begins with http...)
#

import sys
import os
import urllib.parse
import tempfile
import requests
import time
import json
import argparse

from music_api import *
#from gmusicapi.clients import Mobileclient

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *

station_url = None
playlist_name = None

api = None

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
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description=f'Get the tracks from playlist, analyze them and add info to cache database ({tracks_histogram_db})',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--service', type=str,
                        required=True, choices=music_service_mapping.keys(),
                        help=f'Specify which music service provider to use')
    parser.add_argument('--station', type=str,
                        default='IFL',
                        help=f'For gmusic: station URL to analyze (special name IFL stands for "I feel lucky" station)')
    parser.add_argument('-p', '--playlist', type=str,
                        help=f'Playlist name or URL. If specified, will override --station')
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help=f'Enable debugging output')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        debug("enabled debug")

    music_service = args.service
    station_url = args.station
    playlist_name = args.playlist

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(tracks_histogram_db), exist_ok=True)

    if not is_cache_version_ok():
        print(f"wrong cache version, convert or delete it ({tracks_histogram_db})", file=sys.stderr)
        sys.exit(1)

    api = get_music_provider(music_service)
    api.login()
    debug("logged in")

    station = None

    stats = {"processed": 0, "new": 0}

    if not playlist_name:
        station = api.get_station_from_url(station_url)
        api.station_prepare()
        info(f"Now crawling on station {api.get_station_name(station)}")
    else:
        ERRR_MODIFY_TO_MULTISERVICE

    stop = False
    while not stop:
        track = api.station_get_next_track()
        if not track:
            stop = True
            break
        track_id = api.get_track_id(track)
        stats["processed"] += 1
        histogram = ERRR_MODIFY_TO_MULTISERVICE get_cached_track(music_service, track_id)
        if not histogram:
            stats["new"] += 1
            file = ERRR_MODIFY_TO_MULTISERVICE download_track(track_id)
            debug(f"got track {track_id} to {file.name}")
            histogram = calc_bpm_histogram(file.name)
            file.close()
            ERRR_MODIFY_TO_MULTISERVICE save_cached_track(music_service, track_id, histogram)
            info(f"saved histogram for track {track_id}: {histogram}")
        else:
            info(f"already have cached histogram for track {track_id}: {histogram}")

    ERRR_MODIFY_TO_MULTISERVICE
#### old code from here
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
### old code
    info(f"bpmcrawld exiting; stats: {stats}")
