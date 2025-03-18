"""
Module to add songs liked since the last successful run to a specified playlist.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from common.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    DAILY_LIKED_PLAYLIST_ID,
    DAILY_LIKED_PLAYLIST_NAME,
)
from common.utils.notifications import send_notification_via_file


def get_or_create_playlist(sp):
    """
    Get the playlist ID from environment or create a new playlist.

    Args:
        sp: Spotify client

    Returns:
        str: Playlist ID
    """
    # Check if playlist ID is in environment variables or configuration
    playlist_id = DAILY_LIKED_PLAYLIST_ID

    if playlist_id:
        # Verify the playlist still exists
        try:
            playlist = sp.playlist(playlist_id)
            return playlist_id
        except Exception:
            # Playlist doesn't exist anymore
            pass

    # Try to find a playlist with the configured name
    playlists = sp.current_user_playlists()
    for playlist in playlists["items"]:
        if playlist["name"] == DAILY_LIKED_PLAYLIST_NAME:
            return playlist["id"]

    # Create a new playlist
    user_id = sp.current_user()["id"]
    new_playlist = sp.user_playlist_create(
        user_id,
        DAILY_LIKED_PLAYLIST_NAME,
        public=False,
        description="Songs I liked recently",
    )

    return new_playlist["id"]


def get_last_run_time():
    """
    Get the last time the script ran successfully.

    Returns:
        datetime: Timestamp of the last successful run, or a time 24 hours ago if no record exists
    """
    timestamp_file = Path(__file__).parent.parent / ".spotify_daily_liked_timestamp"

    # Default to 24 hours ago if no timestamp file exists
    default_time = (datetime.now() - timedelta(days=1)).isoformat()

    if not timestamp_file.exists():
        return datetime.fromisoformat(default_time)

    try:
        with open(timestamp_file, "r") as f:
            data = json.load(f)
            return datetime.fromisoformat(data.get("last_run", default_time))
    except (json.JSONDecodeError, FileNotFoundError, ValueError):
        # If there's any error reading the file, default to 24 hours ago
        return datetime.fromisoformat(default_time)


def save_last_run_time():
    """Save the current time as the last successful run time."""
    timestamp_file = Path(__file__).parent.parent / ".spotify_daily_liked_timestamp"

    try:
        with open(timestamp_file, "w") as f:
            json.dump({"last_run": datetime.now().isoformat()}, f)

        # Ensure the file has secure permissions
        os.chmod(timestamp_file, 0o600)
    except Exception as e:
        print(f"Warning: Failed to save timestamp: {e}")


def run_action():
    """
    Add songs liked since the last successful run to a specified playlist.

    Returns:
        tuple: (title, message) notification information
    """
    # Set up the cache file path - using a separate cache file for this functionality
    cache_path = Path(__file__).parent.parent / ".spotify_daily_liked_cache"

    # Define the required scopes
    scope = "user-library-read playlist-modify-private playlist-read-private user-read-private playlist-modify-public"

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
        # Get the playlist ID
        playlist_id = get_or_create_playlist(sp)

        # Get the last time the script ran successfully
        last_run_time = get_last_run_time()

        liked_tracks = []

        # We may need to fetch more than 50 tracks if the user has been away for a long time
        # Start with a limit of 50, but we can fetch more if needed
        offset = 0
        limit = 50
        more_tracks = True

        while more_tracks:
            # Get recently saved tracks with pagination
            results = sp.current_user_saved_tracks(limit=limit, offset=offset)

            if not results["items"]:
                break

            found_older_track = False

            for item in results["items"]:
                # Check if the track was saved since the last run
                added_at = datetime.strptime(item["added_at"], "%Y-%m-%dT%H:%M:%SZ")
                if added_at >= last_run_time:
                    liked_tracks.append(item["track"]["id"])
                else:
                    # Since tracks are returned in reverse chronological order,
                    # we can stop once we find a track that's older than the last run
                    found_older_track = True
                    more_tracks = False
                    break

            # If we didn't find any older tracks and there are more to fetch
            if not found_older_track and len(results["items"]) == limit:
                offset += limit
            else:
                more_tracks = False

        if not liked_tracks:
            title = "No New Liked Songs"
            message = (
                f"No songs were liked since {last_run_time.strftime('%Y-%m-%d %H:%M')}."
            )
        else:
            # Add the tracks to the playlist in chunks of 100 (Spotify API limit)
            for i in range(0, len(liked_tracks), 100):
                chunk = liked_tracks[i : i + 100]
                sp.playlist_add_items(playlist_id, chunk)

            # Get playlist details for the message
            playlist = sp.playlist(playlist_id)
            playlist_name = playlist["name"]

            title = f"✅ Added {len(liked_tracks)} Songs"
            message = f"Added {len(liked_tracks)} liked songs to '{playlist_name}'"

            # Update the last run time after a successful execution
            save_last_run_time()
    except Exception as e:
        title = "Error"
        message = f"An error occurred: {str(e)}"

    # Write the result to a temporary file
    result_file = send_notification_via_file(
        title, message, "/tmp/spotify_daily_liked_result.txt"
    )

    # Also print to console
    print(f"{title}\n{message}")

    return title, message


def main():
    """Entry point for command-line use."""
    return run_action()


if __name__ == "__main__":
    main()
