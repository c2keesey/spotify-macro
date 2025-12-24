"""
Test fixtures for folder sorter tests.

Provides mock data for testing folder sorting logic without API calls.
"""

from typing import Dict, List
from tests.mock_spotify_client import MockSpotifyClient


def create_mock_artists() -> Dict[str, Dict]:
    """Create mock artist data."""
    return {
        "artist_alive_1": {
            "id": "artist_alive_1",
            "name": "Alive Artist 1",
            "uri": "spotify:artist:artist_alive_1",
        },
        "artist_alive_2": {
            "id": "artist_alive_2",
            "name": "Alive Artist 2",
            "uri": "spotify:artist:artist_alive_2",
        },
        "artist_electronic_1": {
            "id": "artist_electronic_1",
            "name": "Electronic Artist 1",
            "uri": "spotify:artist:artist_electronic_1",
        },
        "artist_electronic_2": {
            "id": "artist_electronic_2",
            "name": "Electronic Artist 2",
            "uri": "spotify:artist:artist_electronic_2",
        },
        "artist_funk_1": {
            "id": "artist_funk_1",
            "name": "Funk Artist 1",
            "uri": "spotify:artist:artist_funk_1",
        },
        "artist_shared_1": {
            "id": "artist_shared_1",
            "name": "Shared Artist (in multiple folders)",
            "uri": "spotify:artist:artist_shared_1",
        },
        "artist_unknown_1": {
            "id": "artist_unknown_1",
            "name": "Unknown Artist",
            "uri": "spotify:artist:artist_unknown_1",
        },
    }


def create_mock_tracks(artists: Dict[str, Dict]) -> Dict[str, Dict]:
    """Create mock track data."""
    return {
        "track_alive_1": {
            "id": "track_alive_1",
            "name": "Alive Track 1",
            "uri": "spotify:track:track_alive_1",
            "artists": [artists["artist_alive_1"]],
            "is_local": False,
        },
        "track_alive_2": {
            "id": "track_alive_2",
            "name": "Alive Track 2",
            "uri": "spotify:track:track_alive_2",
            "artists": [artists["artist_alive_2"]],
            "is_local": False,
        },
        "track_electronic_1": {
            "id": "track_electronic_1",
            "name": "Electronic Track 1",
            "uri": "spotify:track:track_electronic_1",
            "artists": [artists["artist_electronic_1"]],
            "is_local": False,
        },
        "track_electronic_2": {
            "id": "track_electronic_2",
            "name": "Electronic Track 2",
            "uri": "spotify:track:track_electronic_2",
            "artists": [artists["artist_electronic_2"]],
            "is_local": False,
        },
        "track_funk_1": {
            "id": "track_funk_1",
            "name": "Funk Track 1",
            "uri": "spotify:track:track_funk_1",
            "artists": [artists["artist_funk_1"]],
            "is_local": False,
        },
        "track_multi_artist": {
            "id": "track_multi_artist",
            "name": "Multi Artist Track (Alive + Electronic)",
            "uri": "spotify:track:track_multi_artist",
            "artists": [artists["artist_alive_1"], artists["artist_electronic_1"]],
            "is_local": False,
        },
        "track_shared_artist": {
            "id": "track_shared_artist",
            "name": "Track with Shared Artist",
            "uri": "spotify:track:track_shared_artist",
            "artists": [artists["artist_shared_1"]],
            "is_local": False,
        },
        "track_unknown": {
            "id": "track_unknown",
            "name": "Unknown Track",
            "uri": "spotify:track:track_unknown",
            "artists": [artists["artist_unknown_1"]],
            "is_local": False,
        },
        "track_local": {
            "id": "track_local",
            "name": "Local Track (should be ignored)",
            "uri": "spotify:local:track_local",
            "artists": [artists["artist_alive_1"]],
            "is_local": True,
        },
    }


