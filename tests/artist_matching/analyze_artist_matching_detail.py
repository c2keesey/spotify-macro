#!/usr/bin/env python3
"""
Detailed analysis of artist matching to understand why certain playlists have no matches.
"""

import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path


def load_local_playlist_data(data_dir: str) -> Dict[str, Dict]:
    """Load all playlist data from local JSON files."""
    playlists_dict = {}
    data_path = Path(data_dir)
    
    print("Loading local playlist data...")
    
    for json_file in data_path.glob("*.json"):
        if json_file.name == "__init__.py":
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
            
            playlist_name = playlist_data.get("playlist_name", json_file.stem)
            
            # Extract track and artist information
            tracks = []
            for track_item in playlist_data.get("tracks", []):
                track = track_item
                
                # Handle nested track structure
                if "track" in track_item and isinstance(track_item["track"], dict):
                    track = track_item["track"]
                
                # Skip invalid or local tracks
                if not track or track.get("is_local", False):
                    continue
                    
                track_id = track.get("id")
                if not track_id:
                    continue
                
                # Extract artist information
                artists = []
                for artist in track.get("artists", []):
                    artists.append({
                        "id": artist.get("id"),
                        "name": artist.get("name")
                    })
                
                track_data = {
                    "id": track_id,
                    "name": track.get("name"),
                    "artists": artists
                }
                
                tracks.append(track_data)
            
            playlists_dict[playlist_name] = {
                "name": playlist_name,
                "tracks": tracks,
                "original_id": playlist_data.get("playlist_id", "local_" + json_file.stem)
            }
            
        except Exception as e:
            print(f"Failed to load {json_file.name}: {e}")
            continue
    
    return playlists_dict


def analyze_detailed_matching(playlists_dict: Dict[str, Dict], source_name: str = "New"):
    """Perform detailed analysis of why certain playlists have no matches."""
    
    # Build artist mappings
    artist_to_playlists = defaultdict(set)
    artist_names = {}  # Map artist_id to name for reporting
    
    for playlist_name, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_playlists[artist_id].add(playlist_name)
                    artist_names[artist_id] = artist.get("name", "Unknown")
    
    # Find single playlist artists
    single_playlist_artists = set()
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    print(f"Total artists: {len(artist_to_playlists)}")
    print(f"Single-playlist artists: {len(single_playlist_artists)}")
    
    # Analyze source playlist
    source_playlist = playlists_dict.get(source_name)
    if not source_playlist:
        print(f"Source playlist '{source_name}' not found")
        return
    
    print(f"\nAnalyzing '{source_name}' playlist ({len(source_playlist['tracks'])} tracks)...")
    
    # Check artists in source playlist
    source_artists = set()
    artist_distribution = Counter()
    
    for track in source_playlist["tracks"]:
        for artist in track["artists"]:
            artist_id = artist.get("id")
            if artist_id:
                source_artists.add(artist_id)
                playlist_count = len(artist_to_playlists[artist_id])
                artist_distribution[playlist_count] += 1
    
    print(f"Unique artists in '{source_name}': {len(source_artists)}")
    print(f"Artists appearing in only 1 playlist: {artist_distribution[1]}")
    print(f"Artists appearing in 2-5 playlists: {sum(artist_distribution[i] for i in range(2, 6))}")
    print(f"Artists appearing in 6+ playlists: {sum(artist_distribution[i] for i in range(6, max(artist_distribution.keys()) + 1) if i in artist_distribution)}")
    
    # Show distribution details
    print("\nDistribution of artists in source playlist by playlist count:")
    for count in sorted(artist_distribution.keys())[:10]:
        print(f"  {count} playlist(s): {artist_distribution[count]} artists")
    
    # Find which playlists have the most single-playlist artists
    playlist_single_artist_counts = defaultdict(int)
    for artist_id in single_playlist_artists:
        target_playlist = list(artist_to_playlists[artist_id])[0]
        playlist_single_artist_counts[target_playlist] += 1
    
    print(f"\nTop 10 playlists with most single-playlist artists:")
    for playlist_name, count in sorted(playlist_single_artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        track_count = len(playlists_dict[playlist_name]["tracks"])
        print(f"  {playlist_name}: {count} single artists ({track_count} total tracks)")
    
    # Test with a more specialized playlist
    print(f"\n" + "="*60)
    print("Testing with specialized playlists...")
    
    # Try a few smaller/more specialized playlists
    test_playlists = ["Tokyo Jazz Bar", "Blues", "Classical", "Jazz 🜻", "Tribal"]
    
    for test_name in test_playlists:
        if test_name in playlists_dict:
            print(f"\nTesting '{test_name}':")
            test_playlist = playlists_dict[test_name]
            matches = find_matches_for_playlist(test_playlist, test_name, single_playlist_artists, artist_to_playlists, playlists_dict, artist_names)
            
            if matches:
                total_matches = sum(len(track_list) for track_list in matches.values())
                print(f"  Found {total_matches} potential matches across {len(matches)} playlists")
                for target, track_list in list(matches.items())[:3]:  # Show first 3
                    print(f"    {target}: {len(track_list)} matches")
            else:
                print(f"  No matches found")


def find_matches_for_playlist(source_playlist: Dict, source_name: str, single_playlist_artists: Set[str], 
                             artist_to_playlists: Dict, playlists_dict: Dict, artist_names: Dict) -> Dict[str, List]:
    """Find matches for a specific playlist."""
    matches = defaultdict(list)
    
    for track in source_playlist["tracks"]:
        track_id = track["id"]
        track_name = track["name"]
        
        for artist in track["artists"]:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            if artist_id in single_playlist_artists:
                target_playlists = artist_to_playlists[artist_id]
                
                if len(target_playlists) == 1:
                    target_playlist_name = list(target_playlists)[0]
                    
                    # Don't match to source playlist itself
                    if target_playlist_name == source_name:
                        continue
                    
                    # Check if track is already in target playlist
                    target_tracks = playlists_dict[target_playlist_name]["tracks"]
                    existing_track_ids = {t["id"] for t in target_tracks}
                    
                    if track_id not in existing_track_ids:
                        matches[target_playlist_name].append({
                            "track_name": track_name,
                            "artist_name": artist_name,
                            "track_id": track_id
                        })
                    
                    # Once we find a match, no need to check other artists for this track
                    break
    
    return dict(matches)


def main():
    """Run detailed analysis."""
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "playlists"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return
    
    # Load all playlist data
    playlists_dict = load_local_playlist_data(str(data_dir))
    print(f"Loaded {len(playlists_dict)} playlists")
    
    # Run detailed analysis
    analyze_detailed_matching(playlists_dict, "New")


if __name__ == "__main__":
    main()