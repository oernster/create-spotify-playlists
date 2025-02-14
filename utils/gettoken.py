import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Fill in your Spotify API credentials
CLIENT_ID = 'your client id'
CLIENT_SECRET = 'your client secret'
REDIRECT_URI = 'http://localhost:8888/callback'

def get_access_token():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-library-read"
    ))
    return sp.auth_manager.get_access_token(as_dict=False)

# Get and print the access token
token = get_access_token()
print("Access Token:", token)
