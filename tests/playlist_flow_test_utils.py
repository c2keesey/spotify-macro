"""
Test utilities for playlist flow automation testing.
Provides pytest fixtures and utilities for creating/deleting test playlists and scenarios.
"""

import time
import pytest
from typing import Dict, List, Tuple, Optional
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


class PlaylistFlowTestUtils:
    """Utility class for managing test playlists and scenarios."""
    
    def __init__(self, test_prefix: str = "🧪TEST_"):
        """
        Initialize test utilities.
        
        Args:
            test_prefix: Prefix for all test playlists to identify them
        """
        self.test_prefix = test_prefix
        self.scope = "playlist-read-private playlist-modify-private playlist-modify-public user-read-private"
        self.sp = initialize_spotify_client(self.scope, "playlist_flow_test_cache")
        self.created_playlists = []  # Track created playlists for cleanup
        
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
            description="Test playlist - safe to delete"
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
    
    def cleanup_test_playlists(self):
        """Delete all test playlists created by this instance."""
        for playlist_id in self.created_playlists:
            try:
                spotify_api_call_with_retry(self.sp.current_user_unfollow_playlist, playlist_id)
                print(f"Deleted test playlist: {playlist_id}")
            except Exception as e:
                print(f"Failed to delete playlist {playlist_id}: {e}")
        
        self.created_playlists.clear()
    
    def cleanup_all_test_playlists(self):
        """Delete ALL playlists with the test prefix (not just this instance)."""
        playlists = self.get_all_playlists()
        deleted_count = 0
        
        for playlist in playlists:
            if playlist["name"].startswith(self.test_prefix):
                try:
                    spotify_api_call_with_retry(
                        self.sp.current_user_unfollow_playlist, playlist["id"]
                    )
                    print(f"Deleted test playlist: '{playlist['name']}'")
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete playlist '{playlist['name']}': {e}")
        
        print(f"Cleaned up {deleted_count} test playlists")
    
    def get_all_playlists(self) -> List[Dict]:
        """Get all user playlists."""
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
        
        return playlists
    
    def get_sample_tracks(self, count: int = 5) -> List[str]:
        """
        Get sample track IDs for testing.
        
        Args:
            count: Number of tracks to return
            
        Returns:
            List of track IDs
        """
        # Search for some generic tracks
        search_terms = ["the", "love", "time", "music", "rock"]
        track_ids = []
        
        for term in search_terms[:count]:
            try:
                results = spotify_api_call_with_retry(
                    self.sp.search, term, type="track", limit=1
                )
                if results["tracks"]["items"]:
                    track_ids.append(results["tracks"]["items"][0]["id"])
            except Exception as e:
                print(f"Failed to get sample track for '{term}': {e}")
        
        return track_ids
    
    def create_basic_flow_scenario(self) -> Dict[str, str]:
        """
        Create a basic parent-child flow scenario.
        
        Returns:
            Dict with playlist IDs
        """
        sample_tracks = self.get_sample_tracks(3)
        
        parent_id = self.create_test_playlist("🎵 Basic Parent")
        child_id = self.create_test_playlist("Basic Child 🎵", tracks=sample_tracks)
        
        return {
            "parent": parent_id,
            "child": child_id,
            "expected_flow": len(sample_tracks)
        }
    
    def create_cycle_scenario(self) -> Dict[str, str]:
        """
        Create a cycle scenario for testing cycle detection.
        
        Returns:
            Dict with playlist IDs
        """
        sample_tracks = self.get_sample_tracks(2)
        
        playlist_a = self.create_test_playlist("♪ Cycle A ♫", tracks=sample_tracks)
        playlist_b = self.create_test_playlist("♫ Cycle B ♪", tracks=sample_tracks)
        
        return {
            "playlist_a": playlist_a,
            "playlist_b": playlist_b,
            "expected_cycles": 1
        }
    
    def create_unicode_edge_cases(self) -> Dict[str, str]:
        """
        Create playlists with problematic Unicode characters.
        
        Returns:
            Dict with playlist IDs
        """
        sample_tracks = self.get_sample_tracks(2)
        
        scenarios = {}
        
        # Multi-byte emoji
        scenarios["emoji_parent"] = self.create_test_playlist("👨‍💻 Complex Emoji Parent")
        scenarios["emoji_child"] = self.create_test_playlist("Child Mix 👨‍💻", tracks=sample_tracks)
        
        # Flag emoji
        scenarios["flag_parent"] = self.create_test_playlist("🇺🇸 Flag Parent")
        scenarios["flag_child"] = self.create_test_playlist("Mix 🇺🇸", tracks=sample_tracks)
        
        # Combining characters
        scenarios["accent_parent"] = self.create_test_playlist("é Accent Parent")
        scenarios["accent_child"] = self.create_test_playlist("Child é", tracks=sample_tracks)
        
        return scenarios
    
    def create_self_reference_scenario(self) -> str:
        """
        Create a playlist that references itself.
        
        Returns:
            Playlist ID
        """
        sample_tracks = self.get_sample_tracks(3)
        return self.create_test_playlist("🎵 Self Ref 🎵", tracks=sample_tracks)
    
    def create_multi_hop_scenario(self) -> Dict[str, str]:
        """
        Create a chain of playlists: A🎵 -> 🎵B🎶 -> 🎶C
        
        Returns:
            Dict with playlist IDs
        """
        sample_tracks = self.get_sample_tracks(2)
        
        playlist_a = self.create_test_playlist("Chain A 🎵", tracks=sample_tracks)
        playlist_b = self.create_test_playlist("🎵 Chain B 🎶", tracks=sample_tracks)
        playlist_c = self.create_test_playlist("🎶 Chain C")
        
        return {
            "start": playlist_a,
            "middle": playlist_b,
            "end": playlist_c
        }
    
    def create_large_playlist_scenario(self, track_count: int = 100) -> Dict[str, str]:
        """
        Create playlists with many tracks for performance testing.
        
        Args:
            track_count: Number of tracks to add (will search for this many)
            
        Returns:
            Dict with playlist IDs
        """
        # Get more tracks by searching different terms
        track_ids = []
        search_terms = [
            "rock", "pop", "jazz", "classical", "electronic", "hip hop",
            "country", "reggae", "blues", "funk", "soul", "disco",
            "house", "techno", "ambient", "indie", "alternative", "punk"
        ]
        
        for term in search_terms:
            if len(track_ids) >= track_count:
                break
            try:
                results = spotify_api_call_with_retry(
                    self.sp.search, term, type="track", limit=min(50, track_count - len(track_ids))
                )
                for track in results["tracks"]["items"]:
                    if track["id"] not in track_ids:
                        track_ids.append(track["id"])
                        if len(track_ids) >= track_count:
                            break
            except Exception as e:
                print(f"Failed to search for '{term}': {e}")
        
        parent_id = self.create_test_playlist("🎼 Large Parent")
        child_id = self.create_test_playlist(f"Large Child ({len(track_ids)} tracks) 🎼", tracks=track_ids)
        
        return {
            "parent": parent_id,
            "child": child_id,
            "track_count": len(track_ids)
        }


