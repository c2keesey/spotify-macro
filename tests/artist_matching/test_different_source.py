#!/usr/bin/env python3
"""
Test artist matching with different source playlists to find matches.
"""

import json
from collections import defaultdict
from typing import Dict, List, Set
from pathlib import Path


def load_local_playlist_data(data_dir: str) -> Dict[str, Dict]:
    """Load all playlist data from local JSON files."""
    playlists_dict = {}
    data_path = Path(data_dir)
    
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
                
                if "track" in track_item and isinstance(track_item["track"], dict):
                    track = track_item["track"]
                
                if not track or track.get("is_local", False):
                    continue
                    
                track_id = track.get("id")
                if not track_id:
                    continue
                
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
                "tracks": tracks
            }
            
        except Exception as e:
            continue
    
    return playlists_dict


def find_matches_for_playlist(source_playlist: Dict, source_name: str, single_playlist_artists: Set[str], 
                             artist_to_playlists: Dict, playlists_dict: Dict) -> Dict[str, List]:
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
                        print(f"  Match: '{track_name}' -> '{target_playlist_name}' (artist: {artist_name})")
                    
                    # Once we find a match, break
                    break
    
    return dict(matches)


def main():
    """Test with different source playlists."""
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "playlists"
    
    # Load all playlist data
    playlists_dict = load_local_playlist_data(str(data_dir))
    print(f"Loaded {len(playlists_dict)} playlists")
    
    # Build artist mappings
    artist_to_playlists = defaultdict(set)
    
    for playlist_name, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_playlists[artist_id].add(playlist_name)
    
    # Find single playlist artists
    single_playlist_artists = set()
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    print(f"Found {len(single_playlist_artists)} single-playlist artists")
    
    # Test with different source playlists
    test_sources = [
        "All da EDM",       # Large EDM collection 
        "RHCP",             # Red Hot Chili Peppers specific
        "Throwback EDM",    # Older EDM tracks
        "🜄 Classic EDM",   # Classic EDM
        "Indie",            # Indie music
        "Hitting rn"        # Currently popular
    ]
    
    for source_name in test_sources:
        if source_name in playlists_dict:
            print(f"\n" + "="*50)
            print(f"Testing with source: '{source_name}'")
            print("="*50)
            
            source_playlist = playlists_dict[source_name]
            print(f"Source has {len(source_playlist['tracks'])} tracks")
            
            matches = find_matches_for_playlist(source_playlist, source_name, 
                                              single_playlist_artists, 
                                              artist_to_playlists, playlists_dict)
            
            if matches:
                total_matches = sum(len(track_list) for track_list in matches.values())
                print(f"\nFound {total_matches} potential matches across {len(matches)} target playlists:")
                
                for target_playlist, track_list in sorted(matches.items(), key=lambda x: len(x[1]), reverse=True):
                    print(f"  {target_playlist}: {len(track_list)} matches")
                    for track_info in track_list[:2]:  # Show first 2 matches
                        print(f"    • {track_info['track_name']} (by {track_info['artist_name']})")
                    if len(track_list) > 2:
                        print(f"    ... and {len(track_list) - 2} more")
            else:
                print("No matches found")


if __name__ == "__main__":
    main()