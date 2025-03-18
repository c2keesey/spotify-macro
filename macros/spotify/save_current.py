"""
Module to save the currently playing Spotify track to the user's library.
"""

import os
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from common.config import CLIENT_ID, CLIENT_SECRET
from common.utils.notifications import send_notification_via_file


def save_current_track():
    """
    Save the currently playing Spotify track to the user's library.

    Returns:
        tuple: (title, message) notification information
    """
    # Set up the cache file path
    cache_path = Path(__file__).parent / ".spotify_cache"

    # Define the required scopes
    scope = "user-read-currently-playing user-library-modify user-library-read"

    # Set up the Spotify client
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            scope=scope,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri="http://localhost:8888/callback",
            cache_path=str(cache_path),
        )
    )

    # Ensure the cache file has the correct permissions if it exists
    if cache_path.exists():
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

    # Write the result to a temporary file for shell script to use
    result_file = send_notification_via_file(
        title, message, "/tmp/spotify_add_result.txt"
    )

    # Also print to console
    print(f"{title}\n{message}")

    return title, message


def main():
    """Entry point for command-line use."""
    return save_current_track()


if __name__ == "__main__":
    main()
