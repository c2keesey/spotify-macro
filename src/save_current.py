import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()

# Set up the cache file path in the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
cache_path = os.path.join(script_dir, ".spotify_cache")

# Define the required scopes
scope = "user-read-currently-playing user-library-modify user-library-read"

# Set up the Spotify client
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope=scope,
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri="http://localhost:8888/callback",
        cache_path=cache_path,
    )
)

# Ensure the cache file has the correct permissions if it exists
if os.path.exists(cache_path):
    os.chmod(cache_path, 0o600)

try:
    # Get the currently playing track
    current_track = sp.current_user_playing_track()

    if current_track is not None:
        # Extract track ID
        track_id = current_track["item"]["id"]

        # Check if the track is already in the user's liked songs
        is_saved = sp.current_user_saved_tracks_contains([track_id])[0]

        # Get track details for message
        artist = current_track["item"]["artists"][0]["name"]
        song = current_track["item"]["name"]

        if not is_saved:
            # Add the track to the user's library
            sp.current_user_saved_tracks_add([track_id])
            title = f"✅ {song} ♪ ♫ ♬"
            message = f"By {artist} -- Added to library"
        else:
            title = "Already in your library  (^ヮ^)"
            message = f"{song} By {artist}"
    else:
        title = "❌ No Track Playing"
        message = "♫ ♪ (-_-) ♪ ♫ Zzz..."
except Exception as e:
    title = "Error"
    message = f"An error occurred: {str(e)}"

# Write the result to a temporary file
with open("/tmp/spotify_add_result.txt", "w") as f:
    f.write(f"{title}\n{message}")

print(f"{title}\n{message}")
