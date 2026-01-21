"""
Pytest configuration and shared fixtures.

This module provides fixtures for testing spotify-macro without hitting the real API.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from tests.mock_spotify_client import MockSpotifyClient, create_mock_spotify_client


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "library" / "playlists"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_spotify():
    """Create a mock Spotify client for testing."""
    return create_mock_spotify_client()


@pytest.fixture
def mock_spotify_with_data():
    """Create a mock Spotify client pre-loaded with local playlist data."""
    client = create_mock_spotify_client()
    if DATA_DIR.exists():
        client.load_playlists_from_directory(DATA_DIR)
    return client


@pytest.fixture
def sample_track():
    """A minimal sample track for unit tests."""
    return {
        "id": "test_track_001",
        "name": "Test Track",
        "artists": [
            {"id": "test_artist_001", "name": "Test Artist"}
        ],
        "duration_ms": 180000,
        "popularity": 50,
        "explicit": False,
        "album": {"name": "Test Album"}
    }


@pytest.fixture
def sample_playlist():
    """A minimal sample playlist for unit tests."""
    return {
        "id": "test_playlist_001",
        "name": "Test Playlist",
        "tracks": {
            "total": 2,
            "items": [
                {
                    "track": {
                        "id": "track_001",
                        "name": "Track One",
                        "artists": [{"id": "artist_001", "name": "Artist One"}],
                        "duration_ms": 200000,
                    }
                },
                {
                    "track": {
                        "id": "track_002",
                        "name": "Track Two",
                        "artists": [{"id": "artist_002", "name": "Artist Two"}],
                        "duration_ms": 220000,
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_playlists_dict():
    """Pre-normalized playlists dict for testing utilities."""
    return {
        "playlist_001": {
            "name": "Electronic",
            "tracks": [
                {"id": "t1", "name": "Song 1", "artists": [{"id": "a1", "name": "DJ One"}]},
                {"id": "t2", "name": "Song 2", "artists": [{"id": "a2", "name": "DJ Two"}]},
            ],
            "total_tracks": 2,
        },
        "playlist_002": {
            "name": "House",
            "tracks": [
                {"id": "t3", "name": "Song 3", "artists": [{"id": "a1", "name": "DJ One"}]},
                {"id": "t4", "name": "Song 4", "artists": [{"id": "a3", "name": "DJ Three"}]},
            ],
            "total_tracks": 2,
        },
        "playlist_003": {
            "name": "Jazz",
            "tracks": [
                {"id": "t5", "name": "Song 5", "artists": [{"id": "a4", "name": "Jazz Artist"}]},
            ],
            "total_tracks": 1,
        }
    }


@pytest.fixture
def local_playlists():
    """Load actual local playlist data if available."""
    if not DATA_DIR.exists():
        pytest.skip("Local playlist data not available")

    from common.playlist_data_utils import PlaylistDataLoader
    return PlaylistDataLoader.load_playlists_from_directory(limit=10)


@pytest.fixture(scope="session")
def all_local_playlists():
    """Load all local playlists (session-scoped for efficiency)."""
    if not DATA_DIR.exists():
        pytest.skip("Local playlist data not available")

    from common.playlist_data_utils import PlaylistDataLoader
    return PlaylistDataLoader.load_playlists_from_directory()


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "requires_local_data: marks tests that require local playlist data"
    )
    config.addinivalue_line(
        "markers", "requires_env: marks tests that require environment variables"
    )
