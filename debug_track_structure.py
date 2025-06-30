#!/usr/bin/env python3
"""
Debug script to examine track data structure from mock client.
"""

from common.genre_classification_utils import get_safe_spotify_client

def debug_track_structure():
    """Debug the track data structure."""
    client = get_safe_spotify_client()
    if not client:
        print("❌ No client available")
        return
    
    # Get a folder with playlists
    electronic_playlists = client.get_folder_playlists('Electronic')
    if not electronic_playlists:
        print("❌ No Electronic playlists found")
        return
    
    playlist = electronic_playlists[0]
    print(f"📀 Testing playlist: {playlist['name']}")
    print(f"🆔 Playlist ID: {playlist['id']}")
    
    # Get tracks
    tracks = client.playlist_tracks(playlist['id'], limit=3)
    print(f"📊 Got {len(tracks['items'])} tracks")
    
    for i, track in enumerate(tracks['items']):
        print(f"\n🎵 Track {i+1}:")
        print(f"   Keys: {list(track.keys())}")
        print(f"   ID: {track.get('id', 'MISSING')}")
        print(f"   Name: {track.get('name', 'MISSING')}")
        print(f"   Type: {track.get('type', 'MISSING')}")
        
        if 'artists' in track:
            print(f"   Artists: {[a.get('name', 'MISSING') for a in track['artists']]}")
        
        # Test track lookup
        track_id = track.get('id')
        if track_id:
            print(f"   Testing track lookup for ID: {track_id}")
            track_details = client.track(track_id)
            if track_details:
                print(f"   ✅ Track lookup successful: {track_details.get('name')}")
            else:
                print(f"   ❌ Track lookup failed")
        else:
            print(f"   ❌ No track ID found")

if __name__ == "__main__":
    debug_track_structure()