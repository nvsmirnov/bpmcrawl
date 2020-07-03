#!/usr/bin/env python

import sys
import os
import urllib.parse
import tempfile
import requests
import re
import argparse

from gmusicapi.clients import Mobileclient

from sqlitedict import SqliteDict

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *

playlist_name = "bpmcrawl"

api = None

def get_scaled_good_bpm(bpm, good_bpm):
    """
    Вернёт значение bpm, приведённое с учётом множителя, если bpm попадает в good_bpm (формат см. в get_good_bpms)
    None если не попало
    """
    bpm = float(bpm)
    for mult in good_bpm["mult"]:
        if bpm >= mult*good_bpm["min"] and bpm <= mult*good_bpm["max"]:
            return bpm/mult
    return None

def get_avg_bpm(histogram: dict):
    """Вернёт средний bpm из histogram с учётом доли каждого значения
    histogram должен содержать приведённые значения (т.е. должен быть результатом выполнения get_good_bpms)"""
    sum = 0
    sum_shares = 0
    for bpm in histogram:
        sum += bpm * histogram[bpm]
        sum_shares += histogram[bpm]
    return sum/sum_shares


def get_good_bpms(histogram: dict, good_bpm, min_share=0.85):
    """
    Если доля "хороших" bpm >= min_share, то вернёт dict:
        {bpm1: share1, bpm2: share2}
        Результат будет состоять только из "хороших" bpm, он будет отсортирован по убыванию share
        bpm будут приведены с учётом мультипликатора из good_bpm
        Вернёт None, если гистограмма не даёт уверенного результата или доля "хороших" bpm < min_share
    "хороший" bpm - такой, который попадает в интервал good_bpm
    Параметры:
        histogram: {bpm1: share1, bpm2: share2, ...}
        good_bpm: {"min": bpm_min, "max": bpm_max, "mult": [multiplier1, m2, ...]}, напр., для 180+-4 (90+-2) это {176,184, [1, 0.5]}
        min_share: минимальная суммарная доля всех подходящих bpm
    """
    sum_good_share = 0
    good_bpms = {}
    # you may not need to do this, it's only for clear debug printing
    histogram = OrderedDict(sorted(histogram.items(), key=lambda k: k[1], reverse=True))
    for bpm in histogram:
        bpm_scaled = get_scaled_good_bpm(bpm,good_bpm)
        if bpm_scaled:
            sum_good_share += histogram[bpm]
            if bpm_scaled not in good_bpms:
                good_bpms[bpm_scaled] = 0
            good_bpms[bpm_scaled] += histogram[bpm]

    good_bpms = OrderedDict(sorted(good_bpms.items(), key=lambda k: k[1], reverse=True))
    #debug(f"{whoami()}: orig={histogram}")
    #debug(f"{whoami()}: good={good_bpms}")
    if sum_good_share < min_share:
        debug(f"{whoami()}: returning None")
        return None

    debug(f"{whoami()}: returning {good_bpms}")
    return good_bpms


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description=f'Pick tracks from cache created by bpmcrawld (file {tracks_histogram_db}) and load them to Google Music playlist',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--playlist', default=playlist_name, type=str,
                        help=f'Playlist name to add tracks to, will be created if does not exists')
    parser.add_argument('-b', '--bpm', default='176-184', type=str,
                        help=f'BPM range (with any of multipliers applied also)')
    parser.add_argument('-m', '--mult', default=[1, 0.5], nargs='+', type=float,
                        help=f'Multipliers to BPM range. I.e., if range is 176-180 and multipliers are [1, 0.5], then good BPM ranges are 176-184 and 88-92')
    parser.add_argument('-r', '--reload', default=False, action='store_true',
                        help=
                        f'Do not rely on locally cached info about whether track was already added to playlist or not.\n'
                        f'Without this option, you may remove tracks from playlist manually and they will not be re-added')
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help=f'Enable debugging output')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        debug("enabled debug")

    playlist_name = args.playlist

    m = re.match('^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$', args.bpm)
    if not m:
        error(f'Wrong format for BPM range ({args.bpm}), will accept this form: 176-184')
        sys.exit(1)
    accept_bpm = {"min": float(m.group(1)), "max": float(m.group(2)), "mult": args.mult}

    debug(f"playlist_name = '{playlist_name}'")
    debug(f"accept_bpm    = {accept_bpm}")
    debug(f"reload        = {args.reload}")

    if not is_cache_version_ok():
        print(f"wrong cache version, convert or delete it ({tracks_histogram_db})", file=sys.stderr)
        sys.exit(1)

    # log in to google music suppressing it's debugging messages
    oldloglevel = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    api = Mobileclient(debug_logging=False)
    logging.getLogger("gmusicapi.Mobileclient1").setLevel(logging.WARNING)
    if not api.oauth_login(gmusic_client_id):
        print(f"Please login to Google Music first (run gmusic-login.py)")
        sys.exit(1)
    logging.getLogger().setLevel(oldloglevel)
    debug("logged in")

    # find prevously created playlist with our name
    playlists = api.get_all_user_playlist_contents()
    playlist = None
    for pl in playlists:
        if pl["name"] == playlist_name:
            playlist = pl
            break
    # playlist not found, create it
    if not playlist:
        debug(f"playlist {playlist_name} not found, creating it...")
        id = api.create_playlist(playlist_name)
        debug(f"created playlist, id {id}")
        playlists = api.get_all_playlists()
        for pl in playlists:
            if pl["id"] == id:
                playlist = pl
                break
    if not playlist:
        error(f"Internal error: failed to find or create playlist {playlist_name}")
        sys.exit(1)
    playlists = None  # probably this will free some memory

    debug(f"found target playlist")

    # get tracks of playlist
    tracks_in_playlist = {}
    if "tracks" in playlist:
        for track in playlist["tracks"]:
            if "track" in track:  # it is play music's track
                tracks_in_playlist[track["track"]["storeId"]] = True

    stats = {"tracks_before": len(tracks_in_playlist), "tracks_added": 0, "failures": 0}

    logging.getLogger().setLevel(logging.INFO)
    with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        for track_id in cache:
            if track_id == cache_db_version_recordid:
                continue
            cached = cache[track_id]
            good_bpms = get_good_bpms(cached["histogram"], accept_bpm)
            if good_bpms:
                if not args.reload and "in_playlists" in cached and playlist["id"] in cached["in_playlists"]:
                    # cache says that we already added this track, and no -r option given
                    debug(f"track {track_id} was added to playlist earlier (got this from cache)")
                else:
                    if track_id in tracks_in_playlist:
                        if "in_playlists" not in cached:
                            cached["in_playlists"] = []
                        if playlist["id"] not in cached["in_playlists"]:
                            cached["in_playlists"].append(playlist["id"])
                        cache[track_id] = cached
                        debug(f"track {track_id} is already in playlist")
                    else:
                        info(f"adding track {track_id} to playlist (avg={round(get_avg_bpm(good_bpms),2)}, {good_bpms})")
                        added = api.add_songs_to_playlist(playlist["id"], track_id)
                        if len(added):
                            if "in_playlists" not in cached:
                                cached["in_playlists"] = []
                            if playlist["id"] not in cached["in_playlists"]:
                                cached["in_playlists"].append(playlist["id"])
                            cache[track_id] = cached
                            stats["tracks_added"] += 1
                            info(f"added track {track_id} to playlist {playlist_name}")
                        else:
                            stats["failures"] += 1
                            error(f"failed to add track {id} to playlist (no reason given)")
    info(f"bpmcrawl-pick exiting; stats: {stats}")
