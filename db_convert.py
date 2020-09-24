#!/usr/bin/env python

import json
import shutil

from sqlitedict import SqliteDict

import atexit
import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *


def get_cached_track(track_id):
    with SqliteDict(tracks_histogram_db, autocommit=True) as cache:
        try:
            cached = json.loads(cache[track_id])
        except KeyError:
            return None
        try:
            return cached["histogram"]
        except KeyError:
            error(f"{whoami()}: internal error loading data from cache for track {track_id}")
            sys.exit(1)


def save_cached_track(track_id, histogram):
    """warning: for now, it will override all data saved for this track"""
    with SqliteDict(tracks_histogram_db, autocommit=True) as cache:
        cache[track_id] = json.dumps({"histogram": histogram})


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(tracks_histogram_db), exist_ok=True)

    db_version = get_cache_version()
    if db_version == cache_db_version:
        info(f"db version is already current ({db_version})")
        sys.exit(0)

    new_db = tracks_histogram_db + ".new"
    def rm_tmp():
        if os.path.exists(new_db):
            os.unlink(new_db)
    atexit.register(rm_tmp)

    if (db_version == None) and (cache_db_version == "2"):
        # migrate from v1 to v2
        # it changes format to json, and moves cached data to "histogram" key of stored dict
        rm_tmp()
        get_cache_version(new_db)  # this will create empty database
        with SqliteDict(tracks_histogram_db, autocommit=True) as old_cache:
            with SqliteDict(new_db, autocommit=True, encode=json.dumps, decode=json.loads) as new_cache:
                for trackid in old_cache:
                    new_cache[trackid] = {"histogram": old_cache[trackid]}
                if len(old_cache)+1 != len(new_cache):
                    error(f"{whoami()}: internal error: len(old_cache)+1 ({len(old_cache)+1}) != len(new_cache) ({len(new_cache)})")
                    sys.exit(1)
                info(f"migrated {len(new_cache)-1} records")
        info(f"replacing file f{tracks_histogram_db} with new version, preserving old to {tracks_histogram_db+'.bak'}")
        shutil.move(tracks_histogram_db, tracks_histogram_db+".bak")
        shutil.move(new_db, tracks_histogram_db)
    elif (db_version == "2") and (cache_db_version == "3"):
        # migrate from v2 to v3
        # it adds music service provider name to cache_id
        #   was: 'some_id': { 'histogram': data }
        #   now: 'provider:some_id': { 'histogram': data }
        #   and only provider known for version 2 is gmusic, so it will be 'gmusic:some_id'
        rm_tmp()
        get_cache_version(new_db)  # this will create empty database
        with SqliteDict(tracks_histogram_db, autocommit=True, encode=json.dumps, decode=json.loads) as old_cache:
            with SqliteDict(new_db, autocommit=True, encode=json.dumps, decode=json.loads) as new_cache:
                for trackid in old_cache:
                    if trackid != cache_db_version_recordid:
                        # db version record already was added when db was created
                        new_cache["gmusic:"+trackid] = old_cache[trackid]
                if len(old_cache) != len(new_cache):
                    error(f"{whoami()}: internal error: len(old_cache)+1 ({len(old_cache)+1}) != len(new_cache) ({len(new_cache)})")
                    sys.exit(1)
                info(f"migrated {len(new_cache)-1} records")
        info(f"replacing file f{tracks_histogram_db} with new version, preserving old to {tracks_histogram_db+'.bak'}")
        shutil.move(tracks_histogram_db, tracks_histogram_db+".bak")
        shutil.move(new_db, tracks_histogram_db)
    else:
        error(f"don't know to migrate db from version {db_version} to {cache_db_version}")
        sys.exit(1)
