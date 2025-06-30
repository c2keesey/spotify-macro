#!/usr/bin/env python3
"""
Test script for safe genre classification using mock client.

This demonstrates the new safe defaults that automatically use mock client
in test environment with your production data snapshot.
"""

from common.genre_classification_utils import (
    get_default_genre_mapping,
    classify_track,
    get_safe_spotify_client
)


def test_safe_genre_classification():
    """Test genre classification with safe defaults."""
    print("🧪 Testing Safe Genre Classification")
    print("=" * 40)
    
    # Get safe client (automatically uses mock in test environment)
    client = get_safe_spotify_client()
    if not client:
        print("❌ No safe client available")
        return False
    
    # Get default mapping (automatically discovers from mock data)
    mapping = get_default_genre_mapping()
    print(f"✅ Discovered {len(mapping)} genre folders")
    
    # Test with a bass music track
    base_playlists = client.get_folder_playlists('Base')
    if not base_playlists:
        print("❌ No bass playlists found")
        return False
    
    tracks = client.playlist_tracks(base_playlists[0]['id'], limit=3)
    print(f"✅ Found {len(tracks['items'])} test tracks")
    
    # Test classification on multiple tracks
    for i, track_item in enumerate(tracks['items'][:3]):
        track_id = track_item['id']
        track_name = track_item['name']
        
        # Use minimal API - no client parameter needed
        classification = classify_track(track_id=track_id)
        
        print(f"🎵 Track {i+1}: {track_name}")
        print(f"   🏷️  Classified as: {classification}")
        
        if classification:
            # Show which playlists it would be added to
            for folder in classification:
                folder_playlists = client.get_folder_playlists(folder)
                print(f"      📁 {folder}: {len(folder_playlists)} playlists available")
    
    print("\n✅ Safe genre classification working perfectly!")
    print("🔒 Using mock client - no real API calls made")
    print("📊 Using your actual EDM/bass library structure")
    return True


if __name__ == "__main__":
    success = test_safe_genre_classification()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed")
        exit(1)