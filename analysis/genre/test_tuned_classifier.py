#!/usr/bin/env python3
"""
Test script for the tuned enhanced classifier with detailed performance analysis.

Compares the tuned enhanced classifier against the Simple Electronic-Specialist
baseline to measure improvements from the optimizations.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

from analysis.genre.classification_framework import ClassificationFramework
from analysis.genre.electronic_specialist_classifier import SimpleElectronicSpecialistClassifier  
from analysis.genre.tuned_enhanced_classifier import TunedEnhancedClassifier
from analysis.genre.composite_classifier import CompositeClassifier
from analysis.genre.classification_metrics import load_cached_data, create_train_test_split
from common.playlist_data_utils import PlaylistDataLoader


def analyze_tuning_improvements(baseline_results: Dict, tuned_results: Dict) -> Dict[str, Any]:
    """
    Analyze improvements from tuning compared to baseline results.
    
    Args:
        baseline_results: Results from Simple Electronic-Specialist
        tuned_results: Results from Tuned Enhanced classifier
        
    Returns:
        Dictionary with detailed improvement analysis
    """
    baseline_summary = baseline_results["summary"]
    tuned_summary = tuned_results["summary"]
    
    # Overall metric improvements
    accuracy_improvement = tuned_summary["accuracy"] - baseline_summary["accuracy"]
    precision_improvement = tuned_summary["precision"] - baseline_summary["precision"]
    recall_improvement = tuned_summary["recall"] - baseline_summary["recall"]
    f1_improvement = tuned_summary["f1_score"] - baseline_summary["f1_score"]
    coverage_improvement = tuned_summary["coverage"] - baseline_summary["coverage"]
    
    # Per-folder improvements
    folder_improvements = {}
    baseline_folders = baseline_results["per_folder_metrics"]
    tuned_folders = tuned_results["per_folder_metrics"]
    
    for folder in baseline_folders.keys():
        if folder in tuned_folders:
            baseline_folder = baseline_folders[folder]
            tuned_folder = tuned_folders[folder]
            
            folder_improvements[folder] = {
                "precision_change": tuned_folder["precision"] - baseline_folder["precision"],
                "recall_change": tuned_folder["recall"] - baseline_folder["recall"],
                "f1_change": tuned_folder["f1_score"] - baseline_folder["f1_score"],
                "baseline_precision": baseline_folder["precision"],
                "tuned_precision": tuned_folder["precision"],
                "baseline_recall": baseline_folder["recall"],
                "tuned_recall": tuned_folder["recall"],
                "baseline_f1": baseline_folder["f1_score"],
                "tuned_f1": tuned_folder["f1_score"]
            }
    
    # Identify biggest winners and losers
    precision_winners = sorted(
        [(folder, metrics["precision_change"]) for folder, metrics in folder_improvements.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    recall_winners = sorted(
        [(folder, metrics["recall_change"]) for folder, metrics in folder_improvements.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    f1_winners = sorted(
        [(folder, metrics["f1_change"]) for folder, metrics in folder_improvements.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    return {
        "overall_improvements": {
            "accuracy": {
                "baseline": baseline_summary["accuracy"],
                "tuned": tuned_summary["accuracy"],
                "change": accuracy_improvement,
                "percent_change": (accuracy_improvement / baseline_summary["accuracy"]) * 100
            },
            "precision": {
                "baseline": baseline_summary["precision"],
                "tuned": tuned_summary["precision"],
                "change": precision_improvement,
                "percent_change": (precision_improvement / baseline_summary["precision"]) * 100
            },
            "recall": {
                "baseline": baseline_summary["recall"],
                "tuned": tuned_summary["recall"],
                "change": recall_improvement,
                "percent_change": (recall_improvement / baseline_summary["recall"]) * 100
            },
            "f1_score": {
                "baseline": baseline_summary["f1_score"],
                "tuned": tuned_summary["f1_score"],
                "change": f1_improvement,
                "percent_change": (f1_improvement / baseline_summary["f1_score"]) * 100
            },
            "coverage": {
                "baseline": baseline_summary["coverage"],
                "tuned": tuned_summary["coverage"],
                "change": coverage_improvement,
                "percent_change": (coverage_improvement / baseline_summary["coverage"]) * 100
            }
        },
        "folder_improvements": folder_improvements,
        "top_precision_winners": precision_winners,
        "top_recall_winners": recall_winners,
        "top_f1_winners": f1_winners,
        "performance_summary": {
            "folders_with_precision_gains": sum(1 for f in folder_improvements.values() if f["precision_change"] > 0),
            "folders_with_recall_gains": sum(1 for f in folder_improvements.values() if f["recall_change"] > 0),
            "folders_with_f1_gains": sum(1 for f in folder_improvements.values() if f["f1_change"] > 0),
            "total_folders": len(folder_improvements)
        }
    }


def print_improvement_analysis(analysis: Dict[str, Any]) -> None:
    """Print detailed analysis of tuning improvements."""
    print("\n" + "="*80)
    print("🎯 TUNING IMPROVEMENT ANALYSIS")
    print("="*80)
    
    # Overall improvements
    overall = analysis["overall_improvements"]
    print(f"\n📊 Overall Performance Changes:")
    print(f"  Accuracy:  {overall['accuracy']['baseline']:.3f} → {overall['accuracy']['tuned']:.3f} " +
          f"({overall['accuracy']['change']:+.3f}, {overall['accuracy']['percent_change']:+.1f}%)")
    print(f"  Precision: {overall['precision']['baseline']:.3f} → {overall['precision']['tuned']:.3f} " +
          f"({overall['precision']['change']:+.3f}, {overall['precision']['percent_change']:+.1f}%)")
    print(f"  Recall:    {overall['recall']['baseline']:.3f} → {overall['recall']['tuned']:.3f} " +
          f"({overall['recall']['change']:+.3f}, {overall['recall']['percent_change']:+.1f}%)")
    print(f"  F1-Score:  {overall['f1_score']['baseline']:.3f} → {overall['f1_score']['tuned']:.3f} " +
          f"({overall['f1_score']['change']:+.3f}, {overall['f1_score']['percent_change']:+.1f}%)")
    print(f"  Coverage:  {overall['coverage']['baseline']:.3f} → {overall['coverage']['tuned']:.3f} " +
          f"({overall['coverage']['change']:+.3f}, {overall['coverage']['percent_change']:+.1f}%)")
    
    # Performance summary
    summary = analysis["performance_summary"]
    print(f"\n📈 Folder Improvement Summary:")
    print(f"  Folders with precision gains: {summary['folders_with_precision_gains']}/{summary['total_folders']}")
    print(f"  Folders with recall gains:    {summary['folders_with_recall_gains']}/{summary['total_folders']}")
    print(f"  Folders with F1 gains:       {summary['folders_with_f1_gains']}/{summary['total_folders']}")
    
    # Top winners
    print(f"\n🏆 Top F1-Score Improvements:")
    for i, (folder, change) in enumerate(analysis["top_f1_winners"], 1):
        baseline_f1 = analysis["folder_improvements"][folder]["baseline_f1"]
        tuned_f1 = analysis["folder_improvements"][folder]["tuned_f1"]
        print(f"  {i}. {folder:<12} {baseline_f1:.3f} → {tuned_f1:.3f} ({change:+.3f})")
    
    print(f"\n🎯 Top Precision Improvements:")
    for i, (folder, change) in enumerate(analysis["top_precision_winners"], 1):
        baseline_prec = analysis["folder_improvements"][folder]["baseline_precision"]
        tuned_prec = analysis["folder_improvements"][folder]["tuned_precision"]
        print(f"  {i}. {folder:<12} {baseline_prec:.3f} → {tuned_prec:.3f} ({change:+.3f})")
    
    print(f"\n📡 Top Recall Improvements:")
    for i, (folder, change) in enumerate(analysis["top_recall_winners"], 1):
        baseline_recall = analysis["folder_improvements"][folder]["baseline_recall"]
        tuned_recall = analysis["folder_improvements"][folder]["tuned_recall"]
        print(f"  {i}. {folder:<12} {baseline_recall:.3f} → {tuned_recall:.3f} ({change:+.3f})")


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Test tuned enhanced classifier")
    parser.add_argument("--limit-tracks", type=int, help="Limit number of tracks for testing")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--save-results", action="store_true", default=True, help="Save results to file")
    args = parser.parse_args()
    
    print("🧪 Testing Tuned Enhanced Classifier vs Simple Electronic-Specialist")
    print("="*70)
    
    # Load data
    print("Loading cached data...")
    cached_data = load_cached_data()
    
    print("Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
        verbose=args.verbose
    )
    playlist_folders = cached_data.get("playlist_folders", {})
    
    # Create train/test split
    print("Creating train/test split...")
    train_test_split = create_train_test_split(
        playlist_folders, 
        playlists_dict, 
        train_ratio=0.7,
        random_seed=42
    )
    
    # Initialize classifiers
    baseline_classifier = SimpleElectronicSpecialistClassifier()
    tuned_classifier = TunedEnhancedClassifier()
    composite_classifier = CompositeClassifier()
    
    # Create test framework
    framework = ClassificationFramework()
    framework.set_train_test_split(train_test_split)
    framework.add_classifier(baseline_classifier)
    framework.add_classifier(tuned_classifier)
    framework.add_classifier(composite_classifier)
    
    # Prepare training data
    train_data = {
        "artist_to_playlists": cached_data.get("artist_to_playlists", {}),
        "single_playlist_artists": cached_data.get("single_playlist_artists", {}),
        "playlist_folders": playlist_folders,
        "playlists_dict": playlists_dict,
        "train_tracks": train_test_split.train_tracks,
        "spotify_client": None
    }
    
    # Train classifiers
    print("Training classifiers...")
    framework.train_all_classifiers(train_data)
    
    # Run evaluation
    print("\nEvaluating classifiers...")
    evaluation_results = framework.evaluate_all_classifiers()
    
    # Convert to old format for analysis
    results = {}
    for name, metrics in evaluation_results.items():
        results[name] = {
            "summary": {
                "classifier": name,
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "coverage": metrics.coverage,
                "total_tracks": metrics.total_tracks,
                "correct_predictions": metrics.correct_predictions,
                "avg_processing_time_ms": metrics.avg_processing_time_ms
            },
            "per_folder_metrics": metrics.per_folder_metrics,
            "total_processing_time_ms": metrics.total_processing_time_ms
        }
    
    # Extract results for analysis
    baseline_results = results["Simple Electronic-Specialist"]
    tuned_results = results["Tuned Enhanced Classifier"]
    composite_results = results.get("Composite Strategy Classifier")
    
    # Analyze improvements
    improvement_analysis = analyze_tuning_improvements(baseline_results, tuned_results)
    
    # Print results
    framework.print_comparison_report()
    print_improvement_analysis(improvement_analysis)
    
    # Save results
    if args.save_results:
        output_file = Path("data/tuned_classifier_results.json")
        
        # Combine results with improvement analysis
        full_results = {
            "classifier_results": results,
            "improvement_analysis": improvement_analysis,
            "test_parameters": {
                "limit_tracks": args.limit_tracks,
                "test_split": 0.3,
                "random_seed": 42
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(full_results, f, indent=2)
        
        print(f"\n💾 Results saved to {output_file}")
    
    # Summary
    overall = improvement_analysis["overall_improvements"]
    print(f"\n🎉 SUMMARY:")
    print(f"  Tuned Enhanced vs Baseline:")
    print(f"    Accuracy: {overall['accuracy']['percent_change']:+.1f}%")
    print(f"    Coverage: {overall['coverage']['percent_change']:+.1f}%")
    print(f"    F1-score: {overall['f1_score']['percent_change']:+.1f}%")
    
    if composite_results:
        composite_summary = composite_results["summary"]
        print(f"  Composite vs Baseline:")
        print(f"    Accuracy: {((composite_summary['accuracy'] - baseline_results['summary']['accuracy']) / baseline_results['summary']['accuracy'] * 100):+.1f}%")
        print(f"    Coverage: {((composite_summary['coverage'] - baseline_results['summary']['coverage']) / baseline_results['summary']['coverage'] * 100):+.1f}%")
        print(f"    F1-score: {((composite_summary['f1_score'] - baseline_results['summary']['f1_score']) / baseline_results['summary']['f1_score'] * 100):+.1f}%")


if __name__ == "__main__":
    main()