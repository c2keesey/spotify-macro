#!/usr/bin/env python3
"""
Test and compare high-coverage strategies for pre-sorting workflow.

This script tests multiple coverage-focused strategies against the current
optimized classifier to see which provides the best coverage improvement.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from analysis.genre.classification_framework import BaseClassifier
    from analysis.genre.classification_metrics import (
        load_test_data, split_train_test_playlists, create_train_test_split,
        build_artist_folder_mapping, get_single_folder_artists, get_track_artists
    )
    from analysis.genre.current_classifier import CurrentArtistOnlyClassifier  
    from analysis.genre.composite_classifier import CompositeClassifier
    from analysis.genre.high_coverage_classifier import create_strategy_variants
    from analysis.optimization.run_full_optimization import OptimizedCompositeClassifier
    from common.playlist_data_utils import PlaylistDataLoader
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def load_current_optimal_params():
    """Load the current optimized parameters."""
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


def test_strategy_comparison():
    """Test and compare all strategies for coverage and quality."""
    
    print("🔬 HIGH-COVERAGE STRATEGY COMPARISON")
    print("=" * 60)
    
    # Load data
    print("📚 Loading training data...")
    
    # Load playlist data with folder mapping
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Load folder mapping
    with open(project_root / "data" / "playlist_folders.json", "r") as f:
        playlist_to_folder = json.load(f)
    
    # Create folder-mapped training data
    folder_mapped_data = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                folder_mapped_data.append((track["id"], folder_name))
    
    # Split into train/test by playlist
    train_playlists, test_playlists = split_train_test_playlists(playlists_dict, test_ratio=0.2)
    
    # Create train/test data
    train_data = []
    test_data = []
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name not in playlist_to_folder:
            continue
        
        folder_name = playlist_to_folder[playlist_name]
        track_data = [(track["id"], folder_name) for track in playlist_data["tracks"]]
        
        if playlist_id in train_playlists:
            train_data.extend(track_data)
        elif playlist_id in test_playlists:
            test_data.extend(track_data)
    
    print(f"   Training tracks: {len(train_data)}")
    print(f"   Test tracks: {len(test_data)}")
    print()
    
    # Initialize all classifiers
    classifiers = []
    
    # 1. Current optimized classifier (baseline)
    print("🏭 Setting up classifiers...")
    optimal_params = load_current_optimal_params()
    current_optimized = OptimizedCompositeClassifier()
    current_optimized.apply_parameters(optimal_params)
    classifiers.append(("Current Optimized (Baseline)", current_optimized))
    
    # 2. Basic composite classifier (pre-optimization baseline)
    basic_composite = CompositeClassifier()
    classifiers.append(("Basic Composite", basic_composite))
    
    # 3. High-coverage strategy variants
    strategy_variants = create_strategy_variants()
    for classifier in strategy_variants:
        classifiers.append((classifier.name, classifier))
    
    print(f"   Testing {len(classifiers)} classifiers")
    print()
    
    # Test each classifier
    results = []
    
    for name, classifier in classifiers:
        print(f"🧠 Testing: {name}")
        
        # Train classifier
        classifier.train(train_data)
        
        # Evaluate on test set
        total_tracks = len(test_data)
        classified_tracks = 0
        correct_predictions = 0
        predictions_by_folder = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
        
        for track_id, true_folder in test_data:
            prediction = classifier.predict(track_id)
            
            if prediction is not None:
                classified_tracks += 1
                if prediction == true_folder:
                    correct_predictions += 1
                    predictions_by_folder[true_folder]['tp'] += 1
                else:
                    predictions_by_folder[prediction]['fp'] += 1
                    predictions_by_folder[true_folder]['fn'] += 1
            else:
                predictions_by_folder[true_folder]['fn'] += 1
        
        # Calculate metrics
        accuracy = correct_predictions / total_tracks if total_tracks > 0 else 0
        coverage = (classified_tracks / total_tracks) * 100
        
        # Calculate precision, recall, F1 across all folders
        precisions = []
        recalls = []
        f1_scores = []
        
        for folder_metrics in predictions_by_folder.values():
            tp = folder_metrics['tp']
            fp = folder_metrics['fp'] 
            fn = folder_metrics['fn']
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            precisions.append(precision)
            recalls.append(recall)
            f1_scores.append(f1)
        
        avg_precision = sum(precisions) / len(precisions) if precisions else 0
        avg_recall = sum(recalls) / len(recalls) if recalls else 0
        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0
        
        result = {
            'name': name,
            'accuracy': accuracy,
            'precision': avg_precision,
            'recall': avg_recall, 
            'f1_score': avg_f1,
            'coverage': coverage,
            'classified_tracks': classified_tracks,
            'total_tracks': total_tracks
        }
        
        results.append(result)
        
        print(f"   Accuracy: {accuracy:.3f}")
        print(f"   Precision: {avg_precision:.3f}")
        print(f"   Recall: {avg_recall:.3f}")
        print(f"   F1 Score: {avg_f1:.3f}")
        print(f"   Coverage: {coverage:.1f}% ({classified_tracks}/{total_tracks})")
        print()
    
    # Summary comparison
    print("📊 STRATEGY COMPARISON SUMMARY")
    print("=" * 60)
    
    # Sort by coverage (primary goal)
    results.sort(key=lambda x: x['coverage'], reverse=True)
    
    print(f"{'Strategy':<35} {'Coverage':<10} {'F1':<8} {'Recall':<8} {'Precision':<10}")
    print("-" * 75)
    
    baseline_coverage = None
    for result in results:
        if "Baseline" in result['name']:
            baseline_coverage = result['coverage']
            break
    
    for result in results:
        coverage = result['coverage']
        f1 = result['f1_score']
        recall = result['recall']
        precision = result['precision']
        
        # Show improvement vs baseline
        if baseline_coverage and "Baseline" not in result['name']:
            improvement = coverage - baseline_coverage
            coverage_str = f"{coverage:.1f}% (+{improvement:.1f})"
        else:
            coverage_str = f"{coverage:.1f}%"
        
        print(f"{result['name']:<35} {coverage_str:<10} {f1:.3f}    {recall:.3f}    {precision:.3f}")
    
    print()
    
    # Find best strategies
    best_coverage = max(results, key=lambda x: x['coverage'])
    best_balanced = max(results, key=lambda x: x['f1_score'] * 0.4 + x['coverage'] / 100 * 0.6)
    
    print("🏆 RECOMMENDATIONS")
    print("-" * 30)
    print(f"Best Coverage: {best_coverage['name']} ({best_coverage['coverage']:.1f}%)")
    print(f"Best Balanced: {best_balanced['name']} (Coverage: {best_balanced['coverage']:.1f}%, F1: {best_balanced['f1_score']:.3f})")
    
    return results


def test_on_new_playlist_sample():
    """Test strategies on a sample of the actual 'New' playlist."""
    
    print("\n🎵 TESTING ON 'NEW' PLAYLIST SAMPLE")
    print("=" * 50)
    
    # Load playlist data to get the "New" playlist
    from common.playlist_data_utils import PlaylistDataLoader
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Find "New" playlist
    new_playlist = None
    for playlist_data in playlists_dict.values():
        if playlist_data["name"] == "New":
            new_playlist = playlist_data
            break
    
    if not new_playlist:
        print("❌ Could not find 'New' playlist")
        return
    
    # Take a sample for testing (first 100 tracks)
    sample_tracks = new_playlist["tracks"][:100]
    sample_track_ids = [track["id"] for track in sample_tracks]
    
    print(f"📀 Testing on {len(sample_tracks)} tracks from 'New' playlist")
    print()
    
    # Load training data for classifier training
    # Load folder mapping
    with open(project_root / "data" / "playlist_folders.json", "r") as f:
        playlist_to_folder = json.load(f)
    
    # Create folder-mapped training data
    folder_mapped_data = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                folder_mapped_data.append((track["id"], folder_name))
    
    # Test strategies
    strategy_variants = create_strategy_variants()
    
    # Add current optimized for comparison
    optimal_params = load_current_optimal_params()
    current_optimized = OptimizedCompositeClassifier()
    current_optimized.apply_parameters(optimal_params)
    
    all_classifiers = [("Current Optimized", current_optimized)] + [(c.name, c) for c in strategy_variants]
    
    for name, classifier in all_classifiers:
        print(f"🧠 {name}:")
        
        # Train classifier
        classifier.train(folder_mapped_data)
        
        # Test on sample
        classified = 0
        classifications = defaultdict(int)
        
        for track_id in sample_track_ids:
            prediction = classifier.predict(track_id)
            if prediction:
                classified += 1
                classifications[prediction] += 1
        
        coverage = (classified / len(sample_track_ids)) * 100
        
        print(f"   Coverage: {coverage:.1f}% ({classified}/{len(sample_track_ids)})")
        
        if classifications:
            print(f"   Classifications: {dict(classifications)}")
        
        print()


if __name__ == "__main__":
    try:
        # Test strategy comparison
        results = test_strategy_comparison()
        
        # Test on actual new playlist sample  
        test_on_new_playlist_sample()
        
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()