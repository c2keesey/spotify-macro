#!/usr/bin/env python3
"""
Debug script to analyze why specific tracks are not getting classified.
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from common.config import CURRENT_ENV
from common.playlist_data_utils import PlaylistDataLoader
from common.shared_cache import get_cached_artist_data
from analysis.genre.composite_classifier import CompositeClassifier
from analysis.genre.classification_metrics import get_track_artists

def debug_track_classification(track_id: str, classifier: CompositeClassifier, playlists_dict: dict):
    """Debug why a specific track isn't getting classified."""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING TRACK: {track_id}")
    print(f"{'='*80}")
    
    # Get track info
    track_info = None
    for playlist_data in playlists_dict.values():
        for track in playlist_data.get('tracks', []):
            if track.get('id') == track_id:
                track_info = track
                break
        if track_info:
            break
    
    if not track_info:
        print("❌ Track not found in playlist data")
        return
    
    print(f"🎵 Track: {track_info.get('name', 'Unknown')}")
    
    # Get artists
    track_artists = get_track_artists(track_id, playlists_dict)
    print(f"👥 Artists ({len(track_artists)}):")
    for artist in track_artists:
        print(f"  - {artist.get('name', 'Unknown')} (ID: {artist.get('id', 'Unknown')})")
    
    # Check artist mappings
    print(f"\n🗂️  ARTIST ANALYSIS:")
    for artist in track_artists:
        artist_id = artist.get('id')
        artist_name = artist.get('name', 'Unknown')
        
        # Check single-folder artists
        if artist_id in classifier.single_folder_artists:
            folder = classifier.single_folder_artists[artist_id]
            print(f"  ✅ {artist_name} → Single-folder artist: {folder}")
        
        # Check multi-folder artists  
        elif artist_id in classifier.artist_folder_mapping:
            folders = list(classifier.artist_folder_mapping[artist_id])
            print(f"  📁 {artist_name} → Multi-folder artist: {folders}")
        
        else:
            print(f"  ❌ {artist_name} → Not in artist mapping")
        
        # Check genre data
        if artist_id in classifier.artist_genres:
            genres = classifier.artist_genres[artist_id]['genres']
            print(f"     🎭 Genres: {genres[:5]}{'...' if len(genres) > 5 else ''}")
        else:
            print(f"     ❌ No genre data")
    
    # Test each classification strategy
    print(f"\n🧪 STRATEGY TESTING:")
    
    # Strategy 1: Single-folder artists
    result = classifier._classify_by_single_folder_artists(track_id)
    print(f"  1️⃣ Single-folder artists: {result}")
    
    # Strategy 2: Composite strategy
    result = classifier._classify_by_composite_strategy(track_id)
    print(f"  2️⃣ Composite strategy: {result}")
    
    # Strategy 3: Genre-only
    result = classifier._classify_by_genre_only(track_id)
    print(f"  3️⃣ Genre-only: {result}")
    
    # Strategy 4: Artist-only
    result = classifier._classify_by_artist_only(track_id)
    print(f"  4️⃣ Artist-only: {result}")
    
    # Strategy 5: Multi-folder artists
    result = classifier._classify_by_multi_folder_artists(track_id)
    print(f"  5️⃣ Multi-folder artists: {result}")
    
    # Strategy 6: Statistical fallback
    result = classifier._classify_by_statistical_fallback(track_id)
    print(f"  6️⃣ Statistical fallback: {result}")
    
    # Full prediction
    print(f"\n🎯 FULL PREDICTION:")
    final_result = classifier.predict(track_id)
    print(f"  Folders: {final_result.predicted_folders}")
    print(f"  Confidence: {getattr(final_result, 'confidence_scores', {})}")
    print(f"  Reasoning: {final_result.reasoning}")

def find_unclassified_samples(playlists_dict):
    """Find some unclassified tracks for debugging."""
    # Find New playlist by name (it's loaded by ID as key)
    new_playlist = None
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data.get('name') == 'New':
            new_playlist = playlist_data
            break
    
    if not new_playlist:
        print("❌ Could not find 'New' playlist")
        return []
    
    tracks = new_playlist.get('tracks', [])
    print(f"📊 Total tracks in New playlist: {len(tracks)}")
    
    if not tracks:
        print("❌ No tracks found in New playlist")
        return []
    
    # Sample first 10 tracks for debugging
    unclassified_samples = []
    for i, track in enumerate(tracks[:10]):
        track_id = track.get('id')
        if track_id:
            unclassified_samples.append({
                'id': track_id,
                'name': track.get('name', 'Unknown'),
                'artists': [a.get('name', 'Unknown') for a in track.get('artists', [])]
            })
    
    return unclassified_samples

def main():
    """Main debugging function."""
    print(f"🐛 UNCLASSIFIED TRACKS DEBUGGER")
    print(f"Environment: {CURRENT_ENV}")
    
    # Load data
    print("📁 Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    print("🗂️  Loading cached artist data...")
    artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
    
    # Initialize classifier
    print("🧠 Initializing classifier...")
    classifier = CompositeClassifier()
    
    # Load playlist folder mapping and build training data (same as real classifier)
    print("📁 Loading folder mapping for training...")
    import json
    with open('data/playlist_folders.json', 'r') as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping: playlist name -> folder name  
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    # Prepare training data using FOLDER NAMES (exactly like real classifier)
    train_tracks = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name in playlist_to_folder and playlist_name != 'New':
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                train_tracks.append((track["id"], folder_name))
    
    train_data = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    print(f"   Training on {len(train_tracks)} tracks")
    classifier.train(train_data)
    
    # Get sample unclassified tracks
    print("🔍 Finding sample tracks to debug...")
    sample_tracks = find_unclassified_samples(playlists_dict)
    
    if not sample_tracks:
        print("❌ No sample tracks found")
        return
    
    print(f"📋 Found {len(sample_tracks)} sample tracks to debug")
    
    # Debug each sample track
    for i, track_info in enumerate(sample_tracks[:5]):  # Debug first 5
        print(f"\n{'🔍' * 20} TRACK {i+1}/{min(5, len(sample_tracks))} {'🔍' * 20}")
        debug_track_classification(track_info['id'], classifier, playlists_dict)
        
        # Don't pause between tracks in automation
        # if i < 4:  # Don't ask after the last one
        #     input("\nPress Enter to continue to next track (or Ctrl+C to exit)...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Debugging stopped by user")
    except Exception as e:
        print(f"\n❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()