def run_test_scenario(scenario_name: str, test_utils: PlaylistFlowTestUtils):
    """
    Run a specific test scenario.
    
    Args:
        scenario_name: Name of the scenario to run
        test_utils: Test utilities instance
    """
    print(f"\n=== Running {scenario_name} Scenario ===")
    
    try:
        if scenario_name == "basic_flow":
            scenario = test_utils.create_basic_flow_scenario()
            print(f"Created basic flow: {scenario}")
            
        elif scenario_name == "cycle":
            scenario = test_utils.create_cycle_scenario()
            print(f"Created cycle: {scenario}")
            
        elif scenario_name == "unicode":
            scenario = test_utils.create_unicode_edge_cases()
            print(f"Created unicode edge cases: {scenario}")
            
        elif scenario_name == "self_reference":
            playlist_id = test_utils.create_self_reference_scenario()
            print(f"Created self-reference playlist: {playlist_id}")
            
        elif scenario_name == "multi_hop":
            scenario = test_utils.create_multi_hop_scenario()
            print(f"Created multi-hop chain: {scenario}")
            
        elif scenario_name == "large_playlist":
            scenario = test_utils.create_large_playlist_scenario(50)  # 50 tracks for testing
            print(f"Created large playlist scenario: {scenario}")
            
        else:
            print(f"Unknown scenario: {scenario_name}")
            
        print(f"✅ {scenario_name} scenario created successfully")
        
    except Exception as e:
        print(f"❌ Failed to create {scenario_name} scenario: {e}")


