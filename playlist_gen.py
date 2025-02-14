import os
import sys
import re
import logging
import random
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import musicbrainzngs
from spotify_client import SpotifyPlaylistManager
from brainz import MusicBrainzClient, FLACArtistFetcher
from colorama import Fore, Back, init, Style
import inflect
from fuzzywuzzy import fuzz, process
from logging_utils import log_spotify_search


FLAC_DIRECTORY = "L:\\Storage\\FLACMusic"
p = inflect.engine()

# Initialize colorama for Windows PowerShell
init(autoreset=True)

# Set up logging with UTF-8 support and avoid encoding issues
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs print correctly on Windows
    ]
)


class ArtistProcessor:
    def __init__(self, flac_directory):
        self.flac_directory = flac_directory
        self.number_to_text = {
            1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
            11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
            15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
            19: 'nineteen', 20: 'twenty', 30: 'thirty', 40: 'forty',
            50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety'
        }
        self.text_to_number = {v: k for k, v in self.number_to_text.items()}

    def clean_artist_name(self, artist_name):
        """Normalize artist names for better MusicBrainz matching."""
        if not artist_name:
            return "Unknown Artist"
        
        # Normalize spaces and remove unwanted characters
        cleaned_name = artist_name.replace(",", " ")  # Normalize commas
        cleaned_name = cleaned_name.replace("/", "_")  # Convert slashes to underscores for matching
        cleaned_name = cleaned_name.replace("&", "and")  # Convert '&' to 'and'

        words = cleaned_name.split()
        
        # Handle numeric words
        if words[0].isdigit():
            number = int(words[0])
            if number in self.number_to_text:
                words[0] = self.number_to_text[number]
        elif words[0].lower() in self.text_to_number:
            words[0] = str(self.text_to_number[words[0].lower()])
        
        return " ".join(words)

    def normalize_artist_name(self, artist_name):
        """Generate alternate spellings for fuzzy matching."""
        if not artist_name:
            return {"Unknown Artist"}  # Ensures it always returns a set

        alternate_names = set()

        # Add the original artist name (standard case)
        alternate_names.add(artist_name)

        # Clean up using the `clean_artist_name` function
        cleaned_name = self.clean_artist_name(artist_name)
        alternate_names.add(cleaned_name.lower())  # Normalize to lowercase for fuzzy matching

        # Generate alternate variations (handling special characters like slashes)
        cleaned_name_for_matching = re.sub(r'[\s,!.?]', '', cleaned_name).lower()  # Remove common special chars
        alternate_names.add(cleaned_name_for_matching)

        # Additional common variations
        alternate_names.add(cleaned_name.replace("/", "_"))  # Replace slashes with underscores
        alternate_names.add(cleaned_name.replace(" ", "_"))  # Replace spaces with underscores
        alternate_names.add(cleaned_name.replace(",", " "))  # Ensure commas are converted back to spaces
        alternate_names.add(cleaned_name.replace("and", "&"))  # If 'and' appears, revert to '&'

        # Return all generated alternate names
        return alternate_names


class PlaylistManager:
    def __init__(self):
        self.playlist_manager = SpotifyPlaylistManager()

    def create_playlist(self, playlist_name, track_ids):
        """Shuffle tracks and create a playlist."""
        random.shuffle(track_ids)  # Shuffle the tracks before creating the playlist
        self.playlist_manager.create_playlist(playlist_name, track_ids)


class MusicService:
    def __init__(self):
        self.musicbrainz_client = MusicBrainzClient()
        self.artist_fetcher = FLACArtistFetcher(FLAC_DIRECTORY, related_fetcher=self.musicbrainz_client)

    def process_artists(self, artist_processor):
        """Process artists and fetch related artists and genres."""
        genre_dict = {}
        artist_names = self.artist_fetcher.fetch_artists()  # Fetch the artist names directly
        alternate_names_dict = {}  # Store alternate names for batch processing

        # Preprocess all artist names
        for artist_name in artist_names:
            if artist_name == "Unknown Artist":
                continue
            alternate_names_dict[artist_name] = artist_processor.normalize_artist_name(artist_name)

        # Process artists and fetch related data
        for artist_name, alternate_names in alternate_names_dict.items():
            logging.info(f"Processing artist: {artist_name}")
            time.sleep(0.2)  # Rate limiting adjustment

            # Try each alternate name for searching
            related_artists = []
            genres = []
            for alt_name in alternate_names:
                artist_id, related_artists_temp, genres_temp = self.musicbrainz_client.search_artist(alt_name)
                if related_artists_temp:
                    related_artists = related_artists_temp
                    genres = genres_temp
                    break
            
            # Log related artists and genres
            if related_artists:
                logging.info(Fore.CYAN + f"Related artists for {artist_name}: {', '.join(related_artists)}" + Style.RESET_ALL)
            else:
                logging.info(Fore.YELLOW + f"No related artists found for {artist_name}" + Style.RESET_ALL)

            if genres:
                logging.info(Fore.LIGHTGREEN_EX + f"Genres for {artist_name}: {', '.join(genres)}" + Style.RESET_ALL)
            else:
                logging.info(Fore.YELLOW + f"No genres found for {artist_name}" + Style.RESET_ALL)

            # Store genres in dictionary
            genre_key = tuple(genres) if genres else ("No genres found",)
            if genre_key not in genre_dict:
                genre_dict[genre_key] = set()
            if related_artists:
                genre_dict[genre_key].update(related_artists)

        return genre_dict


def main():
    artist_processor = ArtistProcessor(FLAC_DIRECTORY)
    playlist_manager = PlaylistManager()
    music_service = MusicService()

    genre_dict = music_service.process_artists(artist_processor)

    # Dictionary to keep track of the number of playlists created for each genre
    genre_playlist_count = {}
    unknown_genre_count = 1  # Counter for unknown genre playlists

    # Create playlists for genres and artists
    for genre, artists in genre_dict.items():
        all_new_artists = list(set(artists))  # Remove duplicates

        # Shuffle the artists within the genre
        random.shuffle(all_new_artists)

        track_batches = []
        current_batch = []

        # Fetch and process tracks in bulk
        for related in all_new_artists:
            time.sleep(0.2)  # Rate limiting adjustment
            rel_id = playlist_manager.playlist_manager.fetch_spotify_artist_id(related)
            if rel_id:
                track_ids = playlist_manager.playlist_manager.fetch_top_tracks(rel_id)
                if len(current_batch) + len(track_ids) > 100:
                    track_batches.append(current_batch)
                    current_batch = []
                current_batch.extend(track_ids)
        
        if current_batch:
            track_batches.append(current_batch)

        # Sort the genres alphabetically before creating playlists, and handle unknown genres
        if genre == "Unknown Genre":
            genre_name = f"Playlist {unknown_genre_count}"
            unknown_genre_count += 1
        else:
            genre_name = genre[0] if isinstance(genre, tuple) else genre  # Handle case where genre is a tuple
            genre_name = sorted([genre_name])[0]  # Sort the genre if necessary

        # Create the playlists
        for index, batch in enumerate(track_batches, start=1):
            # Increment the playlist number for each genre
            if genre_name not in genre_playlist_count:
                genre_playlist_count[genre_name] = 1  # Initialize the count for this genre
            else:
                genre_playlist_count[genre_name] += 1  # Increment the count for this genre

            # Create playlist name with the correct incremented number
            playlist_name = f"{genre_name} {genre_playlist_count[genre_name]}"

            playlist_manager.create_playlist(playlist_name, batch)


if __name__ == "__main__":
    main()
