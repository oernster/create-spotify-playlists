import os
import logging
import requests
import time
import musicbrainzngs
from urllib.parse import quote_plus
from fuzzywuzzy import fuzz, process
from colorama import Fore, Back, Style
import inflect
from logging_utils import log_musicbrainz_search, log_attempting_match


musicbrainzngs.set_useragent("PlaylistGenerator", "1.0", "your-email")

# Initialize number-to-text converter
p = inflect.engine()

# Suppress MusicBrainz warnings by setting its logger to ERROR
logging.getLogger("musicbrainzngs").setLevel(logging.ERROR)

# Number to text dictionary
number_to_text = {
    1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
    11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
    15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
    19: 'nineteen', 20: 'twenty', 30: 'thirty', 40: 'forty',
    50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety'
}
text_to_number = {v: k for k, v in number_to_text.items()}

def clean_artist_name(artist_name):
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
        if number in number_to_text:
            words[0] = number_to_text[number]
    elif words[0].lower() in text_to_number:
        words[0] = str(text_to_number[words[0].lower()])
    
    return " ".join(words)

def normalize_artist_name(artist_name):
    """Generate alternate spellings for fuzzy matching."""
    if not artist_name:
        return {"Unknown Artist"}  # Ensures it always returns a set

    alternate_names = set()

    # Add the original artist name (standard case)
    alternate_names.add(artist_name)

    # Clean up using the `clean_artist_name` function
    cleaned_name = clean_artist_name(artist_name)
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


class FLACArtistFetcher:
    def __init__(self, directory, related_fetcher=None):
        self.directory = directory
        musicbrainzngs.set_useragent("PlaylistGenerator", "0.1", contact="oliverjernster@hotmail.com@example.com")
        self.related_fetcher = related_fetcher if related_fetcher else None
        self.musicbrainz = MusicBrainzClient()

    def fetch_artists(self):
        """Extracts artist names from FLAC music directory."""
        if not os.path.exists(self.directory):
            logging.error(Fore.RED + f"FLAC directory not found: {self.directory}" + Style.RESET_ALL)
            return []
        return [name for name in os.listdir(self.directory) if os.path.isdir(os.path.join(self.directory, name))]


class MusicBrainzClient:
    API_URL = "https://musicbrainz.org/ws/2/artist/"
    SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"
    
    MAX_RETRIES = 5
    INITIAL_BACKOFF = 4
    BACKOFF_MULTIPLIER = 2
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_artist(self, artist_name):
        """Search for an artist using MusicBrainz API."""
        normalized_name = clean_artist_name(artist_name)
        logging.info(Fore.BLUE + Back.WHITE + f"[MusicBrainz] Searching for: {normalized_name}" + Style.RESET_ALL)
        retries = 0
        backoff = self.INITIAL_BACKOFF
        while retries < self.MAX_RETRIES:
            try:
                result = musicbrainzngs.search_artists(query=normalized_name, limit=5)
                if "artist-list" in result and result["artist-list"]:
                    best_match = self._find_best_match(normalized_name, result["artist-list"])
                    if best_match:
                        artist_id = best_match["id"]
                        genres = self.get_genres(artist_id)
                        related_artists = self.get_related_artists(artist_id)
                        return artist_id, related_artists, genres
                    else:
                        logging.warning(f"No strong match found for {normalized_name}")
                        return None, [], []
                else:
                    logging.warning(Fore.YELLOW + f"No results found for {normalized_name}" + Style.RESET_ALL)
                    return None, [], []
            except Exception as e:
                logging.error(Fore.RED + f"Error in MusicBrainz search: {e}" + Style.RESET_ALL)
                time.sleep(backoff)
                backoff *= self.BACKOFF_MULTIPLIER
                retries += 1
        return None, [], []
    
    def _find_best_match(self, artist_name, artist_list):
        """Find the best fuzzy match for an artist name."""
        best_match = None
        highest_score = 0
        for artist in artist_list:
            match_name = artist.get("name", "")
            score = fuzz.ratio(artist_name.lower(), match_name.lower())
            if score > highest_score and score > 85:  # Require a strong match
                best_match = artist
                highest_score = score
        return best_match
    
    def get_genres(self, artist_id):
        """Fetch genres for a given MusicBrainz artist ID."""
        try:
            result = musicbrainzngs.get_artist_by_id(artist_id, includes=["tags"])
            return [tag["name"] for tag in result.get("artist", {}).get("tag-list", [])]
        except Exception as e:
            logging.error(f"Error fetching genres: {e}")
            return []
    
    def get_related_artists(self, artist_id):
        """Fetch related artists for a given MusicBrainz artist ID."""
        try:
            result = musicbrainzngs.get_artist_by_id(artist_id, includes=["artist-rels"])
            return [rel["artist"]["name"] for rel in result.get("artist", {}).get("artist-relation-list", [])]
        except Exception as e:
            logging.error(Fore.RED + f"Error fetching related artists: {e}" + Style.RESET_ALL)
            return []


class MusicLibraryProcessor:
    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.musicbrainz_client = MusicBrainzClient()

    def get_flac_artists(self):
        """Retrieve artist directories from FLAC storage."""
        if not os.path.exists(self.music_dir):
            logging.error(Fore.RED + f"FLAC directory not found: {self.music_dir}" + Style.RESET_ALL)
            return []
        return [name for name in os.listdir(self.music_dir) if os.path.isdir(os.path.join(self.music_dir, name))]

    def process_artists(self):
        """Process artists and retrieve related recommendations and genres."""
        artists = self.get_flac_artists()
        logging.info(Fore.LIGHTBLUE_EX + f"Checking {len(artists)} artists in MusicBrainz...\n" + Style.RESET_ALL)

        genre_dict = {}

        for artist in artists:
            artist_id, related_artists, genres = self.musicbrainz_client.search_artist(artist)
            if artist_id:
                genre_dict[artist] = genres if genres else {"No genres found"}
                if related_artists:
                    genre_dict.setdefault(artist, set()).update(related_artists)

        if self.musicbrainz_client.deferred_artists:
            logging.info(Fore.CYAN + f"\nRetrying {len(self.musicbrainz_client.deferred_artists)} failed artists...\n" + Style.RESET_ALL)
            for artist in self.musicbrainz_client.deferred_artists:
                artist_id, related_artists, genres = self.musicbrainz_client.search_artist(artist)
                if artist_id:
                    genre_dict[artist] = genres if genres else {"No genres found"}
                    if related_artists:
                        genre_dict.setdefault(artist, set()).update(related_artists)

        return genre_dict
