"""
Basic tests to verify the test infrastructure works.

Run with: uv run pytest tests/test_infrastructure.py -v
"""

import pytest


class TestMockSpotifyClient:
    """Tests for MockSpotifyClient."""

    def test_create_mock_client(self, mock_spotify):
        """Verify mock client can be created."""
        assert mock_spotify is not None
        assert hasattr(mock_spotify, 'me')
        assert hasattr(mock_spotify, 'current_user_playlists')

    def test_mock_me(self, mock_spotify):
        """Verify me() returns user data."""
        user = mock_spotify.me()
        assert user['id'] == 'test_user'
        assert mock_spotify.assert_called('me')

    def test_mock_playlists(self, mock_spotify):
        """Verify playlist methods work."""
        result = mock_spotify.current_user_playlists()
        assert 'items' in result
        assert 'total' in result

    def test_mock_add_tracks(self, mock_spotify):
        """Verify adding tracks is tracked."""
        mock_spotify.load_playlist('pl_001', {
            'id': 'pl_001',
            'name': 'Test',
            'tracks': {'items': []},
            'owner': {'id': 'test_user'}
        })

        result = mock_spotify.playlist_add_items(
            'pl_001',
            ['spotify:track:abc123']
        )
        assert 'snapshot_id' in result
        assert mock_spotify.assert_called('playlist_add_items', playlist_id='pl_001')


class TestTestDataManager:
    """Tests for TestDataManager utilities."""

    def test_get_test_playlist(self):
        """Verify synthetic playlist generation."""
        from tests.test_data_utils import TestDataManager

        playlist = TestDataManager.get_test_playlist(name='My Test', track_count=10)
        assert playlist['name'] == 'My Test'
        assert len(playlist['tracks']) == 10
        assert playlist['total_tracks'] == 10

    def test_get_test_playlists_dict(self):
        """Verify multiple playlists generation."""
        from tests.test_data_utils import TestDataManager

        playlists = TestDataManager.get_test_playlists_dict(count=5, tracks_per_playlist=3)
        assert len(playlists) == 5
        for playlist_id, playlist in playlists.items():
            assert len(playlist['tracks']) == 3

    def test_minimal_fixtures(self):
        """Verify fallback fixtures work."""
        from tests.test_data_utils import TestDataManager

        fixtures = TestDataManager._get_minimal_fixtures()
        assert len(fixtures) >= 1
        for playlist_id, playlist in fixtures.items():
            assert 'name' in playlist
            assert 'tracks' in playlist


class TestSampleFixtures:
    """Tests using pytest fixtures."""

    def test_sample_track_fixture(self, sample_track):
        """Verify sample_track fixture."""
        assert sample_track['id'] == 'test_track_001'
        assert len(sample_track['artists']) == 1

    def test_sample_playlist_fixture(self, sample_playlist):
        """Verify sample_playlist fixture."""
        assert sample_playlist['name'] == 'Test Playlist'
        assert sample_playlist['tracks']['total'] == 2

    def test_sample_playlists_dict_fixture(self, sample_playlists_dict):
        """Verify sample_playlists_dict fixture."""
        assert len(sample_playlists_dict) == 3
        assert 'Electronic' in [p['name'] for p in sample_playlists_dict.values()]
