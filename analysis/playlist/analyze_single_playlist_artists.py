#!/usr/bin/env python3
"""
Analyze local playlist data to identify single playlist artists.
Artists that appear in only one playlist across all playlists.
"""

import json
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import sys
import os

def load_playlist_data(filepath: str) -> Dict:
    """Load playlist to artists mapping data."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filepath}")
        sys.exit(1)

def build_artist_to_playlists_mapping(playlist_data: Dict) -> Dict[str, Set[str]]:
    """Build mapping of artist -> set of playlists they appear in."""
    artist_to_playlists = defaultdict(set)
    
    for playlist_id, playlist_info in playlist_data.items():
        playlist_name = playlist_info.get('playlist_name', f'Unknown_{playlist_id}')
        top_artists = playlist_info.get('top_artists', {})
        
        for artist_name in top_artists.keys():
            artist_to_playlists[artist_name].add(playlist_name)
    
    return artist_to_playlists

def find_single_playlist_artists(artist_to_playlists: Dict[str, Set[str]]) -> List[Tuple[str, str, int]]:
    """Find artists that appear in only one playlist."""
    single_playlist_artists = []
    
    for artist, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            playlist_name = list(playlists)[0]
            single_playlist_artists.append((artist, playlist_name, 1))
    
    return single_playlist_artists

def analyze_artist_distribution(artist_to_playlists: Dict[str, Set[str]]) -> Dict[int, int]:
    """Analyze how many playlists each artist appears in."""
    distribution = defaultdict(int)
    
    for artist, playlists in artist_to_playlists.items():
        playlist_count = len(playlists)
        distribution[playlist_count] += 1
    
    return distribution

def main():
    data_file = "_data/playlist_to_artists.json"
    
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found. Please run download_playlists.py first.")
        sys.exit(1)
    
    print("Loading playlist data...")
    playlist_data = load_playlist_data(data_file)
    
    print(f"Loaded {len(playlist_data)} playlists")
    
    # Build artist to playlists mapping
    artist_to_playlists = build_artist_to_playlists_mapping(playlist_data)
    
    print(f"Found {len(artist_to_playlists)} unique artists")
    
    # Find single playlist artists
    single_playlist_artists = find_single_playlist_artists(artist_to_playlists)
    
    # Analyze distribution
    distribution = analyze_artist_distribution(artist_to_playlists)
    
    print("\n" + "="*60)
    print("ARTIST DISTRIBUTION ANALYSIS")
    print("="*60)
    
    print(f"\nTotal unique artists: {len(artist_to_playlists)}")
    print(f"Single playlist artists: {len(single_playlist_artists)}")
    print(f"Percentage of single playlist artists: {len(single_playlist_artists)/len(artist_to_playlists)*100:.1f}%")
    
    print("\nDistribution by number of playlists:")
    for playlist_count in sorted(distribution.keys()):
        artist_count = distribution[playlist_count]
        percentage = (artist_count / len(artist_to_playlists)) * 100
        print(f"  {playlist_count} playlist(s): {artist_count} artists ({percentage:.1f}%)")
    
    print("\n" + "="*60)
    print("SINGLE PLAYLIST ARTISTS")
    print("="*60)
    
    if single_playlist_artists:
        # Group by playlist
        playlist_to_single_artists = defaultdict(list)
        for artist, playlist, _ in single_playlist_artists:
            playlist_to_single_artists[playlist].append(artist)
        
        print(f"\nFound {len(single_playlist_artists)} single playlist artists across {len(playlist_to_single_artists)} playlists:\n")
        
        # Sort playlists by number of single artists (descending)
        sorted_playlists = sorted(playlist_to_single_artists.items(), 
                                key=lambda x: len(x[1]), reverse=True)
        
        for playlist_name, artists in sorted_playlists:
            print(f"📀 {playlist_name} ({len(artists)} single artists)")
            for artist in sorted(artists):
                print(f"    • {artist}")
            print()
    else:
        print("No single playlist artists found - all artists appear in multiple playlists!")

if __name__ == "__main__":
    main()