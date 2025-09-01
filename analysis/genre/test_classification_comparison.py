#!/usr/bin/env python3
"""
Main testing harness for classification algorithm comparison.

This script loads cached data, creates train/test splits, and runs comprehensive
comparisons between different classification algorithms.

Usage:
    python test_classification_comparison.py [options]

Options:
    --train-ratio RATIO    Training data ratio (default: 0.7)
    --random-seed SEED     Random seed for reproducible splits (default: 42)
    --output-file FILE     Output file for results (default: classification_results.json)
    --no-audio-features    Skip classifiers that require audio features
    --verbose             Enable verbose output
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.playlist_data_utils import PlaylistDataLoader
from common.genre_classification_utils import get_safe_spotify_client
from analysis.genre.classification_framework import ClassificationFramework
from analysis.genre.classification_metrics import (
    load_cached_data, 
    create_train_test_split, 
    print_data_summary,
    save_evaluation_results
)
from analysis.genre.current_classifier import CurrentArtistOnlyClassifier, CurrentSystemWithGenreMappingClassifier
from analysis.genre.electronic_specialist_classifier import (
    ElectronicSpecialistClassifier, 
    SimpleElectronicSpecialistClassifier
)


def main():
    """Main entry point for classification comparison."""
    parser = argparse.ArgumentParser(
        description="Compare classification algorithms for genre-based playlist sorting"
    )
    parser.add_argument(
        "--train-ratio", 
        type=float, 
        default=0.7, 
        help="Training data ratio (default: 0.7)"
    )
    parser.add_argument(
        "--random-seed", 
        type=int, 
        default=42, 
        help="Random seed for reproducible splits (default: 42)"
    )
    parser.add_argument(
        "--output-file", 
        type=str, 
        default="classification_results.json",
        help="Output file for results (default: classification_results.json)"
    )
    parser.add_argument(
        "--no-audio-features", 
        action="store_true",
        help="Skip classifiers that require audio features"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("CLASSIFICATION ALGORITHM COMPARISON")
    print("="*80)
    
    # Load cached data
    print("\\nLoading cached data...")
    cached_data = load_cached_data()
    
    # Load playlist data using PlaylistDataLoader
    print("Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
        verbose=args.verbose
    )
    
    # Create train/test split
    print("Creating train/test split...")
    playlist_folders = cached_data.get("playlist_folders", {})
    train_test_split = create_train_test_split(
        playlist_folders, 
        playlists_dict, 
        train_ratio=args.train_ratio,
        random_seed=args.random_seed
    )
    
    
    # Print data summary
    print_data_summary(cached_data, train_test_split)
    
    # Set up classification framework
    framework = ClassificationFramework()
    framework.set_train_test_split(train_test_split)
    
    # No Spotify client needed - using local data only
    spotify_client = None
    
    # Register classifiers
    print("\\nRegistering classifiers...")
    
    # Add classifiers that work with local data only
    framework.add_classifier(SimpleElectronicSpecialistClassifier())
    framework.add_classifier(ElectronicSpecialistClassifier())
    
    classifier_names = [c.get_name() for c in framework.classifiers]
    print(f"  Registered {len(classifier_names)} classifiers: {', '.join(classifier_names)}")
    
    # Prepare training data
    train_data = {
        "artist_to_playlists": cached_data.get("artist_to_playlists", {}),
        "single_playlist_artists": cached_data.get("single_playlist_artists", {}),
        "playlist_folders": playlist_folders,
        "playlists_dict": playlists_dict,
        "train_tracks": train_test_split.train_tracks,
        "spotify_client": spotify_client
    }
    
    # Train all classifiers
    print("\\nTraining classifiers...")
    framework.train_all_classifiers(train_data)
    
    # Print classifier information
    if args.verbose:
        print("\\nClassifier Information:")
        for classifier in framework.classifiers:
            info = classifier.get_info()
            print(f"  {info['name']}:")
            print(f"    Description: {info.get('description', 'N/A')}")
            print(f"    Uses Audio Features: {info.get('uses_audio_features', False)}")
            print(f"    Uses Artist Patterns: {info.get('uses_artist_patterns', False)}")
            if "single_folder_artists" in info:
                print(f"    Single-Folder Artists: {info['single_folder_artists']}")
    
    # Evaluate all classifiers
    print("\\nEvaluating classifiers...")
    evaluation_results = framework.evaluate_all_classifiers()
    
    # Print comparison report
    framework.print_comparison_report()
    
    # Save results
    print(f"\\nSaving results to {args.output_file}...")
    save_evaluation_results(evaluation_results, args.output_file)
    
    # Print key findings
    print_key_findings(evaluation_results)
    
    print("\\n" + "="*80)
    print("COMPARISON COMPLETE")
    print("="*80)



def print_key_findings(evaluation_results: Dict[str, Any]) -> None:
    """
    Print key findings from the evaluation results.
    
    Args:
        evaluation_results: Dictionary of evaluation results
    """
    print("\\nKEY FINDINGS:")
    print("-" * 40)
    
    # Find best performer overall
    best_f1 = max(evaluation_results.items(), key=lambda x: x[1].f1_score)
    print(f"Best Overall (F1-Score): {best_f1[0]} ({best_f1[1].f1_score:.3f})")
    
    # Find precision leader
    best_precision = max(evaluation_results.items(), key=lambda x: x[1].precision)
    print(f"Best Precision: {best_precision[0]} ({best_precision[1].precision:.3f})")
    
    # Find recall leader
    best_recall = max(evaluation_results.items(), key=lambda x: x[1].recall)
    print(f"Best Recall: {best_recall[0]} ({best_recall[1].recall:.3f})")
    
    # Check for Electronic-Specialist improvement
    electronic_specialist = None
    current_system = None
    
    for name, metrics in evaluation_results.items():
        if "Electronic-Specialist" in name:
            electronic_specialist = metrics
        elif "Current" in name:
            current_system = metrics
    
    if electronic_specialist and current_system:
        precision_improvement = electronic_specialist.precision / current_system.precision if current_system.precision > 0 else float('inf')
        recall_change = electronic_specialist.recall / current_system.recall if current_system.recall > 0 else float('inf')
        
        print(f"\\nElectronic-Specialist vs Current System:")
        print(f"  Precision improvement: {precision_improvement:.1f}x")
        print(f"  Recall change: {recall_change:.2f}x")
        
        if precision_improvement >= 5.0:
            print("  ✅ TARGET ACHIEVED: 5x+ precision improvement!")
        else:
            print(f"  ⚠️  Target not met: {precision_improvement:.1f}x < 5x precision improvement")
    
    # Coverage analysis
    print(f"\\nCoverage Analysis:")
    for name, metrics in evaluation_results.items():
        print(f"  {name}: {metrics.coverage:.1%} of tracks classified")
    
    # Performance analysis
    print(f"\\nPerformance Analysis:")
    for name, metrics in evaluation_results.items():
        print(f"  {name}: {metrics.avg_processing_time_ms:.1f}ms avg per track")


if __name__ == "__main__":
    main()