"""
Test setup for genre-based playlist classification system.
Creates test playlists with folder naming convention and populates them with appropriate genre songs.
"""

import time
from typing import Dict, List, Tuple, Optional
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


class GenreClassificationTestSetup:
    """Setup utility for genre classification testing."""
    
    def __init__(self, test_prefix: str = "🧪TEST_"):
        """
        Initialize test setup utilities.
        
        Args:
            test_prefix: Prefix for all test playlists to identify them
        """
        self.test_prefix = test_prefix
        self.scope = "playlist-read-private playlist-modify-private playlist-modify-public user-read-private"
        self.sp = initialize_spotify_client(self.scope, "playlist_flow_cache")
        self.created_playlists = []  # Track created playlists for cleanup
        
        # Genre search terms for finding appropriate songs
        self.genre_search_terms = {
            "Rock": ["rock", "alternative rock", "indie rock", "classic rock", "punk rock"],
            "Electronic": ["electronic", "edm", "house", "techno", "ambient electronic"],
            "Jazz": ["jazz", "smooth jazz", "bebop", "jazz fusion", "contemporary jazz"],
            "Pop": ["pop", "dance pop", "electropop", "indie pop", "synthpop"],
            "Hip Hop": ["hip hop", "rap", "trap", "conscious hip hop", "old school hip hop"],
            "Country": ["country", "country rock", "bluegrass", "contemporary country", "folk country"]
        }
        
    def create_test_playlist(self, name: str, tracks: List[str] = None) -> str:
        """
        Create a test playlist with optional tracks.
        
        Args:
            name: Playlist name (test prefix will be added)
            tracks: List of track IDs to add
            
        Returns:
            Playlist ID
        """
        full_name = f"{self.test_prefix}{name}"
        user_id = spotify_api_call_with_retry(self.sp.current_user)["id"]
        
        playlist = spotify_api_call_with_retry(
            self.sp.user_playlist_create,
            user_id,
            full_name,
            public=False,
            description="Genre classification test playlist - safe to delete"
        )
        
        playlist_id = playlist["id"]
        self.created_playlists.append(playlist_id)
        
        if tracks:
            # Add tracks in chunks of 100
            for i in range(0, len(tracks), 100):
                chunk = tracks[i:i + 100]
                spotify_api_call_with_retry(
                    self.sp.playlist_add_items, playlist_id, chunk
                )
        
        print(f"Created test playlist: '{full_name}' ({playlist_id})")
        return playlist_id
    
    def get_genre_tracks(self, genre: str, count: int = 10) -> List[Tuple[str, str, str]]:
        """
        Get track IDs for a specific genre.
        
        Args:
            genre: Genre name
            count: Number of tracks to return
            
        Returns:
            List of tuples (track_id, track_name, artist_name)
        """
        if genre not in self.genre_search_terms:
            print(f"Unknown genre: {genre}")
            return []
        
        tracks = []
        search_terms = self.genre_search_terms[genre]
        
        for term in search_terms:
            if len(tracks) >= count:
                break
                
            try:
                results = spotify_api_call_with_retry(
                    self.sp.search, 
                    f"genre:{term}", 
                    type="track", 
                    limit=min(10, count - len(tracks))
                )
                
                for track in results["tracks"]["items"]:
                    if len(tracks) >= count:
                        break
                    
                    track_info = (
                        track["id"],
                        track["name"],
                        track["artists"][0]["name"] if track["artists"] else "Unknown"
                    )
                    
                    # Avoid duplicates
                    if track_info[0] not in [t[0] for t in tracks]:
                        tracks.append(track_info)
                        
            except Exception as e:
                print(f"Failed to search for genre '{term}': {e}")
                # Fallback to regular search
                try:
                    results = spotify_api_call_with_retry(
                        self.sp.search, 
                        term, 
                        type="track", 
                        limit=min(5, count - len(tracks))
                    )
                    
                    for track in results["tracks"]["items"]:
                        if len(tracks) >= count:
                            break
                        
                        track_info = (
                            track["id"],
                            track["name"],
                            track["artists"][0]["name"] if track["artists"] else "Unknown"
                        )
                        
                        if track_info[0] not in [t[0] for t in tracks]:
                            tracks.append(track_info)
                            
                except Exception as e2:
                    print(f"Fallback search also failed for '{term}': {e2}")
        
        print(f"Found {len(tracks)} tracks for genre '{genre}'")
        return tracks
    
    def create_folder_playlists(self) -> Dict[str, Dict[str, str]]:
        """
        Create test playlists using folder naming convention.
        Format: [Genre] PlaylistName
        
        Returns:
            Dict mapping genres to their playlist info
        """
        folder_playlists = {}
        
        for genre in self.genre_search_terms.keys():
            print(f"\n=== Setting up {genre} folder playlists ===")
            
            # Get sample tracks for this genre
            genre_tracks = self.get_genre_tracks(genre, 15)
            track_ids = [track[0] for track in genre_tracks]
            
            if not track_ids:
                print(f"⚠️  No tracks found for {genre}, skipping...")
                continue
            
            # Create folder playlists
            playlists = {}
            
            # Main collection playlist (parent for flow)
            collection_name = f"[{genre}] Collection 🎵"
            playlists["collection"] = self.create_test_playlist(collection_name)
            
            # Daily finds playlist (child flows to collection)  
            daily_tracks = track_ids[:5] if len(track_ids) >= 5 else track_ids
            daily_name = f"[{genre}] Daily Finds 🎵"
            playlists["daily"] = self.create_test_playlist(daily_name, daily_tracks)
            
            # Favorites playlist (standalone, no flow)
            fav_tracks = track_ids[5:10] if len(track_ids) >= 10 else track_ids[len(daily_tracks):]
            fav_name = f"[{genre}] Favorites"
            playlists["favorites"] = self.create_test_playlist(fav_name, fav_tracks)
            
            folder_playlists[genre] = {
                "playlists": playlists,
                "tracks": [(t[0], t[1], t[2]) for t in genre_tracks],
                "track_count": len(track_ids)
            }
            
            print(f"✅ Created {genre} folder with {len(playlists)} playlists and {len(track_ids)} tracks")
            time.sleep(0.5)  # Rate limiting
        
        return folder_playlists
    
    def create_unsorted_playlist(self, folder_playlists: Dict[str, Dict]) -> str:
        """
        Create an unsorted playlist with mixed genre songs for testing classification.
        
        Args:
            folder_playlists: Dict from create_folder_playlists()
            
        Returns:
            Playlist ID of unsorted playlist
        """
        print(f"\n=== Creating unsorted test playlist ===")
        
        # Collect tracks from all genres
        mixed_tracks = []
        
        for genre, info in folder_playlists.items():
            # Take 2-3 tracks from each genre
            genre_tracks = info["tracks"][:3]
            mixed_tracks.extend([track[0] for track in genre_tracks])
        
        if not mixed_tracks:
            print("⚠️  No tracks available for unsorted playlist")
            return None
        
        # Shuffle the tracks for realistic unsorted scenario
        import random
        random.shuffle(mixed_tracks)
        
        unsorted_name = "Unsorted - Needs Classification"
        playlist_id = self.create_test_playlist(unsorted_name, mixed_tracks)
        
        print(f"✅ Created unsorted playlist with {len(mixed_tracks)} mixed genre tracks")
        return playlist_id
    
    def create_test_scenarios(self) -> Dict[str, any]:
        """
        Create complete test scenario for genre classification.
        
        Returns:
            Dict with all created test data
        """
        print("🧪 Starting Genre Classification Test Setup")
        print("=" * 50)
        
        # Create folder-based playlists
        folder_playlists = self.create_folder_playlists()
        
        # Create unsorted playlist
        unsorted_playlist = self.create_unsorted_playlist(folder_playlists)
        
        # Summary
        total_playlists = sum(len(info["playlists"]) for info in folder_playlists.values())
        if unsorted_playlist:
            total_playlists += 1
        
        print(f"\n🎉 Genre Classification Test Setup Complete!")
        print(f"📊 Summary:")
        print(f"   - Created {len(folder_playlists)} genre folders")
        print(f"   - Created {total_playlists} test playlists")
        print(f"   - Ready for classification testing")
        
        return {
            "folder_playlists": folder_playlists,
            "unsorted_playlist": unsorted_playlist,
            "created_playlists": self.created_playlists.copy()
        }
    
    def cleanup_test_playlists(self):
        """Delete all test playlists created by this instance."""
        print(f"\n🧹 Cleaning up {len(self.created_playlists)} test playlists...")
        
        for playlist_id in self.created_playlists:
            try:
                spotify_api_call_with_retry(self.sp.current_user_unfollow_playlist, playlist_id)
                print(f"Deleted test playlist: {playlist_id}")
            except Exception as e:
                print(f"Failed to delete playlist {playlist_id}: {e}")
        
        self.created_playlists.clear()
        print("✅ Cleanup complete")
    
    def cleanup_all_test_playlists(self):
        """Delete ALL playlists with the test prefix."""
        print(f"\n🧹 Cleaning up ALL test playlists...")
        
        # Get all playlists
        playlists = []
        offset = 0
        limit = 50
        
        while True:
            results = spotify_api_call_with_retry(
                self.sp.current_user_playlists, limit=limit, offset=offset
            )
            
            if not results["items"]:
                break
                
            playlists.extend(results["items"])
            
            if len(results["items"]) < limit:
                break
                
            offset += limit
        
        # Delete test playlists
        deleted_count = 0
        for playlist in playlists:
            if playlist["name"].startswith(self.test_prefix):
                try:
                    spotify_api_call_with_retry(
                        self.sp.current_user_unfollow_playlist, playlist["id"]
                    )
                    print(f"Deleted: '{playlist['name']}'")
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete '{playlist['name']}': {e}")
        
        print(f"✅ Cleaned up {deleted_count} test playlists")


if __name__ == "__main__":
    import sys
    
    setup = GenreClassificationTestSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            # Create full test scenario
            test_data = setup.create_test_scenarios()
            
        elif command == "cleanup":
            # Clean up all test playlists
            setup.cleanup_all_test_playlists()
            
        elif command == "folders_only":
            # Create only folder playlists
            folder_playlists = setup.create_folder_playlists()
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  create       - Create complete test scenario")
            print("  cleanup      - Delete all test playlists")
            print("  folders_only - Create only folder playlists")
    else:
        print("Usage: python genre_classification_test_setup.py <command>")
        print("\nCommands:")
        print("  create       - Create complete genre classification test scenario")
        print("  cleanup      - Delete all test playlists")
        print("  folders_only - Create only folder playlists (no unsorted)")
        print("\nExample:")
        print("  SPOTIFY_ENV=test uv run python tests/genre_classification_test_setup.py create")