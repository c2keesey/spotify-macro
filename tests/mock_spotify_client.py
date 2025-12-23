"""
Mock Spotify client for testing without making real API calls.

Simulates the spotipy API interface but operates on in-memory data structures.
"""

from typing import Dict, List, Optional, Any
from copy import deepcopy
import uuid


class MockSpotifyClient:
    """Mock Spotify client that simulates API operations in-memory."""

    def __init__(self, user_id: str = "test_user"):
        """Initialize mock client with in-memory state.

        Args:
            user_id: The user ID to use for current_user() calls
        """
        self.user_id = user_id
        self.playlists: Dict[str, Dict] = {}  # playlist_id -> playlist object
        self.playlist_tracks: Dict[str, List[Dict]] = {}  # playlist_id -> list of track URIs
        self.tracks: Dict[str, Dict] = {}  # track_id -> track object
        self.artists: Dict[str, Dict] = {}  # artist_id -> artist object

        # Track API call counts for testing
        self.api_calls = {
            "current_user": 0,
            "user_playlists": 0,
            "playlist_items": 0,
            "playlist_add_items": 0,
            "playlist_remove_all_occurrences_of_items": 0,
            "user_playlist_create": 0,
        }

    def current_user(self) -> Dict:
        """Return mock current user."""
        self.api_calls["current_user"] += 1
        return {
            "id": self.user_id,
            "display_name": "Test User",
            "uri": f"spotify:user:{self.user_id}",
        }

    def user_playlists(
        self,
        user: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """Return paginated list of user's playlists."""
        self.api_calls["user_playlists"] += 1

        all_playlists = list(self.playlists.values())
        page = all_playlists[offset:offset + limit]

        return {
            "items": page,
            "total": len(all_playlists),
            "limit": limit,
            "offset": offset,
            "next": f"next_url?offset={offset + limit}" if offset + limit < len(all_playlists) else None,
        }

    def playlist_items(
        self,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        additional_types: tuple = ("track",)
    ) -> Dict:
        """Return paginated list of playlist tracks."""
        self.api_calls["playlist_items"] += 1

        if playlist_id not in self.playlist_tracks:
            return {"items": [], "total": 0, "limit": limit, "offset": offset, "next": None}

        all_items = self.playlist_tracks[playlist_id]
        page = all_items[offset:offset + limit]

        return {
            "items": page,
            "total": len(all_items),
            "limit": limit,
            "offset": offset,
            "next": f"next_url?offset={offset + limit}" if offset + limit < len(all_items) else None,
        }

    def playlist_add_items(
        self,
        playlist_id: str,
        items: List[str],
        position: Optional[int] = None
    ) -> Dict:
        """Add tracks to a playlist."""
        self.api_calls["playlist_add_items"] += 1

        if playlist_id not in self.playlist_tracks:
            self.playlist_tracks[playlist_id] = []

        # Convert URIs to item format if needed
        new_items = []
        for item in items:
            if isinstance(item, str):
                # URI string - convert to item format
                new_items.append({
                    "track": {
                        "uri": item,
                        "id": item.replace("spotify:track:", ""),
                        "is_local": False,
                    }
                })
            else:
                new_items.append(item)

        if position is not None:
            self.playlist_tracks[playlist_id][position:position] = new_items
        else:
            self.playlist_tracks[playlist_id].extend(new_items)

        # Update snapshot_id to simulate change
        if playlist_id in self.playlists:
            self.playlists[playlist_id]["snapshot_id"] = str(uuid.uuid4())

        return {"snapshot_id": self.playlists[playlist_id]["snapshot_id"]}

    def playlist_remove_all_occurrences_of_items(
        self,
        playlist_id: str,
        items: List[str]
    ) -> Dict:
        """Remove all occurrences of tracks from a playlist."""
        self.api_calls["playlist_remove_all_occurrences_of_items"] += 1

        if playlist_id not in self.playlist_tracks:
            return {"snapshot_id": ""}

        # Convert items to URIs if needed
        uris_to_remove = set()
        for item in items:
            if isinstance(item, str):
                uris_to_remove.add(item)
            elif isinstance(item, dict) and "uri" in item:
                uris_to_remove.add(item["uri"])

        # Remove all occurrences
        original_tracks = self.playlist_tracks[playlist_id]
        self.playlist_tracks[playlist_id] = [
            item for item in original_tracks
            if item.get("track", {}).get("uri") not in uris_to_remove
        ]

        # Update snapshot_id
        if playlist_id in self.playlists:
            self.playlists[playlist_id]["snapshot_id"] = str(uuid.uuid4())

        return {"snapshot_id": self.playlists[playlist_id]["snapshot_id"]}

    def user_playlist_create(
        self,
        user: str,
        name: str,
        public: bool = True,
        collaborative: bool = False,
        description: str = ""
    ) -> Dict:
        """Create a new playlist."""
        self.api_calls["user_playlist_create"] += 1

        playlist_id = f"test_playlist_{len(self.playlists)}"
        playlist = {
            "id": playlist_id,
            "name": name,
            "uri": f"spotify:playlist:{playlist_id}",
            "snapshot_id": str(uuid.uuid4()),
            "owner": {"id": user},
            "public": public,
            "collaborative": collaborative,
            "description": description,
            "tracks": {"total": 0},
        }

        self.playlists[playlist_id] = playlist
        self.playlist_tracks[playlist_id] = []

        return playlist

    # Helper methods for test setup

    def add_mock_playlist(
        self,
        name: str,
        playlist_id: Optional[str] = None,
        tracks: Optional[List[Dict]] = None
    ) -> str:
        """Add a mock playlist to the client.

        Args:
            name: Playlist name
            playlist_id: Optional playlist ID (auto-generated if not provided)
            tracks: Optional list of track objects

        Returns:
            The playlist ID
        """
        if playlist_id is None:
            playlist_id = f"mock_{name.lower().replace(' ', '_')}"

        playlist = {
            "id": playlist_id,
            "name": name,
            "uri": f"spotify:playlist:{playlist_id}",
            "snapshot_id": str(uuid.uuid4()),
            "owner": {"id": self.user_id},
            "public": False,
            "collaborative": False,
            "description": "",
            "tracks": {"total": len(tracks) if tracks else 0},
        }

        self.playlists[playlist_id] = playlist

        if tracks:
            self.playlist_tracks[playlist_id] = [
                {"track": track} for track in tracks
            ]
        else:
            self.playlist_tracks[playlist_id] = []

        return playlist_id

    def add_mock_track(
        self,
        track_id: str,
        name: str,
        artists: List[Dict],
        uri: Optional[str] = None
    ) -> Dict:
        """Add a mock track to the client.

        Args:
            track_id: Track ID
            name: Track name
            artists: List of artist objects (must include 'id' and 'name')
            uri: Optional track URI (auto-generated if not provided)

        Returns:
            The track object
        """
        if uri is None:
            uri = f"spotify:track:{track_id}"

        track = {
            "id": track_id,
            "name": name,
            "uri": uri,
            "artists": artists,
            "is_local": False,
        }

        self.tracks[track_id] = track
        return track

    def get_playlist_track_uris(self, playlist_id: str) -> List[str]:
        """Helper to get all track URIs in a playlist."""
        if playlist_id not in self.playlist_tracks:
            return []

        return [
            item.get("track", {}).get("uri")
            for item in self.playlist_tracks[playlist_id]
            if item.get("track", {}).get("uri")
        ]

    def reset_api_call_counts(self):
        """Reset all API call counters."""
        for key in self.api_calls:
            self.api_calls[key] = 0


def create_mock_spotify_client(user_id: str = "test_user") -> MockSpotifyClient:
    """Factory function to create a mock Spotify client.

    Args:
        user_id: The user ID to use for the mock client

    Returns:
        A configured MockSpotifyClient instance
    """
    return MockSpotifyClient(user_id=user_id)
