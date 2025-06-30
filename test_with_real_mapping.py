#!/usr/bin/env python3
"""
Test genre classification accuracy using real track → folders mapping.

Uses actual playlist membership as ground truth for comprehensive testing.
"""

import json
import random
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

from common.genre_classification_utils import classify_track, get_safe_spotify_client
from build_track_folder_mapping import load_mapping

def load_track_mapping() -> Dict[str, List[str]]:
    """Load the track → folders mapping."""
    mapping, _ = load_mapping()
    if mapping is None:
        print("❌ No mapping found. Run build_track_folder_mapping.py first.")
        return {}
    return mapping

def sample_tracks_for_testing(mapping: Dict[str, List[str]], 
                             samples_per_category: int = 20) -> Dict[str, List[str]]:
    """
    Sample tracks for testing, ensuring good representation.
    
    Args:
        mapping: Track ID → folders mapping
        samples_per_category: Number of tracks to sample per category type
        
    Returns:
        Dictionary with track IDs organized by category
    """
    # Categorize tracks by their folder membership pattern
    single_folder_tracks = defaultdict(list)  # folder → [track_ids]
    multi_folder_tracks = []  # [(track_id, [folders])]
    
    for track_id, folders in mapping.items():
        if len(folders) == 1:
            single_folder_tracks[folders[0]].append(track_id)
        else:
            multi_folder_tracks.append((track_id, folders))
    
    test_tracks = {
        'single_folder': {},
        'multi_folder': [],
        'cross_boundary': []  # Tracks that cross major genre boundaries
    }
    
    # Sample single-folder tracks from each folder
    for folder, track_ids in single_folder_tracks.items():
        sample_size = min(samples_per_category, len(track_ids))
        test_tracks['single_folder'][folder] = random.sample(track_ids, sample_size)
    
    # Sample multi-folder tracks
    random.shuffle(multi_folder_tracks)
    test_tracks['multi_folder'] = multi_folder_tracks[:samples_per_category * 3]
    
    # Find cross-boundary tracks (Electronic/Rave/Base vs Rock/Sierra/Soft)
    electronic_folders = {'Electronic', 'Rave', 'Base', 'House', 'Alive'}
    acoustic_folders = {'Rock', 'Sierra', 'Soft', 'Funk Soul'}
    
    for track_id, folders in multi_folder_tracks:
        folder_set = set(folders)
        if (folder_set & electronic_folders) and (folder_set & acoustic_folders):
            test_tracks['cross_boundary'].append((track_id, folders))
            if len(test_tracks['cross_boundary']) >= 10:  # Just a few examples
                break
    
    return test_tracks

def calculate_metrics(actual_folders: List[str], predicted_folders: List[str]) -> Dict[str, float]:
    """Calculate precision, recall, and F1 score."""
    if not actual_folders and not predicted_folders:
        return {'precision': 1.0, 'recall': 1.0, 'f1': 1.0}
    
    if not actual_folders:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    
    if not predicted_folders:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    
    actual_set = set(actual_folders)
    predicted_set = set(predicted_folders)
    
    intersection = actual_set & predicted_set
    
    precision = len(intersection) / len(predicted_set)
    recall = len(intersection) / len(actual_set)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {'precision': precision, 'recall': recall, 'f1': f1}

def test_classification_accuracy(test_tracks: Dict[str, Any]) -> Dict[str, Any]:
    """Test classification accuracy on different track categories."""
    
    results = {
        'single_folder': {'by_folder': {}, 'overall': {'total': 0, 'metrics': []}},
        'multi_folder': {'total': 0, 'metrics': [], 'examples': []},
        'cross_boundary': {'total': 0, 'metrics': [], 'examples': []},
        'overall_stats': {}
    }
    
    print("🧪 Testing Classification Accuracy with Real Mapping")
    print("=" * 60)
    
    # Test single-folder tracks
    print("\n📁 Testing Single-Folder Tracks")
    print("-" * 40)
    
    for folder, track_ids in test_tracks['single_folder'].items():
        folder_metrics = []
        print(f"\n   {folder} ({len(track_ids)} tracks):")
        
        for i, track_id in enumerate(track_ids):
            predicted = classify_track(track_id=track_id)
            actual = [folder]
            
            metrics = calculate_metrics(actual, predicted)
            folder_metrics.append(metrics)
            
            status = "✅" if folder in predicted else "❌"
            extra_predictions = [f for f in predicted if f != folder]
            extra_str = f" +{extra_predictions}" if extra_predictions else ""
            
            print(f"      {status} Track {i+1}: R={metrics['recall']:.2f} P={metrics['precision']:.2f}{extra_str}")
        
        # Calculate folder averages
        if folder_metrics:
            avg_metrics = {
                'precision': sum(m['precision'] for m in folder_metrics) / len(folder_metrics),
                'recall': sum(m['recall'] for m in folder_metrics) / len(folder_metrics),
                'f1': sum(m['f1'] for m in folder_metrics) / len(folder_metrics)
            }
            results['single_folder']['by_folder'][folder] = avg_metrics
            results['single_folder']['overall']['metrics'].extend(folder_metrics)
            results['single_folder']['overall']['total'] += len(track_ids)
            
            print(f"      📊 Avg: R={avg_metrics['recall']:.2f} P={avg_metrics['precision']:.2f} F1={avg_metrics['f1']:.2f}")
    
    # Test multi-folder tracks
    print(f"\n🔄 Testing Multi-Folder Tracks ({len(test_tracks['multi_folder'])} tracks)")
    print("-" * 40)
    
    for i, (track_id, actual_folders) in enumerate(test_tracks['multi_folder']):
        predicted = classify_track(track_id=track_id)
        metrics = calculate_metrics(actual_folders, predicted)
        
        results['multi_folder']['metrics'].append(metrics)
        results['multi_folder']['total'] += 1
        
        if i < 10:  # Show first 10 examples
            found = set(actual_folders) & set(predicted)
            missed = set(actual_folders) - set(predicted)
            extra = set(predicted) - set(actual_folders)
            
            print(f"   🎵 Track {i+1}:")
            print(f"      Actual: {actual_folders}")
            print(f"      Predicted: {predicted}")
            print(f"      ✅ Found: {list(found)}")
            print(f"      ❌ Missed: {list(missed)}")
            print(f"      ➕ Extra: {list(extra)}")
            print(f"      📊 R={metrics['recall']:.2f} P={metrics['precision']:.2f} F1={metrics['f1']:.2f}")
            
            results['multi_folder']['examples'].append({
                'track_id': track_id,
                'actual': actual_folders,
                'predicted': predicted,
                'metrics': metrics
            })
    
    # Test cross-boundary tracks
    if test_tracks['cross_boundary']:
        print(f"\n🌉 Testing Cross-Boundary Tracks ({len(test_tracks['cross_boundary'])} tracks)")
        print("-" * 40)
        
        for i, (track_id, actual_folders) in enumerate(test_tracks['cross_boundary']):
            predicted = classify_track(track_id=track_id)
            metrics = calculate_metrics(actual_folders, predicted)
            
            results['cross_boundary']['metrics'].append(metrics)
            results['cross_boundary']['total'] += 1
            
            print(f"   🎵 Track {i+1}: {actual_folders} → {predicted}")
            print(f"      📊 R={metrics['recall']:.2f} P={metrics['precision']:.2f} F1={metrics['f1']:.2f}")
            
            results['cross_boundary']['examples'].append({
                'track_id': track_id,
                'actual': actual_folders,
                'predicted': predicted,
                'metrics': metrics
            })
    
    return results

