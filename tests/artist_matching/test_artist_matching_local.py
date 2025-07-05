#!/usr/bin/env python3
"""
Test the artist matching automation using local playlist data.
This allows testing without making API calls to Spotify.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path


def load_local_playlist_data(data_dir: str) -> Dict[str, Dict]:
    """
    Load all playlist data from local JSON files.
    
    Args:
        data_dir: Path to the data/playlists directory
        
    Returns:
        Dictionary mapping playlist_name to playlist data including tracks
    """
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
            
            print(f"Loaded '{playlist_name}' ({len(tracks)} tracks)")
            
        except Exception as e:
            print(f"Failed to load {json_file.name}: {e}")
            continue
    
    return playlists_dict


def build_artist_to_playlists_mapping(playlists_dict: Dict[str, Dict]) -> Dict[str, Set[str]]:
    """
    Build mapping of artist ID to set of playlist names they appear in.
    
    Args:
        playlists_dict: Dictionary of playlist data
        
    Returns:
        Dictionary mapping artist_id to set of playlist_names
    """
    artist_to_playlists = defaultdict(set)
    
    for playlist_name, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_playlists[artist_id].add(playlist_name)
    
    return artist_to_playlists


def find_single_playlist_artists(artist_to_playlists: Dict[str, Set[str]]) -> Set[str]:
    """
    Find artists that appear in only one playlist.
    
    Args:
        artist_to_playlists: Mapping of artist_id to set of playlist_names
        
    Returns:
        Set of artist IDs that appear in exactly one playlist
    """
    single_playlist_artists = set()
    
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    return single_playlist_artists


def find_source_playlist(playlists_dict: Dict[str, Dict], source_name: str = "New") -> Optional[str]:
    """
    Find the source playlist by name (case-insensitive).
    
    Args:
        playlists_dict: Dictionary of playlist data
        source_name: Name of the source playlist to find
        
    Returns:
        Playlist name if found, None otherwise
    """
    for playlist_name in playlists_dict.keys():
        if playlist_name.lower() == source_name.lower():
            return playlist_name
    
    return None


def analyze_artist_matching_potential(playlists_dict: Dict[str, Dict], 
                                    source_playlist_name: str,
                                    single_playlist_artists: Set[str],
                                    artist_to_playlists: Dict[str, Set[str]]) -> Dict[str, List[Dict]]:
    """
    Analyze which songs from source playlist could be matched to target playlists.
    
    Args:
        playlists_dict: Dictionary of playlist data
        source_playlist_name: Name of the source playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        artist_to_playlists: Mapping of artist_id to set of playlist_names
        
    Returns:
        Dictionary mapping target_playlist_name to list of matchable tracks
    """
    matches = defaultdict(list)
    source_tracks = playlists_dict[source_playlist_name]["tracks"]
    
    print(f"\nAnalyzing {len(source_tracks)} tracks from '{source_playlist_name}'...")
    
    for track in source_tracks:
        track_id = track["id"]
        track_name = track["name"]
        
        # Check if any artist in this track is a single-playlist artist
        for artist in track["artists"]:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            if artist_id in single_playlist_artists:
                # This artist appears in only one playlist - find which one
                target_playlists = artist_to_playlists[artist_id]
                
                # Should be exactly one playlist
                if len(target_playlists) == 1:
                    target_playlist_name = list(target_playlists)[0]
                    
                    # Don't match to source playlist itself
                    if target_playlist_name == source_playlist_name:
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
                    else:
                        print(f"  Skip: '{track_name}' already in '{target_playlist_name}' (artist: {artist_name})")
                    
                    # Once we find a match, no need to check other artists for this track
                    break
    
    return dict(matches)


def main():
    """Test the artist matching logic with local data."""
    
    # Path to local playlist data
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "playlists"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return
    
    # Load all playlist data
    playlists_dict = load_local_playlist_data(str(data_dir))
    
    print(f"\nLoaded {len(playlists_dict)} playlists")
    
    # Find source playlist
    source_playlist_name = find_source_playlist(playlists_dict, "New")
    
    if not source_playlist_name:
        print("Error: Could not find 'New' playlist in local data")
        print("Available playlists:")
        for name in sorted(playlists_dict.keys())[:10]:
            print(f"  - {name}")
        print("  ...")
        return
    
    source_track_count = len(playlists_dict[source_playlist_name]["tracks"])
    print(f"Found source playlist: '{source_playlist_name}' ({source_track_count} tracks)")
    
    # Build artist to playlists mapping
    print("\nBuilding artist to playlists mapping...")
    artist_to_playlists = build_artist_to_playlists_mapping(playlists_dict)
    
    print(f"Found {len(artist_to_playlists)} unique artists")
    
    # Find single playlist artists
    single_playlist_artists = find_single_playlist_artists(artist_to_playlists)
    
    print(f"Found {len(single_playlist_artists)} single-playlist artists")
    
    # Calculate percentages
    single_percentage = (len(single_playlist_artists) / len(artist_to_playlists)) * 100
    print(f"Percentage of single-playlist artists: {single_percentage:.1f}%")
    
    # Show distribution
    distribution = defaultdict(int)
    for artist_id, playlists in artist_to_playlists.items():
        playlist_count = len(playlists)
        distribution[playlist_count] += 1
    
    print("\nArtist distribution by number of playlists:")
    for playlist_count in sorted(distribution.keys())[:10]:
        artist_count = distribution[playlist_count]
        percentage = (artist_count / len(artist_to_playlists)) * 100
        print(f"  {playlist_count} playlist(s): {artist_count} artists ({percentage:.1f}%)")
    
    # Analyze potential matches
    matches = analyze_artist_matching_potential(playlists_dict, source_playlist_name, 
                                              single_playlist_artists, artist_to_playlists)
    
    # Report results
    print(f"\n" + "="*60)
    print("ARTIST MATCHING ANALYSIS RESULTS")
    print("="*60)
    
    if not matches:
        print(f"No songs from '{source_playlist_name}' matched single-playlist artists.")
    else:
        total_matches = sum(len(track_list) for track_list in matches.values())
        print(f"\nFound {total_matches} potential matches across {len(matches)} target playlists:")
        
        for target_playlist, track_list in sorted(matches.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n📀 {target_playlist} ({len(track_list)} matches):")
            for track_info in track_list[:5]:  # Show first 5 matches
                print(f"    • {track_info['track_name']} (by {track_info['artist_name']})")
            if len(track_list) > 5:
                print(f"    ... and {len(track_list) - 5} more")
    
    print(f"\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Source playlist: '{source_playlist_name}' ({source_track_count} tracks)")
    print(f"Total playlists analyzed: {len(playlists_dict)}")
    print(f"Total unique artists: {len(artist_to_playlists)}")
    print(f"Single-playlist artists: {len(single_playlist_artists)} ({single_percentage:.1f}%)")
    if matches:
        total_matches = sum(len(track_list) for track_list in matches.values())
        print(f"Potential matches found: {total_matches} songs to {len(matches)} playlists")
    else:
        print("No potential matches found")


if __name__ == "__main__":
    main()