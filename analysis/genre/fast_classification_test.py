#!/usr/bin/env python3
"""
Fast genre classification testing with optimized performance.

Minimizes redundant client initialization and cache loading.
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

class FastClassifier:
    """Optimized classifier that reuses client and mapping."""
    
    def __init__(self):
        """Initialize client and mapping once."""
        print("🔧 Initializing classifier...")
        self.client = get_safe_spotify_client()
        self.mapping = get_default_genre_mapping()
        print("✅ Classifier ready")
        
    def get_track_name(self, track_id: str) -> str:
        """Get track name and artist for display."""
        if not self.client:
            return track_id
        
        try:
            track = self.client.track(track_id)
            if track:
                name = track.get('name', 'Unknown')
                artists = track.get('artists', [])
                artist_name = artists[0]['name'] if artists else 'Unknown Artist'
                return f"{name} - {artist_name}"
        except:
            pass
        
        return track_id
        
    def classify_track_fast(self, track_id: str) -> List[str]:
        """Fast track classification using only artist genres (no audio features)."""
        if not self.client:
            return []
        
        # Use only artist genres for classification
        artist_genres = get_artist_genres(self.client, track_id)
        if artist_genres:
            genre_matches = classify_by_genres(artist_genres, self.mapping)
            return genre_matches
        
        return []
    
    def confidence_weighted_classify(self, track_id: str, 
                                   genre_weight: float = 3.0,
                                   audio_weight: float = 1.0,
                                   max_predictions: int = 3) -> List[str]:
        """Fast classification using only artist genres (audio features removed)."""
        if not self.client:
            return []
        
        # Use only artist genres
        artist_genres = get_artist_genres(self.client, track_id)
        if artist_genres:
            genre_matches = classify_by_genres(artist_genres, self.mapping)
            return genre_matches[:max_predictions]
        
        return []
    
    def max_limited_classify(self, track_id: str, max_predictions: int = 3) -> List[str]:
        """Current system but limited to max predictions."""
        predictions = self.classify_track_fast(track_id)
        return predictions[:max_predictions]

def quick_test_sample(mapping: Dict[str, List[str]], n_samples: int = 50) -> List[Tuple[str, List[str]]]:
    """Get a balanced test sample."""
    # Get different types of tracks
    single_folder = [(tid, folders) for tid, folders in mapping.items() if len(folders) == 1]
    multi_folder = [(tid, folders) for tid, folders in mapping.items() if len(folders) > 1]
    
    # Sample proportionally
    single_count = min(n_samples // 2, len(single_folder))
    multi_count = min(n_samples - single_count, len(multi_folder))
    
    sample = (random.sample(single_folder, single_count) + 
              random.sample(multi_folder, multi_count))
    
    return sample

def calculate_metrics(actual: List[str], predicted: List[str]) -> Dict[str, float]:
    """Calculate precision, recall, F1."""
    if not actual and not predicted:
        return {'precision': 1.0, 'recall': 1.0, 'f1': 1.0}
    if not actual:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    if not predicted:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    
    actual_set = set(actual)
    predicted_set = set(predicted)
    intersection = actual_set & predicted_set
    
    precision = len(intersection) / len(predicted_set)
    recall = len(intersection) / len(actual_set)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {'precision': precision, 'recall': recall, 'f1': f1}

def test_strategy_fast(classifier: FastClassifier, 
                      strategy_func: Callable,
                      test_sample: List[Tuple[str, List[str]]], 
                      strategy_name: str) -> Dict[str, float]:
    """Fast test of a classification strategy."""
    
    total_tracks = len(test_sample)
    metrics_sum = {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    total_predictions = 0
    
    print(f"   Testing: {strategy_name} ({total_tracks} tracks)...")
    
    for i, (track_id, actual_folders) in enumerate(test_sample):
        if i % 10 == 0:
            print(f"      Progress: {i}/{total_tracks}")
            
        predicted_folders = strategy_func(track_id)
        metrics = calculate_metrics(actual_folders, predicted_folders)
        
        metrics_sum['precision'] += metrics['precision']
        metrics_sum['recall'] += metrics['recall']
        metrics_sum['f1'] += metrics['f1']
        total_predictions += len(predicted_folders)
    
    # Calculate averages
    avg_metrics = {k: v / total_tracks for k, v in metrics_sum.items()}
    avg_metrics['avg_predictions'] = total_predictions / total_tracks
    avg_metrics['strategy'] = strategy_name
    
    return avg_metrics

def compare_strategies_fast():
    """Fast comparison of different strategies."""
    
    print("🚀 Fast Classification Strategy Comparison")
    print("=" * 50)
    
    # Load mapping
    mapping, _ = load_mapping()
    if not mapping:
        print("❌ No mapping found")
        return
    
    print(f"📊 Loaded {len(mapping)} tracks")
    
    # Get test sample
    test_sample = quick_test_sample(mapping, n_samples=100)  # Larger sample since it's faster
    print(f"🎯 Testing on {len(test_sample)} tracks")
    
    # Initialize classifier once
    classifier = FastClassifier()
    
    # Define strategies (all using genres only now)
    strategies = [
        (classifier.classify_track_fast, "Genres Only (unlimited)"),
        (lambda tid: classifier.max_limited_classify(tid, 3), "Genres Only (max 3)"),
        (lambda tid: classifier.max_limited_classify(tid, 2), "Genres Only (max 2)"),
        (lambda tid: classifier.max_limited_classify(tid, 4), "Genres Only (max 4)"),
        (lambda tid: classifier.max_limited_classify(tid, 1), "Genres Only (max 1)"),
    ]
    
    results = []
    
    print("\n🧪 Testing Strategies:")
    print("-" * 40)
    
    for strategy_func, strategy_name in strategies:
        result = test_strategy_fast(classifier, strategy_func, test_sample, strategy_name)
        results.append(result)
        print(f"   ✅ {strategy_name}")
        print(f"      R={result['recall']:.3f} P={result['precision']:.3f} F1={result['f1']:.3f} Avg={result['avg_predictions']:.1f}")
    
    # Print comparison table
    print(f"\n📊 STRATEGY COMPARISON")
    print("=" * 90)
    print(f"{'Strategy':<40} {'Recall':<8} {'Precision':<10} {'F1':<8} {'Avg Pred':<8}")
    print("-" * 90)
    
    # Sort by F1 score
    results.sort(key=lambda x: x['f1'], reverse=True)
    
    for result in results:
        print(f"{result['strategy']:<40} {result['recall']:<8.3f} {result['precision']:<10.3f} {result['f1']:<8.3f} {result['avg_predictions']:<8.1f}")
    
    # Show detailed insights
    print(f"\n🎯 INSIGHTS:")
    
    best_overall = results[0]
    best_recall = max(results, key=lambda x: x['recall'])
    best_precision = max(results, key=lambda x: x['precision'])
    lowest_predictions = min(results, key=lambda x: x['avg_predictions'])
    
    print(f"   🏆 Best Overall (F1):      {best_overall['strategy']} (F1: {best_overall['f1']:.3f})")
    print(f"   🔍 Best Recall:            {best_recall['strategy']} (R: {best_recall['recall']:.3f})")
    print(f"   🎯 Best Precision:         {best_precision['strategy']} (P: {best_precision['precision']:.3f})")
    print(f"   📉 Fewest Predictions:     {lowest_predictions['strategy']} ({lowest_predictions['avg_predictions']:.1f} avg)")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if best_overall['avg_predictions'] > 5:
        print(f"   • Consider 'max 2-3' strategies to reduce over-classification")
    
    if best_recall['recall'] > 0.8:
        print(f"   • Recall is strong - system finds correct folders well")
    else:
        print(f"   • Recall could be improved - some correct folders are missed")
    
    if best_precision['precision'] < 0.3:
        print(f"   • Precision is low - many incorrect folders predicted")
        print(f"   • For recall-focused use case, this may be acceptable")
    
    return results

def show_examples(classifier: FastClassifier, mapping: Dict[str, List[str]], n_examples: int = 5):
    """Show concrete examples of different strategies."""
    
    print(f"\n🎵 EXAMPLE CLASSIFICATIONS")
    print("=" * 80)
    
    # Get a few interesting tracks
    multi_folder_tracks = [(tid, folders) for tid, folders in mapping.items() if len(folders) > 1]
    example_tracks = random.sample(multi_folder_tracks, n_examples)
    
    for i, (track_id, actual_folders) in enumerate(example_tracks):
        track_name = classifier.get_track_name(track_id)
        
        print(f"\n🎵 Example {i+1}: {track_name}")
        print(f"   Actual folders: {actual_folders}")
        
        # Test different strategies
        current = classifier.classify_track_fast(track_id)
        limited = classifier.max_limited_classify(track_id, 3)
        
        print(f"   Current system (genres only):  {current}")
        print(f"   Limited (max 3):               {limited}")
        
        # Show which found the actual folders
        current_found = set(actual_folders) & set(current)
        limited_found = set(actual_folders) & set(limited)
        
        print(f"   ✅ Found by current:           {list(current_found)}")
        print(f"   ✅ Found by limited:           {list(limited_found)}")
        
        # Show recall percentages
        current_recall = len(current_found) / len(actual_folders) if actual_folders else 0
        limited_recall = len(limited_found) / len(actual_folders) if actual_folders else 0
        
        print(f"   📊 Recall: Current={current_recall:.1%}, Limited={limited_recall:.1%}")

def main():
    """Main function."""
    results = compare_strategies_fast()
    
    # Ask if user wants to see examples
    try:
        response = input("\n🎵 Show classification examples? (y/n): ").lower().strip()
        if response == 'y':
            mapping, _ = load_mapping()
            classifier = FastClassifier()
            show_examples(classifier, mapping)
    except EOFError:
        pass  # Handle non-interactive environments

if __name__ == "__main__":
    main()