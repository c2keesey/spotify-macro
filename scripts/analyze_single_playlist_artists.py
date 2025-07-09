#!/usr/bin/env python3
"""
Analyze single-playlist artists, excluding those that only appear in the "New" playlist.
"""

from common.shared_cache import get_cached_artist_data
from common.playlist_data_utils import PlaylistDataLoader


def analyze_single_playlist_artists():
    """
    Analyze single-playlist artists and filter out those only in "New" playlist.
    """
    print("Loading cached artist data...")
    
    # Load cached artist data
    artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
    
    print(f"\nLoading playlists dictionary...")
    
    # Load playlists dictionary
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    print(f"Total playlists loaded: {len(playlists_dict)}")
    print(f"Total single-playlist artists from cache: {len(single_playlist_artists)}")
    
    # Find artists that appear only in the "New" playlist (case-insensitive)
    artists_only_in_new = []
    artists_in_other_playlists = []
    
    for artist in single_playlist_artists:
        # Get the playlist(s) this artist appears in
        artist_playlists = artist_to_playlists.get(artist, set())
        
        # Check if artist appears only in "New" playlist (case-insensitive)
        if len(artist_playlists) == 1:
            playlist_id = list(artist_playlists)[0]
            playlist_name = playlists_dict.get(playlist_id, {}).get('name', playlist_id)
            if playlist_name.lower() == "new":
                artists_only_in_new.append(artist)
            else:
                artists_in_other_playlists.append(artist)
    
    # Display results
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Total single-playlist artists: {len(single_playlist_artists)}")
    print(f"Artists only in 'New' playlist: {len(artists_only_in_new)}")
    print(f"Single-playlist artists (excluding 'New'): {len(artists_in_other_playlists)}")
    
    print(f"\n=== BREAKDOWN ===")
    print(f"Percentage only in 'New': {len(artists_only_in_new) / len(single_playlist_artists) * 100:.1f}%")
    print(f"Percentage in other playlists: {len(artists_in_other_playlists) / len(single_playlist_artists) * 100:.1f}%")
    
    # Show some examples
    if artists_only_in_new:
        print(f"\n=== EXAMPLES: Artists only in 'New' playlist (first 10) ===")
        for artist in artists_only_in_new[:10]:
            print(f"  - {artist}")
    
    if artists_in_other_playlists:
        print(f"\n=== EXAMPLES: Single-playlist artists in other playlists (first 10) ===")
        for artist in artists_in_other_playlists[:10]:
            playlist_id = list(artist_to_playlists[artist])[0]
            playlist_name = playlists_dict.get(playlist_id, {}).get('name', playlist_id)
            print(f"  - {artist} (in '{playlist_name}')")
    
    # Check for any "New" variants
    new_variants = set()
    for artist in single_playlist_artists:
        artist_playlists = artist_to_playlists.get(artist, set())
        for playlist_id in artist_playlists:
            playlist_name = playlists_dict.get(playlist_id, {}).get('name', playlist_id)
            if "new" in playlist_name.lower():
                new_variants.add(playlist_name)
    
    if new_variants:
        print(f"\n=== 'New' playlist variants found ===")
        for variant in sorted(new_variants):
            print(f"  - '{variant}'")
    
    return {
        'total_single_playlist_artists': len(single_playlist_artists),
        'artists_only_in_new': len(artists_only_in_new),
        'artists_in_other_playlists': len(artists_in_other_playlists),
        'artists_only_in_new_list': artists_only_in_new,
        'artists_in_other_playlists_list': artists_in_other_playlists
    }


if __name__ == "__main__":
    results = analyze_single_playlist_artists()