"""
Module to save the currently playing Spotify track to the user's library.
"""

from common.spotify_utils import initialize_spotify_client
from common.utils.notifications import send_notification_via_file
from common.telegram_utils import SpotifyTelegramNotifier


def save_current_track():
    """
    Save the currently playing Spotify track to the user's library.

    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Save Current Track")
    
    # Define the required scopes
    scope = "user-read-currently-playing user-library-modify user-library-read"

    # Set up the Spotify client using the new utilities
    sp = initialize_spotify_client(scope, "save_current_cache")

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
                telegram.send_success(f"Added '{song}' to library", f"By {artist}")
            else:
                title = "Already in your library  (^ヮ^)"
                message = f"{song} By {artist}"
                telegram.send_info(f"'{song}' already in library", f"By {artist}")
        else:
            title = "❌ No Track Playing"
            message = "♫ ♪ (-_-) ♪ ♫ Zzz..."
            telegram.send_info("No track currently playing", "Start playing a song on Spotify")
    except Exception as e:
        title = "Error"
        message = f"An error occurred: {str(e)}"
        telegram.send_error("Failed to save current track", str(e))

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
