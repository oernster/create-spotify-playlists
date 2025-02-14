import logging
from colorama import Fore, Back, Style


def log_musicbrainz_search(artist_name, best_match, best_score, artist_id):
    """Log MusicBrainz search results."""
    if best_match:
        # Adding a reset at the end ensures that the color and background reset properly
        logging.info(Fore.BLACK + Back.LIGHTBLUE_EX + f"[MusicBrainz] Matched '{artist_name}' -> {best_match} (ID: {artist_id}, Score: {best_score})" + Style.RESET_ALL)
    else:
        logging.warning(Fore.YELLOW + f"[MusicBrainz] No strong match for '{artist_name}'" + Style.RESET_ALL)

def log_spotify_search(artist_name, artist_id, attempted=True):
    """Log Spotify search results."""
    if artist_name == "Unknown Artist":
        return  # Silently ignore
    
    if attempted:
        logging.info(Fore.YELLOW + f"[Spotify] Searching for '{artist_name}'...")
    
    if artist_id:
        logging.info(Fore.GREEN + f"[Spotify] Matched '{artist_name}'" + Style.RESET_ALL)
        logging.debug(Fore.GREEN + f"[Spotify] Matched '{artist_name}' -> ID: {artist_id}" + Style.RESET_ALL)
    else:
        logging.warning(Fore.YELLOW + f"[Spotify] No match found for '{artist_name}'" + Style.RESET_ALL)

def log_attempting_match(artist_name, alternate_names):
    logging.info(Fore.LIGHTBLUE_EX + f"[MusicBrainz] Attempting to match '{artist_name}' with alternate names: {alternate_names}" + Style.RESET_ALL)
