import os

def list_artists(directory):
    """
    Lists all artist directories in the specified music directory.

    :param directory: Path to the music directory.
    :return: List of artists.
    """
    try:
        # List all entries in the directory
        entries = os.listdir(directory)
        # Filter out files, only keep directories
        artists = [entry for entry in entries if os.path.isdir(os.path.join(directory, entry))]
        return artists
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Path to the music directory where you have ripped your CDs or store your mp3s / whatever.
# It expects the directory you define to have folders with artist names as the directory names inside.
music_dir = "L:\\Storage\\FLACMusic"

# List artists
artists = list_artists(music_dir)
print("Artists found:")
for artist in artists:
    print(artist)
