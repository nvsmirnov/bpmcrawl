import spotipy

from spotipy.oauth2 import SpotifyOAuth

from pprint import pprint

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

# set open_browser=False to prevent Spotipy from attempting to open the default browser
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
print(sp.me())

#results = sp.current_user_playlists(limit=50)
#for i, item in enumerate(results['items']):
#    print("%d %s" % (i, item['name']))
#    #from pprint import pprint
#    #pprint(item)

#response = sp.featured_playlists()
#print(response['message'])

#while response:
#    playlists = response['playlists']
#    for i, item in enumerate(playlists['items']):
#        print(playlists['offset'] + i, item['name'])
#
#    if playlists['next']:
#        response = sp.next(playlists)
#    else:
#        response = None

#pl = sp.playlist("37i9dQZF1E380nDmsOSXst")
#pprint(pl)

print("Getting playlist...")
tracks = []
result = sp.playlist_items("37i9dQZF1DXdbXrPNafg9d", additional_types=['track'])
tracks.extend(result['items'])
# if playlist is larger than 100 songs, continue loading it until end
while result['next']:
    print("Continuing...")
    result = sp.next(result)
    tracks.extend(result['items'])
# remove all local songs
i = 0  # just for counting how many tracks are local
for item in tracks:
    if item['is_local']:
        tracks.remove(item)
        i += 1
# print result
print("Playlist length: " + str(len(tracks)) + "\nExcluding: " + str(i))
print(tracks[0]['track']['id'])
print(tracks[0]['track']['name'])
# TODO: изучить https://github.com/plamere/spotipy/blob/master/examples/audio_analysis_for_track.py
#       посмотреть на тему поиск по BPM
