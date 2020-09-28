#!/usr/bin/env python

import json
from datetime import datetime
from sqlitedict import SqliteDict
import spotipy
from spotipy.oauth2 import SpotifyOAuth

spotify_scopes = [
    "playlist-read-collaborative",
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-library-read",
    "user-library-modify",
    "user-top-read",
    "user-follow-read",
    "user-read-recently-played"
]
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False, scope=" ".join(spotify_scopes)))

cache_path = "data/spotify-chtracker.db"

track_playlists = [
    "1vKJ87bMCWpFB0F44QLPG5",  # test
    "37i9dQZEVXbtKGfqAm3gL8",  # радар новинок
    "37i9dQZF1E380nDmsOSXst",  # day mix 1
    "37i9dQZF1E35BzEB401FN4",  # day mix 2
    "37i9dQZF1E37rBAZW86maL",  # day mix 3
    "37i9dQZF1E35ne6X1r4JyH",  # day mix 4
    "37i9dQZF1E364ZpwzX1gQ9",  # day mix 5
    "37i9dQZF1E35nNfmzUm8kY",  # day mix 6
    "37i9dQZEVXcNY7wbLgIBOw",  # мои открытия недели
    "37i9dQZF1Egp4maXQCFx1A",  # family mix
    "37i9dQZF1DX8z1UW9HQvSq",  # Инди-сквот
    "37i9dQZF1DXdbXrPNafg9d",  # All New Indie
    "37i9dQZF1DX2sUQwD7tbmL",  # Feel Good Indie
]

def get_playlist_track_ids(playlist):
    """Get list of ids of non-local track in playlist"""
    tracks = []
    result = sp.playlist_items(playlist, additional_types=['track'])
    tracks.extend(result['items'])
    # if playlist is larger than 100 songs, continue loading it until end
    while result['next']:
        result = sp.next(result)
        tracks.extend(result['items'])
    track_ids = []
    for item in tracks:
        if not item['is_local']:
            track_ids.append(item['track']['id'])
    return track_ids

if __name__ == '__main__':
    with SqliteDict(cache_path, autocommit=True, encode=json.dumps, decode=json.loads) as cache:
        for playlist in track_playlists:
            playlist_name = None
            try:
                playlist_name = sp.playlist(playlist, fields=["name"])["name"]
            except Exception as e:
                print(f"failed to get playlist info for {playlist}, but proceeding anyway. The error was: {e}")
            print(f"Tracking playlist {playlist} ({playlist_name})")
            try:
                cached = cache[playlist]
            except KeyError:
                cached = {"tracks_seen_anytime": [], "tracks_last": [], "changelog": []}
            try:
                tracks_current = get_playlist_track_ids(playlist)
            except Exception as e:
                print(f"failed to get playlist {playlist}: {e}")
            tracks_added = list(set(tracks_current) - set(cached["tracks_last"]))
            tracks_removed = list(set(cached["tracks_last"]) - set(tracks_current))
            if len(tracks_added) or len(tracks_removed):
                tracks_new = list(set(tracks_current) - set(cached["tracks_seen_anytime"]))
                print(f"playlist {playlist} changed: {len(tracks_added)} added, {len(tracks_removed)} removed, {len(tracks_new)} never been here")
                cached["tracks_seen_anytime"].extend(tracks_new)
                cached["tracks_last"] = tracks_current
                cached["changelog"].append(
                    {
                        "date": str(datetime.now()),
                        "added": len(tracks_added),
                        "removed": len(tracks_removed),
                        "unseen": len(tracks_new)
                    }
                )
                cache[playlist] = cached
