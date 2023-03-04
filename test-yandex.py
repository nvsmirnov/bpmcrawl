import pprint
from music_api import *
import logging

import json
import ast
import datetime

logging.basicConfig(level=logging.DEBUG)
#logging.getLogger("yandex_music").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("sqlitedict").setLevel(logging.ERROR)

pp = pprint.PrettyPrinter(indent=4)

api = get_music_provider("yandexmusic")
api.login()
print(f"Logged in as {api.client.me.account.login}")

# get all playlists
if False:
    playlists = api.client.users_playlists_list()
    for playlist in playlists:
        #pp.pprint(ast.literal_eval(f"{playlist}"))
        print(f"{playlist.title} ({playlist.playlist_id})")

# get tracks of playlists
if False:
    playlists = api.client.users_playlists_list()
    for playlist in playlists:
        pp.pprint(ast.literal_eval(f"{playlist}"))
        print(f"{playlist.title} ({playlist.playlist_id})")
        tracks = playlist.tracks if playlist.tracks else playlist.fetch_tracks()
        for track in tracks:
            #pp.pprint(ast.literal_eval(f"{track}"))
            print(f"Id: {track.track.id}, Title: {track.track.title}, duration: {track.track.duration_ms/1000}s")
            break
        break

# personal blocks
if False:
    PersonalPlaylistBlocks = api.client.landing(blocks=['personalplaylists']).blocks[0]
    for block in PersonalPlaylistBlocks:
        p = block.data.data
        print(f"title: {p.title}, type: {p.generated_playlist_type}, kind: {p.kind}, uid: {p.uid}, ")
        #pp.pprint(ast.literal_eval(f"{block}"))

# get tracks of playlist of the day
if False:
    pers_blocks = api.client.landing(blocks=['personalplaylists']).blocks[0]
    playlist = next(
        x.data.data for x in pers_blocks.entities if x.data.data.generated_playlist_type == 'playlistOfTheDay'
    )
    modifiedDate = datetime.datetime.strptime(playlist.modified, "%Y-%m-%dT%H:%M:%S%z").date()
    print(f"Playlist updated: {modifiedDate}")
    tracks = playlist.tracks if playlist.tracks else playlist.fetch_tracks()
    for track in tracks:
        # pp.pprint(ast.literal_eval(f"{track}"))
        print(f"Id: {track.track.id}, Title: {track.track.title}, duration: {int(track.track.duration_ms / 1000)}s")

# get liked tracks
if False:
    tracks = api.client.users_likes_tracks()
    track_ids = [x.id for x in tracks]
    tracks = api.client.tracks(track_ids)
    for track in tracks:
        #track = track_entry.track if track_entry.track else track_entry.fetchTrack()
        album_id = track.albums[0].id
        pp.pprint(ast.literal_eval(f"{track}"))
        print(f"Id: {track.id}, Title: {track.title}, duration: {int(track.duration_ms / 1000)}s, album_id: {album_id}")
        quit()

# track info by id
if False:
    tracks = api.client.tracks(['10441924'])
    pp.pprint(ast.literal_eval(f"{tracks[0].albums[0].id}"))

# tracks by artist
if True:
    artist = api.client.artists(['41075'])[0]
    pp.pprint(ast.literal_eval(f"{artist}"))
    print(f"artist {artist.id}: {artist.name}")
    api.artist_pager_init(artist)
    for n in range(0,4):
        track = api.artist_pager_get_next_track(artist)
        if not track:
            break
        album_id = track.albums[0].id
        #pp.pprint(ast.literal_eval(f"{track}"))
        print(f"Id: {track.id}, Title: {track.title}, duration: {int(track.duration_ms / 1000)}s, album_id: {album_id}")

