"""
Tests for folder sorter progress tracking functionality.

Tests the ability to track which tracks have been manually processed
and skip them on subsequent sorting runs.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Set
from unittest.mock import patch

from tests.mock_spotify_client import MockSpotifyClient, create_mock_spotify_client
from tests.fixtures.folder_sorter_fixtures import (
    create_mock_artists,
    create_mock_tracks,
    setup_complete_test_environment,
)

# Import progress tracking functions (to be implemented)
from common.folder_sort_progress import (
    FolderSortProgress,
    load_progress_state,
    save_progress_state,
    mark_tracks_as_processed,
    is_track_processed,
    get_processed_tracks_for_folder,
)

from automations.spotify.folder_sorter.action import (
    _plan_additions,
    _fetch_new_tracks_with_artists,
    TrackRef,
)


class TestProgressStateManagement:
    """Test basic progress state management operations."""

    def test_create_empty_progress_state(self, tmp_path):
        """Test creating an empty progress state."""
        progress = FolderSortProgress()

        assert progress.processed_tracks == {}
        assert progress.last_updated is not None

    def test_save_and_load_progress_state(self, tmp_path):
        """Test saving and loading progress state from file."""
        progress_file = tmp_path / "folder_sort_progress.json"

        # Create and save progress state
        progress = FolderSortProgress()
        progress.mark_processed("spotify:track:1", "Alive")
        progress.mark_processed("spotify:track:2", "Electronic")
        progress.mark_processed("spotify:track:1", "Electronic")  # Same track, different folder

        with patch("common.folder_sort_progress.get_progress_file_path", return_value=progress_file):
            save_progress_state(progress)

        # Load and verify
        with patch("common.folder_sort_progress.get_progress_file_path", return_value=progress_file):
            loaded = load_progress_state()

        assert loaded.is_processed("spotify:track:1", "Alive")
        assert loaded.is_processed("spotify:track:2", "Electronic")
        assert loaded.is_processed("spotify:track:1", "Electronic")
        assert not loaded.is_processed("spotify:track:3", "Alive")

    def test_mark_track_as_processed(self):
        """Test marking tracks as processed."""
        progress = FolderSortProgress()

        # Mark track for single folder
        progress.mark_processed("spotify:track:1", "Alive")
        assert progress.is_processed("spotify:track:1", "Alive")
        assert not progress.is_processed("spotify:track:1", "Electronic")

        # Mark same track for different folder
        progress.mark_processed("spotify:track:1", "Electronic")
        assert progress.is_processed("spotify:track:1", "Alive")
        assert progress.is_processed("spotify:track:1", "Electronic")

    def test_get_processed_tracks_for_folder(self):
        """Test getting all processed tracks for a specific folder."""
        progress = FolderSortProgress()

        progress.mark_processed("spotify:track:1", "Alive")
        progress.mark_processed("spotify:track:2", "Alive")
        progress.mark_processed("spotify:track:3", "Electronic")

        alive_tracks = progress.get_processed_tracks_for_folder("Alive")
        assert "spotify:track:1" in alive_tracks
        assert "spotify:track:2" in alive_tracks
        assert "spotify:track:3" not in alive_tracks

    def test_unmark_track(self):
        """Test removing a track from processed list."""
        progress = FolderSortProgress()

        progress.mark_processed("spotify:track:1", "Alive")
        progress.mark_processed("spotify:track:1", "Electronic")

        # Unmark from one folder only
        progress.unmark_processed("spotify:track:1", "Alive")

        assert not progress.is_processed("spotify:track:1", "Alive")
        assert progress.is_processed("spotify:track:1", "Electronic")

    def test_clear_all_progress(self):
        """Test clearing all progress."""
        progress = FolderSortProgress()

        progress.mark_processed("spotify:track:1", "Alive")
        progress.mark_processed("spotify:track:2", "Electronic")

        progress.clear()

        assert progress.processed_tracks == {}
        assert not progress.is_processed("spotify:track:1", "Alive")


class TestProgressIntegrationWithSorting:
    """Test progress tracking integration with folder sorting."""

    def test_plan_additions_skips_processed_tracks(self):
        """Test that planning skips tracks already marked as processed."""
        progress = FolderSortProgress()

        # Mark track_1 as processed for Alive folder
        progress.mark_processed("spotify:track:1", "Alive")

        new_tracks = [
            TrackRef(uri="spotify:track:1", artist_ids=["artist_alive_1"]),
            TrackRef(uri="spotify:track:2", artist_ids=["artist_alive_1"]),
        ]

        folder_to_artist_ids = {
            "Alive": {"artist_alive_1"},
        }

        folder_to_aggregator = {
            "Alive": {"id": "agg_alive", "name": "「Alive」"},
        }

        # Import the modified planning function that respects progress
        from automations.spotify.folder_sorter.action import _plan_additions_with_progress

        plan, track_to_folders = _plan_additions_with_progress(
            new_tracks, folder_to_artist_ids, folder_to_aggregator, progress
        )

        # track_1 should be skipped (processed)
        assert "spotify:track:1" not in plan.get("agg_alive", [])

        # track_2 should be included (not processed)
        assert "spotify:track:2" in plan.get("agg_alive", [])

    def test_plan_additions_with_multi_folder_partial_processing(self):
        """Test that tracks processed in one folder can still be added to others."""
        progress = FolderSortProgress()

        # Track is processed for Electronic but not for Funk Soul
        progress.mark_processed("spotify:track:shared", "Electronic")

        new_tracks = [
            TrackRef(uri="spotify:track:shared", artist_ids=["artist_shared"]),
        ]

        folder_to_artist_ids = {
            "Electronic": {"artist_shared"},
            "Funk Soul": {"artist_shared"},
        }

        folder_to_aggregator = {
            "Electronic": {"id": "agg_electronic", "name": "「Electronic」"},
            "Funk Soul": {"id": "agg_funk", "name": "「Funk Soul」"},
        }

        from automations.spotify.folder_sorter.action import _plan_additions_with_progress

        plan, track_to_folders = _plan_additions_with_progress(
            new_tracks, folder_to_artist_ids, folder_to_aggregator, progress
        )

        # Should NOT be in Electronic (processed)
        assert "spotify:track:shared" not in plan.get("agg_electronic", [])

        # Should be in Funk Soul (not processed)
        assert "spotify:track:shared" in plan.get("agg_funk", [])

    def test_mark_current_aggregator_contents_as_processed(self):
        """Test marking current aggregator contents as processed."""
        sp = create_mock_spotify_client()

        # Create aggregator with some tracks
        agg_id = sp.add_mock_playlist(
            name="「Alive」",
            playlist_id="agg_alive",
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
            ]
        )

        progress = FolderSortProgress()

        # Mark current contents as processed
        from automations.spotify.folder_sorter.action import _mark_aggregator_as_processed

        aggregators = {
            "Alive": sp.playlists[agg_id]
        }

        _mark_aggregator_as_processed(sp, aggregators, progress)

        # Both tracks should now be marked as processed
        assert progress.is_processed("spotify:track:1", "Alive")
        assert progress.is_processed("spotify:track:2", "Alive")


class TestProgressCLIOperations:
    """Test CLI operations for progress management."""

    def test_show_progress_empty(self, capsys):
        """Test showing progress when no tracks are processed."""
        progress = FolderSortProgress()

        from automations.spotify.folder_sorter.action import show_progress

        show_progress(progress)

        captured = capsys.readouterr()
        assert "No tracks" in captured.out or "empty" in captured.out.lower()

    def test_show_progress_with_data(self, capsys):
        """Test showing progress with processed tracks."""
        progress = FolderSortProgress()
        progress.mark_processed("spotify:track:1", "Alive")
        progress.mark_processed("spotify:track:2", "Alive")
        progress.mark_processed("spotify:track:3", "Electronic")

        from automations.spotify.folder_sorter.action import show_progress

        show_progress(progress)

        captured = capsys.readouterr()
        assert "Alive" in captured.out
        assert "Electronic" in captured.out
        assert "2" in captured.out  # 2 tracks in Alive


class TestCompleteProgressWorkflow:
    """Integration test for complete progress tracking workflow."""

    def test_rerun_sorting_preserves_manual_curation(self):
        """Test that rerunning sort doesn't re-add manually removed tracks."""
        env = setup_complete_test_environment()
        sp = env["sp"]

        # Initial run - add tracks to aggregators
        from automations.spotify.folder_sorter.action import (
            _build_folder_artist_index,
            _fetch_new_tracks_with_artists,
            _plan_additions_with_progress,
            _apply_additions_and_optionally_remove,
        )

        progress = FolderSortProgress()

        folder_artist_index = _build_folder_artist_index(
            env["folder_playlists"], env["playlist_loader_data"]
        )

        new_tracks = _fetch_new_tracks_with_artists(sp, env["new_playlist_id"])

        # First sort - no progress yet
        plan, track_to_folders = _plan_additions_with_progress(
            new_tracks, folder_artist_index, env["aggregators"], progress
        )

        added, removed = _apply_additions_and_optionally_remove(
            sp, plan, track_to_folders, keep_in_new=False, new_playlist_id=env["new_playlist_id"]
        )

        # User manually removes track_alive_1 from Alive aggregator (simulating manual curation)
        alive_agg_id = env["aggregators"]["Alive"]["id"]
        sp.playlist_remove_all_occurrences_of_items(alive_agg_id, ["spotify:track:track_alive_1"])

        # Mark current state as processed (user runs --mark-current-as-processed)
        from automations.spotify.folder_sorter.action import _mark_aggregator_as_processed
        _mark_aggregator_as_processed(sp, env["aggregators"], progress)

        # Put track_alive_1 back in New (simulating it being re-added or still there)
        sp.playlist_add_items(env["new_playlist_id"], ["spotify:track:track_alive_1"])

        # Second sort - should skip track_alive_1 for Alive (it's processed)
        new_tracks_2 = _fetch_new_tracks_with_artists(sp, env["new_playlist_id"])
        plan_2, track_to_folders_2 = _plan_additions_with_progress(
            new_tracks_2, folder_artist_index, env["aggregators"], progress
        )

        # track_alive_1 should NOT be in the plan for Alive aggregator
        alive_plan = plan_2.get(alive_agg_id, [])
        assert "spotify:track:track_alive_1" not in alive_plan

        # Verify it's still not in the aggregator after second run
        _apply_additions_and_optionally_remove(
            sp, plan_2, track_to_folders_2, keep_in_new=False, new_playlist_id=env["new_playlist_id"]
        )

        alive_agg_uris = sp.get_playlist_track_uris(alive_agg_id)
        assert "spotify:track:track_alive_1" not in alive_agg_uris


# Pytest fixtures

@pytest.fixture
def progress_file(tmp_path):
    """Fixture providing a temporary progress file path."""
    return tmp_path / "folder_sort_progress.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
