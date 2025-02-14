import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Replace 'your_client_id', 'your_client_secret', and 'your_redirect_uri' with your actual Spotify API credentials
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="your client id",
    client_secret="your client secret",
    redirect_uri="http://localhost:8888/callback",
    scope="user-library-read"
))

def get_artist_id(artist_name):
    results = sp.search(q="artist:" + artist_name, type='artist', limit=1)
    items = results['artists']['items']
    if items:
        artist = items[0]
        print(f"Artist Name: {artist['name']}, Artist ID: {artist['id']}")
        return artist['id']
    else:
        print("No artist found.")
        return None

# Example usage
artist_id = get_artist_id("Tool")
