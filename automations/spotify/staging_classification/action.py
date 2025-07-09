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
        self.unclassified = []    # list of track_ids
        self.errors = []          # list of error messages
        self.statistics = {
            'total_tracks': 0,
            'artist_classification_count': 0,
            'genre_classification_count': 0,
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
    
    def add_unclassified(self, track_id: str):
        """Add a track that couldn't be classified."""
        self.unclassified.append(track_id)
        self.statistics['unclassified_count'] += 1
    
    def add_error(self, error_msg: str):
        """Add an error message."""
        self.errors.append(error_msg)


def classify_staging_tracks(sp, playlists_dict: Dict[str, Dict], 
                          source_playlist_id: str,
                          single_playlist_artists: Set[str],
                          artist_to_playlists: Dict[str, Set[str]]) -> StagingClassificationResults:
    """
    Classify tracks from staging playlist using multi-strategy approach.
    
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
    source_tracks = playlists_dict[source_playlist_id]["tracks"]
    source_name = playlists_dict[source_playlist_id]["name"]
    
    results.statistics['total_tracks'] = len(source_tracks)
    results.statistics['single_playlist_artists_available'] = len(single_playlist_artists)
    
    print(f"Classifying {len(source_tracks)} tracks from '{source_name}'...")
    print(f"Available single-playlist artists: {len(single_playlist_artists)}")
    
    for track in source_tracks:
        track_id = track["id"]
        track_name = track["name"]
        artists = track["artists"]
        
        # STRATEGY 1: Artist Matching (Priority 1 - 100% accuracy)
        artist_matched = False
        for artist in artists:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            if artist_id in single_playlist_artists:
                # This artist appears in only one playlist
                target_playlist_ids = artist_to_playlists[artist_id]
                
                if len(target_playlist_ids) == 1:
                    target_playlist_id = list(target_playlist_ids)[0]
                    
                    # Don't add to source playlist itself
                    if target_playlist_id == source_playlist_id:
                        continue
                    
                    # Check if track is already in target playlist
                    target_tracks = playlists_dict[target_playlist_id]["tracks"]
                    existing_track_ids = {t["id"] for t in target_tracks}
                    
                    if track_id not in existing_track_ids:
                        results.add_artist_match(target_playlist_id, track_id)
                        target_name = playlists_dict[target_playlist_id]["name"]
                        print(f"  🎯 Artist match: '{track_name}' → '{target_name}' (artist: {artist_name})")
                        artist_matched = True
                        break
        
        if artist_matched:
            continue
        
        # STRATEGY 2: Genre Classification (Priority 2 - 76% accuracy)
        try:
            classifications = classify_track(sp, track_id)
            
            if classifications:
                # Find the best target playlist for each genre
                genre_matched = False
                for genre in classifications:
                    target_playlist_id = find_best_target_playlist(sp, genre, track_id)
                    
                    if target_playlist_id and target_playlist_id != source_playlist_id:
                        # Verify the playlist exists in our data
                        if target_playlist_id in playlists_dict:
                            # Check if track is already in target playlist
                            target_tracks = playlists_dict[target_playlist_id]["tracks"]
                            existing_track_ids = {t["id"] for t in target_tracks}
                            
                            if track_id not in existing_track_ids:
                                results.add_genre_match(target_playlist_id, track_id)
                                target_name = playlists_dict[target_playlist_id]["name"]
                                print(f"  🎵 Genre match: '{track_name}' → '{target_name}' (genre: {genre})")
                                genre_matched = True
                                break
                
                if not genre_matched:
                    results.add_unclassified(track_id)
                    print(f"  ❓ No suitable playlist found for '{track_name}' (genres: {', '.join(classifications)})")
            else:
                results.add_unclassified(track_id)
                print(f"  ❓ No genre classification for '{track_name}'")
        
        except Exception as e:
            results.add_error(f"Genre classification failed for '{track_name}': {str(e)}")
            results.add_unclassified(track_id)
            print(f"  ❌ Genre classification error for '{track_name}': {e}")
    
    return results


def execute_classifications(sp, playlists_dict: Dict[str, Dict], 
                          results: StagingClassificationResults) -> Dict[str, int]:
    """
    Execute the actual playlist additions based on classification results.
    
    Args:
        sp: Spotify client
        playlists_dict: Dictionary of playlist data
        results: Classification results to execute
        
    Returns:
        Dictionary mapping playlist_id to number of songs successfully added
    """
    songs_added = {}
    
    # Process artist matches first (higher priority)
    if results.artist_matches:
        print("Executing artist-based classifications...")
        for target_playlist_id, track_ids in results.artist_matches.items():
            target_name = playlists_dict[target_playlist_id]["name"]
            
            # Remove duplicates
            unique_track_ids = list(set(track_ids))
            
            if unique_track_ids:
                try:
                    # Add tracks in chunks of 100
                    chunk_size = 100
                    for i in range(0, len(unique_track_ids), chunk_size):
                        chunk = unique_track_ids[i:i + chunk_size]
                        spotify_api_call_with_retry(
                            sp.playlist_add_items, target_playlist_id, chunk
                        )
                    
                    songs_added[target_playlist_id] = len(unique_track_ids)
                    print(f"  ✅ Added {len(unique_track_ids)} songs to '{target_name}' (artist matching)")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(perm_keyword in error_msg for perm_keyword in [
                        'insufficient privileges', 'permission', 'forbidden', 
                        'unauthorized', 'access denied', 'not allowed', 
                        'modify', 'owner', 'collaborative'
                    ]):
                        results.add_error(f"Permission denied for '{target_name}' - skipping")
                        print(f"  ⚠️ Permission denied for '{target_name}' - skipping")
                    else:
                        results.add_error(f"Failed to add tracks to '{target_name}': {e}")
                        print(f"  ❌ Failed to add tracks to '{target_name}': {e}")
    
    # Process genre matches second (lower priority)
    if results.genre_matches:
        print("Executing genre-based classifications...")
        for target_playlist_id, track_ids in results.genre_matches.items():
            target_name = playlists_dict[target_playlist_id]["name"]
            
            # Remove duplicates
            unique_track_ids = list(set(track_ids))
            
            if unique_track_ids:
                try:
                    # Add tracks in chunks of 100
                    chunk_size = 100
                    for i in range(0, len(unique_track_ids), chunk_size):
                        chunk = unique_track_ids[i:i + chunk_size]
                        spotify_api_call_with_retry(
                            sp.playlist_add_items, target_playlist_id, chunk
                        )
                    
                    current_count = songs_added.get(target_playlist_id, 0)
                    songs_added[target_playlist_id] = current_count + len(unique_track_ids)
                    print(f"  ✅ Added {len(unique_track_ids)} songs to '{target_name}' (genre matching)")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(perm_keyword in error_msg for perm_keyword in [
                        'insufficient privileges', 'permission', 'forbidden', 
                        'unauthorized', 'access denied', 'not allowed', 
                        'modify', 'owner', 'collaborative'
                    ]):
                        results.add_error(f"Permission denied for '{target_name}' - skipping")
                        print(f"  ⚠️ Permission denied for '{target_name}' - skipping")
                    else:
                        results.add_error(f"Failed to add tracks to '{target_name}': {e}")
                        print(f"  ❌ Failed to add tracks to '{target_name}': {e}")
    
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
        
        # Classify tracks using multi-strategy approach
        print("Starting multi-strategy classification...")
        results = classify_staging_tracks(sp, playlists_dict, source_playlist_id, 
                                        single_playlist_artists, artist_to_playlists)
        
        # Execute classifications
        songs_added = execute_classifications(sp, playlists_dict, results)
        
        # Build comprehensive notification message
        stats = results.statistics
        total_classified = stats['artist_classification_count'] + stats['genre_classification_count']
        
        if total_classified == 0:
            title = "ℹ️ No Songs Classified"
            message = f"No songs from '{source_name}' could be classified."
            telegram.send_info("No songs classified", f"Processed {stats['total_tracks']} tracks")
        else:
            title = f"✅ Classified {total_classified} Songs"
            
            # Build detailed breakdown
            breakdown = []
            breakdown.append(f"📊 Classification Results:")
            breakdown.append(f"  • Artist matching: {stats['artist_classification_count']} songs (100% accuracy)")
            breakdown.append(f"  • Genre matching: {stats['genre_classification_count']} songs (76% accuracy)")
            breakdown.append(f"  • Unclassified: {stats['unclassified_count']} songs")
            breakdown.append(f"  • Available single-playlist artists: {stats['single_playlist_artists_available']}")
            
            if songs_added:
                breakdown.append(f"")
                breakdown.append(f"🎵 Added to {len(songs_added)} playlists:")
                for target_playlist_id, count in songs_added.items():
                    target_name = playlists_dict[target_playlist_id]["name"]
                    breakdown.append(f"  • {target_name}: +{count}")
            
            if results.errors:
                breakdown.append(f"")
                breakdown.append(f"⚠️ Errors ({len(results.errors)}):")
                for error in results.errors[:3]:  # Show first 3 errors
                    breakdown.append(f"  • {error}")
                if len(results.errors) > 3:
                    breakdown.append(f"  • ... and {len(results.errors) - 3} more errors")
            
            message = "\n".join(breakdown)
            
            # Send success notification
            telegram_summary = f"Artist: {stats['artist_classification_count']}, Genre: {stats['genre_classification_count']}, Unclassified: {stats['unclassified_count']}"
            telegram.send_success(f"Classified {total_classified}/{stats['total_tracks']} songs", telegram_summary)
    
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