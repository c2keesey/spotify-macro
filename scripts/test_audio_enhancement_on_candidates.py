#!/usr/bin/env python3
"""
Test enhanced audio classifier on specific weak candidates.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.composite_classifier import CompositeClassifier
from analysis.genre.enhanced_audio_classifier import EnhancedAudioClassifier
from common.music_api_clients import MusicFeatureFetcher
from common.music_api_config import get_lastfm_api_key, get_getsongbpm_api_key
import json
import time

def test_candidates():
    """Test enhanced classifier on weak classification candidates."""
    
    print("🧪 TESTING AUDIO ENHANCEMENT ON WEAK CANDIDATES")
    print("=" * 60)
    
    # Candidate tracks that need better classification
    candidates = [
        ("3yxE4Fhv4K1FoTPYoE9uDg", "M4verick", ["Bravo Charlie"]),
        ("1KY3su6yQ7pNiCqSGMZOOj", "Silence", ["NVYKO"]),
        ("3KcDfeZ1UAMtun8TuvG1kT", "Peak (Fed Up)", ["RAAHiiM"]),
        ("3qhVuoRARUUL9PYlVeMEen", "All In", ["Artifakts"]),
        ("3BINSFSuHalV8yoX3zAVbl", "Juice", ["Young Franco", "Pell"]),
    ]
    
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
    
    # Initialize music fetcher for manual audio feature inspection
    print("\n🎵 Initializing music feature fetcher...")
    music_fetcher = MusicFeatureFetcher(
        lastfm_api_key=get_lastfm_api_key(),
        getsongbpm_api_key=get_getsongbpm_api_key()
    )
    
    # Test each candidate
    print("\n🔍 TESTING CANDIDATES")
    print("=" * 60)
    
    for i, (track_id, track_name, artists) in enumerate(candidates):
        print(f"\n🎵 Candidate {i+1}: {track_name}")
        print(f"   👥 Artists: {', '.join(artists)}")
        print("-" * 50)
        
        # Get available audio features for this track
        print("🎼 Fetching audio features...")
        audio_features = music_fetcher.get_combined_features(artists[0], track_name)
        
        print("📊 Available audio features:")
        for key, value in audio_features.items():
            if value is not None and value != []:
                if key == 'tags':
                    print(f"   {key}: {value[:3]}{'...' if len(value) > 3 else ''}")
                else:
                    print(f"   {key}: {value}")
        
        if not any(audio_features.values()):
            print("   ❌ No audio features available")
        
        # Test original classifier
        print(f"\n🔶 Original Classifier:")
        original_result = original_classifier.predict(track_id)
        print(f"   Folders: {original_result.predicted_folders}")
        print(f"   Confidence: {getattr(original_result, 'confidence_scores', {})}")
        print(f"   Reasoning: {original_result.reasoning}")
        
        # Test enhanced classifier
        print(f"\n🔷 Enhanced Classifier:")
        enhanced_result = enhanced_classifier.predict(track_id)
        print(f"   Folders: {enhanced_result.predicted_folders}")
        print(f"   Confidence: {getattr(enhanced_result, 'confidence_scores', {})}")
        print(f"   Reasoning: {enhanced_result.reasoning}")
        
        # Analysis
        original_folders = set(original_result.predicted_folders)
        enhanced_folders = set(enhanced_result.predicted_folders)
        
        if enhanced_folders != original_folders:
            new_folders = enhanced_folders - original_folders
            lost_folders = original_folders - enhanced_folders
            
            print(f"\n📈 AUDIO ENHANCEMENT EFFECT:")
            if new_folders:
                print(f"   ➕ New folders: {list(new_folders)}")
            if lost_folders:
                print(f"   ➖ Lost folders: {list(lost_folders)}")
                
            # Check if confidence improved
            original_conf = getattr(original_result, 'confidence_scores', {})
            enhanced_conf = getattr(enhanced_result, 'confidence_scores', {})
            
            if enhanced_conf and original_conf:
                original_max = max(original_conf.values()) if original_conf else 0
                enhanced_max = max(enhanced_conf.values()) if enhanced_conf else 0
                
                if enhanced_max > original_max:
                    print(f"   📈 Confidence improved: {original_max:.2f} → {enhanced_max:.2f}")
                elif enhanced_max < original_max:
                    print(f"   📉 Confidence decreased: {original_max:.2f} → {enhanced_max:.2f}")
        else:
            print(f"\n✅ Same classification (no audio enhancement)")
            
        print("=" * 60)
    
    print(f"\n📊 AUDIO FEATURE AVAILABILITY SUMMARY")
    print("=" * 60)
    
    # Quick summary of what audio features we can get
    available_apis = list(music_fetcher.clients.keys())
    print(f"🔑 Available APIs: {', '.join(available_apis)}")
    
    if 'lastfm' not in available_apis:
        print("💡 Tip: Set LASTFM_API_KEY environment variable for genre tags")
    if 'getsongbpm' not in available_apis:
        print("💡 Tip: Set GETSONGBPM_API_KEY environment variable for BPM data")

if __name__ == "__main__":
    try:
        test_candidates()
    except KeyboardInterrupt:
        print("\n\n👋 Testing stopped by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()