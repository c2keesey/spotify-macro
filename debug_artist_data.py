#!/usr/bin/env python3
"""
Debug script to check artist data in mock client.
"""

from common.genre_classification_utils import get_safe_spotify_client

def debug_artist_data():
    """Debug artist data loading."""
    client = get_safe_spotify_client()
    if not client:
        print("❌ No client available")
        return
    
    # Check if artist_genres is loaded
    print(f"🎤 Artist genres loaded: {hasattr(client, 'artist_genres')}")
    if hasattr(client, 'artist_genres'):
        print(f"   Total artists: {len(client.artist_genres)}")
        # Show first few
        sample_artists = list(client.artist_genres.items())[:5]
        for artist_id, genres in sample_artists:
            print(f"   {artist_id}: {genres}")
    
    # Test getting a track and its artists
    electronic_playlists = client.get_folder_playlists('Electronic')
    tracks = client.playlist_tracks(electronic_playlists[0]['id'], limit=1)
    track = tracks['items'][0]
    
    print(f"\n🎵 Track: {track['name']}")
    print(f"   Artists in track: {track.get('artists', [])}")
    
    for artist in track.get('artists', []):
        artist_id = artist.get('id')
        artist_name = artist.get('name')
        print(f"\n👤 Artist: {artist_name} (ID: {artist_id})")
        
        # Test direct artist lookup
        if artist_id:
            artist_details = client.artist(artist_id)
            if artist_details:
                print(f"   ✅ Artist lookup successful")
                print(f"   Name: {artist_details.get('name')}")
                print(f"   Genres: {artist_details.get('genres')}")
            else:
                print(f"   ❌ Artist lookup failed")
                # Check if artist is in our data
                if hasattr(client, 'artist_genres') and artist_id in client.artist_genres:
                    print(f"   📊 Artist genres in data: {client.artist_genres[artist_id]}")
                else:
                    print(f"   📊 Artist not in genre data")

if __name__ == "__main__":
    debug_artist_data()