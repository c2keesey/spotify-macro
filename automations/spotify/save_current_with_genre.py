"""
Module to save the currently playing Spotify track to genre-specific playlists.

Enhanced version of save_current.py that uses genre classification to automatically
sort saved tracks into appropriate genre-based playlists.
"""

from typing import List, Tuple
from common.spotify_utils import initialize_spotify_client
from common.utils.notifications import send_notification_via_file
from common.genre_classification_utils import classify_track, add_track_to_genre_playlists, get_safe_spotify_client
from common.telegram_utils import SpotifyTelegramNotifier
from common.config import (
    GENRE_CLASSIFICATION_ENABLED, 
    GENRE_CLASSIFICATION_FALLBACK_PLAYLIST,
    GENRE_CLASSIFICATION_USE_AUDIO_FEATURES
)


def save_current_track_with_genre():
    """
    Save the currently playing Spotify track to the user's library and 
    automatically sort it into genre-specific playlists.

    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Save Current Track with Genre")
    
    # Define the required scopes (includes playlist modification for genre sorting)
    scope = "user-read-currently-playing user-library-modify user-library-read playlist-modify-public playlist-modify-private playlist-read-private"

    # Set up the Spotify client using the master cache
    sp = initialize_spotify_client(scope)

    try:
        # Get the currently playing track
        current_track = sp.current_user_playing_track()

        if current_track is not None:
            # Extract track information
            track_id = current_track["item"]["id"]
            artist = current_track["item"]["artists"][0]["name"]
            song = current_track["item"]["name"]

            # Check if the track is already in the user's liked songs
            is_saved = sp.current_user_saved_tracks_contains([track_id])[0]

            # Always add to library first (existing functionality)
            if not is_saved:
                sp.current_user_saved_tracks_add([track_id])
                library_status = "Added to library"
            else:
                library_status = "Already in library"

            # Genre classification and playlist sorting
            genre_results = []
            if GENRE_CLASSIFICATION_ENABLED:
                try:
                    # Classify the track by genre
                    classifications = classify_track(sp, track_id)
                    
                    if classifications:
                        # Add to genre-specific playlists
                        add_results = add_track_to_genre_playlists(sp, track_id, classifications)
                        
                        # Build result summary
                        successful_genres = [genre for genre, success in add_results.items() if success]
                        failed_genres = [genre for genre, success in add_results.items() if not success]
                        
                        if successful_genres:
                            genre_results.append(f"Added to: {', '.join(successful_genres)}")
                        if failed_genres:
                            genre_results.append(f"Failed: {', '.join(failed_genres)}")
                    else:
                        genre_results.append("No genre classification found")
                        
                except Exception as e:
                    genre_results.append(f"Genre classification error: {str(e)}")

            # Build notification message
            if not is_saved:
                title = f"✅ {song} ♪ ♫ ♬"
            else:
                title = f"🔄 {song} (already saved)"
                
            message_parts = [f"By {artist} -- {library_status}"]
            if genre_results:
                message_parts.extend(genre_results)
            message = "\n".join(message_parts)
            
            # Send Telegram notification
            details = f"By {artist}\n{chr(10).join(genre_results)}" if genre_results else f"By {artist}"
            if not is_saved:
                telegram.send_success(f"Added '{song}' to library with genre sorting", details)
            else:
                telegram.send_info(f"'{song}' already in library, processed genre sorting", details)

        else:
            title = "❌ No Track Playing"
            message = "♫ ♪ (-_-) ♪ ♫ Zzz..."
            telegram.send_info("No track currently playing", "Start playing a song on Spotify")
            
    except Exception as e:
        title = "Error"
        message = f"An error occurred: {str(e)}"
        telegram.send_error("Failed to save current track with genre", str(e))

    # Write the result to a temporary file for shell script to use
    result_file = send_notification_via_file(
        title, message, "/tmp/spotify_genre_save_result.txt"
    )

    # Also print to console
    print(f"{title}\n{message}")

    return title, message


def test_genre_classification(track_id: str = None):
    """
    Test genre classification on a specific track or currently playing track.
    
    Args:
        track_id: Optional specific track ID to test. Uses currently playing if None.
    """
    scope = "user-read-currently-playing playlist-read-private"
    sp = initialize_spotify_client(scope)
    
    try:
        if track_id is None:
            # Get currently playing track
            current_track = sp.current_user_playing_track()
            if not current_track:
                print("❌ No track playing")
                return
            track_id = current_track["item"]["id"]
            track_name = f"{current_track['item']['name']} by {current_track['item']['artists'][0]['name']}"
        else:
            # Get track details
            track = sp.track(track_id)
            track_name = f"{track['name']} by {track['artists'][0]['name']}"
        
        print(f"🎵 Testing classification for: {track_name}")
        print(f"🆔 Track ID: {track_id}")
        
        # Test classification
        classifications = classify_track(sp, track_id)
        
        if classifications:
            print(f"📂 Classifications: {', '.join(classifications)}")
            
            # Show which playlists would be used
            from common.genre_classification_utils import find_best_target_playlist
            for genre in classifications:
                target_playlist_id = find_best_target_playlist(sp, genre, track_id)
                if target_playlist_id:
                    # Get playlist name
                    playlist = sp.playlist(target_playlist_id, fields="name")
                    print(f"   → {genre}: {playlist['name']}")
                else:
                    print(f"   → {genre}: No suitable playlist found")
        else:
            print("❌ No genre classification found")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")


def main():
    """Entry point for command-line use."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        track_id = sys.argv[2] if len(sys.argv) > 2 else None
        test_genre_classification(track_id)
    else:
        # Normal mode
        return save_current_track_with_genre()


if __name__ == "__main__":
    main()