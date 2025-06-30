#!/usr/bin/env python3
"""
Test script to evaluate genre classification accuracy.

Tests existing songs from genre playlists to see if they get classified
back to their original categories, providing an accuracy score.
"""

import random
from collections import defaultdict
from typing import Dict, List, Tuple

from common.genre_classification_utils import (
    classify_track,
    get_safe_spotify_client,
    get_default_genre_mapping
)


def sample_tracks_from_genre_folders(sp, num_samples_per_folder: int = 10) -> Dict[str, List[Dict]]:
    """
    Sample tracks from each genre folder for testing.
    
    Args:
        sp: Spotify client
        num_samples_per_folder: Number of tracks to sample per folder
        
    Returns:
        Dictionary mapping folder names to list of track samples
    """
    samples = {}
    
    # Get all genre folders
    genre_mapping = get_default_genre_mapping()
    
    for folder_name in genre_mapping.keys():
        folder_playlists = sp.get_folder_playlists(folder_name)
        
        if not folder_playlists:
            print(f"⚠️  No playlists found for folder: {folder_name}")
            continue
            
        # Collect all tracks from all playlists in this folder
        all_tracks = []
        
        for playlist in folder_playlists:
            try:
                tracks = sp.playlist_tracks(playlist['id'], limit=50)
                for track_item in tracks['items']:
                    if track_item and 'id' in track_item:
                        # Extract artist name (first artist)
                        artists = track_item.get('artists', [])
                        artist_name = artists[0]['name'] if artists else 'Unknown'
                        
                        all_tracks.append({
                            'id': track_item['id'],
                            'name': track_item['name'],
                            'artist': artist_name,
                            'playlist': playlist['name']
                        })
            except Exception as e:
                print(f"⚠️  Error getting tracks from {playlist['name']}: {e}")
                continue
        
        # Sample random tracks
        if all_tracks:
            sample_size = min(num_samples_per_folder, len(all_tracks))
            samples[folder_name] = random.sample(all_tracks, sample_size)
            print(f"📁 {folder_name}: Sampled {sample_size} tracks from {len(folder_playlists)} playlists")
        else:
            print(f"⚠️  No tracks found in folder: {folder_name}")
    
    return samples


def test_classification_accuracy(samples: Dict[str, List[Dict]]) -> Dict[str, any]:
    """
    Test classification accuracy on sampled tracks.
    
    Args:
        samples: Dictionary mapping folder names to track samples
        
    Returns:
        Dictionary with accuracy statistics
    """
    results = {
        'total_tested': 0,
        'correct_classifications': 0,
        'partial_matches': 0,
        'misclassifications': 0,
        'no_classification': 0,
        'folder_stats': {},
        'detailed_results': []
    }
    
    print("\n🧪 Testing Classification Accuracy")
    print("=" * 50)
    
    for original_folder, tracks in samples.items():
        folder_stats = {
            'tested': 0,
            'correct': 0,
            'partial': 0,
            'wrong': 0,
            'none': 0
        }
        
        print(f"\n📁 Testing {original_folder} ({len(tracks)} tracks)")
        print("-" * 30)
        
        for track in tracks:
            results['total_tested'] += 1
            folder_stats['tested'] += 1
            
            # Classify the track
            classifications = classify_track(track_id=track['id'])
            
            # Analyze results
            if not classifications:
                results['no_classification'] += 1
                folder_stats['none'] += 1
                status = "❌ No classification"
            elif original_folder in classifications:
                if len(classifications) == 1:
                    results['correct_classifications'] += 1
                    folder_stats['correct'] += 1
                    status = "✅ Correct"
                else:
                    results['partial_matches'] += 1
                    folder_stats['partial'] += 1
                    status = f"🟡 Partial (also: {', '.join([c for c in classifications if c != original_folder])})"
            else:
                results['misclassifications'] += 1
                folder_stats['wrong'] += 1
                status = f"❌ Wrong ({', '.join(classifications)})"
            
            # Store detailed result
            result_detail = {
                'track': f"{track['name']} - {track['artist']}",
                'original_folder': original_folder,
                'classifications': classifications,
                'status': status,
                'playlist': track['playlist']
            }
            results['detailed_results'].append(result_detail)
            
            print(f"  🎵 {track['name'][:30]:<30} | {status}")
        
        # Calculate folder accuracy
        folder_accuracy = (folder_stats['correct'] + folder_stats['partial'] * 0.5) / folder_stats['tested'] * 100
        results['folder_stats'][original_folder] = {
            **folder_stats,
            'accuracy': folder_accuracy
        }
        
        print(f"     📊 Folder Accuracy: {folder_accuracy:.1f}% ({folder_stats['correct']} correct, {folder_stats['partial']} partial)")
    
    return results


