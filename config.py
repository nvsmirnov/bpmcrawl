import os
import json
from sqlitedict import SqliteDict
from whoami import *
from logging import debug, info, warning, error

gmusic_client_id = '3ae9278a98fd8efe'

# key-value database of all track's histograms ever found
tracks_histogram_db = 'data/histograms.db'
temp_dir = 'data/tmp'

cache_db_version = "2"
cache_db_version_recordid = "bpmcrawl_db_version"


def get_cache_version(filename=tracks_histogram_db):
    """Return cache version or None if it is not defined"""
    if not os.path.exists(filename):
        debug(f"{whoami()}: creating new cache database {filename}")
        with SqliteDict(filename, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
            cache[cache_db_version_recordid] = cache_db_version
            return True

    with SqliteDict(filename, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        try:
            cached = cache[cache_db_version_recordid]
        except KeyError:
            debug(f"{whoami()}: failed to load db version from {filename}")
            return None
        return cached
    debug(f"{whoami()}: internal error: should not be here")
    return False


def is_cache_version_ok():
    """Return True if cache version is compatible"""
    db_version = get_cache_version()
    if db_version == cache_db_version:
        debug(f"{whoami()}: db version ok ({cache_db_version})")
        return True
    else:
        debug(f"{whoami()}: db version mismatch (need {cache_db_version}, got {db_version})")
        return False

