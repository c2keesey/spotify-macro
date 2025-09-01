#!/usr/bin/env python3
"""
Test multi-class threshold optimization on local data split.

This script tests different multi-class threshold values to find the optimal
balance between coverage and precision for multi-class assignments.
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from analysis.genre.classification_metrics import load_test_data, create_train_test_split
from analysis.genre.composite_classifier import CompositeClassifier


def test_multiclass_thresholds(train_data: Dict, test_data: List[Tuple], 
                               thresholds: List[float]) -> Dict[str, Any]:
    """Test different multi-class thresholds and return metrics."""
    
    print("🧠 Training composite classifier...")
    classifier = CompositeClassifier()
    classifier.train(train_data)
    
    results = {}
    
    for threshold in thresholds:
        print(f"\n🔍 Testing threshold: {threshold:.3f}")
        
        # Track metrics for this threshold
        metrics = {
            'threshold': threshold,
            'total_tracks': len(test_data),
            'classified_tracks': 0,
            'total_assignments': 0,
            'multi_class_tracks': 0,
            'folder_assignments': defaultdict(int),
            'correct_assignments': 0,
            'total_possible_correct': 0
        }
        
        for track_id, true_folder in test_data:
            # Get prediction from classifier
            result = classifier.predict(track_id)
            
            if hasattr(result, 'predicted_folders'):
                predicted_folders = result.predicted_folders
                confidence_scores = result.confidence_scores
            else:
                predicted_folders = result.get('folders', [])
                confidence_scores = result.get('confidence_scores', {})
            
            # Apply multi-class threshold
            valid_folders = {
                folder: confidence_scores.get(folder, 0) 
                for folder in predicted_folders 
                if confidence_scores.get(folder, 0) >= threshold
            }
            
            if valid_folders:
                metrics['classified_tracks'] += 1
                metrics['total_assignments'] += len(valid_folders)
                
                if len(valid_folders) > 1:
                    metrics['multi_class_tracks'] += 1
                
                # Count assignments per folder
                for folder in valid_folders:
                    metrics['folder_assignments'][folder] += 1
                
                # Check if true folder is in predictions
                if true_folder in valid_folders:
                    metrics['correct_assignments'] += 1
            
            # Track total possible correct (for recall calculation)
            metrics['total_possible_correct'] += 1
        
        # Calculate final metrics
        coverage = metrics['classified_tracks'] / metrics['total_tracks'] if metrics['total_tracks'] > 0 else 0
        precision = metrics['correct_assignments'] / metrics['classified_tracks'] if metrics['classified_tracks'] > 0 else 0
        recall = metrics['correct_assignments'] / metrics['total_possible_correct'] if metrics['total_possible_correct'] > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        avg_assignments_per_track = metrics['total_assignments'] / metrics['classified_tracks'] if metrics['classified_tracks'] > 0 else 0
        multi_class_ratio = metrics['multi_class_tracks'] / metrics['classified_tracks'] if metrics['classified_tracks'] > 0 else 0
        
        metrics.update({
            'coverage': coverage,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'avg_assignments_per_track': avg_assignments_per_track,
            'multi_class_ratio': multi_class_ratio
        })
        
        print(f"   Coverage: {coverage:.1%} ({metrics['classified_tracks']}/{metrics['total_tracks']})")
        print(f"   Precision: {precision:.1%}")
        print(f"   Recall: {recall:.1%}")
        print(f"   F1 Score: {f1_score:.3f}")
        print(f"   Avg assignments/track: {avg_assignments_per_track:.2f}")
        print(f"   Multi-class tracks: {multi_class_ratio:.1%}")
        
        results[f"threshold_{threshold:.3f}"] = metrics
    
    return results


def main():
    """Main entry point for multi-class threshold optimization."""
    print("🎯 Multi-Class Threshold Optimization")
    print("=" * 50)
    
    # Load test data
    print("📚 Loading test data...")
    test_tracks, playlists_dict = load_test_data(limit_tracks=1000)  # Use smaller subset for faster testing
    
    if not test_tracks:
        print("❌ No test data loaded. Exiting.")
        return
    
    print(f"   Loaded {len(test_tracks)} test tracks")
    
    # Load playlist folder mapping
    import json
    with open('data/playlist_folders.json', 'r') as f:
        playlist_folders = json.load(f)
    
    # Create train/test split
    print("🔀 Creating train/test split...")
    split_result = create_train_test_split(playlist_folders, playlists_dict, train_ratio=0.8, random_seed=42)
    train_data = {'playlists_dict': playlists_dict, 'train_tracks': split_result.train_tracks}
    test_data = split_result.test_tracks
    
    print(f"   Training tracks: {len(train_data['train_tracks'])}")
    print(f"   Test tracks: {len(test_data)}")
    
    # Test different thresholds
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    print(f"\n🔍 Testing {len(thresholds)} threshold values...")
    
    results = test_multiclass_thresholds(train_data, test_data, thresholds)
    
    # Find optimal threshold
    print("\n📊 Optimization Results:")
    print("=" * 70)
    print(f"{'Threshold':<10} {'Coverage':<10} {'Precision':<10} {'Recall':<8} {'F1':<8} {'Avg/Track':<10} {'Multi%':<8}")
    print("-" * 70)
    
    best_f1 = 0
    best_threshold = None
    
    for threshold_key, metrics in results.items():
        threshold = metrics['threshold']
        print(f"{threshold:<10.3f} {metrics['coverage']:<10.1%} {metrics['precision']:<10.1%} "
              f"{metrics['recall']:<8.1%} {metrics['f1_score']:<8.3f} "
              f"{metrics['avg_assignments_per_track']:<10.2f} {metrics['multi_class_ratio']:<8.1%}")
        
        if metrics['f1_score'] > best_f1:
            best_f1 = metrics['f1_score']
            best_threshold = threshold
    
    print("-" * 70)
    print(f"🏆 Best threshold: {best_threshold:.3f} (F1: {best_f1:.3f})")
    
    # Save results
    output_file = Path("data/optimization_results/multiclass_threshold_optimization.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    optimization_summary = {
        'best_threshold': best_threshold,
        'best_f1_score': best_f1,
        'test_results': results,
        'test_config': {
            'train_tracks': len(train_data['train_tracks']),
            'test_tracks': len(test_data),
            'train_ratio': 0.8,
            'random_seed': 42
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(optimization_summary, f, indent=2, default=str)
    
    print(f"📁 Results saved to: {output_file}")


if __name__ == "__main__":
    main()