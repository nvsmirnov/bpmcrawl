import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
from music_api import *
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("sqlitedict").setLevel(logging.ERROR)

# Set these environment variables:
# SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
#   obtain them on https://developer.spotify.com/dashboard/ by creating application; don't copy them to code.
# SPOTIPY_REDIRECT_URI=http://localhost
#   this is stub only, it should:
#     1) point to page that will not really open (or, you'll need to fully implement process);
#     2) should match redirect uri that you set in app's settings - so copy it there.
# Then, if requested to proceed in browser, accept request, and you'll be redirected to given redirect URI.
# URI will fail to open, bu you'll need to copy URI from browser address bar to script's input. And that's it.
# P.S. don't know yet where it caches authorization token and how to clear it.

## set open_browser=False to prevent Spotipy from attempting to open the default browser
#spotify_scopes = [
#    "playlist-read-collaborative",
#    "playlist-read-private",
#    "playlist-modify-public",
#    "playlist-modify-private",
#    "user-library-read",
#    "user-library-modify",
#    "user-top-read",
#    "user-follow-read",
#    "user-read-recently-played"
#]
#sp = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False, scope=" ".join(spotify_scopes)))
#print(sp.me())
#
#results = sp.current_user_playlists(limit=50)
###results = sp.next(results)
#for i, item in enumerate(results['items']):
#    print(f"{i}, {item['id']}, {item['name']}")
#
#response = sp.featured_playlists()
#print(response['message'])
#while response:
#    playlists = response['playlists']
#    for i, item in enumerate(playlists['items']):
#        print(f"{playlists['offset'] + i}, {item['id']}, {item['name']}")
#    if playlists['next']:
#        response = sp.next(playlists)
#    else:
#        response = None

#pl = sp.playlist("37i9dQZF1E380nDmsOSXst")
#pprint(pl)

# print("Getting playlist...")
# tracks = []
# result = sp.playlist("37i9dQZF1DXdbXrPNafg9d", fields=['id', 'name', 'uri'])
# print(f"Playlist {result}")
# result = sp.playlist_items("37i9dQZF1DXdbXrPNafg9d", additional_types=['track'])
# tracks.extend(result['items'])
# # if playlist is larger than 100 songs, continue loading it until end
# while result['next']:
#     print("Continuing...")
#     result = sp.next(result)
#     tracks.extend(result['items'])
# # remove all local songs
# i = 0  # just for counting how many tracks are local
# for item in tracks:
#     if item['is_local']:
#         tracks.remove(item)
#         i += 1
# # print result
# print("Playlist length: " + str(len(tracks)) + "\nExcluding: " + str(i))
# print(tracks[0]['track']['id'])
# print(tracks[0]['track']['name'])
# #analysis = sp.audio_analysis(tracks[0]['track']['id'])
# #pprint(analysis['sections'])
# #features = sp.audio_features([tracks[0]['track']['id']])
# #pprint(features)

api = get_music_provider("spotify")
api.login()
#print(api.calc_bpm_histogram(tracks[0]))
#pprint(api.get_or_create_playlist("37i9dQZF1DXdbXrPNafg9d"))
#pprint(api.get_or_create_my_playlist("bpmcrawl.180- - Google Play Музыка"))
#pprint(api.get_playlist_tracks(api.get_or_create_my_playlist("test")))
#pprint(api.add_track_to_playlist(api.get_or_create_my_playlist("test"), "2QvA4PTJzMYRBQeOVXLxhi"))
pprint(api.get_or_create_my_playlist("test2"))
