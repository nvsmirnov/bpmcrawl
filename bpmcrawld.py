#!/usr/bin/env python

#
# If run without parameters, it will crawl on I'm Feeling Lucky station
# If single parameter given - it will be treated as station URL
# If -p playlist given, playlist will be treated as own playlist name or as shared playlist url (if begins with http...)
#
# TODO: implement mp3 download for spotify and fix MusicProviderSpotify.calc_bpm_histogram
# TODO: implement usage of spotipy's API named "recommendations".
# TODO: implement supplementary DB, store there criterias which to use to find interested tracks (recommendations for genres, playlists to track, etc)
# TODO: when logging "now crawling on playlist ..." - show not only id, but name

import sys
import os
import urllib.parse
import tempfile
import requests
import time
import json
import argparse

from music_api import *

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *

station_url = None
playlist_name = None

api = None

def get_cached_track(music_service, track_id):
    with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        try:
            key = music_service + ":" + track_id
            cached = cache[music_service + ":" + track_id]
        except KeyError:
            return None
        try:
            return cached["histogram"]
        except KeyError:
            error(f"{whoami()}: internal error loading data from cache for track {track_id}")
            sys.exit(1)


def save_cached_track(music_service, track_id, histogram):
    """warning: for now, it will override all data saved for this track"""
    with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        cache[music_service + ":" + track_id] = {"histogram": histogram}


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
    parser.add_argument('-a', '--artist', type=str,
                        help=f'Artist name. If will not find exact artist, will list them')
    parser.add_argument('-A', '--artist-id', type=str,
                        help=f'Artist id.')
    parser.add_argument('-l', '--limit', default=0, type=int,
                        help=f'Process no more than this amount of tracks (useful for testing), 0 for no limit.')
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help=f'Enable debugging output')
    parser.add_argument('-D', '--provider-debug', default=False, action='store_true',
                        help=f'Enable debugging output for music provider library')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        debug("enabled debug")

    provider_logging_level = logging.CRITICAL
    if args.provider_debug:
        provider_logging_level = logging.DEBUG

    music_service = args.service
    station_url = args.station
    playlist_name = args.playlist

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(tracks_histogram_db), exist_ok=True)

    if not is_cache_version_ok():
        print(f"wrong cache version, convert or delete it ({tracks_histogram_db})", file=sys.stderr)
        sys.exit(1)

    api = get_music_provider(music_service, provider_logging_level)
    api.login()

    station = None

    stats = {"processed": 0, "new": 0, "failed": 0}

    mode = None
    if playlist_name:
        mode = 'playlist'
        playlist_tracks = api.get_playlist_tracks(api.get_playlist(playlist_name))
        if playlist_tracks is None:
            info(f"Playlist not found: {playlist_name}")
            sys.exit(1)
        playlist_current_track = 0
        info(f"Now crawling on playlist {playlist_name} ({len(playlist_tracks)} tracks)")
    elif args.artist or args.artist_id:
        mode = 'artist'
        artist_id = None
        if args.artist_id:
            artist_id = args.artist_id
        elif args.artist:
            raise ExBpmCrawlGeneric(f"artist by name is not implemented yet")
        artist = api.get_artist(artist_id)
        if not artist:
            raise ExBpmCrawlGeneric(f"Failed to find artist with id {artist_id}")
        api.artist_pager_init(artist)
    else:
        mode = 'stations'
        # this is what was for google music, there were "stations"
        station = api.get_station_from_url(station_url)
        api.station_prepare(station)
        info(f"Now crawling on station {api.get_station_name(station)}")

    stop = False
    while not stop:
        if mode == 'stations':
            track = api.station_get_next_track()
        elif mode == 'playlist':
            if playlist_current_track < len(playlist_tracks):
                track = playlist_tracks[playlist_current_track]
                playlist_current_track += 1
            else:
                track = None
        elif mode == 'artist':
            track = api.artist_pager_get_next_track(artist)
        else:
            raise ExBpmCrawlGeneric(f"Internal error: unknown mode :'{mode}'")
        if not track:
            stop = True
            break
        track_id = api.get_track_id(track)
        stats["processed"] += 1
        histogram = get_cached_track(music_service, track_id)
        if not histogram:
            histogram = api.calc_bpm_histogram(track)
            if histogram:
                stats["new"] += 1
                save_cached_track(music_service, track_id, histogram)
                info(f"saved histogram for track {track_id}: {histogram}")
            else:
                stats["failed"] += 1
                error(f"Failed to get histogram for {track_id}, skipping")
        else:
            info(f"already have cached histogram for track {track_id}: {histogram}")
        if stats["processed"] >= args.limit:
            info(f"Reached limit of {args.limit} tracks, stopping.")
            stop = True
        time.sleep(0.1)
    info(f"bpmcrawld exiting; stats: {stats}")

