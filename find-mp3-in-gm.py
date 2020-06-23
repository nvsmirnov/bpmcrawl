#!/usr/bin/env python

#
# I used this tool once to import tracks to google music
# (to find matches between local mp3s possibly without tags and play music tracks)
#
# run without parameters to see help
#

import sys
import os
import urllib.parse
import tempfile
import requests
import json
import re

import taglib
from gmusicapi.clients import Mobileclient

import logging
from logging import debug, info, warning, error

from exceptions import *
from whoami import *
from config import *
from calc_bpm import *
import hashlib

from sqlitedict import SqliteDict

# if more than this count of songs for one mp3 file found, try to search by hand
results_max = 5

playlist_name = "bpmcrawl-imported"
cache_db = "data/map-local-gm.db"
md5_cache_db = "data/map-local-gm-md5sums.db"

if not cache_db.startswith(os.sep):
    cache_db = os.path.abspath(os.path.dirname(__file__)) + os.sep + cache_db
if not md5_cache_db.startswith(os.sep):
    md5_cache_db = os.path.abspath(os.path.dirname(__file__)) + os.sep + md5_cache_db

api = None

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(2**20), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def cache_get(db, key):
    with SqliteDict(db, autocommit=True) as cache:
        try:
            return json.loads(cache[key])
        except KeyError:
            return None


def cache_save(db, key, value):
    with SqliteDict(db, autocommit=True) as cache:
        cache[key] = json.dumps(value)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("sqlitedict").setLevel(logging.ERROR)

    if len(sys.argv) <= 1:
        print(
            "parameters: -l | dirname [ dirname ... ]"
            "  if dirname given, walk through it and try to make mapping between mp3 file and gmusic tracks"
            "    and save results to local db file"
            "  if -l given, load info from db to gmusic playlist",
            file=sys.stderr
        )
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

    if sys.argv[1] == "-l":
        # load to playlist mode
        playlists = api.get_all_user_playlist_contents()
        # find prevously created playlist with our name
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
        playlists = None

        debug(f"found target playlist")

        # get tracks of playlist
        tracks_in_playlist = {}
        if "tracks" in playlist:
            for track in playlist["tracks"]:
                if "track" in track:  # it is play music's track
                    tracks_in_playlist[track["track"]["storeId"]] = True
        debug(f"{len(tracks_in_playlist)} unique tracks found in playlist")

        with SqliteDict(cache_db, autocommit=True) as cache:
            for entry in [json.loads(cache[x]) for x in cache]:
                for track_id in entry["tracks"]:
                    if track_id in tracks_in_playlist:
                        debug(f"track {track_id} is already in playlist")
                    else:
                        debug(f"adding track {track_id} to playlist")
                        added = api.add_songs_to_playlist(playlist["id"], track_id)
                        if len(added):
                            debug(f"added {len(added)} track(s) to playlist")
                        else:
                            error(f"failed to add track {id} to playlist (no reason given)")

    # load to playlist mode ends
    else:
        # file import mode
        for dirname in sys.argv[1:]:

            os.chdir(dirname)

            for root, dirs, files in os.walk(u"."):
                for orig_filename in files:
                    if not orig_filename.lower().endswith(".mp3"):
                        continue
                    filename = root + os.sep + orig_filename
                    track_md5 = cache_get(md5_cache_db, filename)
                    if not track_md5:
                        track_md5 = md5(filename)
                        cache_save(md5_cache_db, filename, track_md5)

                    track_info = cache_get(cache_db, track_md5)
                    if track_info:
                        debug(f"(from cache) {track_info}")
                    else:
                        mp3 = taglib.File(filename)

                        tags_read = mp3.tags

                        debug(f"read tags: {tags_read}")
                        tags = {}
                        for field in ['ALBUM', 'ARTIST', 'TITLE']:
                            if field in tags_read and len(tags_read[field]):
                                tags[field] = tags_read[field][0]
                                try:
                                    tags[field] = tags[field].encode('windows-1252').decode('windows-1251')
                                except UnicodeEncodeError:
                                    pass
                        debug(f"got info: {tags}")

                        track_info = {"filename": filename}
                        search_terms = []
                        for term in ['ALBUM', 'ARTIST', 'TITLE']:
                            got = False
                            if term in tags and len(tags[term]):
                                search_terms.append(tags[term])

                        do_again = True
                        skip = False
                        while do_again:
                            do_again = False
                            if len(search_terms):
                                # got from tags; trying to use it
                                debug(f"search terms: {search_terms}")
                                search = api.search(' '.join(search_terms))
                            else:
                                error(f"failed to find search terms for {filename}")
                                error(f"trying with path name")
                                tmp_terms = re.split('\./+|/+', filename)
                                search_terms = []
                                for term in tmp_terms:
                                    if not len(term):
                                        continue
                                    m = re.match('^\d+[\s\-_.]+([^\s]+.*)(?:\.mp3?)$', term, re.I)
                                    if m:
                                        term = m.group(1)
                                    search_terms.append(term)
                                debug(f"search terms: {search_terms}")
                                search = api.search(' '.join(search_terms))
                                print(f"found {len(search['song_hits'])} tracks:")
                                for track in search['song_hits']:
                                    print(f"  - id: {track['track']['storeId']}")
                                    print(f"    artist: {track['track']['artist']}")
                                    print(f"    album : {track['track']['album']}")
                                    print(f"    title : {track['track']['title']}")
                            if 'song_hits' not in search or not len(search['song_hits']):
                                do_again = True
                                print(f"failed to find songs for {search_terms} ({' '.join(search_terms)})")
                            elif len(search['song_hits']) > results_max:
                                do_again = True
                                print(f"got too many results for {search_terms} ({' '.join(search_terms)})")
                            if do_again:
                                print(f"{filename}")
                                newsearch = input("Enter terms manually (empty to skip): ")
                                if not len(newsearch):
                                    do_again = False
                                    skip = True
                                else:
                                    search_terms = [newsearch]
                        if skip:
                            continue
                        #debug(search_terms)
                        #debug(f"{search['song_hits']}")
                        #debug(f"{filename} ({len(search['song_hits'])} results)")
                        track_info["tracks"] = [x['track']['storeId'] for x in search['song_hits']]
                        cache_save(cache_db, track_md5, track_info)
                        debug(track_info)
        # file import mode ends