def setup_folder_playlists(sp: MockSpotifyClient, artists: Dict[str, Dict]) -> Dict[str, str]:
    """Set up folder playlists with tracks.

    Returns a mapping of folder name -> playlist ID
    """
    # Alive folder playlists
    alive_playlist_1 = sp.add_mock_playlist(
        name="Awaken",
        playlist_id="playlist_awaken",
        tracks=[
            {
                "id": "track_existing_alive_1",
                "name": "Existing Alive Track 1",
                "uri": "spotify:track:track_existing_alive_1",
                "artists": [artists["artist_alive_1"]],
                "is_local": False,
            },
        ]
    )

    alive_playlist_2 = sp.add_mock_playlist(
        name="Emergence",
        playlist_id="playlist_emergence",
        tracks=[
            {
                "id": "track_existing_alive_2",
                "name": "Existing Alive Track 2",
                "uri": "spotify:track:track_existing_alive_2",
                "artists": [artists["artist_alive_2"]],
                "is_local": False,
            },
        ]
    )

    # Electronic folder playlists
    electronic_playlist_1 = sp.add_mock_playlist(
        name="EDM Bangers",
        playlist_id="playlist_edm",
        tracks=[
            {
                "id": "track_existing_electronic_1",
                "name": "Existing Electronic Track 1",
                "uri": "spotify:track:track_existing_electronic_1",
                "artists": [artists["artist_electronic_1"]],
                "is_local": False,
            },
        ]
    )

    electronic_playlist_2 = sp.add_mock_playlist(
        name="Synth Wave",
        playlist_id="playlist_synth",
        tracks=[
            {
                "id": "track_existing_electronic_2",
                "name": "Existing Electronic Track 2",
                "uri": "spotify:track:track_existing_electronic_2",
                "artists": [artists["artist_electronic_2"]],
                "is_local": False,
            },
            # This playlist also has the shared artist
            {
                "id": "track_shared_in_electronic",
                "name": "Shared Track in Electronic",
                "uri": "spotify:track:track_shared_in_electronic",
                "artists": [artists["artist_shared_1"]],
                "is_local": False,
            },
        ]
    )

    # Funk Soul folder playlist
    funk_playlist_1 = sp.add_mock_playlist(
        name="Groovy Funk",
        playlist_id="playlist_funk",
        tracks=[
            {
                "id": "track_existing_funk_1",
                "name": "Existing Funk Track 1",
                "uri": "spotify:track:track_existing_funk_1",
                "artists": [artists["artist_funk_1"]],
                "is_local": False,
            },
            # This playlist also has the shared artist
            {
                "id": "track_shared_in_funk",
                "name": "Shared Track in Funk",
                "uri": "spotify:track:track_shared_in_funk",
                "artists": [artists["artist_shared_1"]],
                "is_local": False,
            },
        ]
    )

    return {
        "Alive": [alive_playlist_1, alive_playlist_2],
        "Electronic": [electronic_playlist_1, electronic_playlist_2],
        "Funk Soul": [funk_playlist_1],
    }


def setup_new_playlist(
    sp: MockSpotifyClient,
    tracks: Dict[str, Dict],
    track_keys: List[str] = None
) -> str:
    """Set up the "New" playlist with specified tracks.

    Args:
        sp: Mock Spotify client
        tracks: Dictionary of all available tracks
        track_keys: List of track keys to include (defaults to a standard set)

    Returns:
        The "New" playlist ID
    """
    if track_keys is None:
        track_keys = [
            "track_alive_1",
            "track_electronic_1",
            "track_funk_1",
            "track_multi_artist",
            "track_unknown",
            "track_local",  # Should be filtered out
        ]

    new_tracks = [tracks[key] for key in track_keys if key in tracks]

    return sp.add_mock_playlist(
        name="New",
        playlist_id="playlist_new",
        tracks=new_tracks
    )


