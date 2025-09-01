#!/usr/bin/env python3
"""
Comprehensive coverage test using existing infrastructure.

Tests both:
1. 80/20 split of sorted songs (proper validation) 
2. Full "New" playlist (real-world coverage)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from analysis.genre.composite_classifier import CompositeClassifier
from analysis.genre.classification_metrics import split_train_test_playlists
from common.playlist_data_utils import PlaylistDataLoader
from tests.test_data_utils import TestDataManager


def load_folder_mapping() -> Dict[str, str]:
    """Load the playlist to folder mapping."""
    with open(project_root / "data" / "playlist_folders.json", "r") as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping: playlist name -> folder name
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    return playlist_to_folder


def create_train_test_data(playlists_dict: Dict, playlist_to_folder: Dict, test_ratio: float = 0.2) -> Tuple[List, List, Dict]:
    """Create train/test split using existing infrastructure."""
    
    # Use existing split_train_test_playlists function
    train_ratio = 1.0 - test_ratio  # Convert test_ratio to train_ratio
    train_playlist_ids, test_playlist_ids = split_train_test_playlists(
        playlists_dict, train_ratio=train_ratio, random_seed=42
    )
    
    print(f"📊 Split: {len(train_playlist_ids)} train playlists, {len(test_playlist_ids)} test playlists")
    
    # Create train data
    train_tracks = []
    train_folder_counts = defaultdict(int)
    
    for playlist_id in train_playlist_ids:
        if playlist_id not in playlists_dict:
            continue
        playlist_data = playlists_dict[playlist_id]
        playlist_name = playlist_data["name"]
        
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                train_tracks.append((track["id"], folder_name))
                train_folder_counts[folder_name] += 1
    
    # Create test data  
    test_tracks = []
    test_folder_counts = defaultdict(int)
    
    for playlist_id in test_playlist_ids:
        if playlist_id not in playlists_dict:
            continue
        playlist_data = playlists_dict[playlist_id]
        playlist_name = playlist_data["name"]
        
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                test_tracks.append((track["id"], folder_name))
                test_folder_counts[folder_name] += 1
    
    # Create training data dict for classifiers
    train_data_dict = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    return train_tracks, test_tracks, train_data_dict


def evaluate_classifier_on_test_set(classifier, test_tracks: List) -> Dict:
    """Evaluate classifier on test set and return metrics."""
    
    total_tracks = len(test_tracks)
    classified_tracks = 0
    correct_predictions = 0
    folder_predictions = defaultdict(lambda: {'correct': 0, 'total': 0, 'predicted': 0})
    
    print(f"  🧪 Evaluating on {total_tracks} test tracks...")
    
    for track_id, true_folder in test_tracks:
        prediction = classifier.predict(track_id)
        
        # Handle CompositeClassifier result format
        predicted_folder = None
        if hasattr(prediction, 'predicted_folders') and prediction.predicted_folders:
            predicted_folder = prediction.predicted_folders[0]
            classified_tracks += 1
        elif isinstance(prediction, str):
            predicted_folder = prediction
            classified_tracks += 1
        
        # Update metrics
        folder_predictions[true_folder]['total'] += 1
        
        if predicted_folder:
            folder_predictions[predicted_folder]['predicted'] += 1
            if predicted_folder == true_folder:
                correct_predictions += 1
                folder_predictions[true_folder]['correct'] += 1
    
    # Calculate overall metrics
    coverage = (classified_tracks / total_tracks) * 100 if total_tracks > 0 else 0
    accuracy = (correct_predictions / total_tracks) * 100 if total_tracks > 0 else 0
    
    # Calculate per-folder metrics
    folder_metrics = {}
    for folder, counts in folder_predictions.items():
        precision = (counts['correct'] / counts['predicted']) * 100 if counts['predicted'] > 0 else 0
        recall = (counts['correct'] / counts['total']) * 100 if counts['total'] > 0 else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
        
        folder_metrics[folder] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'total_true': counts['total'],
            'total_predicted': counts['predicted'],
            'correct': counts['correct']
        }
    
    return {
        'coverage': coverage,
        'accuracy': accuracy,
        'classified_tracks': classified_tracks,
        'total_tracks': total_tracks,
        'correct_predictions': correct_predictions,
        'folder_metrics': folder_metrics
    }


def test_on_new_playlist(classifier, playlists_dict: Dict) -> Dict:
    """Test classifier on full 'New' playlist."""
    
    # Find "New" playlist
    new_playlist = None
    for playlist_data in playlists_dict.values():
        if playlist_data["name"] == "New":
            new_playlist = playlist_data
            break
    
    if not new_playlist:
        print("❌ Could not find 'New' playlist")
        return {}
    
    tracks = new_playlist["tracks"]
    print(f"  🎵 Testing on full 'New' playlist ({len(tracks)} tracks)...")
    
    classified = 0
    classifications = defaultdict(int)
    
    for track in tracks:
        track_id = track["id"]
        prediction = classifier.predict(track_id)
        
        # Handle different return types
        if hasattr(prediction, 'predicted_folders') and prediction.predicted_folders:
            classified += 1
            folder = prediction.predicted_folders[0]
            classifications[folder] += 1
        elif isinstance(prediction, str):
            classified += 1
            classifications[prediction] += 1
    
    coverage = (classified / len(tracks)) * 100
    
    return {
        'coverage': coverage,
        'classified_tracks': classified,
        'total_tracks': len(tracks),
        'classifications': dict(classifications)
    }


def run_comprehensive_coverage_test():
    """Run comprehensive coverage test on both validation and real data."""
    
    print("🧪 COMPREHENSIVE COVERAGE TEST")
    print("=" * 60)
    print("Testing on:")
    print("1. 80/20 split of sorted songs (validation)")
    print("2. Full 'New' playlist (real-world coverage)")
    print()
    
    # Load data
    print("📚 Loading data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    playlist_to_folder = load_folder_mapping()
    
    print(f"📁 Loaded {len(playlists_dict)} playlists")
    print(f"🗂️ Mapped {len(playlist_to_folder)} playlists to folders")
    print()
    
    # Create train/test split for validation
    print("🔀 Creating 80/20 train/test split...")
    train_tracks, test_tracks, train_data_dict = create_train_test_data(
        playlists_dict, playlist_to_folder, test_ratio=0.2
    )
    
    print(f"   Training: {len(train_tracks)} tracks")
    print(f"   Testing: {len(test_tracks)} tracks")
    print()
    
    # Set up classifiers
    print("🧠 Setting up classifiers...")
    
    # 1. Current optimized thresholds (baseline)
    current_classifier = CompositeClassifier()
    current_classifier.folder_strategies.update({
        "House": {"strategy": "simple_artist", "threshold": 0.175, "boost": 0.9},
        "Electronic": {"strategy": "balanced", "threshold": 0.313, "boost": 0.5},
        "Base": {"strategy": "conservative", "threshold": 0.399, "boost": 0.7},
        "Alive": {"strategy": "enhanced_genre", "threshold": 0.178, "boost": 0.8},
        "Rave": {"strategy": "balanced", "threshold": 0.270, "boost": 0.6},
        "Rock": {"strategy": "enhanced_genre", "threshold": 0.220, "boost": 0.9}
    })
    
    # 2. Aggressive low thresholds
    aggressive_classifier = CompositeClassifier()
    aggressive_classifier.folder_strategies.update({
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
    
    classifiers = [
        ("Current Optimized", current_classifier),
        ("Aggressive Thresholds", aggressive_classifier)
    ]
    
    results = {}
    
    for name, classifier in classifiers:
        print(f"🔬 Testing: {name}")
        
        # Train classifier
        print("  📖 Training...")
        classifier.train(train_data_dict)
        
        # Test 1: Validation on 80/20 split
        print("  🧪 Validation on 80/20 split...")
        validation_results = evaluate_classifier_on_test_set(classifier, test_tracks)
        
        # Test 2: Real-world on full "New" playlist
        print("  🎵 Real-world test on 'New' playlist...")
        new_playlist_results = test_on_new_playlist(classifier, playlists_dict)
        
        results[name] = {
            'validation': validation_results,
            'new_playlist': new_playlist_results
        }
        
        print(f"     Validation Coverage: {validation_results['coverage']:.1f}%")
        print(f"     Validation Accuracy: {validation_results['accuracy']:.1f}%")
        print(f"     New Playlist Coverage: {new_playlist_results.get('coverage', 0):.1f}%")
        print()
    
    # Summary comparison
    print("📊 COMPREHENSIVE RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"{'Classifier':<20} {'Val Coverage':<12} {'Val Accuracy':<12} {'New Coverage':<12}")
    print("-" * 60)
    
    for name, result in results.items():
        val_cov = result['validation']['coverage']
        val_acc = result['validation']['accuracy']
        new_cov = result['new_playlist'].get('coverage', 0)
        
        print(f"{name:<20} {val_cov:>8.1f}%     {val_acc:>8.1f}%     {new_cov:>8.1f}%")
    
    print()
    
    # Detailed analysis
    print("🔍 DETAILED ANALYSIS")
    print("-" * 30)
    
    for name, result in results.items():
        print(f"\n{name}:")
        
        val_result = result['validation']
        new_result = result['new_playlist']
        
        print(f"  Validation (80/20 split):")
        print(f"    Coverage: {val_result['coverage']:.1f}% ({val_result['classified_tracks']}/{val_result['total_tracks']})")
        print(f"    Accuracy: {val_result['accuracy']:.1f}% ({val_result['correct_predictions']}/{val_result['total_tracks']})")
        
        print(f"  New Playlist (real-world):")
        print(f"    Coverage: {new_result.get('coverage', 0):.1f}% ({new_result.get('classified_tracks', 0)}/{new_result.get('total_tracks', 0)})")
        
        if 'classifications' in new_result:
            top_classifications = sorted(new_result['classifications'].items(), 
                                       key=lambda x: x[1], reverse=True)[:5]
            print(f"    Top classifications: {dict(top_classifications)}")
    
    # Performance gap analysis
    print(f"\n🎯 PERFORMANCE GAP ANALYSIS")
    print("-" * 35)
    
    for name, result in results.items():
        val_cov = result['validation']['coverage']
        new_cov = result['new_playlist'].get('coverage', 0)
        gap = new_cov - val_cov
        
        print(f"{name}:")
        print(f"  Validation → Real-world gap: {gap:+.1f}% ({val_cov:.1f}% → {new_cov:.1f}%)")
        
        if gap < -10:
            print(f"  ⚠️  Large negative gap suggests validation optimism")
        elif gap > 10:
            print(f"  ✅ Positive gap suggests robust performance")
        else:
            print(f"  📊 Reasonable gap between validation and real-world")
    
    return results


if __name__ == "__main__":
    try:
        results = run_comprehensive_coverage_test()
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()