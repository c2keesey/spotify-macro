#!/usr/bin/env python3
"""
Test script to compare Enhanced Artist-Genre classifier with current best classifier.

This script runs both the current Electronic-Specialist and the new Enhanced Artist-Genre
classifier to compare their performance on the same dataset.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.classification_framework import ClassificationFramework
from analysis.genre.classification_metrics import (
    load_cached_data,
    create_train_test_split,
    print_data_summary,
    save_evaluation_results
)
from analysis.genre.electronic_specialist_classifier import (
    ElectronicSpecialistClassifier,
    SimpleElectronicSpecialistClassifier
)
from analysis.genre.enhanced_artist_genre_classifier import EnhancedArtistGenreClassifier


def run_enhanced_classifier_comparison(verbose: bool = False, limit_tracks: Optional[int] = None) -> Dict[str, Any]:
    """
    Run comparison between current best and enhanced classifiers.
    
    Args:
        verbose: Enable verbose output
        limit_tracks: Limit tracks per folder for testing
        
    Returns:
        Dictionary of evaluation results
    """
    print("="*80)
    print("ENHANCED ARTIST-GENRE CLASSIFIER COMPARISON")
    print("="*80)
    
    # Load cached data
    print("\nLoading cached data...")
    cached_data = load_cached_data()
    
    # Load playlist data
    print("Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(verbose=verbose)
    
    # Create train/test split
    print("Creating train/test split...")
    playlist_folders = cached_data.get("playlist_folders", {})
    train_test_split = create_train_test_split(
        playlist_folders,
        playlists_dict,
        train_ratio=0.7,
        random_seed=42
    )
    
    # Optionally limit tracks for testing
    if limit_tracks:
        print(f"Limiting to {limit_tracks} tracks per folder for testing...")
        train_test_split = limit_tracks_per_folder(train_test_split, limit_tracks)
    
    # Print data summary
    if verbose:
        print_data_summary(cached_data, train_test_split)
    
    # Set up classification framework
    framework = ClassificationFramework()
    framework.set_train_test_split(train_test_split)
    
    # Register classifiers for comparison
    print("\nRegistering classifiers...")
    
    # Current best classifier
    framework.add_classifier(SimpleElectronicSpecialistClassifier())
    
    # New enhanced classifier
    framework.add_classifier(EnhancedArtistGenreClassifier())
    
    classifier_names = [c.get_name() for c in framework.classifiers]
    print(f"  Registered {len(classifier_names)} classifiers: {', '.join(classifier_names)}")
    
    # Prepare training data
    train_data = {
        "artist_to_playlists": cached_data.get("artist_to_playlists", {}),
        "single_playlist_artists": cached_data.get("single_playlist_artists", {}),
        "playlist_folders": playlist_folders,
        "playlists_dict": playlists_dict,
        "train_tracks": train_test_split.train_tracks,
        "spotify_client": None
    }
    
    # Train all classifiers
    print("\nTraining classifiers...")
    framework.train_all_classifiers(train_data)
    
    # Print classifier information
    if verbose:
        print("\nClassifier Information:")
        for classifier in framework.classifiers:
            info = classifier.get_info()
            print(f"  {info['name']}:")
            print(f"    Description: {info.get('description', 'N/A')}")
            print(f"    Uses Audio Features: {info.get('uses_audio_features', False)}")
            print(f"    Uses Artist Patterns: {info.get('uses_artist_patterns', False)}")
            print(f"    Uses Genre Data: {info.get('uses_genre_data', False)}")
            if "single_folder_artists" in info:
                print(f"    Single-Folder Artists: {info['single_folder_artists']}")
            if "artists_with_genres" in info:
                print(f"    Artists with Genres: {info['artists_with_genres']}")
    
    # Evaluate all classifiers
    print("\nEvaluating classifiers...")
    evaluation_results = framework.evaluate_all_classifiers()
    
    # Print comparison report
    framework.print_comparison_report()
    
    return evaluation_results


def print_enhancement_analysis(evaluation_results: Dict[str, Any]) -> None:
    """
    Print detailed analysis of enhancement improvements.
    
    Args:
        evaluation_results: Dictionary of evaluation results
    """
    print("\n" + "="*80)
    print("ENHANCEMENT ANALYSIS")
    print("="*80)
    
    # Compare Simple Electronic-Specialist with Enhanced Artist-Genre
    baseline = None
    enhanced = None
    
    for name, metrics in evaluation_results.items():
        if "Simple Electronic-Specialist" in name:
            baseline = metrics
        elif "Enhanced Artist-Genre" in name:
            enhanced = metrics
    
    if not baseline or not enhanced:
        print("Warning: Could not find both baseline and enhanced results for comparison")
        return
    
    print(f"\nPERFORMANCE COMPARISON:")
    print("-" * 60)
    
    # Overall metrics comparison
    metrics = [
        ("Accuracy", "accuracy"),
        ("Precision", "precision"), 
        ("Recall", "recall"),
        ("F1-Score", "f1_score"),
        ("Coverage", "coverage")
    ]
    
    improvements = {}
    for metric_name, metric_attr in metrics:
        baseline_val = getattr(baseline, metric_attr)
        enhanced_val = getattr(enhanced, metric_attr)
        improvement = ((enhanced_val - baseline_val) / baseline_val * 100) if baseline_val > 0 else 0
        improvements[metric_attr] = improvement
        
        status = "✅" if improvement > 0 else "❌" if improvement < 0 else "➡️"
        print(f"{metric_name:12}: {baseline_val:.3f} → {enhanced_val:.3f} ({improvement:+.1f}%) {status}")
    
    # Overall assessment
    print(f"\nOVERALL ASSESSMENT:")
    print("-" * 40)
    
    significant_improvements = sum(1 for imp in improvements.values() if imp > 2.0)
    positive_improvements = sum(1 for imp in improvements.values() if imp > 0)
    
    if improvements['accuracy'] > 5.0:
        print("🎉 MAJOR IMPROVEMENT: >5% accuracy gain!")
    elif improvements['accuracy'] > 2.0:
        print("✅ SIGNIFICANT IMPROVEMENT: >2% accuracy gain")
    elif improvements['accuracy'] > 0:
        print("✅ Positive improvement in accuracy")
    else:
        print("❌ No accuracy improvement")
    
    if positive_improvements >= 4:
        print(f"✅ Broad improvements across {positive_improvements}/5 metrics")
    elif positive_improvements >= 2:
        print(f"📈 Mixed results: {positive_improvements}/5 metrics improved")
    else:
        print(f"❌ Limited improvements: {positive_improvements}/5 metrics improved")
    
    # Genre data utilization
    print(f"\nGENRE DATA IMPACT:")
    print("-" * 40)
    
    enhanced_info = enhanced.per_folder_metrics if hasattr(enhanced, 'per_folder_metrics') else {}
    baseline_info = baseline.per_folder_metrics if hasattr(baseline, 'per_folder_metrics') else {}
    
    # Find folders with biggest improvements
    folder_improvements = []
    for folder in enhanced_info.keys():
        if folder in baseline_info:
            enhanced_f1 = enhanced_info[folder].get('f1_score', 0)
            baseline_f1 = baseline_info[folder].get('f1_score', 0)
            improvement = enhanced_f1 - baseline_f1
            folder_improvements.append((folder, improvement, enhanced_f1, baseline_f1))
    
    # Sort by improvement
    folder_improvements.sort(key=lambda x: x[1], reverse=True)
    
    print("Top folder improvements:")
    for folder, improvement, enhanced_f1, baseline_f1 in folder_improvements[:5]:
        if improvement > 0.01:  # > 1% improvement
            print(f"  {folder}: {baseline_f1:.1%} → {enhanced_f1:.1%} (+{improvement:.1%})")
    
    print("\nFolders with reduced performance:")
    for folder, improvement, enhanced_f1, baseline_f1 in folder_improvements[-3:]:
        if improvement < -0.01:  # > 1% degradation
            print(f"  {folder}: {baseline_f1:.1%} → {enhanced_f1:.1%} ({improvement:.1%})")


def limit_tracks_per_folder(train_test_split, limit_per_folder: int):
    """
    Limit the number of tracks per folder for testing purposes.
    """
    from collections import defaultdict
    from analysis.genre.classification_framework import TrainTestSplit
    
    # Group tracks by folder
    train_by_folder = defaultdict(list)
    test_by_folder = defaultdict(list)
    
    for track_id, folder in train_test_split.train_tracks:
        train_by_folder[folder].append((track_id, folder))
    
    for track_id, folder in train_test_split.test_tracks:
        test_by_folder[folder].append((track_id, folder))
    
    # Limit tracks per folder
    limited_train = []
    limited_test = []
    
    for folder, tracks in train_by_folder.items():
        limited_train.extend(tracks[:limit_per_folder])
    
    for folder, tracks in test_by_folder.items():
        limited_test.extend(tracks[:limit_per_folder])
    
    return TrainTestSplit(
        train_playlists=train_test_split.train_playlists,
        test_playlists=train_test_split.test_playlists,
        train_tracks=limited_train,
        test_tracks=limited_test
    )


def main():
    """Main entry point for enhanced classifier testing."""
    parser = argparse.ArgumentParser(
        description="Test Enhanced Artist-Genre classifier vs current best"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--limit-tracks",
        type=int,
        help="Limit number of tracks per folder for testing"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="enhanced_classifier_results.json",
        help="Save results to file"
    )
    
    args = parser.parse_args()
    
    # Run enhanced classifier comparison
    evaluation_results = run_enhanced_classifier_comparison(
        verbose=args.verbose,
        limit_tracks=args.limit_tracks
    )
    
    # Save results
    print(f"\nSaving results to {args.output_file}...")
    save_evaluation_results(evaluation_results, args.output_file)
    
    # Print enhancement analysis
    print_enhancement_analysis(evaluation_results)
    
    print("\n" + "="*80)
    print("ENHANCED CLASSIFIER TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()