"""
Tests for folder sorter without making real API calls.

Uses mock Spotify client and fixtures to test sorting logic.
"""

import pytest
from typing import Dict, List, Set
from unittest.mock import patch, MagicMock

from tests.mock_spotify_client import MockSpotifyClient, create_mock_spotify_client
from tests.fixtures.folder_sorter_fixtures import (
    create_mock_artists,
    create_mock_tracks,
    setup_folder_playlists,
    setup_new_playlist,
    setup_aggregator_playlists,
    create_playlist_folders_map,
    create_mock_library_manifest,
    create_mock_playlist_loader_data,
    setup_complete_test_environment,
)

# Import the functions we want to test
from automations.spotify.folder_sorter.action import (
    _load_playlist_folders_map,
    _build_manifest_name_index,
    _resolve_folder_playlist_ids,
    _build_folder_artist_index,
    _fetch_new_tracks_with_artists,
    _plan_additions,
    _apply_additions_and_optionally_remove,
    TrackRef,
)


class TestFolderSorterBasics:
    """Test basic folder sorter functionality."""

    def test_load_playlist_folders_map(self, tmp_path):
        """Test loading playlist folders map from JSON."""
        # Create a temporary folders JSON file in data subdirectory
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        folders_file = data_dir / "playlist_folders.json"
        import json
        folders_data = {
            "Alive": ["Awaken.json", "Emergence.json"],
            "Electronic": ["EDM Bangers.json"],
        }
        with open(folders_file, "w") as f:
            json.dump(folders_data, f)

        # Mock PROJECT_ROOT to point to tmp_path
        with patch("automations.spotify.folder_sorter.action.PROJECT_ROOT", tmp_path):
            result = _load_playlist_folders_map()

        assert "Alive" in result
        assert "Awaken" in result["Alive"]  # .json suffix stripped
        assert "Emergence" in result["Alive"]
        assert "Electronic" in result
        assert "EDM Bangers" in result["Electronic"]

    def test_build_manifest_name_index(self):
        """Test building name index from manifest."""
        manifest = {
            "playlists": {
                "playlist_1": {"name": "Test Playlist 1"},
                "playlist_2": {"name": "Test Playlist 2"},
                "playlist_3": {"name": "UPPERCASE NAME"},
            }
        }

        index = _build_manifest_name_index(manifest)

        # Index should normalize names to lowercase
        assert "test playlist 1" in index
        assert "test playlist 2" in index
        assert "uppercase name" in index

        # Values should be (playlist_id, entry) tuples
        pid, entry = index["test playlist 1"]
        assert pid == "playlist_1"
        assert entry["name"] == "Test Playlist 1"

    def test_resolve_folder_playlist_ids(self):
        """Test resolving folder playlist names to IDs."""
        folders_map = {
            "Alive": ["Awaken", "Emergence"],
            "Electronic": ["EDM Bangers", "Missing Playlist"],
        }

        manifest_index = {
            "awaken": ("playlist_awaken", {"name": "Awaken"}),
            "emergence": ("playlist_emergence", {"name": "Emergence"}),
            "edm bangers": ("playlist_edm", {"name": "EDM Bangers"}),
        }

        folder_ids, missing = _resolve_folder_playlist_ids(folders_map, manifest_index)

        # Should resolve existing playlists
        assert "Alive" in folder_ids
        assert "playlist_awaken" in folder_ids["Alive"]
        assert "playlist_emergence" in folder_ids["Alive"]

        assert "Electronic" in folder_ids
        assert "playlist_edm" in folder_ids["Electronic"]

        # Should report missing playlist
        assert len(missing) == 1
        assert "Electronic:Missing Playlist" in missing

    def test_build_folder_artist_index(self):
        """Test building folder -> artist_id index."""
        artists = create_mock_artists()
        playlist_loader_data = {
            "playlist_1": {
                "name": "Playlist 1",
                "tracks": [
                    {
                        "id": "track_1",
                        "artists": [artists["artist_alive_1"], artists["artist_alive_2"]],
                    }
                ],
            },
            "playlist_2": {
                "name": "Playlist 2",
                "tracks": [
                    {
                        "id": "track_2",
                        "artists": [artists["artist_electronic_1"]],
                    }
                ],
            },
        }

        folders_to_playlist_ids = {
            "Alive": ["playlist_1"],
            "Electronic": ["playlist_2"],
        }

        index = _build_folder_artist_index(folders_to_playlist_ids, playlist_loader_data)

        assert "Alive" in index
        assert "artist_alive_1" in index["Alive"]
        assert "artist_alive_2" in index["Alive"]

        assert "Electronic" in index
        assert "artist_electronic_1" in index["Electronic"]


