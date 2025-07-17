"""
Unified staging playlist classification automation.

This automation processes songs from a staging playlist (default: "new") and distributes them
to appropriate target playlists using intelligent multi-strategy classification:

1. **Artist Matching (Priority 1)**: If the artist appears in only one playlist, add to that playlist
2. **Genre Classification (Priority 2)**: Use hybrid genre classification system as fallback
3. **Confidence Scoring**: Single playlist artist (100%) > Genre classification (76% accuracy)

INTEGRATION WITH EXISTING SYSTEMS:
- Shares cache with playlist flow automation for optimal performance
- Uses existing artist matching logic from artist_matching/action.py
- Leverages genre classification from save_current_with_genre.py
- Integrates with telegram notifications and error handling

BIDIRECTIONAL FLOW INTEGRATION:
- Excludes parent playlists from artist uniqueness (they receive songs via upward flow)
- Targets child playlists where artists are manually curated
- Automatic promotion to parent collections happens via playlist flow automation
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

from common.config import get_config_value
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.utils.notifications import send_notification_via_file
from common.telegram_utils import SpotifyTelegramNotifier
from common.genre_classification_utils import classify_track, find_best_target_playlist

# Import artist matching utilities (we'll reuse the flow character logic)
try:
    from automations.spotify.artist_matching import action as artist_matching_action
except ImportError:
    # Fallback to path-based import
    import sys
    from pathlib import Path
    artist_matching_path = str(Path(__file__).parent.parent / "artist_matching")
    sys.path.append(artist_matching_path)
    import action as artist_matching_action


class StagingClassificationResults:
    """Container for classification results and statistics."""
    
    def __init__(self):
        self.artist_matches = {}  # playlist_id -> list of track_ids
        self.genre_matches = {}   # playlist_id -> list of track_ids  
        self.already_classified = []  # list of track_ids already in target playlists
        self.unclassified = []    # list of track_ids
        self.errors = []          # list of error messages
        self.statistics = {
            'total_tracks': 0,
            'artist_classification_count': 0,
            'genre_classification_count': 0,
            'already_classified_count': 0,
            'unclassified_count': 0,
            'single_playlist_artists_available': 0
        }
    
    def add_artist_match(self, playlist_id: str, track_id: str):
        """Add a track classified by artist matching."""
        if playlist_id not in self.artist_matches:
            self.artist_matches[playlist_id] = []
        self.artist_matches[playlist_id].append(track_id)
        self.statistics['artist_classification_count'] += 1
    
    def add_genre_match(self, playlist_id: str, track_id: str):
        """Add a track classified by genre."""
        if playlist_id not in self.genre_matches:
            self.genre_matches[playlist_id] = []
        self.genre_matches[playlist_id].append(track_id)
        self.statistics['genre_classification_count'] += 1
    
    def add_already_classified(self, track_id: str):
        """Add a track that's already in its correct target playlist."""
        self.already_classified.append(track_id)
        self.statistics['already_classified_count'] += 1
    
    def add_unclassified(self, track_id: str):
        """Add a track that couldn't be classified."""
        self.unclassified.append(track_id)
        self.statistics['unclassified_count'] += 1
    
    def add_error(self, error_msg: str):
        """Add an error message."""
        self.errors.append(error_msg)


