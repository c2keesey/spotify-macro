#!/usr/bin/env python3
"""
Test hybrid classification systems using real artist and audio feature data.

Uses cached playlist data to get actual artist information for tracks.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import random
from hybrid_classification_systems import (
    ArtistFirstSystem, ConfidenceWeightedSystem, 
    ElectronicSpecialistSystem, EnsembleSystem, TestResults
)

def load_real_track_data() -> Dict[str, Dict]:
    """Load real track data with artists from playlist files."""
    
    # Load folder structure
    folder_structure_file = Path('_data/playlist_folders.json')
    with open(folder_structure_file, 'r') as f:
        folder_structure = json.load(f)
    
    # Load playlist data
    playlists_dir = Path('_data/playlists')
    track_data = {}  # track_id -> {artists, folders, audio_features}
    
    print("📊 Loading real track data...")
    
    for folder_name, playlist_files in folder_structure.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_path = playlists_dir / f"{playlist_name}.json"
            
            if not playlist_path.exists():
                continue
            
            try:
                with open(playlist_path, 'r') as f:
                    playlist_data = json.load(f)
                
                tracks = playlist_data.get('tracks', [])
                for track in tracks:
                    track_id = track.get('id')
                    if not track_id:
                        continue
                    
                    artists = [artist.get('name') for artist in track.get('artists', []) if artist.get('name')]
                    
                    if track_id not in track_data:
                        track_data[track_id] = {
                            'artists': artists,
                            'folders': set(),
                            'name': track.get('name', 'Unknown'),
                            # Mock audio features based on folder patterns (for testing)
                            'audio_features': generate_mock_audio_features(folder_name)
                        }
                    
                    track_data[track_id]['folders'].add(folder_name)
            
            except Exception as e:
                print(f"❌ Error loading {playlist_name}: {e}")
                continue
    
    # Convert folder sets to lists
    for track_id in track_data:
        track_data[track_id]['folders'] = list(track_data[track_id]['folders'])
    
    print(f"✅ Loaded data for {len(track_data)} tracks")
    return track_data

def generate_mock_audio_features(folder_name: str) -> Dict[str, float]:
    """Generate realistic audio features based on folder characteristics."""
    
    # Base patterns for each folder (with some randomness)
    folder_patterns = {
        'Base': {
            'energy': (0.7, 0.95),
            'danceability': (0.5, 0.8),
            'valence': (0.1, 0.4),
            'tempo': (140, 180),
            'loudness': (-5, -2),
            'acousticness': (0.0, 0.1)
        },
        'Rave': {
            'energy': (0.8, 0.98),
            'danceability': (0.7, 0.95),
            'valence': (0.3, 0.7),
            'tempo': (128, 150),
            'loudness': (-6, -3),
            'acousticness': (0.0, 0.05)
        },
        'House': {
            'energy': (0.6, 0.85),
            'danceability': (0.7, 0.9),
            'valence': (0.4, 0.8),
            'tempo': (118, 130),
            'loudness': (-7, -4),
            'acousticness': (0.0, 0.1)
        },
        'Electronic': {
            'energy': (0.5, 0.8),
            'danceability': (0.5, 0.8),
            'valence': (0.3, 0.7),
            'tempo': (110, 140),
            'loudness': (-8, -4),
            'acousticness': (0.0, 0.2)
        },
        'Alive': {
            'energy': (0.4, 0.7),
            'danceability': (0.4, 0.7),
            'valence': (0.5, 0.8),
            'tempo': (100, 130),
            'loudness': (-10, -5),
            'acousticness': (0.0, 0.3)
        },
        'Vibes': {
            'energy': (0.3, 0.6),
            'danceability': (0.4, 0.7),
            'valence': (0.5, 0.8),
            'tempo': (90, 120),
            'loudness': (-12, -6),
            'acousticness': (0.1, 0.4)
        },
        'Rock': {
            'energy': (0.6, 0.9),
            'danceability': (0.3, 0.6),
            'valence': (0.3, 0.7),
            'tempo': (110, 150),
            'loudness': (-6, -3),
            'acousticness': (0.0, 0.2)
        },
        'Chill': {
            'energy': (0.1, 0.4),
            'danceability': (0.2, 0.5),
            'valence': (0.4, 0.7),
            'tempo': (70, 110),
            'loudness': (-15, -8),
            'acousticness': (0.3, 0.8)
        }
    }
    
    # Default pattern for unknown folders
    default_pattern = {
        'energy': (0.3, 0.7),
        'danceability': (0.3, 0.7),
        'valence': (0.3, 0.7),
        'tempo': (90, 140),
        'loudness': (-12, -5),
        'acousticness': (0.0, 0.5)
    }
    
    pattern = folder_patterns.get(folder_name, default_pattern)
    
    # Generate random values within the pattern ranges
    features = {}
    for feature, (min_val, max_val) in pattern.items():
        features[feature] = random.uniform(min_val, max_val)
    
    return features

def test_system_with_real_data(system, track_data: Dict, sample_size: int = 1000) -> TestResults:
    """Test a classification system with real track data."""
    
    print(f"\n🧪 Testing {system.name} with real data")
    print("=" * 50)
    
    # Sample tracks for testing
    test_tracks = dict(random.sample(list(track_data.items()), min(sample_size, len(track_data))))
    
    correct_predictions = 0
    total_predictions = 0
    total_tracks = len(test_tracks)
    
    precision_correct = 0
    precision_total = 0
    recall_correct = 0
    recall_total = 0
    
    detailed_results = []
    
    for track_id, track_info in test_tracks.items():
        artists = track_info['artists']
        actual_folders = set(track_info['folders'])
        audio_features = track_info['audio_features']
        track_name = track_info['name']
        
        # Get prediction
        result = system.classify_track(track_id, artists, audio_features)
        predicted_folders = set(result.predicted_folders)
        
        # Calculate metrics
        recall_total += len(actual_folders)
        
        if predicted_folders:
            total_predictions += 1
            precision_total += len(predicted_folders)
            
            # Check for correct predictions
            correct = predicted_folders.intersection(actual_folders)
            if correct:
                correct_predictions += 1
                precision_correct += len(correct)
                recall_correct += len(correct)
        
        # Store detailed result for analysis
        detailed_results.append({
            'track_id': track_id,
            'track_name': track_name,
            'artists': artists,
            'actual_folders': list(actual_folders),
            'predicted_folders': list(predicted_folders),
            'correct': len(predicted_folders.intersection(actual_folders)) > 0,
            'confidence_scores': result.confidence_scores,
            'method': result.method,
            'reasoning': result.reasoning
        })
    
    # Calculate final metrics
    accuracy = correct_predictions / total_tracks if total_tracks > 0 else 0
    precision = precision_correct / precision_total if precision_total > 0 else 0
    recall = recall_correct / recall_total if recall_total > 0 else 0
    coverage = total_predictions / total_tracks if total_tracks > 0 else 0
    
    results = TestResults(
        name=system.name,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        coverage=coverage,
        correct_predictions=correct_predictions,
        total_predictions=total_predictions,
        total_tracks=total_tracks
    )
    
    print(f"✅ {system.name} Results:")
    print(f"   🎯 Accuracy: {accuracy:.1%} ({correct_predictions}/{total_tracks})")
    print(f"   🎯 Precision: {precision:.1%} ({precision_correct}/{precision_total})")
    print(f"   🎯 Recall: {recall:.1%} ({recall_correct}/{recall_total})")
    print(f"   📊 Coverage: {coverage:.1%} ({total_predictions}/{total_tracks})")
    
    # Show some example predictions
    print(f"\n🔍 Example predictions:")
    for result in detailed_results[:5]:
        status = "✅" if result['correct'] else "❌"
        print(f"   {status} {result['track_name'][:30]:30} by {', '.join(result['artists'][:2])}")
        print(f"      Actual: {result['actual_folders']}")
        print(f"      Predicted: {result['predicted_folders']} ({result['method']})")
    
    return results, detailed_results

def analyze_system_performance(detailed_results: List[Dict], system_name: str):
    """Analyze detailed performance of a system."""
    
    print(f"\n📊 Detailed Analysis: {system_name}")
    print("=" * 50)
    
    # Performance by folder
    folder_performance = defaultdict(lambda: {'correct': 0, 'total': 0, 'predicted': 0})
    
    for result in detailed_results:
        for folder in result['actual_folders']:
            folder_performance[folder]['total'] += 1
            if folder in result['predicted_folders']:
                folder_performance[folder]['correct'] += 1
        
        for folder in result['predicted_folders']:
            folder_performance[folder]['predicted'] += 1
    
    print("Folder Performance (Recall):")
    for folder, stats in sorted(folder_performance.items()):
        if stats['total'] > 0:
            recall = stats['correct'] / stats['total']
            precision = stats['correct'] / stats['predicted'] if stats['predicted'] > 0 else 0
            print(f"   {folder:12}: {recall:.1%} recall, {precision:.1%} precision ({stats['correct']}/{stats['total']} correct)")
    
    # Method usage
    method_counts = Counter(result['method'] for result in detailed_results)
    print(f"\nClassification Methods Used:")
    for method, count in method_counts.most_common():
        print(f"   {method:20}: {count:4} tracks ({count/len(detailed_results):.1%})")

def main():
    """Test all hybrid systems with real data."""
    print("🎵 Hybrid Classification Systems - Real Data Testing")
    print("=" * 70)
    
    # Load real track data
    track_data = load_real_track_data()
    
    if not track_data:
        print("❌ No track data loaded")
        return
    
    # Initialize systems
    systems = [
        ArtistFirstSystem(),
        ConfidenceWeightedSystem(),
        ElectronicSpecialistSystem(),
        EnsembleSystem()
    ]
    
    # Test each system
    all_results = []
    all_detailed_results = {}
    
    for system in systems:
        results, detailed = test_system_with_real_data(system, track_data, sample_size=1000)
        all_results.append(results)
        all_detailed_results[system.name] = detailed
    
    # Compare results
    print(f"\n📈 SYSTEM COMPARISON")
    print("=" * 80)
    print(f"{'System':<20} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'Coverage':<10}")
    print("-" * 80)
    
    for result in all_results:
        print(f"{result.name:<20} {result.accuracy:<10.1%} {result.precision:<10.1%} {result.recall:<10.1%} {result.coverage:<10.1%}")
    
    # Find best system
    best_system = max(all_results, key=lambda x: x.accuracy)
    print(f"\n🏆 Best System: {best_system.name} with {best_system.accuracy:.1%} accuracy")
    
    # Detailed analysis of best system
    analyze_system_performance(all_detailed_results[best_system.name], best_system.name)
    
    # Save results
    results_summary = {
        'timestamp': json.dumps(None, default=str),
        'systems_tested': len(systems),
        'sample_size': len(all_detailed_results[systems[0].name]),
        'results': [
            {
                'name': r.name,
                'accuracy': r.accuracy,
                'precision': r.precision,
                'recall': r.recall,
                'coverage': r.coverage
            }
            for r in all_results
        ],
        'best_system': best_system.name
    }
    
    cache_dir = Path.home() / ".spotify_cache"
    results_file = cache_dir / "hybrid_systems_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    main()