class TestFolderSorterTrackMatching:
    """Test track matching and planning logic."""

    def test_fetch_new_tracks_with_artists(self):
        """Test fetching tracks from New playlist."""
        sp = create_mock_spotify_client()
        artists = create_mock_artists()
        tracks = create_mock_tracks(artists)

        # Set up New playlist with some tracks
        new_playlist_id = setup_new_playlist(sp, tracks)

        # Fetch tracks
        result = _fetch_new_tracks_with_artists(sp, new_playlist_id)

        # Should get non-local tracks
        assert len(result) > 0

        # Check structure
        for track_ref in result:
            assert isinstance(track_ref, TrackRef)
            assert track_ref.uri.startswith("spotify:track:")
            assert len(track_ref.artist_ids) > 0

        # Local track should be filtered out
        local_uris = [t.uri for t in result if "local" in t.uri]
        assert len(local_uris) == 0

    def test_plan_additions_single_folder_match(self):
        """Test planning additions for tracks matching single folder."""
        # Create simple test data
        new_tracks = [
            TrackRef(uri="spotify:track:1", artist_ids=["artist_alive_1"]),
            TrackRef(uri="spotify:track:2", artist_ids=["artist_electronic_1"]),
            TrackRef(uri="spotify:track:3", artist_ids=["artist_unknown"]),
        ]

        folder_to_artist_ids = {
            "Alive": {"artist_alive_1", "artist_alive_2"},
            "Electronic": {"artist_electronic_1"},
        }

        folder_to_aggregator = {
            "Alive": {"id": "agg_alive", "name": "「Alive」"},
            "Electronic": {"id": "agg_electronic", "name": "「Electronic」"},
        }

        plan, track_to_folders = _plan_additions(
            new_tracks, folder_to_artist_ids, folder_to_aggregator
        )

        # Track 1 should go to Alive aggregator
        assert "agg_alive" in plan
        assert "spotify:track:1" in plan["agg_alive"]

        # Track 2 should go to Electronic aggregator
        assert "agg_electronic" in plan
        assert "spotify:track:2" in plan["agg_electronic"]

        # Track 3 should not be in any plan (unknown artist)
        all_planned_uris = [uri for uris in plan.values() for uri in uris]
        assert "spotify:track:3" not in all_planned_uris

        # Check track_to_folders mapping
        assert "spotify:track:1" in track_to_folders
        assert "Alive" in track_to_folders["spotify:track:1"]

    def test_plan_additions_multi_folder_match(self):
        """Test planning additions for tracks matching multiple folders."""
        new_tracks = [
            # Track with artist in multiple folders
            TrackRef(uri="spotify:track:shared", artist_ids=["artist_shared"]),
            # Track with multiple artists from different folders
            TrackRef(uri="spotify:track:multi", artist_ids=["artist_alive_1", "artist_electronic_1"]),
        ]

        folder_to_artist_ids = {
            "Alive": {"artist_alive_1"},
            "Electronic": {"artist_electronic_1", "artist_shared"},
            "Funk Soul": {"artist_shared"},
        }

        folder_to_aggregator = {
            "Alive": {"id": "agg_alive", "name": "「Alive」"},
            "Electronic": {"id": "agg_electronic", "name": "「Electronic」"},
            "Funk Soul": {"id": "agg_funk", "name": "「Funk Soul」"},
        }

        plan, track_to_folders = _plan_additions(
            new_tracks, folder_to_artist_ids, folder_to_aggregator
        )

        # Shared artist track should go to both Electronic and Funk Soul
        assert "agg_electronic" in plan
        assert "spotify:track:shared" in plan["agg_electronic"]
        assert "agg_funk" in plan
        assert "spotify:track:shared" in plan["agg_funk"]

        # Multi-artist track should go to both Alive and Electronic
        assert "spotify:track:multi" in plan["agg_alive"]
        assert "spotify:track:multi" in plan["agg_electronic"]

        # Check track_to_folders
        assert len(track_to_folders["spotify:track:shared"]) == 2
        assert "Electronic" in track_to_folders["spotify:track:shared"]
        assert "Funk Soul" in track_to_folders["spotify:track:shared"]