def print_summary_report(results: Dict[str, Any]):
    """Print comprehensive summary report."""
    
    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE ACCURACY REPORT")
    print("=" * 80)
    
    # Overall statistics
    all_metrics = (results['single_folder']['overall']['metrics'] + 
                  results['multi_folder']['metrics'] + 
                  results['cross_boundary']['metrics'])
    
    if all_metrics:
        avg_precision = sum(m['precision'] for m in all_metrics) / len(all_metrics)
        avg_recall = sum(m['recall'] for m in all_metrics) / len(all_metrics)
        avg_f1 = sum(m['f1'] for m in all_metrics) / len(all_metrics)
        
        total_tracks = (results['single_folder']['overall']['total'] + 
                       results['multi_folder']['total'] + 
                       results['cross_boundary']['total'])
        
        print(f"📊 Overall Performance ({total_tracks} tracks tested):")
        print(f"   🎯 Average Recall:    {avg_recall:.3f}")
        print(f"   🎯 Average Precision: {avg_precision:.3f}")
        print(f"   🎯 Average F1 Score:  {avg_f1:.3f}")
    
    # Single-folder performance
    if results['single_folder']['by_folder']:
        print(f"\n📁 Single-Folder Performance:")
        for folder, metrics in sorted(results['single_folder']['by_folder'].items(), 
                                    key=lambda x: x[1]['recall'], reverse=True):
            print(f"   {folder:<12}: R={metrics['recall']:.3f} P={metrics['precision']:.3f} F1={metrics['f1']:.3f}")
    
    # Multi-folder performance
    if results['multi_folder']['metrics']:
        multi_metrics = results['multi_folder']['metrics']
        multi_recall = sum(m['recall'] for m in multi_metrics) / len(multi_metrics)
        multi_precision = sum(m['precision'] for m in multi_metrics) / len(multi_metrics)
        multi_f1 = sum(m['f1'] for m in multi_metrics) / len(multi_metrics)
        
        print(f"\n🔄 Multi-Folder Performance ({len(multi_metrics)} tracks):")
        print(f"   🎯 Average Recall:    {multi_recall:.3f}")
        print(f"   🎯 Average Precision: {multi_precision:.3f}")
        print(f"   🎯 Average F1 Score:  {multi_f1:.3f}")
    
    # Cross-boundary performance
    if results['cross_boundary']['metrics']:
        cross_metrics = results['cross_boundary']['metrics']
        cross_recall = sum(m['recall'] for m in cross_metrics) / len(cross_metrics)
        cross_precision = sum(m['precision'] for m in cross_metrics) / len(cross_metrics)
        cross_f1 = sum(m['f1'] for m in cross_metrics) / len(cross_metrics)
        
        print(f"\n🌉 Cross-Boundary Performance ({len(cross_metrics)} tracks):")
        print(f"   🎯 Average Recall:    {cross_recall:.3f}")
        print(f"   🎯 Average Precision: {cross_precision:.3f}")
        print(f"   🎯 Average F1 Score:  {cross_f1:.3f}")

def main():
    """Main function to run the comprehensive test."""
    print("🎵 Comprehensive Genre Classification Test")
    print("==========================================")
    
    # Load the real mapping
    mapping = load_track_mapping()
    if not mapping:
        return
    
    print(f"📊 Loaded mapping: {len(mapping)} tracks across folders")
    
    # Sample tracks for testing
    test_tracks = sample_tracks_for_testing(mapping, samples_per_category=15)
    
    # Run the test
    results = test_classification_accuracy(test_tracks)
    
    # Print summary
    print_summary_report(results)

if __name__ == "__main__":
    main()