if __name__ == "__main__":
    import sys
    
    test_utils = PlaylistFlowTestUtils()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "cleanup":
            test_utils.cleanup_all_test_playlists()
            
        elif command == "create_all":
            scenarios = ["basic_flow", "cycle", "unicode", "self_reference", "multi_hop"]
            for scenario in scenarios:
                run_test_scenario(scenario, test_utils)
                time.sleep(1)  # Brief pause between creations
                
        elif command.startswith("create_"):
            scenario = command[7:]  # Remove "create_" prefix
            run_test_scenario(scenario, test_utils)
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: cleanup, create_all, create_basic_flow, create_cycle, create_unicode, create_self_reference, create_multi_hop, create_large_playlist")
    else:
        print("Usage: python playlist_flow_test_utils.py <command>")
        print("Commands:")
        print("  cleanup                    - Delete all test playlists")
        print("  create_all                 - Create all test scenarios")
        print("  create_basic_flow          - Create basic parent-child flow")
        print("  create_cycle               - Create cycle scenario")
        print("  create_unicode             - Create unicode edge cases")
        print("  create_self_reference      - Create self-referencing playlist")
        print("  create_multi_hop           - Create multi-hop chain")
        print("  create_large_playlist      - Create large playlist scenario")


# Pytest Fixtures
@pytest.fixture(scope="session")
def test_utils():
    """Session-scoped fixture that provides test utilities instance."""
    utils = PlaylistFlowTestUtils()
    yield utils
    # Cleanup all test playlists at end of session
    utils.cleanup_all_test_playlists()


@pytest.fixture(scope="function") 
def clean_test_utils():
    """Function-scoped fixture that provides clean test utilities for each test."""
    utils = PlaylistFlowTestUtils()
    yield utils
    # Cleanup after each test
    utils.cleanup_test_playlists()


@pytest.fixture
def sample_tracks(test_utils):
    """Fixture that provides sample track IDs for testing."""
    return test_utils.get_sample_tracks(5)


@pytest.fixture
def basic_flow_scenario(clean_test_utils):
    """Fixture that creates a basic parent-child flow scenario."""
    return clean_test_utils.create_basic_flow_scenario()


@pytest.fixture
def cycle_scenario(clean_test_utils):
    """Fixture that creates a cycle scenario."""
    return clean_test_utils.create_cycle_scenario()


@pytest.fixture  
def unicode_scenario(clean_test_utils):
    """Fixture that creates unicode edge case scenarios."""
    return clean_test_utils.create_unicode_edge_cases()


@pytest.fixture
def self_reference_scenario(clean_test_utils):
    """Fixture that creates a self-referencing playlist."""
    playlist_id = clean_test_utils.create_self_reference_scenario()
    return {"self_ref_playlist": playlist_id}


@pytest.fixture
def multi_hop_scenario(clean_test_utils):
    """Fixture that creates a multi-hop chain scenario."""
    return clean_test_utils.create_multi_hop_scenario()


@pytest.fixture
def large_playlist_scenario(clean_test_utils):
    """Fixture that creates a large playlist scenario."""
    return clean_test_utils.create_large_playlist_scenario(20)  # Smaller for testing


@pytest.fixture(scope="session", autouse=True)
def cleanup_before_session():
    """Auto-cleanup fixture that runs before the test session starts."""
    utils = PlaylistFlowTestUtils()
    utils.cleanup_all_test_playlists()
    yield