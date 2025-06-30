#!/usr/bin/env python3
"""
Analyze artist → folder patterns to understand how predictive artists are
for folder classification.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set
from common.genre_classification_utils import get_safe_spotify_client

def load_track_mapping() -> Dict[str, List[str]]:
    """Load the cached track → folder mapping."""
    cache_dir = Path.home() / ".spotify_cache"
    mapping_file = cache_dir / "track_folder_mapping.json"
    
    if not mapping_file.exists():
        print("❌ No track mapping found. Run build_track_folder_mapping.py first")
        return {}
    
    with open(mapping_file, 'r') as f:
        return json.load(f)

def analyze_artist_folder_patterns():
    """Analyze how artists map to folders."""
    print("🎵 Artist → Folder Pattern Analysis")
    print("=" * 50)
    
    # Load track mapping
    track_mapping = load_track_mapping()
    if not track_mapping:
        return
    
    print(f"📊 Analyzing {len(track_mapping)} tracks...")
    
    # Get Spotify client to fetch artist info
    client = get_safe_spotify_client()
    if not client:
        print("❌ No Spotify client available")
        return
    
    # Build artist → folders mapping
    artist_to_folders = defaultdict(set)
    artist_to_tracks = defaultdict(set)
    folder_to_artists = defaultdict(set)
    
    # Process tracks in batches to get artist info
    track_ids = list(track_mapping.keys())
    batch_size = 50
    
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        
        try:
            tracks = client.tracks(batch)
            
            for track in tracks['tracks']:
                if not track:
                    continue
                    
                track_id = track['id']
                folders = track_mapping.get(track_id, [])
                
                # Get all artists for this track
                for artist in track['artists']:
                    artist_name = artist['name']
                    artist_to_folders[artist_name].update(folders)
                    artist_to_tracks[artist_name].add(track_id)
                    
                    for folder in folders:
                        folder_to_artists[folder].add(artist_name)
        
        except Exception as e:
            print(f"❌ Error processing batch {i//batch_size + 1}: {e}")
            continue
        
        # Progress update
        if (i // batch_size + 1) % 10 == 0:
            print(f"   📈 Processed {i + len(batch)} tracks...")
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Found {len(artist_to_folders)} unique artists")
    
    # Analyze artist specificity
    print(f"\n🎯 ARTIST SPECIFICITY ANALYSIS")
    print("=" * 50)
    
    # Single-folder artists (most predictive)
    single_folder_artists = {
        artist: list(folders)[0] 
        for artist, folders in artist_to_folders.items() 
        if len(folders) == 1
    }
    print(f"🎯 Single-folder artists: {len(single_folder_artists)} ({len(single_folder_artists)/len(artist_to_folders)*100:.1f}%)")
    
    # Multi-folder artists
    multi_folder_artists = {
        artist: folders 
        for artist, folders in artist_to_folders.items() 
        if len(folders) > 1
    }
    print(f"🔄 Multi-folder artists: {len(multi_folder_artists)} ({len(multi_folder_artists)/len(artist_to_folders)*100:.1f}%)")
    
    # Artist coverage per folder
    print(f"\n📁 FOLDER COVERAGE")
    print("=" * 30)
    for folder, artists in sorted(folder_to_artists.items(), key=lambda x: len(x[1]), reverse=True):
        single_folder_count = sum(1 for a in artists if len(artist_to_folders[a]) == 1)
        print(f"{folder:12}: {len(artists):4} artists ({single_folder_count:3} exclusive)")
    
    # Most predictive artists by folder
    print(f"\n🌟 TOP PREDICTIVE ARTISTS BY FOLDER")
    print("=" * 45)
    
    for folder in sorted(folder_to_artists.keys()):
        folder_artists = folder_to_artists[folder]
        # Get artists with most tracks in this folder
        folder_artist_counts = Counter()
        
        for artist in folder_artists:
            # Count tracks by this artist in this folder
            track_count = sum(
                1 for track_id in artist_to_tracks[artist]
                if folder in track_mapping.get(track_id, [])
            )
            folder_artist_counts[artist] = track_count
        
        print(f"\n📁 {folder}:")
        top_artists = folder_artist_counts.most_common(10)
        for artist, count in top_artists:
            specificity = len(artist_to_folders[artist])
            marker = "🎯" if specificity == 1 else f"🔄{specificity}"
            print(f"   {marker} {artist:25} ({count:2} tracks)")
    
    # Calculate predictive power
    print(f"\n📈 PREDICTIVE POWER ANALYSIS")
    print("=" * 35)
    
    total_tracks = len(track_mapping)
    correctly_predicted = 0
    
    for track_id, actual_folders in track_mapping.items():
        try:
            track = client.track(track_id)
            if not track:
                continue
                
            # Get artist predictions
            predicted_folders = set()
            for artist in track['artists']:
                artist_name = artist['name']
                if artist_name in single_folder_artists:
                    predicted_folders.add(single_folder_artists[artist_name])
            
            # Check if any prediction matches actual folders
            if predicted_folders.intersection(set(actual_folders)):
                correctly_predicted += 1
                
        except Exception:
            continue
    
    if total_tracks > 0:
        accuracy = correctly_predicted / total_tracks * 100
        print(f"🎯 Artist-based prediction accuracy: {accuracy:.1f}%")
        print(f"   ({correctly_predicted}/{total_tracks} tracks correctly predicted)")
    
    # Save results
    results = {
        'single_folder_artists': {k: list(v) if isinstance(v, set) else v for k, v in single_folder_artists.items()},
        'multi_folder_artists': {k: list(v) for k, v in multi_folder_artists.items()},
        'folder_artist_counts': {
            folder: dict(Counter(
                artist for artist in artists 
                if len(artist_to_folders[artist]) == 1
            ).most_common(20))
            for folder, artists in folder_to_artists.items()
        },
        'stats': {
            'total_artists': len(artist_to_folders),
            'single_folder_artists': len(single_folder_artists),
            'multi_folder_artists': len(multi_folder_artists),
            'prediction_accuracy': accuracy if 'accuracy' in locals() else 0
        }
    }
    
    cache_dir = Path.home() / ".spotify_cache"
    results_file = cache_dir / "artist_folder_analysis.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    analyze_artist_folder_patterns()