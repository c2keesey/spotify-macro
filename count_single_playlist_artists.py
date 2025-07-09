#!/usr/bin/env python3
"""
Count single-playlist artists excluding the "New" playlist.

This script:
1. Loads cached artist data using get_cached_artist_data()
2. Loads playlists dictionary using PlaylistDataLoader
3. Finds all single-playlist artists (those appearing in exactly one playlist)
4. Filters out any artists that appear only in the "New" playlist (case-insensitive)
5. Counts how many single-playlist artists remain after excluding "New"
6. Provides the total number of single-playlist artists for comparison
"""

from common.shared_cache import get_cached_artist_data
from common.playlist_data_utils import PlaylistDataLoader
from typing import Dict, Set


def count_single_playlist_artists_excluding_new():
    """Count single-playlist artists excluding those only in the "New" playlist."""
    
    print("=" * 60)
    print("Single-Playlist Artists Analysis (Excluding 'New' Playlist)")
    print("=" * 60)
    
    # Step 1: Load cached artist data
    print("\n1. Loading cached artist data...")
    artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
    
    # Step 2: Load playlists dictionary
    print("\n2. Loading playlists dictionary...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(verbose=True)
    
    # Step 3: Find the "New" playlist (case-insensitive)
    print("\n3. Searching for 'New' playlist...")
    new_playlist_id = PlaylistDataLoader.find_playlist_by_name(
        playlists_dict, 
        "New", 
        case_sensitive=False
    )
    
    if new_playlist_id:
        new_playlist_name = playlists_dict[new_playlist_id]["name"]
        new_playlist_tracks = len(playlists_dict[new_playlist_id]["tracks"])
        print(f"   Found playlist: '{new_playlist_name}' (ID: {new_playlist_id})")
        print(f"   Contains {new_playlist_tracks} tracks")
    else:
        print("   No 'New' playlist found")
    
    # Step 4: Count total single-playlist artists
    total_single_playlist_artists = len(single_playlist_artists)
    print(f"\n4. Total single-playlist artists: {total_single_playlist_artists}")
    
    # Step 5: Filter out artists that only appear in the "New" playlist
    if new_playlist_id:
        print("\n5. Filtering out artists that only appear in 'New' playlist...")
        
        # Find artists that only appear in the "New" playlist
        new_only_artists = set()
        for artist_id in single_playlist_artists:
            if artist_id in artist_to_playlists:
                artist_playlists = artist_to_playlists[artist_id]
                if len(artist_playlists) == 1 and new_playlist_id in artist_playlists:
                    new_only_artists.add(artist_id)
        
        print(f"   Artists only in 'New' playlist: {len(new_only_artists)}")
        
        # Count artists excluding those only in "New"
        single_playlist_artists_excluding_new = single_playlist_artists - new_only_artists
        remaining_count = len(single_playlist_artists_excluding_new)
        
        print(f"   Single-playlist artists excluding 'New': {remaining_count}")
        
        # Calculate percentages
        if total_single_playlist_artists > 0:
            new_percentage = (len(new_only_artists) / total_single_playlist_artists) * 100
            remaining_percentage = (remaining_count / total_single_playlist_artists) * 100
            
            print(f"   Percentage in 'New' only: {new_percentage:.1f}%")
            print(f"   Percentage in other playlists: {remaining_percentage:.1f}%")
    
    else:
        print("\n5. No 'New' playlist found, so no filtering needed")
        remaining_count = total_single_playlist_artists
        single_playlist_artists_excluding_new = single_playlist_artists
    
    # Step 6: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total artists in library: {len(artist_to_playlists)}")
    print(f"Total single-playlist artists: {total_single_playlist_artists}")
    
    if new_playlist_id:
        print(f"Artists only in 'New' playlist: {len(new_only_artists)}")
        print(f"Single-playlist artists excluding 'New': {remaining_count}")
        
        # Show some example artists from different categories
        print("\nExample breakdown:")
        
        # Show some artists only in "New"
        if new_only_artists:
            print(f"\nArtists only in 'New' playlist (showing first 5):")
            sample_new_artists = list(new_only_artists)[:5]
            for artist_id in sample_new_artists:
                # Find artist name from tracks
                artist_name = find_artist_name_by_id(artist_id, playlists_dict)
                print(f"  - {artist_name} ({artist_id})")
        
        # Show some artists in other single playlists
        if remaining_count > 0:
            other_single_artists = list(single_playlist_artists_excluding_new)[:5]
            print(f"\nArtists in other single playlists (showing first 5):")
            for artist_id in other_single_artists:
                artist_name = find_artist_name_by_id(artist_id, playlists_dict)
                playlist_ids = artist_to_playlists[artist_id]
                playlist_id = list(playlist_ids)[0]  # Get the single playlist
                playlist_name = playlists_dict[playlist_id]["name"]
                print(f"  - {artist_name} in '{playlist_name}' ({artist_id})")
    
    else:
        print(f"Single-playlist artists (no 'New' playlist found): {remaining_count}")
    
    print("\n" + "=" * 60)
    
    return {
        "total_single_playlist_artists": total_single_playlist_artists,
        "single_playlist_artists_excluding_new": remaining_count,
        "new_only_artists": len(new_only_artists) if new_playlist_id else 0,
        "new_playlist_found": new_playlist_id is not None,
        "new_playlist_id": new_playlist_id,
        "total_artists": len(artist_to_playlists)
    }


def find_artist_name_by_id(artist_id: str, playlists_dict: Dict[str, Dict]) -> str:
    """Find artist name by searching through playlist tracks."""
    for playlist_data in playlists_dict.values():
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                if artist.get("id") == artist_id:
                    return artist.get("name", "Unknown Artist")
    return "Unknown Artist"


if __name__ == "__main__":
    result = count_single_playlist_artists_excluding_new()