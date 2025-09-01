#!/usr/bin/env python3
"""
Test that folder playlists are properly set up and that classification finds them.

This script verifies that:
1. All folder playlists exist with the correct names
2. The classification system can find and use them
3. Shows some sample tracks from the "New" playlist for testing
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import CURRENT_ENV
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.constants import FOLDER_PLAYLIST_PREFIX, GENRE_FOLDERS
from common.playlist_data_utils import PlaylistDataLoader


def test_folder_playlist_setup():
    """Test that all folder playlists are properly set up."""
    print(f"🧪 Testing folder playlist setup (Environment: {CURRENT_ENV})")
    print(f"📁 Expected prefix: '{FOLDER_PLAYLIST_PREFIX}'")
    print(f"📂 Expected folders: {', '.join(GENRE_FOLDERS)}")
    print()
    
    # Initialize Spotify client (read-only)
    scope = "playlist-read-private"
    sp = initialize_spotify_client(scope)
    
    # Get all user playlists
    print("📚 Fetching user playlists...")
    user_playlists = spotify_api_call_with_retry(sp.current_user_playlists, limit=50)
    
    existing_playlists = {}
    while user_playlists:
        for playlist in user_playlists['items']:
            existing_playlists[playlist['name']] = {
                'id': playlist['id'],
                'tracks_total': playlist['tracks']['total']
            }
        
        if user_playlists['next']:
            user_playlists = spotify_api_call_with_retry(sp.next, user_playlists)
        else:
            break
    
    print(f"Found {len(existing_playlists)} total playlists")
    print()
    
    # Check folder playlists
    print("🔍 Checking folder playlists:")
    folder_playlists_found = {}
    
    for folder in GENRE_FOLDERS:
        expected_name = f"{FOLDER_PLAYLIST_PREFIX} {folder}"
        
        if expected_name in existing_playlists:
            playlist_data = existing_playlists[expected_name]
            folder_playlists_found[folder] = playlist_data
            print(f"  ✅ {expected_name} (ID: {playlist_data['id']}, {playlist_data['tracks_total']} tracks)")
        else:
            print(f"  ❌ {expected_name} - NOT FOUND")
    
    print(f"\nFound {len(folder_playlists_found)}/{len(GENRE_FOLDERS)} folder playlists")
    
    # Check if "New" playlist exists
    print("\n🎵 Checking 'New' playlist:")
    if "New" in existing_playlists:
        new_playlist = existing_playlists["New"]
        print(f"  ✅ New playlist found (ID: {new_playlist['id']}, {new_playlist['tracks_total']} tracks)")
        
        if new_playlist['tracks_total'] > 0:
            print(f"  📀 Ready for classification with {new_playlist['tracks_total']} tracks")
        else:
            print(f"  ℹ️ New playlist is empty - no tracks to classify")
    else:
        print("  ❌ New playlist not found")
    
    # Load some sample tracks from local data
    print("\n📁 Loading sample tracks from local data:")
    try:
        playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
        
        new_playlist_id = None
        for playlist_id, playlist_data in playlists_dict.items():
            if playlist_data["name"].lower() == "new":
                new_playlist_id = playlist_id
                break
        
        if new_playlist_id:
            tracks = playlists_dict[new_playlist_id]["tracks"]
            print(f"  📚 Local data shows {len(tracks)} tracks in 'New' playlist")
            
            if tracks:
                print("  🎵 Sample tracks (first 5):")
                for i, track in enumerate(tracks[:5]):
                    artist_names = [artist["name"] for artist in track["artists"]]
                    print(f"    {i+1}. {track['name']} by {', '.join(artist_names)}")
            else:
                print("  ℹ️ No tracks in local data")
        else:
            print("  ❌ 'New' playlist not found in local data")
            
    except Exception as e:
        print(f"  ❌ Error loading local data: {e}")
    
    # Summary
    print(f"\n📊 Setup Status:")
    print(f"  • Folder playlists: {len(folder_playlists_found)}/{len(GENRE_FOLDERS)} found")
    print(f"  • New playlist: {'✅ Found' if 'New' in existing_playlists else '❌ Missing'}")
    
    if len(folder_playlists_found) == len(GENRE_FOLDERS) and "New" in existing_playlists:
        print(f"  🎉 System is ready for classification!")
    else:
        print(f"  ⚠️ Setup incomplete - missing components")


if __name__ == "__main__":
    test_folder_playlist_setup()