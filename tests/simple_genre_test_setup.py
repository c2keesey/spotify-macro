"""
Simple genre classification test setup for SSH environments.
Creates basic test playlists step by step.
"""

from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


def create_simple_test_playlists():
    """Create basic test playlists for genre classification testing."""
    
    print("🧪 Setting up simple genre classification test...")
    print("If this requires OAuth, you'll need to:")
    print("1. Copy the authorization URL from the output")  
    print("2. Open it in your local browser")
    print("3. Complete authorization")
    print("4. Copy the callback URL and paste it back")
    print()
    
    try:
        # Try to use existing cache first
        print("Attempting to connect with existing credentials...")
        sp = initialize_spotify_client(
            "playlist-read-private playlist-modify-private playlist-modify-public user-read-private", 
            "playlist_flow_cache"
        )
        
        # Test connection
        user = spotify_api_call_with_retry(sp.current_user)
        print(f"✅ Connected to: {user['display_name']} ({user['id']})")
        
        # Get current playlists to see test env
        playlists = spotify_api_call_with_retry(sp.current_user_playlists, limit=5)
        print(f"📁 Found {playlists['total']} total playlists")
        
        # Look for existing test playlists
        test_playlists = [p for p in playlists['items'] if p['name'].startswith('🧪TEST_')]
        print(f"🧪 Found {len(test_playlists)} existing test playlists")
        
        if test_playlists:
            print("Existing test playlists:")
            for p in test_playlists:
                print(f"   - {p['name']}")
        
        # Create a simple test playlist to verify write access
        user_id = user['id']
        test_name = "🧪TEST_[Rock] Simple Test"
        
        print(f"\n📝 Creating test playlist: {test_name}")
        playlist = spotify_api_call_with_retry(
            sp.user_playlist_create,
            user_id,
            test_name,
            public=False,
            description="Simple genre classification test - safe to delete"
        )
        
        playlist_id = playlist['id']
        print(f"✅ Created playlist: {playlist_id}")
        
        # Search for a simple rock song to add
        print("🔍 Searching for test track...")
        search_results = spotify_api_call_with_retry(
            sp.search, "rock", type="track", limit=1
        )
        
        if search_results['tracks']['items']:
            track = search_results['tracks']['items'][0]
            track_id = track['id']
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            
            print(f"🎵 Found track: {track_name} by {artist_name}")
            
            # Add track to playlist
            spotify_api_call_with_retry(
                sp.playlist_add_items, playlist_id, [track_id]
            )
            print(f"✅ Added track to playlist")
        
        print(f"\n🎉 Simple test setup complete!")
        print(f"Playlist created: {test_name}")
        print(f"Playlist ID: {playlist_id}")
        
        return {
            "playlist_id": playlist_id,
            "playlist_name": test_name,
            "user_id": user_id
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nIf you see an OAuth URL above, copy it and open in your browser")
        print("Then paste the callback URL here when prompted")
        return None


if __name__ == "__main__":
    result = create_simple_test_playlists()
    if result:
        print(f"\n✅ Success! Test playlist ready for development.")
    else:
        print(f"\n❌ Setup failed. Check OAuth flow above.")