def setup_aggregator_playlists(sp: MockSpotifyClient) -> Dict[str, Dict]:
    """Set up existing aggregator playlists.

    Returns a mapping of folder name -> aggregator playlist object
    """
    alive_id = sp.add_mock_playlist(
        name="「Alive」",
        playlist_id="aggregator_alive",
        tracks=[]
    )
    electronic_id = sp.add_mock_playlist(
        name="「Electronic」",
        playlist_id="aggregator_electronic",
        tracks=[]
    )

    return {
        "Alive": sp.playlists[alive_id],
        "Electronic": sp.playlists[electronic_id],
        # Funk Soul folder has no aggregator yet - will be created
    }


def create_playlist_folders_map() -> Dict[str, List[str]]:
    """Create a mock playlist_folders.json structure."""
    return {
        "Alive": [
            "Awaken.json",
            "Emergence.json",
        ],
        "Electronic": [
            "EDM Bangers.json",
            "Synth Wave.json",
        ],
        "Funk Soul": [
            "Groovy Funk.json",
        ],
    }


def create_mock_library_manifest(folder_playlists: Dict[str, List[str]]) -> Dict:
    """Create a mock library manifest.

    Args:
        folder_playlists: Mapping of folder -> list of playlist IDs

    Returns:
        Mock manifest structure
    """
    playlists = {}

    # Add all folder playlists to manifest
    for folder, playlist_ids in folder_playlists.items():
        for i, pid in enumerate(playlist_ids):
            # Get playlist name from ID (remove "playlist_" prefix)
            name = pid.replace("playlist_", "").replace("_", " ").title()
            playlists[pid] = {
                "name": name,
                "id": pid,
                "snapshot_id": f"snapshot_{pid}",
                "owner": {"id": "test_user"},
                "public": False,
            }

    return {
        "playlists": playlists,
        "last_updated": "2025-12-23T10:00:00",
    }


def create_mock_playlist_loader_data(
    folder_playlists: Dict[str, List[str]],
    artists: Dict[str, Dict]
) -> Dict[str, Dict]:
    """Create mock data for PlaylistDataLoader.

    Returns data in the format expected by PlaylistDataLoader.
    """
    data = {}

    # Map of playlist_id -> (name, artist_ids)
    playlist_info = {
        "playlist_awaken": ("Awaken", ["artist_alive_1"]),
        "playlist_emergence": ("Emergence", ["artist_alive_2"]),
        "playlist_edm": ("EDM Bangers", ["artist_electronic_1"]),
        "playlist_synth": ("Synth Wave", ["artist_electronic_2", "artist_shared_1"]),
        "playlist_funk": ("Groovy Funk", ["artist_funk_1", "artist_shared_1"]),
    }

    for playlist_id, (name, artist_ids_list) in playlist_info.items():
        tracks = []
        for i, artist_id in enumerate(artist_ids_list):
            tracks.append({
                "id": f"{playlist_id}_track_{i}",
                "name": f"Track {i} in {name}",
                "uri": f"spotify:track:{playlist_id}_track_{i}",
                "artists": [artists[artist_id]],
            })

        data[playlist_id] = {
            "name": name,
            "tracks": tracks,
        }

    return data


def setup_complete_test_environment(sp: MockSpotifyClient = None) -> Dict:
    """Set up a complete test environment with all fixtures.

    Returns:
        Dictionary containing all test fixtures and data
    """
    if sp is None:
        sp = MockSpotifyClient()

    artists = create_mock_artists()
    tracks = create_mock_tracks(artists)
    folder_playlists = setup_folder_playlists(sp, artists)
    new_playlist_id = setup_new_playlist(sp, tracks)
    aggregators = setup_aggregator_playlists(sp)
    folders_map = create_playlist_folders_map()
    manifest = create_mock_library_manifest(folder_playlists)
    playlist_loader_data = create_mock_playlist_loader_data(folder_playlists, artists)

    return {
        "sp": sp,
        "artists": artists,
        "tracks": tracks,
        "folder_playlists": folder_playlists,
        "new_playlist_id": new_playlist_id,
        "aggregators": aggregators,
        "folders_map": folders_map,
        "manifest": manifest,
        "playlist_loader_data": playlist_loader_data,
    }
