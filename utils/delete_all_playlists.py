import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Spotify API credentials
SPOTIFY_CLIENT_ID = "YOUR_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "playlist-modify-public playlist-modify-private user-library-read"

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def delete_all_playlists():
    """Delete all playlists from the user's Spotify account, including owned and followed ones."""
    try:
        user_id = sp.me()['id']
        playlists = sp.current_user_playlists()
        
        for playlist in playlists['items']:
            if playlist['owner']['id'] == user_id or playlist['name'].endswith('Recommendations'):
                logging.info(f"🗑 Deleting playlist: {playlist['name']} (ID: {playlist['id']})")
                sp.current_user_unfollow_playlist(playlist['id'])
        
        logging.info("✅ All playlists deleted.")
    except Exception as e:
        logging.error(f"Error deleting playlists: {e}")

if __name__ == "__main__":
    delete_all_playlists()
