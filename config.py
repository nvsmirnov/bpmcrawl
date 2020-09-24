import os
import json
import re
from sqlitedict import SqliteDict
from exceptions import *
from whoami import *
from logging import debug, info, warning, error

gmusic_client_id = '3ae9278a98fd8efe'

# key-value database of all track's histograms ever found
tracks_histogram_db = 'data/histograms.db'
temp_dir = 'data/tmp'

cache_db_version = "3"
cache_db_version_recordid = "bpmcrawl_db_version"
cache_db_regexp_cache_id = '^([^:]+):(.+)$'

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


def get_track_provider_from_cache_id(cache_id):
    m = re.match(cache_db_regexp_cache_id, cache_id)
    if m:
        provider = m.group(1)
        return provider
    else:
        raise ExBpmCrawlGeneric(f"Bad cache record found, can't extract service provider from cache id '{cache_id}'")


def get_track_id_from_cache_id(cache_id):
    m = re.match(cache_db_regexp_cache_id, cache_id)
    if m:
        track_id = m.group(2)
        return track_id
    else:
        raise ExBpmCrawlGeneric(f"Bad cache record found, can't extract track id from cache id '{cache_id}'")
