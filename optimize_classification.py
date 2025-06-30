#!/usr/bin/env python3
"""
Fast optimization framework for testing different classification strategies.
"""

import json
import random
from typing import Dict, List, Tuple, Any, Callable
from collections import defaultdict

from common.genre_classification_utils import (
    get_safe_spotify_client,
    get_artist_genres,
    get_audio_features,
    classify_by_genres,
    classify_by_audio_features,
    get_default_genre_mapping
)
from build_track_folder_mapping import load_mapping

def quick_test_sample(mapping: Dict[str, List[str]], n_samples: int = 100) -> List[Tuple[str, List[str]]]:
    """Get a quick test sample for optimization."""
    # Mix of single and multi-folder tracks
    single_folder = [(tid, folders) for tid, folders in mapping.items() if len(folders) == 1]
    multi_folder = [(tid, folders) for tid, folders in mapping.items() if len(folders) > 1]
    
    # Sample proportionally
    single_sample = random.sample(single_folder, min(n_samples//2, len(single_folder)))
    multi_sample = random.sample(multi_folder, min(n_samples//2, len(multi_folder)))
    
    return single_sample + multi_sample

def confidence_weighted_classification(track_id: str, 
                                     genre_weight: float = 3.0,
                                     audio_weight: float = 1.0,
                                     max_predictions: int = 3) -> List[str]:
    """
    Enhanced classification with confidence weighting.
    
    Args:
        track_id: Track to classify
        genre_weight: Weight for artist genre matches
        audio_weight: Weight for audio feature matches  
        max_predictions: Maximum number of folders to return
        
    Returns:
        List of predicted folder names, sorted by confidence
    """
    client = get_safe_spotify_client()
    if not client:
        return []
    
    mapping = get_default_genre_mapping()
    
    # Get data
    artist_genres = get_artist_genres(client, track_id)
    audio_features = get_audio_features(client, track_id)
    
    # Calculate confidence scores for each folder
    folder_scores = defaultdict(float)
    
    # Genre-based scoring
    genre_matches = classify_by_genres(artist_genres, mapping)
    for folder in genre_matches:
        folder_scores[folder] += genre_weight
    
    # Audio feature scoring
    if audio_features:
        audio_matches = classify_by_audio_features(audio_features, mapping)
        for folder in audio_matches:
            folder_scores[folder] += audio_weight
    
    # Sort by score and return top predictions
    sorted_folders = sorted(folder_scores.items(), key=lambda x: x[1], reverse=True)
    return [folder for folder, score in sorted_folders[:max_predictions]]

def genre_count_weighted_classification(track_id: str, max_predictions: int = 3) -> List[str]:
    """
    Classification weighted by playlist genre diversity.
    
    Folders with fewer unique genres get higher confidence.
    """
    client = get_safe_spotify_client()
    if not client:
        return []
    
    mapping = get_default_genre_mapping()
    
    # Get basic classifications
    artist_genres = get_artist_genres(client, track_id)
    audio_features = get_audio_features(client, track_id)
    
    genre_matches = classify_by_genres(artist_genres, mapping)
    audio_matches = classify_by_audio_features(audio_features, mapping) if audio_features else []
    
    all_matches = set(genre_matches + audio_matches)
    
    # Weight by genre count (fewer genres = higher weight)
    folder_scores = {}
    for folder in all_matches:
        genre_count = len(mapping[folder].get('genres', []))
        # Inverse weighting: fewer genres = higher score
        folder_scores[folder] = 1.0 / (genre_count + 1)
    
    # Sort by score and return top predictions
    sorted_folders = sorted(folder_scores.items(), key=lambda x: x[1], reverse=True)
    return [folder for folder, score in sorted_folders[:max_predictions]]

def strict_audio_classification(track_id: str, max_predictions: int = 3) -> List[str]:
    """
    Classification with stricter audio feature thresholds.
    """
    client = get_safe_spotify_client()
    if not client:
        return []
    
    # Use stricter audio feature mapping
    strict_mapping = {
        "Electronic": {
            "genres": ["electronic", "edm", "house", "techno", "ambient", "dubstep"],
            "audio_features": {"danceability": ">0.7", "energy": ">0.7"}  # Much stricter
        },
        "Base": {
            "genres": ["bass music", "dubstep", "drum and bass", "glitch"],
            "audio_features": {"energy": ">0.8", "danceability": ">0.8"}  # Very strict
        },
        "Rock": {
            "genres": ["rock", "metal", "punk", "alternative"],
            "audio_features": {"energy": ">0.7", "acousticness": "<0.3"}  # Stricter
        },
        "Chill": {
            "genres": ["ambient", "lo-fi", "chillout"],
            "audio_features": {"energy": "<0.3", "valence": ">0.4"}  # Much stricter
        }
        # Add more as needed...
    }
    
    artist_genres = get_artist_genres(client, track_id)
    audio_features = get_audio_features(client, track_id)
    
    # Use original mapping for genre matching, strict for audio
    original_mapping = get_default_genre_mapping()
    genre_matches = classify_by_genres(artist_genres, original_mapping)
    
    # Use strict mapping for audio features
    audio_matches = classify_by_audio_features(audio_features, strict_mapping) if audio_features else []
    
    # Combine and limit
    all_matches = list(set(genre_matches + audio_matches))
    return all_matches[:max_predictions]

def test_strategy(strategy_func: Callable, test_sample: List[Tuple[str, List[str]]], 
                 strategy_name: str) -> Dict[str, float]:
    """Test a classification strategy on the sample."""
    
    total_tracks = len(test_sample)
    total_recall = 0.0
    total_precision = 0.0
    total_predictions = 0
    
    for track_id, actual_folders in test_sample:
        predicted_folders = strategy_func(track_id)
        
        if not actual_folders:
            continue
            
        # Calculate metrics
        actual_set = set(actual_folders)
        predicted_set = set(predicted_folders)
        intersection = actual_set & predicted_set
        
        recall = len(intersection) / len(actual_set) if actual_set else 0
        precision = len(intersection) / len(predicted_set) if predicted_set else 0
        
        total_recall += recall
        total_precision += precision
        total_predictions += len(predicted_folders)
    
    avg_recall = total_recall / total_tracks
    avg_precision = total_precision / total_tracks  
    avg_predictions_per_track = total_predictions / total_tracks
    f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
    
    return {
        'recall': avg_recall,
        'precision': avg_precision,
        'f1': f1,
        'avg_predictions': avg_predictions_per_track,
        'strategy': strategy_name
    }

def compare_strategies():
    """Compare different classification strategies."""
    
    print("🚀 Classification Strategy Optimization")
    print("=" * 50)
    
    # Load mapping and get test sample
    mapping, _ = load_mapping()
    if not mapping:
        print("❌ No mapping found")
        return
    
    print(f"📊 Loaded {len(mapping)} tracks")
    
    # Get quick test sample
    test_sample = quick_test_sample(mapping, n_samples=50)  # Small for speed
    print(f"🎯 Testing on {len(test_sample)} tracks")
    
    # Define strategies to test
    strategies = [
        # Current system (baseline)
        (lambda tid: classify_track(track_id=tid), "Current System"),
        
        # Confidence weighted
        (lambda tid: confidence_weighted_classification(tid, genre_weight=3.0, audio_weight=1.0, max_predictions=3), 
         "Confidence Weighted (3x genres, max 3)"),
        
        (lambda tid: confidence_weighted_classification(tid, genre_weight=5.0, audio_weight=1.0, max_predictions=2), 
         "High Genre Weight (5x genres, max 2)"),
        
        # Genre count weighted
        (lambda tid: genre_count_weighted_classification(tid, max_predictions=3), 
         "Genre Count Weighted (max 3)"),
        
        (lambda tid: genre_count_weighted_classification(tid, max_predictions=2), 
         "Genre Count Weighted (max 2)"),
        
        # Strict audio
        (lambda tid: strict_audio_classification(tid, max_predictions=3), 
         "Strict Audio Features"),
    ]
    
    results = []
    
    print("\n🧪 Testing Strategies:")
    print("-" * 30)
    
    for strategy_func, strategy_name in strategies:
        print(f"Testing: {strategy_name}")
        result = test_strategy(strategy_func, test_sample, strategy_name)
        results.append(result)
        print(f"   R={result['recall']:.3f} P={result['precision']:.3f} F1={result['f1']:.3f} Avg={result['avg_predictions']:.1f}")
    
    # Print comparison
    print(f"\n📊 STRATEGY COMPARISON")
    print("=" * 80)
    print(f"{'Strategy':<35} {'Recall':<8} {'Precision':<10} {'F1':<8} {'Avg Pred':<8}")
    print("-" * 80)
    
    # Sort by F1 score
    results.sort(key=lambda x: x['f1'], reverse=True)
    
    for result in results:
        print(f"{result['strategy']:<35} {result['recall']:<8.3f} {result['precision']:<10.3f} {result['f1']:<8.3f} {result['avg_predictions']:<8.1f}")
    
    # Recommendations
    best_f1 = results[0]
    best_recall = max(results, key=lambda x: x['recall'])
    best_precision = max(results, key=lambda x: x['precision'])
    
    print(f"\n🏆 RECOMMENDATIONS:")
    print(f"   🎯 Best Overall (F1):     {best_f1['strategy']}")
    print(f"   🔍 Best Recall:           {best_recall['strategy']}")
    print(f"   🎯 Best Precision:        {best_precision['strategy']}")

def main():
    """Main optimization function."""
    # Import here to avoid circular import
    from common.genre_classification_utils import classify_track
    globals()['classify_track'] = classify_track
    
    compare_strategies()

if __name__ == "__main__":
    main()