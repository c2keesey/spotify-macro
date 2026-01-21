"""
Test data utilities for loading sample data and managing test fixtures.

This module provides the TestDataManager class referenced by existing tests.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
import sys
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.playlist_data_utils import PlaylistDataLoader


class TestDataManager:
    """Utilities for loading and managing test data."""

    DATA_DIR = PROJECT_ROOT / "data" / "library" / "playlists"
    FIXTURES_DIR = Path(__file__).parent / "fixtures"

    @classmethod
    def load_sample_playlists(
        cls,
        limit: int = 10,
        strategy: str = "diverse"
    ) -> Dict[str, Dict]:
        """
        Load a sample of playlists for testing.

        Args:
            limit: Maximum number of playlists to load
            strategy: Sampling strategy ("random", "largest", "smallest", "diverse")

        Returns:
            Dictionary of sampled playlists
        """
        if not cls.DATA_DIR.exists():
            # Return minimal fixture data if no local data
            return cls._get_minimal_fixtures()

        # Load all playlists then sample
        all_playlists = PlaylistDataLoader.load_playlists_from_directory(
            include_empty=False,
            verbose=False
        )

        return PlaylistDataLoader.sample_playlists(all_playlists, limit, strategy)

    @classmethod
    def load_fixture(cls, fixture_name: str) -> Dict:
        """
        Load a specific fixture file.

        Args:
            fixture_name: Name of the fixture file (without .json extension)

        Returns:
            Fixture data as dictionary
        """
        fixture_path = cls.FIXTURES_DIR / f"{fixture_name}.json"

        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")

        with open(fixture_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def save_fixture(cls, fixture_name: str, data: Dict):
        """
        Save data as a fixture for future tests.

        Args:
            fixture_name: Name for the fixture file
            data: Data to save
        """
        cls.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_path = cls.FIXTURES_DIR / f"{fixture_name}.json"

        with open(fixture_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_test_playlist(
        cls,
        name: str = "Test Playlist",
        track_count: int = 5
    ) -> Dict:
        """
        Generate a test playlist with synthetic data.

        Args:
            name: Playlist name
            track_count: Number of tracks to generate

        Returns:
            Synthetic playlist data
        """
        tracks = []
        for i in range(track_count):
            tracks.append({
                "id": f"track_{i:03d}",
                "name": f"Test Track {i + 1}",
                "artists": [
                    {"id": f"artist_{i % 10:03d}", "name": f"Test Artist {i % 10 + 1}"}
                ],
                "duration_ms": 180000 + (i * 10000),
                "popularity": 50 + (i % 50),
                "explicit": i % 3 == 0,
                "album": {"name": f"Test Album {i // 5 + 1}"}
            })

        return {
            "name": name,
            "tracks": tracks,
            "total_tracks": len(tracks),
            "metadata": {"generated": True}
        }

    @classmethod
    def get_test_playlists_dict(
        cls,
        count: int = 3,
        tracks_per_playlist: int = 5
    ) -> Dict[str, Dict]:
        """
        Generate multiple test playlists.

        Args:
            count: Number of playlists to generate
            tracks_per_playlist: Tracks per playlist

        Returns:
            Dictionary of synthetic playlists
        """
        playlists = {}
        genres = ["Electronic", "House", "Jazz", "Rock", "Hip-Hop", "Ambient"]

        for i in range(count):
            playlist_id = f"playlist_{i:03d}"
            genre = genres[i % len(genres)]
            playlists[playlist_id] = cls.get_test_playlist(
                name=f"{genre} Test",
                track_count=tracks_per_playlist
            )

        return playlists

    @classmethod
    def _get_minimal_fixtures(cls) -> Dict[str, Dict]:
        """Return minimal hardcoded fixtures when no local data is available."""
        return {
            "fixture_playlist_001": {
                "name": "Fixture Electronic",
                "tracks": [
                    {
                        "id": "fix_track_001",
                        "name": "Fixture Track 1",
                        "artists": [{"id": "fix_artist_001", "name": "Fixture Artist"}],
                        "duration_ms": 200000,
                    }
                ],
                "total_tracks": 1,
            },
            "fixture_playlist_002": {
                "name": "Fixture House",
                "tracks": [
                    {
                        "id": "fix_track_002",
                        "name": "Fixture Track 2",
                        "artists": [{"id": "fix_artist_002", "name": "Fixture DJ"}],
                        "duration_ms": 220000,
                    }
                ],
                "total_tracks": 1,
            }
        }

    @classmethod
    def has_local_data(cls) -> bool:
        """Check if local playlist data is available."""
        return cls.DATA_DIR.exists() and (cls.DATA_DIR.parent / "manifest.json").exists()
