#!/usr/bin/env python3
"""
Simple test of high-coverage strategies on New playlist sample.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from analysis.genre.high_coverage_classifier import create_strategy_variants
from analysis.genre.composite_classifier import CompositeClassifier
from common.playlist_data_utils import PlaylistDataLoader


def test_coverage_on_new_playlist():
    """Test coverage strategies on a sample of the 'New' playlist."""
    
    print("🎵 TESTING HIGH-COVERAGE STRATEGIES ON 'NEW' PLAYLIST")
    print("=" * 60)
    
    # Load playlist data
    print("📚 Loading data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Load folder mapping (folder -> [playlist files])
    with open(project_root / "data" / "playlist_folders.json", "r") as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping: playlist name -> folder name
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            # Remove .json extension to get playlist name
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    print(f"📁 Loaded mapping for {len(playlist_to_folder)} playlists to {len(playlist_folders)} folders")
    
    # Find "New" playlist
    new_playlist = None
    for playlist_data in playlists_dict.values():
        if playlist_data["name"] == "New":
            new_playlist = playlist_data
            break
    
    if not new_playlist:
        print("❌ Could not find 'New' playlist")
        return
    
    # Take a larger sample for testing (first 1000 tracks)
    sample_tracks = new_playlist["tracks"][:1000]
    sample_track_ids = [track["id"] for track in sample_tracks]
    
    print(f"📀 Testing on {len(sample_tracks)} tracks from 'New' playlist")
    print()
    
    # Create folder-mapped training data in the format expected by classifiers
    train_tracks_list = []
    folder_track_counts = {}
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        
        # Map playlist name to folder name
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            
            # Count tracks per folder for stats
            if folder_name not in folder_track_counts:
                folder_track_counts[folder_name] = 0
            
            for track in playlist_data["tracks"]:
                train_tracks_list.append((track["id"], folder_name))
                folder_track_counts[folder_name] += 1
    
    print(f"📊 Training data: {len(train_tracks_list)} tracks across {len(folder_track_counts)} folders:")
    for folder, count in sorted(folder_track_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"     {folder}: {count} tracks")
    
    # Create dict format for composite classifier
    train_data_dict = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks_list
    }
    print()
    
    # Test strategies
    strategy_variants = create_strategy_variants()
    
    # Add current composite classifier for comparison (with optimized thresholds)
    current_composite = CompositeClassifier()
    
    # Apply the current optimized thresholds manually
    current_composite.folder_strategies.update({
        "House": {"strategy": "simple_artist", "threshold": 0.175, "boost": 0.9},
        "Electronic": {"strategy": "balanced", "threshold": 0.313, "boost": 0.5},
        "Base": {"strategy": "conservative", "threshold": 0.399, "boost": 0.7},
        "Alive": {"strategy": "enhanced_genre", "threshold": 0.178, "boost": 0.8},
        "Rave": {"strategy": "balanced", "threshold": 0.270, "boost": 0.6},
        "Rock": {"strategy": "enhanced_genre", "threshold": 0.220, "boost": 0.9}
    })
    
    # Test basic composite with different thresholds
    aggressive_composite = CompositeClassifier()
    # Apply much lower thresholds for higher coverage
    aggressive_composite.folder_strategies.update({
        "House": {"strategy": "simple_artist", "threshold": 0.05, "boost": 0.9},
        "Electronic": {"strategy": "balanced", "threshold": 0.05, "boost": 0.5},
        "Base": {"strategy": "conservative", "threshold": 0.05, "boost": 0.7},
        "Alive": {"strategy": "enhanced_genre", "threshold": 0.05, "boost": 0.8},
        "Rave": {"strategy": "balanced", "threshold": 0.05, "boost": 0.6},
        "Rock": {"strategy": "enhanced_genre", "threshold": 0.05, "boost": 0.9},
        "Vibes": {"strategy": "simple_artist", "threshold": 0.03, "boost": 0.6},
        "Sierra": {"strategy": "balanced", "threshold": 0.05, "boost": 0.7},
        "Ride": {"strategy": "conservative", "threshold": 0.03, "boost": 0.7},
        "Funk Soul": {"strategy": "balanced", "threshold": 0.05, "boost": 0.8},
        "Reggae": {"strategy": "enhanced_genre", "threshold": 0.05, "boost": 1.0},
        "Spiritual": {"strategy": "conservative", "threshold": 0.03, "boost": 0.7},
        "Soft": {"strategy": "conservative", "threshold": 0.05, "boost": 0.9},
        "Chill": {"strategy": "conservative", "threshold": 0.02, "boost": 0.6}
    })
    
    all_classifiers = [
        ("Current Optimized (Baseline)", current_composite),
        ("Aggressive Low Thresholds", aggressive_composite)
    ]
    
    results = []
    
    for name, classifier in all_classifiers:
        print(f"🧠 Testing: {name}")
        
        try:
            # Train classifier with appropriate data format
            if "High Coverage" in name:
                # High-coverage classifiers expect list format
                classifier.train(train_tracks_list)
            else:
                # Composite classifier expects dict format  
                classifier.train(train_data_dict)
            
            # Test on sample
            classified = 0
            classifications = defaultdict(int)
            
            for track_id in sample_track_ids:
                prediction = classifier.predict(track_id)
                
                # Handle different return types
                if hasattr(prediction, 'predicted_folders'):
                    # CompositeClassifier returns ClassificationResult
                    if prediction.predicted_folders:
                        classified += 1
                        folder = prediction.predicted_folders[0]  # Take first prediction
                        classifications[folder] += 1
                elif prediction:
                    # High-coverage classifiers return string or None
                    classified += 1
                    classifications[prediction] += 1
            
            coverage = (classified / len(sample_track_ids)) * 100
            
            result = {
                'name': name,
                'coverage': coverage,
                'classified': classified,
                'total': len(sample_track_ids),
                'classifications': dict(classifications)
            }
            
            results.append(result)
            
            print(f"   Coverage: {coverage:.1f}% ({classified}/{len(sample_track_ids)})")
            
            if classifications:
                top_folders = sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"   Top classifications: {dict(top_folders)}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
    
    # Summary
    print("📊 COVERAGE COMPARISON SUMMARY")
    print("=" * 40)
    
    results.sort(key=lambda x: x['coverage'], reverse=True)
    
    print(f"{'Strategy':<25} {'Coverage':<12} {'Classified'}")
    print("-" * 45)
    
    baseline_coverage = None
    for result in results:
        if "Baseline" in result['name']:
            baseline_coverage = result['coverage']
            break
    
    for result in results:
        coverage = result['coverage']
        classified = result['classified']
        
        if baseline_coverage and "Baseline" not in result['name']:
            improvement = coverage - baseline_coverage
            coverage_str = f"{coverage:.1f}% (+{improvement:.1f})"
        else:
            coverage_str = f"{coverage:.1f}%"
        
        print(f"{result['name']:<25} {coverage_str:<12} {classified}/{result['total']}")
    
    print()
    
    # Best strategy
    if results:
        best = results[0]
        if best['coverage'] > (baseline_coverage or 0):
            improvement = best['coverage'] - (baseline_coverage or 0)
            print(f"🏆 Best strategy: {best['name']}")
            print(f"   Improvement: +{improvement:.1f}% coverage")
            print(f"   Classifications: {best['classifications']}")
        else:
            print("🤔 No significant improvement found - may need further tuning")
    
    return results


if __name__ == "__main__":
    try:
        results = test_coverage_on_new_playlist()
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()