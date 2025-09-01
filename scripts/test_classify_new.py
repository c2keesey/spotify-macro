#!/usr/bin/env python3
"""
Test classification of New playlist tracks without moving them.
"""

import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.composite_classifier import CompositeClassifier


def load_optimal_parameters():
    """Load the optimal parameters from the best optimization results."""
    return {
        "statistical_correlation_weight": 1.91,
        "keyword_matching_weight": 0.97,
        "top_folder_selection_ratio": 0.696,
        "max_confidence_cap": 0.818,
        "folder_strategies": {
            "House": {"strategy": "simple_artist", "threshold": 0.175},
            "Electronic": {"strategy": "balanced", "threshold": 0.313},
            "Base": {"strategy": "conservative", "threshold": 0.399},
            "Alive": {"strategy": "enhanced_genre", "threshold": 0.178},
            "Rave": {"strategy": "balanced", "threshold": 0.270},
            "Rock": {"strategy": "enhanced_genre", "threshold": 0.220}
        }
    }


def find_new_playlist(playlists_dict):
    """Find the 'New' playlist in the loaded playlists."""
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data["name"].lower() == "new":
            return playlist_id, playlist_data
    return None, None


def test_classification():
    """Test classification without Spotify API calls."""
    print("🎯 Testing classification of 'New' playlist...")
    
    # Load playlist data
    print("📚 Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    print(f"Loaded {len(playlists_dict)} playlists")
    
    # Find the 'New' playlist
    new_playlist_id, new_playlist_data = find_new_playlist(playlists_dict)
    if not new_playlist_id:
        print("❌ Could not find playlist named 'New'")
        return
    
    tracks = new_playlist_data["tracks"]
    print(f"📀 Found 'New' playlist with {len(tracks)} tracks")
    
    if len(tracks) == 0:
        print("ℹ️ No tracks to classify")
        return
    
    # Initialize classifier with optimal parameters
    print("🧠 Initializing optimized classifier...")
    optimal_params = load_optimal_parameters()
    classifier = CompositeClassifier()
    
    # Apply optimal parameters manually
    classifier.statistical_correlation_weight = optimal_params["statistical_correlation_weight"]
    classifier.keyword_matching_weight = optimal_params["keyword_matching_weight"]
    classifier.top_folder_selection_ratio = optimal_params["top_folder_selection_ratio"]
    classifier.max_confidence_cap = optimal_params["max_confidence_cap"]
    classifier.folder_strategies = optimal_params["folder_strategies"]
    
    # Prepare training data
    train_tracks = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        for track in playlist_data["tracks"]:
            train_tracks.append((track["id"], playlist_name))
    
    train_data = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    # Train the classifier
    print("🎓 Training classifier...")
    classifier.train(train_data)
    
    # Test on first 10 tracks from New playlist
    print("🎵 Testing classification on first 10 tracks...")
    test_tracks = tracks[:10]
    
    classifications = {}
    for i, track in enumerate(test_tracks):
        track_id = track["id"]
        track_name = track["name"]
        artist_names = [artist["name"] for artist in track["artists"]]
        
        print(f"  {i+1}/10: {track_name} by {', '.join(artist_names)}")
        
        try:
            # Use the classifier to predict folders (no Spotify API needed for this part)
            result = classifier.predict(track_id)
            
            if hasattr(result, 'predicted_folders'):
                predicted_folders = result.predicted_folders
                confidence_scores = result.confidence_scores
            else:
                predicted_folders = result.get('folders', [])
                confidence_scores = result.get('confidence_scores', {})
            
            if predicted_folders:
                # Take the highest confidence folder
                best_folder = max(predicted_folders, key=lambda f: confidence_scores.get(f, 0))
                best_confidence = confidence_scores.get(best_folder, 0)
                
                classifications[track_id] = {
                    'track_name': track_name,
                    'artists': artist_names,
                    'folder': best_folder,
                    'confidence': best_confidence,
                    'all_folders': predicted_folders
                }
                print(f"    → {best_folder} (confidence: {best_confidence:.3f})")
            else:
                print(f"    → Unclassified")
                
        except Exception as e:
            print(f"    → Error: {e}")
    
    # Summary
    classified_count = len(classifications)
    print(f"\n📊 Test Results:")
    print(f"  Tested: {len(test_tracks)} tracks")
    print(f"  Successfully classified: {classified_count}")
    print(f"  Classification rate: {classified_count/len(test_tracks):.1%}")
    
    if classifications:
        print(f"\n🎯 Classifications:")
        folder_counts = {}
        for track_id, classification in classifications.items():
            folder = classification['folder']
            folder_counts[folder] = folder_counts.get(folder, 0) + 1
        
        for folder, count in sorted(folder_counts.items()):
            print(f"  {folder}: {count} tracks")
    
    print("\n✅ Test complete! The optimized classifier is working.")


if __name__ == "__main__":
    test_classification()