#!/usr/bin/env python3
"""
Clear all folder playlists (📁 prefixed) in the test environment.

This script finds all playlists with the 📁 prefix and removes all tracks from them,
effectively clearing them for a fresh classification run.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import get_config_value
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


def clear_folder_playlists():
    """Clear all folder playlists in the test environment."""
    print("🧹 Clearing all folder playlists in test environment...")
    
    # Initialize Spotify client
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope, "playlist_flow_cache")
    
    # Get all user playlists
    print("📚 Fetching user playlists...")
    user_playlists = sp.current_user_playlists(limit=50)
    all_playlists = []
    
    # Get all playlists with pagination
    while user_playlists:
        all_playlists.extend(user_playlists['items'])
        if user_playlists['next']:
            user_playlists = sp.next(user_playlists)
        else:
            break
    
    print(f"Found {len(all_playlists)} total playlists")
    
    # Find folder playlists (those with 📁 prefix)
    folder_playlists = []
    for playlist in all_playlists:
        if playlist['name'].startswith('📁 '):
            folder_playlists.append(playlist)
    
    print(f"Found {len(folder_playlists)} folder playlists to clear:")
    for playlist in folder_playlists:
        print(f"  📁 {playlist['name']} ({playlist['tracks']['total']} tracks)")
    
    if not folder_playlists:
        print("✅ No folder playlists found to clear")
        return
    
    # Proceed with clearing
    print(f"\n🚀 Proceeding to clear {len(folder_playlists)} folder playlists...")
    
    # Clear each folder playlist
    total_tracks_removed = 0
    
    for playlist in folder_playlists:
        playlist_id = playlist['id']
        playlist_name = playlist['name']
        track_count = playlist['tracks']['total']
        
        if track_count == 0:
            print(f"  ⭕ '{playlist_name}' is already empty")
            continue
        
        print(f"  🧹 Clearing '{playlist_name}' ({track_count} tracks)...")
        
        try:
            # Get all track URIs from the playlist
            tracks = spotify_api_call_with_retry(sp.playlist_tracks, playlist_id, limit=100)
            track_uris = []
            
            while tracks:
                for item in tracks['items']:
                    if item['track'] and item['track']['uri']:
                        track_uris.append(item['track']['uri'])
                
                if tracks['next']:
                    tracks = spotify_api_call_with_retry(sp.next, tracks)
                else:
                    break
            
            if track_uris:
                # Remove tracks in chunks of 100 (Spotify API limit)
                chunk_size = 100
                for i in range(0, len(track_uris), chunk_size):
                    chunk = track_uris[i:i + chunk_size]
                    spotify_api_call_with_retry(sp.playlist_remove_all_occurrences_of_items, playlist_id, chunk)
                
                total_tracks_removed += len(track_uris)
                print(f"    ✅ Removed {len(track_uris)} tracks from '{playlist_name}'")
            else:
                print(f"    ⭕ No valid tracks found in '{playlist_name}'")
                
        except Exception as e:
            print(f"    ❌ Error clearing '{playlist_name}': {e}")
    
    print(f"\n🎉 Clearing complete!")
    print(f"   Cleared {len(folder_playlists)} folder playlists")
    print(f"   Removed {total_tracks_removed} total tracks")
    print("   Folder playlists are now ready for fresh classification")


if __name__ == "__main__":
    clear_folder_playlists()