class TestFolderSorterAdditionsAndRemovals:
    """Test applying additions and removals."""

    def test_apply_additions_with_deduplication(self):
        """Test that additions are deduplicated against existing tracks."""
        sp = create_mock_spotify_client()

        # Create aggregator with existing track
        agg_id = sp.add_mock_playlist(
            name="「Alive」",
            playlist_id="agg_alive",
            tracks=[
                {
                    "id": "existing_track",
                    "uri": "spotify:track:existing",
                    "name": "Existing Track",
                    "artists": [],
                    "is_local": False,
                }
            ]
        )

        # Plan to add tracks (including duplicate)
        plan = {
            agg_id: [
                "spotify:track:existing",  # Duplicate - should be skipped
                "spotify:track:new_1",      # New - should be added
                "spotify:track:new_2",      # New - should be added
            ]
        }

        track_to_folders = {
            "spotify:track:existing": ["Alive"],
            "spotify:track:new_1": ["Alive"],
            "spotify:track:new_2": ["Alive"],
        }

        # Apply without removing from New
        added, removed = _apply_additions_and_optionally_remove(
            sp, plan, track_to_folders, keep_in_new=True, new_playlist_id="playlist_new"
        )

        # Should only add 2 new tracks (duplicate skipped)
        assert added == 2

        # Should not remove any (keep_in_new=True)
        assert removed == 0

        # Verify aggregator contents
        agg_uris = sp.get_playlist_track_uris(agg_id)
        assert len(agg_uris) == 3  # 1 existing + 2 new
        assert "spotify:track:existing" in agg_uris
        assert "spotify:track:new_1" in agg_uris
        assert "spotify:track:new_2" in agg_uris

    def test_apply_additions_with_removal_from_new(self):
        """Test that matched tracks are removed from New when --keep is not set."""
        sp = create_mock_spotify_client()

        # Create New playlist with tracks
        new_id = sp.add_mock_playlist(
            name="New",
            playlist_id="playlist_new",
            tracks=[
                {
                    "id": "track_1",
                    "uri": "spotify:track:1",
                    "name": "Track 1",
                    "artists": [],
                    "is_local": False,
                },
                {
                    "id": "track_2",
                    "uri": "spotify:track:2",
                    "name": "Track 2",
                    "artists": [],
                    "is_local": False,
                },
                {
                    "id": "track_3",
                    "uri": "spotify:track:3",
                    "name": "Track 3",
                    "artists": [],
                    "is_local": False,
                },
            ]
        )

        # Create aggregator
        agg_id = sp.add_mock_playlist(name="「Alive」", playlist_id="agg_alive")

        # Plan to add track_1 and track_2
        plan = {
            agg_id: ["spotify:track:1", "spotify:track:2"]
        }

        track_to_folders = {
            "spotify:track:1": ["Alive"],
            "spotify:track:2": ["Alive"],
        }

        # Apply with removal from New
        added, removed = _apply_additions_and_optionally_remove(
            sp, plan, track_to_folders, keep_in_new=False, new_playlist_id=new_id
        )

        assert added == 2
        assert removed == 2

        # Verify New playlist only has track_3 left
        new_uris = sp.get_playlist_track_uris(new_id)
        assert len(new_uris) == 1
        assert "spotify:track:3" in new_uris

        # Verify aggregator has both tracks
        agg_uris = sp.get_playlist_track_uris(agg_id)
        assert len(agg_uris) == 2
        assert "spotify:track:1" in agg_uris
        assert "spotify:track:2" in agg_uris

    def test_apply_additions_batch_processing(self):
        """Test that large additions are batched correctly (100 tracks per batch)."""
        sp = create_mock_spotify_client()
        agg_id = sp.add_mock_playlist(name="「Test」", playlist_id="agg_test")

        # Create plan with 250 tracks (should require 3 batches: 100, 100, 50)
        track_uris = [f"spotify:track:{i}" for i in range(250)]
        plan = {agg_id: track_uris}
        track_to_folders = {uri: ["Test"] for uri in track_uris}

        # Reset API call counter
        sp.reset_api_call_counts()

        added, removed = _apply_additions_and_optionally_remove(
            sp, plan, track_to_folders, keep_in_new=True, new_playlist_id="playlist_new"
        )

        assert added == 250

        # Should make 3 API calls for additions (100 + 100 + 50)
        assert sp.api_calls["playlist_add_items"] == 3

        # Verify all tracks were added
        agg_uris = sp.get_playlist_track_uris(agg_id)
        assert len(agg_uris) == 250


