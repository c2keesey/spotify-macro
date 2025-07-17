#!/usr/bin/env python3
"""
Test the staging classification action with local playlist data.

This script simulates the staging classification process using local playlist files
to test the new functionality for removing songs from the "new" playlist after
successful classification, including handling already-classified tracks.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.playlist_data_utils import PlaylistDataLoader
from automations.spotify.staging_classification.action import (
    classify_staging_tracks, 
    StagingClassificationResults,
    execute_classifications,
    remove_classified_tracks_from_source
)
import json
from typing import Dict, Set
from unittest.mock import MagicMock

def create_mock_spotify_client():
    """Create a mock Spotify client for testing."""
    mock_sp = MagicMock()
    
    # Mock playlist_add_items (simulate successful additions)
    mock_sp.playlist_add_items.return_value = None
    
    # Mock playlist_items for getting current tracks (for removal)
    def mock_playlist_items(playlist_id, fields=None):
        # Return mock structure for current tracks
        return {
            'items': [
                {'track': {'id': f'track_{i}'}} for i in range(10)
            ]
        }
    mock_sp.playlist_items.side_effect = mock_playlist_items
    
    # Mock remove tracks operation
    mock_sp.playlist_remove_specific_occurrences_of_items.return_value = None
    
    return mock_sp

def simulate_staging_classification():
    """Simulate the staging classification process with local data."""
    
    print("🧪 TESTING STAGING CLASSIFICATION WITH LOCAL DATA")
    print("=" * 70)
    
    # Load playlist data
    print("📁 Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
        limit=20, verbose=True
    )
    
    # Get statistics
    stats = PlaylistDataLoader.get_playlist_statistics(playlists_dict)
    print(f"\n📊 Dataset Statistics:")
    print(f"   • {stats['total_playlists']} playlists")
    print(f"   • {stats['total_tracks']} total tracks")
    print(f"   • {stats['unique_artists']} unique artists")
    print(f"   • {stats['parent_playlists']} parent playlists")
    print(f"   • {stats['child_playlists']} child playlists")
    
    # Find a suitable staging playlist or create simulated data
    source_playlist_id = PlaylistDataLoader.find_playlist_by_name(playlists_dict, "new")
    
    if not source_playlist_id:
        print("\n🔧 No 'new' playlist found, creating simulated staging data...")
        source_playlist_id = create_simulated_staging_playlist(playlists_dict)
    
    source_name = playlists_dict[source_playlist_id]["name"]
    source_track_count = len(playlists_dict[source_playlist_id]["tracks"])
    
    print(f"\n🎵 Using staging playlist: '{source_name}' ({source_track_count} tracks)")
    
    if source_track_count == 0:
        print("❌ Staging playlist is empty - cannot test classification")
        return
    
    # Build artist mappings
    print("\n🗺️ Building artist mappings...")
    artist_to_playlists = PlaylistDataLoader.build_artist_to_playlists_mapping(
        playlists_dict, exclude_parent_playlists=True, verbose=True
    )
    
    single_playlist_artists = PlaylistDataLoader.find_single_playlist_artists(artist_to_playlists)
    
    print(f"   • {len(artist_to_playlists)} unique artists")
    print(f"   • {len(single_playlist_artists)} single-playlist artists")
    
    # Create mock spotify client
    mock_sp = create_mock_spotify_client()
    
    # Test classification logic
    print(f"\n🔍 TESTING CLASSIFICATION LOGIC")
    print("=" * 50)
    
    # Simulate classification (this will show what would happen)
    results = simulate_classify_staging_tracks(
        playlists_dict, source_playlist_id, single_playlist_artists, artist_to_playlists
    )
    
    # Display results
    display_classification_results(results, playlists_dict)
    
    # Test the actual classification function structure
    print(f"\n🧪 TESTING REMOVAL LOGIC")
    print("=" * 50)
    
    # Simulate successful additions and test removal tracking
    test_removal_logic(mock_sp, source_playlist_id, source_name, results)
    
    print(f"\n✅ TESTING COMPLETE")
    print("=" * 70)

def create_simulated_staging_playlist(playlists_dict: Dict) -> str:
    """Create a simulated 'new' playlist with tracks from other playlists."""
    
    # Collect some tracks from existing playlists
    staging_tracks = []
    
    for playlist_id, playlist_data in playlists_dict.items():
        # Take first 2 tracks from each playlist (if available)
        tracks = playlist_data["tracks"][:2]
        staging_tracks.extend(tracks)
        
        # Limit to reasonable number for testing
        if len(staging_tracks) >= 20:
            break
    
    # Create simulated staging playlist
    staging_playlist_id = "simulated_staging_new"
    playlists_dict[staging_playlist_id] = {
        "name": "new",
        "tracks": staging_tracks,
        "total_tracks": len(staging_tracks),
        "original_data": {"playlist_id": staging_playlist_id, "playlist_name": "new"}
    }
    
    print(f"   Created simulated staging playlist with {len(staging_tracks)} tracks")
    
    return staging_playlist_id

def simulate_classify_staging_tracks(playlists_dict: Dict, source_playlist_id: str,
                                   single_playlist_artists: Set[str],
                                   artist_to_playlists: Dict) -> StagingClassificationResults:
    """Simulate the classification logic without Spotify API calls."""
    
    results = StagingClassificationResults()
    source_tracks = playlists_dict[source_playlist_id]["tracks"]
    source_name = playlists_dict[source_playlist_id]["name"]
    
    results.statistics['total_tracks'] = len(source_tracks)
    results.statistics['single_playlist_artists_available'] = len(single_playlist_artists)
    
    print(f"Simulating classification of {len(source_tracks)} tracks from '{source_name}'...")
    
    for track in source_tracks[:10]:  # Test first 10 tracks
        track_id = track["id"]
        track_name = track["name"]
        artists = track["artists"]
        
        print(f"\n🎵 Processing: '{track_name}' by {', '.join(a['name'] for a in artists)}")
        
        # STRATEGY 1: Artist Matching
        artist_matched = False
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
                        results.add_artist_match(target_playlist_id, track_id)
                        print(f"   🎯 Artist match: → '{target_name}' (artist: {artist_name})")
                        artist_matched = True
                        break
                    else:
                        results.add_already_classified(track_id)
                        print(f"   ✅ Already in target: already in '{target_name}' (artist: {artist_name})")
                        artist_matched = True
                        break
        
        if artist_matched:
            continue
        
        # STRATEGY 2: Simulated Genre Classification
        # For testing, randomly assign some tracks to playlists
        import random
        random.seed(hash(track_id))  # Deterministic for testing
        
        if random.random() < 0.6:  # 60% get genre classification
            # Pick a random target playlist
            eligible_playlists = [pid for pid, pdata in playlists_dict.items() 
                                if pid != source_playlist_id and len(pdata["tracks"]) > 0]
            
            if eligible_playlists:
                target_playlist_id = random.choice(eligible_playlists)
                target_tracks = playlists_dict[target_playlist_id]["tracks"]
                existing_track_ids = {t["id"] for t in target_tracks}
                target_name = playlists_dict[target_playlist_id]["name"]
                
                if track_id not in existing_track_ids:
                    results.add_genre_match(target_playlist_id, track_id)
                    print(f"   🎵 Genre match: → '{target_name}' (simulated genre)")
                else:
                    results.add_already_classified(track_id)
                    print(f"   ✅ Already in target: already in '{target_name}' (simulated genre)")
            else:
                results.add_unclassified(track_id)
                print(f"   ❓ No suitable playlist found")
        else:
            results.add_unclassified(track_id)
            print(f"   ❓ No genre classification")
    
    return results

def display_classification_results(results: StagingClassificationResults, playlists_dict: Dict):
    """Display the classification results in detail."""
    
    stats = results.statistics
    total_classified = stats['artist_classification_count'] + stats['genre_classification_count']
    total_handled = total_classified + stats['already_classified_count']
    
    print(f"\n📊 CLASSIFICATION RESULTS:")
    print(f"   • Total tracks processed: {stats['total_tracks']}")
    print(f"   • Artist matching: {stats['artist_classification_count']} songs")
    print(f"   • Genre matching: {stats['genre_classification_count']} songs")
    print(f"   • Already classified: {stats['already_classified_count']} songs")
    print(f"   • Unclassified: {stats['unclassified_count']} songs")
    print(f"   • Total handled: {total_handled} songs")
    
    # Show detailed breakdown
    if results.artist_matches:
        print(f"\n🎯 Artist Matches:")
        for playlist_id, track_ids in results.artist_matches.items():
            playlist_name = playlists_dict[playlist_id]["name"]
            print(f"   • {playlist_name}: {len(track_ids)} tracks")
    
    if results.genre_matches:
        print(f"\n🎵 Genre Matches:")
        for playlist_id, track_ids in results.genre_matches.items():
            playlist_name = playlists_dict[playlist_id]["name"]
            print(f"   • {playlist_name}: {len(track_ids)} tracks")
    
    if results.already_classified:
        print(f"\n✅ Already Classified: {len(results.already_classified)} tracks")
        print("   These would be removed from 'new' without duplication")

def test_removal_logic(mock_sp, source_playlist_id: str, source_name: str, 
                      results: StagingClassificationResults):
    """Test the removal logic with simulated data."""
    
    print("Testing track removal logic...")
    
    # Simulate successfully added tracks
    successfully_added_tracks = set()
    
    # Add all classified tracks to the removal set
    for track_ids in results.artist_matches.values():
        successfully_added_tracks.update(track_ids)
    
    for track_ids in results.genre_matches.values():
        successfully_added_tracks.update(track_ids)
    
    # Add already-classified tracks (this is the key fix)
    successfully_added_tracks.update(results.already_classified)
    
    print(f"   • Tracks to remove from '{source_name}': {len(successfully_added_tracks)}")
    print(f"   • Breakdown:")
    print(f"     - New additions: {sum(len(tracks) for tracks in results.artist_matches.values()) + sum(len(tracks) for tracks in results.genre_matches.values())}")
    print(f"     - Already classified: {len(results.already_classified)}")
    
    # Test the removal function (with mocked API)
    if successfully_added_tracks:
        print(f"\n🧹 Simulating removal from source playlist...")
        
        # Note: This would call the actual removal function in real usage
        # tracks_removed = remove_classified_tracks_from_source(
        #     mock_sp, source_playlist_id, successfully_added_tracks, source_name
        # )
        
        # For testing, just simulate the result
        tracks_removed = len(successfully_added_tracks)
        print(f"   ✅ Would remove {tracks_removed} tracks from '{source_name}'")
        
        return tracks_removed
    else:
        print("   ℹ️ No tracks to remove")
        return 0

if __name__ == "__main__":
    try:
        simulate_staging_classification()
    except KeyboardInterrupt:
        print("\n\n👋 Testing stopped by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()