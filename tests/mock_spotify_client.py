"""
Mock Spotify client for testing without API calls.

Provides a mock implementation of the Spotipy client that:
- Returns data from local JSON files
- Tracks method calls for assertions
- Simulates common API behaviors
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock


class MockSpotifyClient:
    """
    Mock Spotify client that uses local data instead of API calls.

    Supports loading data from:
    - Local playlist JSON files
    - In-memory test data
    - Fixture files
    """

    def __init__(self):
        self.playlists: Dict[str, Dict] = {}
        self.tracks: Dict[str, Dict] = {}
        self.artists: Dict[str, Dict] = {}
        self.user_data: Dict = {"id": "test_user", "display_name": "Test User"}

        # Track API calls for assertions
        self.call_log: List[Dict] = []

        # Simulate rate limiting behavior
        self.rate_limit_after: Optional[int] = None
        self.call_count = 0

    def _log_call(self, method: str, **kwargs):
        """Log a method call for later assertions."""
        self.call_log.append({"method": method, "args": kwargs})
        self.call_count += 1

    def load_playlists_from_directory(self, data_dir: Path):
        """Load playlist data from local JSON files."""
        manifest_path = data_dir.parent / "manifest.json"

        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            for playlist_id, meta in manifest.get("playlists", {}).items():
                playlist_file = data_dir / f"{playlist_id}.json"
                if playlist_file.exists():
                    with open(playlist_file, "r", encoding="utf-8") as f:
                        playlist_data = json.load(f)
                    self.playlists[playlist_id] = {
                        "id": playlist_id,
                        "name": playlist_data.get("playlist_name", meta.get("name", playlist_id)),
                        "tracks": {"items": playlist_data.get("tracks", [])},
                        "owner": {"id": "test_user"}
                    }

    def load_playlist(self, playlist_id: str, data: Dict):
        """Load a single playlist from test data."""
        self.playlists[playlist_id] = data

    def load_track(self, track_id: str, data: Dict):
        """Load a single track for testing."""
        self.tracks[track_id] = data

    def load_artist(self, artist_id: str, data: Dict):
        """Load a single artist for testing."""
        self.artists[artist_id] = data

    # Spotipy API method mocks

    def me(self) -> Dict:
        """Get current user profile."""
        self._log_call("me")
        return self.user_data

    def current_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get current user's playlists."""
        self._log_call("current_user_playlists", limit=limit, offset=offset)
        playlist_list = list(self.playlists.values())
        return {
            "items": playlist_list[offset:offset + limit],
            "total": len(playlist_list),
            "limit": limit,
            "offset": offset,
            "next": None if offset + limit >= len(playlist_list) else "next_url"
        }

    def playlist(self, playlist_id: str, fields: Optional[str] = None) -> Dict:
        """Get a playlist by ID."""
        self._log_call("playlist", playlist_id=playlist_id, fields=fields)
        return self.playlists.get(playlist_id, {})

    def playlist_tracks(
        self,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None
    ) -> Dict:
        """Get tracks from a playlist."""
        self._log_call("playlist_tracks", playlist_id=playlist_id, limit=limit, offset=offset)

        playlist = self.playlists.get(playlist_id, {})
        tracks = playlist.get("tracks", {}).get("items", [])

        return {
            "items": tracks[offset:offset + limit],
            "total": len(tracks),
            "limit": limit,
            "offset": offset,
            "next": None if offset + limit >= len(tracks) else "next_url"
        }

    def playlist_add_items(
        self,
        playlist_id: str,
        items: List[str],
        position: Optional[int] = None
    ) -> Dict:
        """Add tracks to a playlist."""
        self._log_call("playlist_add_items", playlist_id=playlist_id, items=items, position=position)

        # Simulate adding tracks
        if playlist_id in self.playlists:
            current_items = self.playlists[playlist_id].get("tracks", {}).get("items", [])
            new_items = [{"track": {"id": uri.split(":")[-1]}} for uri in items]

            if position is not None:
                current_items[position:position] = new_items
            else:
                current_items.extend(new_items)

        return {"snapshot_id": f"snapshot_{len(items)}"}

    def playlist_remove_all_occurrences_of_items(
        self,
        playlist_id: str,
        items: List[str]
    ) -> Dict:
        """Remove tracks from a playlist."""
        self._log_call("playlist_remove_all_occurrences_of_items", playlist_id=playlist_id, items=items)
        return {"snapshot_id": "snapshot_remove"}

    def track(self, track_id: str) -> Dict:
        """Get a track by ID."""
        self._log_call("track", track_id=track_id)
        return self.tracks.get(track_id, {"id": track_id, "name": f"Track {track_id}"})

    def tracks(self, track_ids: List[str]) -> Dict:
        """Get multiple tracks by ID."""
        self._log_call("tracks", track_ids=track_ids)
        return {
            "tracks": [self.tracks.get(tid, {"id": tid, "name": f"Track {tid}"}) for tid in track_ids]
        }

    def artist(self, artist_id: str) -> Dict:
        """Get an artist by ID."""
        self._log_call("artist", artist_id=artist_id)
        return self.artists.get(artist_id, {
            "id": artist_id,
            "name": f"Artist {artist_id}",
            "genres": []
        })

    def artists(self, artist_ids: List[str]) -> Dict:
        """Get multiple artists by ID."""
        self._log_call("artists", artist_ids=artist_ids)
        return {
            "artists": [
                self.artists.get(aid, {"id": aid, "name": f"Artist {aid}", "genres": []})
                for aid in artist_ids
            ]
        }

    def current_user_saved_tracks(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get user's saved/liked tracks."""
        self._log_call("current_user_saved_tracks", limit=limit, offset=offset)
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "next": None}

    def current_user_saved_tracks_add(self, tracks: List[str]) -> None:
        """Save tracks to user's library."""
        self._log_call("current_user_saved_tracks_add", tracks=tracks)

    def current_user_saved_tracks_delete(self, tracks: List[str]) -> None:
        """Remove tracks from user's library."""
        self._log_call("current_user_saved_tracks_delete", tracks=tracks)

    def current_playback(self) -> Optional[Dict]:
        """Get current playback state."""
        self._log_call("current_playback")
        return None

    def search(
        self,
        q: str,
        limit: int = 10,
        offset: int = 0,
        type: str = "track"
    ) -> Dict:
        """Search for items."""
        self._log_call("search", q=q, limit=limit, offset=offset, type=type)
        return {
            "tracks": {"items": [], "total": 0},
            "artists": {"items": [], "total": 0},
            "albums": {"items": [], "total": 0},
            "playlists": {"items": [], "total": 0}
        }

    # Assertion helpers

    def assert_called(self, method: str, **expected_kwargs) -> bool:
        """Assert a method was called with specific arguments."""
        for call in self.call_log:
            if call["method"] == method:
                if not expected_kwargs:
                    return True
                if all(call["args"].get(k) == v for k, v in expected_kwargs.items()):
                    return True
        return False

    def get_calls(self, method: str) -> List[Dict]:
        """Get all calls to a specific method."""
        return [c for c in self.call_log if c["method"] == method]

    def reset_calls(self):
        """Reset the call log."""
        self.call_log = []
        self.call_count = 0


def create_mock_spotify_client() -> MockSpotifyClient:
    """Factory function to create a configured mock client."""
    return MockSpotifyClient()