def print_summary_report(results: Dict[str, any]):
    """Print a summary report of the accuracy test."""
    
    total = results['total_tested']
    if total == 0:
        print("No tracks tested!")
        return
    
    print("\n" + "=" * 60)
    print("🎯 GENRE CLASSIFICATION ACCURACY REPORT")
    print("=" * 60)
    
    # Overall stats
    correct_pct = (results['correct_classifications'] / total) * 100
    partial_pct = (results['partial_matches'] / total) * 100
    wrong_pct = (results['misclassifications'] / total) * 100
    none_pct = (results['no_classification'] / total) * 100
    
    # Effective accuracy (correct + half credit for partial)
    effective_accuracy = (results['correct_classifications'] + results['partial_matches'] * 0.5) / total * 100
    
    print(f"📊 Overall Results ({total} tracks tested):")
    print(f"   ✅ Correct:        {results['correct_classifications']:3d} ({correct_pct:5.1f}%)")
    print(f"   🟡 Partial Match:  {results['partial_matches']:3d} ({partial_pct:5.1f}%)")
    print(f"   ❌ Wrong:          {results['misclassifications']:3d} ({wrong_pct:5.1f}%)")
    print(f"   ⚫ No Class:       {results['no_classification']:3d} ({none_pct:5.1f}%)")
    print(f"   🎯 Effective Accuracy: {effective_accuracy:.1f}%")
    
    # Folder breakdown
    print(f"\n📁 Per-Folder Accuracy:")
    for folder, stats in results['folder_stats'].items():
        print(f"   {folder:<12}: {stats['accuracy']:5.1f}% ({stats['correct']}/{stats['tested']} correct)")
    
    # Best and worst performing folders
    if results['folder_stats']:
        best_folder = max(results['folder_stats'].items(), key=lambda x: x[1]['accuracy'])
        worst_folder = min(results['folder_stats'].items(), key=lambda x: x[1]['accuracy'])
        
        print(f"\n🏆 Best:  {best_folder[0]} ({best_folder[1]['accuracy']:.1f}%)")
        print(f"🔻 Worst: {worst_folder[0]} ({worst_folder[1]['accuracy']:.1f}%)")
    
    # Show some example misclassifications
    misclassified = [r for r in results['detailed_results'] if '❌ Wrong' in r['status']]
    if misclassified:
        print(f"\n❌ Example Misclassifications:")
        for i, result in enumerate(misclassified[:5]):  # Show first 5
            print(f"   {i+1}. {result['track'][:40]}")
            print(f"      Expected: {result['original_folder']}")
            print(f"      Got: {', '.join(result['classifications'])}")
            print(f"      From: {result['playlist']}")


def main():
    """Main function to run the accuracy test."""
    print("🎵 Genre Classification Accuracy Test")
    print("=====================================")
    
    # Get safe client (uses mock data)
    client = get_safe_spotify_client()
    if not client:
        print("❌ No safe client available")
        return
    
    # Sample tracks from each genre folder
    samples = sample_tracks_from_genre_folders(client, num_samples_per_folder=15)
    
    if not samples:
        print("❌ No samples collected")
        return
    
    # Test classification accuracy
    results = test_classification_accuracy(samples)
    
    # Print summary report
    print_summary_report(results)
    
    # Ask if user wants detailed results
    response = input("\n📋 Show detailed results? (y/n): ").lower().strip()
    if response == 'y':
        print("\n📋 Detailed Results:")
        print("-" * 60)
        for result in results['detailed_results']:
            print(f"🎵 {result['track']}")
            print(f"   📁 Expected: {result['original_folder']}")
            print(f"   🎯 Got: {result['classifications'] if result['classifications'] else 'None'}")
            print(f"   📀 From: {result['playlist']}")
            print(f"   {result['status']}")
            print()


if __name__ == "__main__":
    main()