#!/usr/bin/env python3
"""
Debug the high-coverage classifier to see what's causing the unpacking error.
"""

import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from analysis.genre.high_coverage_classifier import HighCoverageClassifier
from common.playlist_data_utils import PlaylistDataLoader


def debug_high_coverage():
    """Debug what's causing the unpacking error."""
    
    print("🔍 DEBUGGING HIGH-COVERAGE CLASSIFIER")
    print("=" * 50)
    
    # Load data
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Load folder mapping
    with open(project_root / "data" / "playlist_folders.json", "r") as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    # Create training data
    train_tracks_list = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"][:2]:  # Just first 2 tracks per playlist
                train_tracks_list.append((track["id"], folder_name))
    
    print(f"📊 Training with {len(train_tracks_list)} tracks")
    
    # Test one classifier
    classifier = HighCoverageClassifier("aggressive_coverage")
    
    try:
        print("🧠 Training classifier...")
        classifier.train(train_tracks_list)
        print("✅ Training successful")
        
        # Test prediction on one track
        if train_tracks_list:
            test_track_id = train_tracks_list[0][0]
            print(f"🎵 Testing prediction on track: {test_track_id}")
            
            result = classifier.predict(test_track_id)
            print(f"✅ Prediction result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_high_coverage()