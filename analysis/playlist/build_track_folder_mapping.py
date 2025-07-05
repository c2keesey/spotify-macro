#!/usr/bin/env python3
"""
Build track → folders mapping from actual playlist data.

Creates a comprehensive mapping of which tracks appear in which folders
for accurate testing of the genre classification system.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
from common.genre_classification_utils import get_safe_spotify_client

def build_track_folder_mapping() -> Dict[str, List[str]]:
    """
    Build mapping from track IDs to the folders they actually appear in.
    
    Returns:
        Dictionary mapping track_id → [list_of_folder_names]
    """
    client = get_safe_spotify_client()
    if not client:
        print("❌ No client available")
        return {}
    
    print("🔍 Building track → folders mapping from your library...")
    
    # Track ID → Set of folder names
    track_to_folders = defaultdict(set)
    
    # Get all folders
    if hasattr(client, 'playlist_folders'):
        folders = client.playlist_folders
    else:
        print("❌ No playlist folders data available")
        return {}
    
    folder_stats = {}
    total_tracks_processed = 0
    
    for folder_name, playlist_files in folders.items():
        print(f"\n📁 Processing folder: {folder_name}")
        folder_tracks = set()
        playlists_processed = 0
        
        for playlist_file in playlist_files:
            try:
                # Get playlist name and ID
                playlist_name = playlist_file.replace('.json', '')
                
                # Find playlist ID from client's name mapping
                if hasattr(client, 'name_to_id') and playlist_name in client.name_to_id:
                    playlist_id = client.name_to_id[playlist_name]
                    
                    # Get tracks from this playlist
                    tracks = client.playlist_tracks(playlist_id, limit=1000)  # Get more tracks
                    
                    playlist_track_count = 0
                    for track_item in tracks['items']:
                        if track_item and 'id' in track_item:
                            track_id = track_item['id']
                            track_to_folders[track_id].add(folder_name)
                            folder_tracks.add(track_id)
                            playlist_track_count += 1
                    
                    playlists_processed += 1
                    print(f"   📀 {playlist_name}: {playlist_track_count} tracks")
                    
            except Exception as e:
                print(f"   ⚠️  Error processing {playlist_file}: {e}")
                continue
        
        folder_stats[folder_name] = {
            'playlists': playlists_processed,
            'unique_tracks': len(folder_tracks),
            'total_playlist_files': len(playlist_files)
        }
        total_tracks_processed += len(folder_tracks)
        
        print(f"   📊 Folder summary: {len(folder_tracks)} unique tracks across {playlists_processed} playlists")
    
    # Convert sets to lists for JSON serialization
    final_mapping = {track_id: list(folders) for track_id, folders in track_to_folders.items()}
    
    print(f"\n🎯 Mapping Complete!")
    print(f"   📊 Total unique tracks: {len(final_mapping)}")
    print(f"   📁 Folders processed: {len(folder_stats)}")
    
    return final_mapping, folder_stats

def analyze_mapping(mapping: Dict[str, List[str]], folder_stats: Dict):
    """Analyze the track → folders mapping for insights."""
    
    print(f"\n📈 MAPPING ANALYSIS")
    print("=" * 50)
    
    # Track distribution
    single_folder_tracks = sum(1 for folders in mapping.values() if len(folders) == 1)
    multi_folder_tracks = sum(1 for folders in mapping.values() if len(folders) > 1)
    max_folders = max(len(folders) for folders in mapping.values()) if mapping else 0
    
    print(f"📊 Track Distribution:")
    print(f"   🎵 Total tracks: {len(mapping)}")
    print(f"   📁 Single folder: {single_folder_tracks} ({single_folder_tracks/len(mapping)*100:.1f}%)")
    print(f"   🔄 Multi folder: {multi_folder_tracks} ({multi_folder_tracks/len(mapping)*100:.1f}%)")
    print(f"   🎯 Max folders per track: {max_folders}")
    
    # Folder stats
    print(f"\n📁 Folder Statistics:")
    for folder, stats in sorted(folder_stats.items(), key=lambda x: x[1]['unique_tracks'], reverse=True):
        print(f"   {folder:<12}: {stats['unique_tracks']:4d} tracks, {stats['playlists']:2d} playlists")
    
    # Cross-folder analysis
    print(f"\n🔄 Cross-Folder Analysis:")
    folder_pairs = defaultdict(int)
    for track_id, folders in mapping.items():
        if len(folders) > 1:
            folders_sorted = sorted(folders)
            for i, folder1 in enumerate(folders_sorted):
                for folder2 in folders_sorted[i+1:]:
                    folder_pairs[(folder1, folder2)] += 1
    
    # Show top folder overlaps
    top_overlaps = sorted(folder_pairs.items(), key=lambda x: x[1], reverse=True)[:10]
    for (folder1, folder2), count in top_overlaps:
        print(f"   {folder1} ↔ {folder2}: {count} shared tracks")
    
    # Most distributed tracks
    most_distributed = sorted(mapping.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    if most_distributed:
        print(f"\n🌟 Most Distributed Tracks:")
        for track_id, folders in most_distributed:
            print(f"   {track_id}: {len(folders)} folders → {', '.join(folders)}")

def save_mapping(mapping: Dict[str, List[str]], folder_stats: Dict):
    """Save the mapping to cache files."""
    cache_dir = Path.home() / ".spotify_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # Save track mapping
    mapping_file = cache_dir / "track_folder_mapping.json"
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    print(f"💾 Saved track mapping to: {mapping_file}")
    
    # Save folder stats
    stats_file = cache_dir / "folder_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(folder_stats, f, indent=2)
    print(f"💾 Saved folder stats to: {stats_file}")
    
    return mapping_file, stats_file

def load_mapping() -> tuple:
    """Load the cached mapping and stats."""
    cache_dir = Path.home() / ".spotify_cache"
    mapping_file = cache_dir / "track_folder_mapping.json"
    stats_file = cache_dir / "folder_stats.json"
    
    if not mapping_file.exists():
        return None, None
    
    try:
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
        
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        print(f"📁 Loaded cached mapping: {len(mapping)} tracks")
        return mapping, stats
    except Exception as e:
        print(f"⚠️  Error loading cached mapping: {e}")
        return None, None

def main():
    """Main function to build or load the mapping."""
    print("🎵 Track → Folders Mapping Builder")
    print("=" * 40)
    
    # Try to load cached mapping first
    mapping, folder_stats = load_mapping()
    
    if mapping is None:
        print("🔄 Building new mapping...")
        mapping, folder_stats = build_track_folder_mapping()
        
        if mapping:
            save_mapping(mapping, folder_stats)
        else:
            print("❌ Failed to build mapping")
            return
    else:
        print("✅ Using cached mapping")
    
    # Analyze the mapping
    if mapping:
        analyze_mapping(mapping, folder_stats)
        
        # Ask if user wants to rebuild
        response = input("\n🔄 Rebuild mapping from scratch? (y/n): ").lower().strip()
        if response == 'y':
            print("🔄 Rebuilding mapping...")
            mapping, folder_stats = build_track_folder_mapping()
            if mapping:
                save_mapping(mapping, folder_stats)
                analyze_mapping(mapping, folder_stats)

if __name__ == "__main__":
    main()