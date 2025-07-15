#!/usr/bin/env python3
"""
Find tracks where base classifier struggles but audio features might help.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.composite_classifier import CompositeClassifier
import json

def find_enhancement_candidates():
    """Find tracks that are unclassified or have low confidence."""
    
    print("🔍 FINDING AUDIO ENHANCEMENT CANDIDATES")
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
    
    # Initialize classifier
    print("\n🧠 Initializing classifier...")
    classifier = CompositeClassifier()
    classifier.train(train_data)
    
    # Get tracks from New playlist
    print("\n🎵 Analyzing New playlist tracks...")
    new_playlist = None
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data.get('name') == 'New':
            new_playlist = playlist_data
            break
    
    if not new_playlist or not new_playlist.get('tracks'):
        print("❌ Could not find New playlist with tracks")
        return
    
    tracks = new_playlist['tracks']
    print(f"   Analyzing {len(tracks)} tracks")
    
    # Classify all tracks and find weak classifications
    weak_classifications = []
    unclassified = []
    statistical_fallbacks = []
    
    for i, track in enumerate(tracks):
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(tracks)}")
            
        track_id = track.get('id')
        track_name = track.get('name', 'Unknown')
        artist_names = [a.get('name', 'Unknown') for a in track.get('artists', [])]
        
        result = classifier.predict(track_id)
        
        # Categorize results
        if not result.predicted_folders:
            unclassified.append({
                'track_id': track_id,
                'track_name': track_name,
                'artists': artist_names,
                'reasoning': result.reasoning
            })
        elif 'Statistical fallback' in result.reasoning:
            statistical_fallbacks.append({
                'track_id': track_id,
                'track_name': track_name,
                'artists': artist_names,
                'folders': result.predicted_folders,
                'confidence': getattr(result, 'confidence_scores', {}),
                'reasoning': result.reasoning
            })
        elif hasattr(result, 'confidence_scores') and result.confidence_scores:
            max_confidence = max(result.confidence_scores.values())
            if max_confidence < 0.3:  # Low confidence threshold
                weak_classifications.append({
                    'track_id': track_id,
                    'track_name': track_name,
                    'artists': artist_names,
                    'folders': result.predicted_folders,
                    'confidence': result.confidence_scores,
                    'max_confidence': max_confidence,
                    'reasoning': result.reasoning
                })
    
    # Report findings
    print(f"\n📊 CLASSIFICATION ANALYSIS")
    print("=" * 60)
    print(f"📈 Total tracks analyzed: {len(tracks)}")
    print(f"❌ Unclassified: {len(unclassified)} ({len(unclassified)/len(tracks):.1%})")
    print(f"📉 Statistical fallbacks: {len(statistical_fallbacks)} ({len(statistical_fallbacks)/len(tracks):.1%})")
    print(f"🔻 Weak classifications (<30% confidence): {len(weak_classifications)} ({len(weak_classifications)/len(tracks):.1%})")
    
    print(f"\n🎯 BEST CANDIDATES FOR AUDIO ENHANCEMENT:")
    print("=" * 60)
    
    # Show some examples of each category
    print(f"\n1️⃣ UNCLASSIFIED TRACKS (showing first 5):")
    for track in unclassified[:5]:
        print(f"   🎵 {track['track_name']} - {', '.join(track['artists'])}")
        print(f"      Reasoning: {track['reasoning']}")
    
    print(f"\n2️⃣ STATISTICAL FALLBACK TRACKS (showing first 5):")
    for track in statistical_fallbacks[:5]:
        print(f"   🎵 {track['track_name']} - {', '.join(track['artists'])}")
        print(f"      Assigned: {track['folders']} (confidence: {track['confidence']})")
    
    print(f"\n3️⃣ WEAK CLASSIFICATION TRACKS (showing first 5):")
    for track in weak_classifications[:5]:
        print(f"   🎵 {track['track_name']} - {', '.join(track['artists'])}")
        print(f"      Folders: {track['folders']} (max confidence: {track['max_confidence']:.2f})")
        print(f"      Reasoning: {track['reasoning']}")
    
    # Return some candidates for further testing
    candidates = []
    candidates.extend(unclassified[:3])
    candidates.extend(statistical_fallbacks[:3])
    candidates.extend(weak_classifications[:3])
    
    print(f"\n🧪 SELECTED TEST CANDIDATES:")
    print("=" * 60)
    for i, candidate in enumerate(candidates):
        print(f"{i+1}. {candidate['track_name']} - {', '.join(candidate['artists'])}")
        print(f"   ID: {candidate['track_id']}")
    
    return candidates

if __name__ == "__main__":
    try:
        candidates = find_enhancement_candidates()
    except KeyboardInterrupt:
        print("\n\n👋 Analysis stopped by user")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()