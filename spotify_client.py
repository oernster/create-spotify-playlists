import io
import os
import sys
import time
import logging
import random
import requests
import spotipy
from spotipy import SpotifyOAuth
import musicbrainzngs
from fuzzywuzzy import process, fuzz
from colorama import Fore, init, Style
from brainz import MusicBrainzClient
from logging_utils import log_spotify_search, log_attempting_match


# Function to log errors to errors.txt instead of console
def log_error(message):
    with open("errors.txt", "a") as f:
        f.write(message + "\n")


class SpotifyPlaylistManager:
    def __init__(self):
        logging.info(Fore.YELLOW + "Initializing Spotify Authentication..." + Style.RESET_ALL)

        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id="YOUR_CLIENT_ID",
                client_secret="YOUR_CLIENT_SECRET",
                redirect_uri="http://localhost:8888/callback",
                scope="playlist-modify-public playlist-modify-private user-library-read"
            ))
            logging.info(Fore.GREEN + "Spotify Authentication Successful!" + Style.RESET_ALL)

            # Verify that authentication works
            current_user = self.sp.current_user()
            logging.info(Fore.LIGHTBLUE_EX + f"Logged in as: {current_user['display_name']}" + Style.RESET_ALL)

        except Exception as e:
            logging.error(Fore.RED + f"Spotify Authentication Failed: {e}" + Style.RESET_ALL)
        self.failed_spotify_requests = []  # Track failed requests

    def fetch_spotify_artist_id(self, artist_name):
        """Fetch Spotify artist ID with rate limiting and error handling."""
        logging.debug(f"Entering fetch_spotify_artist_id() for: {artist_name}")  # Removed 🔍 emoji

        retries = 0
        while retries < 5:
            try:
                logging.debug(f"Calling Spotify API for: {artist_name}")  # Removed 🎵 emoji

                time.sleep(0.3)  # Ensure requests are at least 0.3 seconds apart
                results = self.sp.search(q=artist_name, type='artist', limit=1)

                if results['artists']['items']:
                    artist_id = results['artists']['items'][0]['id']
                    log_spotify_search(artist_name, artist_id)
                    return artist_id
                else:
                    log_spotify_search(artist_name, None)
                    return None
            except Exception as e:
                logging.error(Fore.RED + f"Error fetching Spotify artist ID for {artist_name}: {e}" + Style.RESET_ALL)
                retries += 1
                time.sleep(6 * (2 ** (retries - 1)))  # Exponential backoff

        logging.error(Fore.RED + f"Failed to retrieve Spotify artist ID for '{artist_name}' after {retries} attempts." + Style.RESET_ALL)
        return None

    def fetch_top_tracks(self, artist_id, country="UK"):
        """Fetch top tracks for the given artist from Spotify."""
        try:
            # Use the artist's Spotify ID to fetch top tracks
            tracks = self.sp.artist_top_tracks(artist_id, country=country)
            track_ids = [track['id'] for track in tracks['tracks']]
            logging.debug(f"Found {len(track_ids)} top tracks for artist ID: {artist_id}")
            return track_ids
        except Exception as e:
            logging.error(f"Error fetching top tracks for artist {artist_id}: {e}")
            return []

    def create_playlist(self, playlist_name, track_ids):
        """Create a new playlist and add the provided tracks in random order."""
        try:
            # Create a new playlist on the authenticated user's account
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(user_id, playlist_name, public=True)
            playlist_id = playlist['id']

            # Add tracks to the playlist in batches
            batch_size = 100
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                self.sp.user_playlist_add_tracks(user_id, playlist_id, batch)
                logging.info(f"Added {len(batch)} tracks to playlist '{playlist_name}'.")

            logging.info(Fore.GREEN + f"Playlist '{playlist_name}' created successfully with shuffled tracks!" + Style.RESET_ALL)

        except Exception as e:
            logging.error(Fore.RED + f"Error creating playlist: {e}" + Style.RESET_ALL)