class TestFolderSorterIntegration:
    """Integration tests using complete test environment."""

    def test_complete_sorting_workflow(self):
        """Test complete sorting workflow from New to aggregators."""
        # Set up complete test environment
        env = setup_complete_test_environment()
        sp = env["sp"]
        artists = env["artists"]
        tracks = env["tracks"]

        # Build folder artist index
        folder_artist_index = _build_folder_artist_index(
            env["folder_playlists"], env["playlist_loader_data"]
        )

        # Fetch New tracks
        new_tracks = _fetch_new_tracks_with_artists(sp, env["new_playlist_id"])

        # Plan additions
        plan, track_to_folders = _plan_additions(
            new_tracks, folder_artist_index, env["aggregators"]
        )

        # Verify planning results
        assert len(plan) > 0  # Should have at least one aggregator with tracks

        # Apply additions
        added, removed = _apply_additions_and_optionally_remove(
            sp, plan, track_to_folders, keep_in_new=False, new_playlist_id=env["new_playlist_id"]
        )

        assert added > 0
        assert removed > 0

        # Verify tracks were moved correctly
        alive_agg_uris = sp.get_playlist_track_uris(env["aggregators"]["Alive"]["id"])
        electronic_agg_uris = sp.get_playlist_track_uris(env["aggregators"]["Electronic"]["id"])

        # Alive aggregator should have tracks from alive artists
        assert "spotify:track:track_alive_1" in alive_agg_uris

        # Electronic aggregator should have tracks from electronic artists
        assert "spotify:track:track_electronic_1" in electronic_agg_uris

        # Multi-artist track should be in both
        assert "spotify:track:track_multi_artist" in alive_agg_uris
        assert "spotify:track:track_multi_artist" in electronic_agg_uris

        # Unknown track should still be in New (not removed)
        new_uris = sp.get_playlist_track_uris(env["new_playlist_id"])
        assert "spotify:track:track_unknown" in new_uris


# Pytest fixtures for reuse across tests

@pytest.fixture
def mock_spotify_client():
    """Fixture providing a fresh mock Spotify client."""
    return create_mock_spotify_client()


@pytest.fixture
def test_environment(mock_spotify_client):
    """Fixture providing complete test environment."""
    return setup_complete_test_environment(mock_spotify_client)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