def classify_and_process_track(sp, track: Dict, source_playlist_id: str, 
                             single_playlist_artists: Set[str],
                             artist_to_playlists: Dict[str, Set[str]],
                             playlists_dict: Dict[str, Dict],
                             unclassified_playlist_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Classify and immediately process a single track (add to target + remove from source).
    
    Args:
        sp: Spotify client
        track: Track data dictionary
        source_playlist_id: ID of the source staging playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        artist_to_playlists: Mapping of artist_id to set of playlist_ids
        playlists_dict: Dictionary of playlist data
        unclassified_playlist_id: ID of unclassified playlist (if it exists)
        
    Returns:
        Tuple of (classification_result, target_playlist_id_or_action)
    """
    track_id = track["id"]
    track_name = track["name"]
    artists = track["artists"]
    
    # STRATEGY 1: Artist Matching (Priority 1 - 100% accuracy)
    for artist in artists:
        artist_id = artist.get("id")
        artist_name = artist.get("name")
        
        if artist_id in single_playlist_artists:
            target_playlist_ids = artist_to_playlists[artist_id]
            
            if len(target_playlist_ids) == 1:
                target_playlist_id = list(target_playlist_ids)[0]
                
                if target_playlist_id == source_playlist_id:
                    continue
                
                # Check if track is already in target playlist
                target_tracks = playlists_dict[target_playlist_id]["tracks"]
                existing_track_ids = {t["id"] for t in target_tracks}
                target_name = playlists_dict[target_playlist_id]["name"]
                
                if track_id not in existing_track_ids:
                    # Add to target playlist immediately
                    try:
                        spotify_api_call_with_retry(
                            sp.playlist_add_items, target_playlist_id, [track_id]
                        )
                        print(f"  🎯 Artist match: '{track_name}' → '{target_name}' (artist: {artist_name})")
                        
                        # Remove from source immediately
                        remove_single_track_from_playlist(sp, source_playlist_id, track_id)
                        
                        return "artist_match", target_playlist_id
                        
                    except Exception as e:
                        print(f"  ❌ Failed to add '{track_name}' to '{target_name}': {e}")
                        continue
                else:
                    # Already in target - just remove from source
                    print(f"  ✅ Already in target: '{track_name}' already in '{target_name}' (artist: {artist_name})")
                    remove_single_track_from_playlist(sp, source_playlist_id, track_id)
                    return "already_classified", target_playlist_id
    
    # STRATEGY 2: Genre Classification (Priority 2 - 76% accuracy)
    try:
        classifications = classify_track(sp, track_id)
        
        if classifications:
            for genre in classifications:
                target_playlist_id = find_best_target_playlist(sp, genre, track_id)
                
                if target_playlist_id and target_playlist_id != source_playlist_id:
                    if target_playlist_id in playlists_dict:
                        # Check if track is already in target playlist
                        target_tracks = playlists_dict[target_playlist_id]["tracks"]
                        existing_track_ids = {t["id"] for t in target_tracks}
                        target_name = playlists_dict[target_playlist_id]["name"]
                        
                        if track_id not in existing_track_ids:
                            # Add to target playlist immediately
                            try:
                                spotify_api_call_with_retry(
                                    sp.playlist_add_items, target_playlist_id, [track_id]
                                )
                                print(f"  🎵 Genre match: '{track_name}' → '{target_name}' (genre: {genre})")
                                
                                # Remove from source immediately
                                remove_single_track_from_playlist(sp, source_playlist_id, track_id)
                                
                                return "genre_match", target_playlist_id
                                
                            except Exception as e:
                                print(f"  ❌ Failed to add '{track_name}' to '{target_name}': {e}")
                                continue
                        else:
                            # Already in target - just remove from source
                            print(f"  ✅ Already in target: '{track_name}' already in '{target_name}' (genre: {genre})")
                            remove_single_track_from_playlist(sp, source_playlist_id, track_id)
                            return "already_classified", target_playlist_id
    
    except Exception as e:
        print(f"  ❌ Genre classification error for '{track_name}': {e}")
    
    # STRATEGY 3: Move to Unclassified playlist
    print(f"  ❓ Moving '{track_name}' to Unclassified")
    
    # Ensure unclassified playlist exists
    if not unclassified_playlist_id:
        unclassified_playlist_id = get_or_create_unclassified_playlist(sp, playlists_dict)
    
    if unclassified_playlist_id:
        try:
            # Add to unclassified playlist immediately
            spotify_api_call_with_retry(
                sp.playlist_add_items, unclassified_playlist_id, [track_id]
            )
            print(f"  📋 Moved '{track_name}' to 'Unclassified'")
            
            # Remove from source immediately
            remove_single_track_from_playlist(sp, source_playlist_id, track_id)
            
            return "unclassified", unclassified_playlist_id
            
        except Exception as e:
            print(f"  ❌ Failed to move '{track_name}' to Unclassified: {e}")
    
    # If all else fails, leave in source
    print(f"  ⚠️ Could not process '{track_name}' - leaving in source")
    return "failed", None


def remove_single_track_from_playlist(sp, playlist_id: str, track_id: str):
    """Remove a single track from a playlist by finding its position."""
    try:
        # Get current tracks to find position
        current_tracks = spotify_api_call_with_retry(
            sp.playlist_items, playlist_id, fields="items.track.id"
        )
        
        # Find the position of this track (take first occurrence)
        for i, item in enumerate(current_tracks['items']):
            if item['track']['id'] == track_id:
                # Remove this specific occurrence
                spotify_api_call_with_retry(
                    sp.playlist_remove_specific_occurrences_of_items,
                    playlist_id,
                    [{"positions": [i]}]
                )
                return
                
    except Exception as e:
        print(f"    ⚠️ Error removing track from playlist: {e}")


def get_or_create_unclassified_playlist(sp, playlists_dict: Dict[str, Dict]) -> Optional[str]:
    """Get existing or create new Unclassified playlist."""
    # Check if it already exists
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data["name"].lower() == "unclassified":
            return playlist_id
    
    # Create new one
    try:
        user_id = spotify_api_call_with_retry(sp.current_user)["id"]
        playlist_response = spotify_api_call_with_retry(
            sp.user_playlist_create,
            user_id,
            "Unclassified",
            public=False,
            description="Songs that couldn't be automatically classified"
        )
        unclassified_playlist_id = playlist_response["id"]
        print(f"  ✅ Created new 'Unclassified' playlist")
        
        # Add to playlists_dict for tracking
        playlists_dict[unclassified_playlist_id] = {
            "name": "Unclassified",
            "tracks": []
        }
        
        return unclassified_playlist_id
        
    except Exception as e:
        print(f"  ❌ Failed to create 'Unclassified' playlist: {e}")
        return None


def classify_staging_tracks(sp, playlists_dict: Dict[str, Dict], 
                          source_playlist_id: str,
                          single_playlist_artists: Set[str],
                          artist_to_playlists: Dict[str, Set[str]]) -> StagingClassificationResults:
    """
    Classify tracks from staging playlist using immediate processing approach.
    Each track is classified and immediately moved (resilient to interruptions).
    
    Args:
        sp: Spotify client
        playlists_dict: Dictionary of playlist data
        source_playlist_id: ID of the staging playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        artist_to_playlists: Mapping of artist_id to set of playlist_ids
        
    Returns:
        StagingClassificationResults: Comprehensive classification results
    """
    results = StagingClassificationResults()
    source_tracks = playlists_dict[source_playlist_id]["tracks"].copy()  # Copy to avoid modification during iteration
    source_name = playlists_dict[source_playlist_id]["name"]
    
    results.statistics['total_tracks'] = len(source_tracks)
    results.statistics['single_playlist_artists_available'] = len(single_playlist_artists)
    
    print(f"Processing {len(source_tracks)} tracks from '{source_name}' (immediate mode)...")
    print(f"Available single-playlist artists: {len(single_playlist_artists)}")
    
    # Track results for summary
    processed_tracks = {}
    unclassified_playlist_id = None
    
    for i, track in enumerate(source_tracks):
        track_id = track["id"]
        track_name = track["name"]
        print(f"\n🎵 Track {i+1}/{len(source_tracks)}: '{track_name}'")
        
        try:
            # Process track immediately (classify + add to target + remove from source)
            classification_result, target_id = classify_and_process_track(
                sp, track, source_playlist_id, single_playlist_artists, 
                artist_to_playlists, playlists_dict, unclassified_playlist_id
            )
            
            # Update unclassified playlist ID if it was created
            if classification_result == "unclassified" and target_id:
                unclassified_playlist_id = target_id
            
            # Track results for statistics
            if classification_result == "artist_match":
                results.add_artist_match(target_id, track_id)
                processed_tracks[target_id] = processed_tracks.get(target_id, 0) + 1
            elif classification_result == "genre_match":
                results.add_genre_match(target_id, track_id)
                processed_tracks[target_id] = processed_tracks.get(target_id, 0) + 1
            elif classification_result == "already_classified":
                results.add_already_classified(track_id)
            elif classification_result == "unclassified":
                results.add_unclassified(track_id)
                if target_id:
                    processed_tracks[target_id] = processed_tracks.get(target_id, 0) + 1
            elif classification_result == "failed":
                results.add_error(f"Failed to process '{track_name}'")
                results.add_unclassified(track_id)
                
        except Exception as e:
            results.add_error(f"Error processing '{track_name}': {str(e)}")
            print(f"  ❌ Error processing '{track_name}': {e}")
    
    # Update statistics with actual processed counts
    print(f"\n📊 Processing complete:")
    print(f"  • Artist matches: {results.statistics['artist_classification_count']}")
    print(f"  • Genre matches: {results.statistics['genre_classification_count']}")
    print(f"  • Already classified: {results.statistics['already_classified_count']}")
    print(f"  • Moved to Unclassified: {results.statistics['unclassified_count']}")
    
    return results


def summarize_processed_tracks(results: StagingClassificationResults, 
                             playlists_dict: Dict[str, Dict]) -> Dict[str, int]:
    """
    Summarize tracks that have already been processed (since processing is now immediate).
    
    Args:
        results: Classification results with processed tracks
        playlists_dict: Dictionary of playlist data
        
    Returns:
        Dictionary mapping playlist_id to number of songs processed
    """
    songs_added = {}
    
    # Count artist matches
    for target_playlist_id, track_ids in results.artist_matches.items():
        songs_added[target_playlist_id] = songs_added.get(target_playlist_id, 0) + len(track_ids)
    
    # Count genre matches
    for target_playlist_id, track_ids in results.genre_matches.items():
        songs_added[target_playlist_id] = songs_added.get(target_playlist_id, 0) + len(track_ids)
    
    # Count unclassified tracks (they were moved to Unclassified playlist)
    unclassified_count = len(results.unclassified)
    if unclassified_count > 0:
        # Find the Unclassified playlist ID
        for playlist_id, playlist_data in playlists_dict.items():
            if playlist_data["name"].lower() == "unclassified":
                songs_added[playlist_id] = songs_added.get(playlist_id, 0) + unclassified_count
                break
    
    return songs_added




def run_action():
    """
    Main action to process staging playlist using unified classification.
    
    This automation combines artist matching (100% accuracy) and genre classification 
    (76% accuracy) to intelligently distribute songs from a staging playlist to 
    appropriate target playlists.
    
    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Staging Classification")
    
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    
    # Share cache with playlist flow for optimal performance
    sp = initialize_spotify_client(scope, "playlist_flow_cache")
    
    try:
        # Load all playlist data (reuse existing logic)
        playlists_dict = artist_matching_action.load_playlist_data(sp)
        
        print(f"Loaded {len(playlists_dict)} playlists")
        
        # Find staging playlist (default: "new")
        source_playlist_id = artist_matching_action.find_source_playlist(playlists_dict, "new")
        
        if not source_playlist_id:
            title = "❌ Staging Playlist Not Found"
            message = "Could not find staging playlist named 'new' to process."
            telegram.send_error("Staging playlist not found", message)
            send_notification_via_file(title, message, "/tmp/spotify_staging_classification_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        source_name = playlists_dict[source_playlist_id]["name"]
        source_track_count = len(playlists_dict[source_playlist_id]["tracks"])
        
        print(f"Found staging playlist: '{source_name}' ({source_track_count} tracks)")
        
        if source_track_count == 0:
            title = "ℹ️ No Songs to Classify"
            message = f"Staging playlist '{source_name}' is empty."
            telegram.send_info("No songs to classify", message)
            send_notification_via_file(title, message, "/tmp/spotify_staging_classification_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        # Build artist to playlists mapping (excluding parent playlists)
        print("Building artist to playlists mapping (excluding parent playlists)...")
        artist_to_playlists = artist_matching_action.build_artist_to_playlists_mapping(playlists_dict)
        
        print(f"Found {len(artist_to_playlists)} unique artists in non-parent playlists")
        
        # Find single playlist artists
        single_playlist_artists = artist_matching_action.find_single_playlist_artists(artist_to_playlists)
        
        print(f"Found {len(single_playlist_artists)} single-playlist artists")
        
        # Process tracks with immediate classification and movement (interruption-safe)
        print("Starting immediate classification and processing...")
        results = classify_staging_tracks(sp, playlists_dict, source_playlist_id, 
                                        single_playlist_artists, artist_to_playlists)
        
        # Summarize what was processed (tracks already moved)
        songs_added = summarize_processed_tracks(results, playlists_dict)
        
        # Calculate totals
        unclassified_moved = len(results.unclassified)
        tracks_processed = (results.statistics['artist_classification_count'] + 
                          results.statistics['genre_classification_count'] + 
                          results.statistics['already_classified_count'] + 
                          unclassified_moved)
        
        # Build comprehensive notification message
        stats = results.statistics
        total_classified = stats['artist_classification_count'] + stats['genre_classification_count']
        total_handled = total_classified + stats['already_classified_count'] + unclassified_moved
        
        if total_handled == 0:
            title = "ℹ️ No Songs Classified"
            message = f"No songs from '{source_name}' could be classified."
            telegram.send_info("No songs classified", f"Processed {stats['total_tracks']} tracks")
        else:
            title = f"✅ Processed {total_handled} Songs"
            
            # Build detailed breakdown
            breakdown = []
            breakdown.append(f"📊 Classification Results:")
            breakdown.append(f"  • Artist matching: {stats['artist_classification_count']} songs (100% accuracy)")
            breakdown.append(f"  • Genre matching: {stats['genre_classification_count']} songs (76% accuracy)")
            breakdown.append(f"  • Already classified: {stats['already_classified_count']} songs")
            breakdown.append(f"  • Moved to Unclassified: {unclassified_moved} songs")
            breakdown.append(f"  • Available single-playlist artists: {stats['single_playlist_artists_available']}")
            
            if songs_added:
                breakdown.append(f"")
                breakdown.append(f"🎵 Added to {len(songs_added)} playlists:")
                for target_playlist_id, count in songs_added.items():
                    target_name = playlists_dict[target_playlist_id]["name"]
                    breakdown.append(f"  • {target_name}: +{count}")
            
            if unclassified_moved > 0:
                breakdown.append(f"")
                breakdown.append(f"📋 Moved to 'Unclassified': +{unclassified_moved} tracks")
            
            if tracks_processed > 0:
                breakdown.append(f"")
                breakdown.append(f"🧹 Processed and removed from '{source_name}': {tracks_processed} tracks")
            
            if results.errors:
                breakdown.append(f"")
                breakdown.append(f"⚠️ Errors ({len(results.errors)}):")
                for error in results.errors[:3]:  # Show first 3 errors
                    breakdown.append(f"  • {error}")
                if len(results.errors) > 3:
                    breakdown.append(f"  • ... and {len(results.errors) - 3} more errors")
            
            message = "\n".join(breakdown)
            
            # Send success notification
            telegram_summary = f"New: {total_classified}, Already: {stats['already_classified_count']}, Unclassified: {unclassified_moved}"
            telegram.send_success(f"Processed {total_handled}/{stats['total_tracks']} songs", telegram_summary)
    
    except Exception as e:
        title = "❌ Classification Error"
        message = f"Staging classification failed: {str(e)}"
        telegram.send_error("Staging classification failed", str(e))
    
    # Send notification
    send_notification_via_file(title, message, "/tmp/spotify_staging_classification_result.txt")
    print(f"{title}\n{message}")
    
    return title, message


def main():
    """Entry point for command-line use."""
    return run_action()


if __name__ == "__main__":
    main()