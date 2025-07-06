"""
Centralized test data utilities for consistent testing.

Provides utilities for:
- Loading sample playlist data for tests
- Creating mock data structures
- Managing test data lifecycle
- Consistent test data patterns
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from unittest.mock import Mock

from common.playlist_data_utils import PlaylistDataLoader
from common.flow_character_utils import extract_flow_characters


class TestDataManager:
    """Manages test data loading and mock generation."""
    
    @staticmethod
    def load_sample_playlists(
        limit: int = 20,
        include_staging: bool = True,
        strategy: str = "diverse"
    ) -> Dict[str, Dict]:
        """
        Load sample playlists for testing.
        
        Args:
            limit: Maximum number of playlists to load
            include_staging: Whether to ensure staging playlist ("New") is included
            strategy: Sampling strategy ("diverse", "random", "largest", "smallest")
            
        Returns:
            Dictionary of sampled playlist data
        """
        # Load all playlists first
        all_playlists = PlaylistDataLoader.load_playlists_from_directory(
            include_empty=False,
            verbose=False
        )
        
        # Ensure staging playlist is included if requested
        staging_playlist = None
        if include_staging:
            staging_id = PlaylistDataLoader.find_playlist_by_name(all_playlists, "New")
            if staging_id:
                staging_playlist = {staging_id: all_playlists[staging_id]}
                # Remove from main dict to avoid duplication
                del all_playlists[staging_id]
                limit -= 1  # Reduce limit since we're adding staging separately
        
        # Sample the remaining playlists
        sampled = PlaylistDataLoader.sample_playlists(all_playlists, limit, strategy)
        
        # Add staging playlist back if found
        if staging_playlist:
            sampled.update(staging_playlist)
        
        return sampled
    
    @staticmethod
    def create_mock_track_data(
        track_id: str,
        artist_names: List[str],
        track_name: str = "Test Track",
        artist_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Create mock track data for testing.
        
        Args:
            track_id: ID for the track
            artist_names: List of artist names
            track_name: Name of the track
            artist_ids: Optional list of artist IDs (generated if None)
            
        Returns:
            Mock track data dictionary
        """
        if artist_ids is None:
            artist_ids = [f"artist_{i}_{name.lower().replace(' ', '_')}" 
                         for i, name in enumerate(artist_names)]
        
        artists = []
        for i, name in enumerate(artist_names):
            artist_id = artist_ids[i] if i < len(artist_ids) else f"artist_{i}"
            artists.append({
                "id": artist_id,
                "name": name,
                "external_urls": {"spotify": f"https://open.spotify.com/artist/{artist_id}"},
                "href": f"https://api.spotify.com/v1/artists/{artist_id}",
                "type": "artist",
                "uri": f"spotify:artist:{artist_id}"
            })
        
        return {
            "id": track_id,
            "name": track_name,
            "artists": artists,
            "duration_ms": 180000,  # 3 minutes
            "popularity": 50,
            "explicit": False,
            "preview_url": f"https://example.com/preview/{track_id}",
            "external_urls": {"spotify": f"https://open.spotify.com/track/{track_id}"},
            "href": f"https://api.spotify.com/v1/tracks/{track_id}",
            "is_local": False,
            "type": "track",
            "uri": f"spotify:track:{track_id}",
            "album": {
                "id": f"album_{track_id}",
                "name": "Test Album",
                "type": "album"
            }
        }
    
    @staticmethod
    def create_mock_playlist_data(
        playlist_name: str,
        tracks: List[Dict],
        playlist_id: Optional[str] = None
    ) -> Dict:
        """
        Create mock playlist data for testing.
        
        Args:
            playlist_name: Name of the playlist
            tracks: List of track dictionaries
            playlist_id: Optional playlist ID (generated if None)
            
        Returns:
            Mock playlist data dictionary
        """
        if playlist_id is None:
            playlist_id = f"playlist_{playlist_name.lower().replace(' ', '_')}"
        
        return {
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "playlist_url": f"https://open.spotify.com/playlist/{playlist_id}",
            "owner": "test_user",
            "total_tracks_api": len(tracks),
            "total_tracks_fetched": len(tracks),
            "tracks": tracks
        }
    
    @staticmethod
    def create_test_scenario_single_playlist_artists() -> Dict[str, Dict]:
        """
        Create a test scenario with known single playlist artists.
        
        Returns:
            Dictionary of playlists designed to test single playlist artist detection
        """
        # Artist A appears only in Playlist 1
        # Artist B appears in both Playlist 1 and 2
        # Artist C appears only in Playlist 2
        # Artist D appears only in Playlist 3 (parent)
        
        track1 = TestDataManager.create_mock_track_data(
            "track1", ["Artist A"], "Song A", ["artist_a"]
        )
        track2 = TestDataManager.create_mock_track_data(
            "track2", ["Artist B"], "Song B", ["artist_b"]
        )
        track3 = TestDataManager.create_mock_track_data(
            "track3", ["Artist B"], "Song B2", ["artist_b"]
        )
        track4 = TestDataManager.create_mock_track_data(
            "track4", ["Artist C"], "Song C", ["artist_c"]
        )
        track5 = TestDataManager.create_mock_track_data(
            "track5", ["Artist D"], "Song D", ["artist_d"]
        )
        
        playlist1_data = TestDataManager.create_mock_playlist_data(
            "Test Playlist 1", [track1, track2], "playlist1"
        )
        playlist2_data = TestDataManager.create_mock_playlist_data(
            "Test Playlist 2", [track3, track4], "playlist2"
        )
        parent_playlist_data = TestDataManager.create_mock_playlist_data(
            "🎵 Parent Collection", [track5], "parent_playlist"
        )
        
        return {
            "playlist1": {
                "name": "Test Playlist 1",
                "tracks": [track1, track2]
            },
            "playlist2": {
                "name": "Test Playlist 2", 
                "tracks": [track3, track4]
            },
            "parent_playlist": {
                "name": "🎵 Parent Collection",
                "tracks": [track5]
            }
        }
    
    @staticmethod
    def create_test_scenario_flow_hierarchy() -> Dict[str, Dict]:
        """
        Create a test scenario with flow hierarchy relationships.
        
        Returns:
            Dictionary of playlists with parent/child flow relationships
        """
        # Create tracks for different playlists
        tracks_child1 = [
            TestDataManager.create_mock_track_data("track1", ["Artist 1"], "Child Song 1"),
            TestDataManager.create_mock_track_data("track2", ["Artist 2"], "Child Song 2")
        ]
        
        tracks_child2 = [
            TestDataManager.create_mock_track_data("track3", ["Artist 3"], "Child Song 3")
        ]
        
        tracks_parent = [
            TestDataManager.create_mock_track_data("track4", ["Artist 4"], "Parent Song 1")
        ]
        
        tracks_staging = [
            TestDataManager.create_mock_track_data("track5", ["Artist 1"], "Staging Song 1"),
            TestDataManager.create_mock_track_data("track6", ["Artist 5"], "Staging Song 2")
        ]
        
        return {
            "child1": {
                "name": "Daily Mix 🎵",
                "tracks": tracks_child1
            },
            "child2": {
                "name": "Favorites 🎵",
                "tracks": tracks_child2
            },
            "parent": {
                "name": "🎵 Main Collection",
                "tracks": tracks_parent
            },
            "staging": {
                "name": "New",
                "tracks": tracks_staging
            }
        }
    
    @staticmethod
    def create_mock_spotify_client(playlists_dict: Dict[str, Dict]) -> Mock:
        """
        Create a mock Spotify client for testing.
        
        Args:
            playlists_dict: Playlist data to use for mock responses
            
        Returns:
            Mock Spotify client object
        """
        mock_client = Mock()
        
        # Mock playlist lookup
        def mock_playlist(playlist_id, fields=None):
            if playlist_id in playlists_dict:
                return {
                    "id": playlist_id,
                    "name": playlists_dict[playlist_id]["name"],
                    "tracks": {"total": len(playlists_dict[playlist_id]["tracks"])}
                }
            raise Exception(f"Playlist {playlist_id} not found")
        
        # Mock track lookup
        def mock_track(track_id):
            for playlist_data in playlists_dict.values():
                for track in playlist_data["tracks"]:
                    if track["id"] == track_id:
                        return track
            raise Exception(f"Track {track_id} not found")
        
        # Mock playlist modification
        def mock_playlist_add_items(playlist_id, track_ids):
            if playlist_id not in playlists_dict:
                raise Exception(f"Playlist {playlist_id} not found")
            return {"snapshot_id": "mock_snapshot"}
        
        mock_client.playlist = mock_playlist
        mock_client.track = mock_track
        mock_client.playlist_add_items = mock_playlist_add_items
        
        return mock_client
    
    @staticmethod
    def save_test_data_to_temp_dir(playlists_dict: Dict[str, Dict]) -> Path:
        """
        Save test playlist data to a temporary directory.
        
        Args:
            playlists_dict: Playlist data to save
            
        Returns:
            Path to temporary directory containing JSON files
        """
        temp_dir = Path(tempfile.mkdtemp())
        
        for playlist_id, playlist_data in playlists_dict.items():
            playlist_file = temp_dir / f"{playlist_data['name']}.json"
            
            # Create full playlist structure
            full_data = TestDataManager.create_mock_playlist_data(
                playlist_data["name"],
                playlist_data["tracks"],
                playlist_id
            )
            
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2)
        
        return temp_dir
    
    @staticmethod
    def cleanup_temp_dir(temp_dir: Path):
        """
        Clean up temporary directory.
        
        Args:
            temp_dir: Path to temporary directory to clean up
        """
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    @staticmethod
    def assert_playlist_structure(playlist_data: Dict):
        """
        Assert that playlist data has the expected structure.
        
        Args:
            playlist_data: Playlist data to validate
            
        Raises:
            AssertionError: If structure is invalid
        """
        assert "name" in playlist_data, "Playlist must have name"
        assert "tracks" in playlist_data, "Playlist must have tracks"
        assert isinstance(playlist_data["tracks"], list), "Tracks must be a list"
        
        for i, track in enumerate(playlist_data["tracks"]):
            assert "id" in track, f"Track {i} must have id"
            assert "name" in track, f"Track {i} must have name"
            assert "artists" in track, f"Track {i} must have artists"
            assert isinstance(track["artists"], list), f"Track {i} artists must be a list"
            
            for j, artist in enumerate(track["artists"]):
                assert "id" in artist, f"Track {i} artist {j} must have id"
                assert "name" in artist, f"Track {i} artist {j} must have name"