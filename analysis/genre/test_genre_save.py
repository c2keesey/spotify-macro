#!/usr/bin/env python3
"""
Test script for the genre-aware save functionality.
Tests the complete workflow from track classification to playlist addition.
"""

from common.spotify_utils import initialize_spotify_client
from common.genre_classification_utils import classify_track, add_track_to_genre_playlists

def test_complete_workflow():
    """Test the complete genre classification and save workflow."""
    
    # Initialize client with required scopes
    scope = "playlist-read-private playlist-modify-public playlist-modify-private"
    sp = initialize_spotify_client(scope, 'save_current_cache')
    
    # Find our unsorted test playlist
    playlists = sp.current_user_playlists(limit=50)['items']
    unsorted_playlist = None
    for p in playlists:
        if '🧪TEST_Unsorted - Needs Classification' in p['name']:
            unsorted_playlist = p
            break
    
    if not unsorted_playlist:
        print("❌ Unsorted test playlist not found")
        return
    
    print(f"🎵 Found test playlist: {unsorted_playlist['name']}")
    
    # Get tracks from unsorted playlist
    tracks = sp.playlist_tracks(unsorted_playlist['id'], limit=10)['items']
    
    print(f"\n📊 Testing {len(tracks)} tracks from unsorted playlist:")
    print("=" * 60)
    
    for i, item in enumerate(tracks):
        if not item['track'] or not item['track']['id']:
            continue
            
        track = item['track']
        track_id = track['id']
        track_name = f"{track['name']} by {track['artists'][0]['name']}"
        
        print(f"\n{i+1}. 🎵 {track_name}")
        
        # Classify the track
        try:
            classifications = classify_track(sp, track_id)
            
            if classifications:
                print(f"   📂 Classifications: {', '.join(classifications)}")
                
                # Add to genre playlists
                results = add_track_to_genre_playlists(sp, track_id, classifications)
                
                # Show results
                successful = [genre for genre, success in results.items() if success]
                failed = [genre for genre, success in results.items() if not success]
                
                if successful:
                    print(f"   ✅ Successfully added to: {', '.join(successful)}")
                if failed:
                    print(f"   ❌ Failed to add to: {', '.join(failed)}")
                    
            else:
                print("   ❌ No genre classification found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Genre classification test completed!")
    

if __name__ == "__main__":
    test_complete_workflow()