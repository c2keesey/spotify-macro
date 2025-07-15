#!/usr/bin/env python3
"""
Test the enhanced audio classifier against the original composite classifier.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.composite_classifier import CompositeClassifier
from analysis.genre.enhanced_audio_classifier import EnhancedAudioClassifier
import json
import time

def compare_classifiers():
    """Compare original vs enhanced classifier on sample tracks."""
    
    print("🧪 ENHANCED CLASSIFIER COMPARISON TEST")
    print("=" * 60)
    
    # Load data
    print("📁 Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Load playlist folder mapping and build training data
    print("📁 Loading folder mapping for training...")
    with open('data/playlist_folders.json', 'r') as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping: playlist name -> folder name  
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    # Prepare training data
    train_tracks = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        if playlist_name in playlist_to_folder and playlist_name != 'New':
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data["tracks"]:
                train_tracks.append((track["id"], folder_name))
    
    train_data = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    print(f"   Training on {len(train_tracks)} tracks")
    
    # Initialize both classifiers
    print("\n🧠 Initializing classifiers...")
    
    print("  1️⃣ Training original composite classifier...")
    original_classifier = CompositeClassifier()
    original_classifier.train(train_data)
    
    print("  2️⃣ Training enhanced audio classifier...")
    enhanced_classifier = EnhancedAudioClassifier()
    enhanced_classifier.train(train_data)
    
    # Get sample tracks from New playlist
    print("\n🎵 Getting sample tracks from New playlist...")
    new_playlist = None
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data.get('name') == 'New':
            new_playlist = playlist_data
            break
    
    if not new_playlist or not new_playlist.get('tracks'):
        print("❌ Could not find New playlist with tracks")
        return
    
    sample_tracks = new_playlist['tracks'][:10]  # Test first 10 tracks
    print(f"   Testing {len(sample_tracks)} sample tracks")
    
    # Compare classifications
    print("\n📊 CLASSIFICATION COMPARISON")
    print("=" * 60)
    
    comparison_results = []
    
    for i, track in enumerate(sample_tracks):
        track_id = track.get('id')
        track_name = track.get('name', 'Unknown')
        artist_names = [a.get('name', 'Unknown') for a in track.get('artists', [])]
        
        print(f"\n🎵 Track {i+1}: {track_name}")
        print(f"   👥 Artists: {', '.join(artist_names)}")
        print("-" * 50)
        
        # Test original classifier
        original_start = time.time()
        original_result = original_classifier.predict(track_id)
        original_time = time.time() - original_start
        
        # Test enhanced classifier
        enhanced_start = time.time()
        enhanced_result = enhanced_classifier.predict(track_id)
        enhanced_time = time.time() - enhanced_start
        
        # Display results
        print(f"🔶 Original Classifier ({original_time*1000:.1f}ms):")
        print(f"   Folders: {original_result.predicted_folders}")
        print(f"   Confidence: {getattr(original_result, 'confidence_scores', {})}")
        print(f"   Reasoning: {original_result.reasoning}")
        
        print(f"\n🔷 Enhanced Classifier ({enhanced_time*1000:.1f}ms):")
        print(f"   Folders: {enhanced_result.predicted_folders}")
        print(f"   Confidence: {getattr(enhanced_result, 'confidence_scores', {})}")
        print(f"   Reasoning: {enhanced_result.reasoning}")
        
        # Analysis
        original_folders = set(original_result.predicted_folders)
        enhanced_folders = set(enhanced_result.predicted_folders)
        
        if enhanced_folders != original_folders:
            new_folders = enhanced_folders - original_folders
            lost_folders = original_folders - enhanced_folders
            
            print(f"\n📈 CHANGES:")
            if new_folders:
                print(f"   ➕ New folders: {list(new_folders)}")
            if lost_folders:
                print(f"   ➖ Lost folders: {list(lost_folders)}")
        else:
            print(f"\n✅ Same classification")
            
        comparison_results.append({
            'track_name': track_name,
            'artists': artist_names,
            'original_folders': original_result.predicted_folders,
            'enhanced_folders': enhanced_result.predicted_folders,
            'original_time_ms': original_time * 1000,
            'enhanced_time_ms': enhanced_time * 1000,
            'audio_features_used': 'Audio:' in enhanced_result.reasoning
        })
        
        print("=" * 60)
    
    # Summary statistics
    print(f"\n📊 SUMMARY STATISTICS")
    print("=" * 60)
    
    total_tracks = len(comparison_results)
    audio_enhanced_count = sum(1 for r in comparison_results if r['audio_features_used'])
    different_results_count = sum(1 for r in comparison_results 
                                 if set(r['original_folders']) != set(r['enhanced_folders']))
    
    avg_original_time = sum(r['original_time_ms'] for r in comparison_results) / total_tracks
    avg_enhanced_time = sum(r['enhanced_time_ms'] for r in comparison_results) / total_tracks
    
    print(f"📈 Audio features used: {audio_enhanced_count}/{total_tracks} ({audio_enhanced_count/total_tracks:.1%})")
    print(f"🔄 Different results: {different_results_count}/{total_tracks} ({different_results_count/total_tracks:.1%})")
    print(f"⏱️ Avg processing time:")
    print(f"   Original: {avg_original_time:.1f}ms")
    print(f"   Enhanced: {avg_enhanced_time:.1f}ms")
    print(f"   Overhead: {avg_enhanced_time - avg_original_time:.1f}ms")

if __name__ == "__main__":
    try:
        compare_classifiers()
    except KeyboardInterrupt:
        print("\n\n👋 Comparison stopped by user")
    except Exception as e:
        print(f"\n❌ Error during comparison: {e}")
        import traceback
        traceback.print_exc()