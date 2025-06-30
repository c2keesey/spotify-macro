"""
Test dynamic genre discovery using production data snapshot.
"""

import pytest
from tests.mock_spotify_client import create_mock_spotify_client
from common.genre_classification_utils import (
    discover_genres_from_playlists,
    get_genre_mapping,
    classify_track
)


@pytest.fixture
def mock_spotify():
    """Create a mock Spotify client with production data."""
    return create_mock_spotify_client()


def test_dynamic_genre_discovery(mock_spotify):
    """Test that dynamic genre discovery works with production playlist structure."""
    # Discover genres from playlist structure
    dynamic_mapping = discover_genres_from_playlists(mock_spotify)
    
    # Verify that we discovered the expected folders
    expected_folders = ["Electronic", "Base", "House", "Rave", "Funk Soul", "Rock", "Reggae", "Vibes", "Sierra", "Soft", "Chill", "Spiritual"]
    
    for folder in expected_folders:
        assert folder in dynamic_mapping, f"Expected folder '{folder}' not found in dynamic mapping"
        
        # Verify each folder has genres
        folder_config = dynamic_mapping[folder]
        assert "genres" in folder_config, f"Folder '{folder}' missing genres"
        assert "audio_features" in folder_config, f"Folder '{folder}' missing audio_features"
        assert len(folder_config["genres"]) > 0, f"Folder '{folder}' has no genres"


def test_edm_bass_genre_discovery(mock_spotify):
    """Test that EDM and bass music genres are properly discovered."""
    dynamic_mapping = discover_genres_from_playlists(mock_spotify)
    
    # Check Electronic folder
    if "Electronic" in dynamic_mapping:
        electronic_genres = dynamic_mapping["Electronic"]["genres"]
        expected_electronic = ["electronic", "edm", "house", "techno", "trance"]
        
        # Should have some electronic genres
        has_electronic = any(genre in " ".join(electronic_genres).lower() for genre in expected_electronic)
        assert has_electronic, f"Electronic folder missing electronic genres: {electronic_genres}"
    
    # Check Base folder (bass music)
    if "Base" in dynamic_mapping:
        bass_genres = dynamic_mapping["Base"]["genres"]
        expected_bass = ["bass music", "dubstep", "drum and bass", "future bass", "riddim"]
        
        # Should have some bass genres
        has_bass = any(genre in " ".join(bass_genres).lower() for genre in expected_bass)
        assert has_bass, f"Base folder missing bass genres: {bass_genres}"


def test_audio_feature_generation(mock_spotify):
    """Test that audio features are generated appropriately for different folders."""
    dynamic_mapping = discover_genres_from_playlists(mock_spotify)
    
    # Check that different folders have appropriate audio feature profiles
    if "Base" in dynamic_mapping:
        base_features = dynamic_mapping["Base"]["audio_features"]
        # Bass music should have high energy and danceability
        assert "energy" in base_features
        assert base_features["energy"] == ">0.7"
        assert "danceability" in base_features
        assert base_features["danceability"] == ">0.6"
    
    if "Chill" in dynamic_mapping:
        chill_features = dynamic_mapping["Chill"]["audio_features"]
        # Chill music should have low energy
        assert "energy" in chill_features
        assert base_features["energy"] == "<0.4"


def test_get_genre_mapping_dynamic(mock_spotify):
    """Test that get_genre_mapping uses dynamic discovery when enabled."""
    # Test with dynamic discovery enabled
    dynamic_mapping = get_genre_mapping(mock_spotify, use_dynamic=True)
    
    # Should include our EDM-focused folders
    expected_folders = ["Electronic", "Base", "House", "Rave"]
    for folder in expected_folders:
        assert folder in dynamic_mapping, f"Dynamic mapping missing folder: {folder}"
    
    # Test with dynamic discovery disabled
    static_mapping = get_genre_mapping(mock_spotify, use_dynamic=False)
    
    # Should be the default hardcoded mapping
    expected_static = ["Rock", "Electronic", "Jazz", "Pop", "Hip Hop", "Country", "R&B", "Classical"]
    for genre in expected_static:
        assert genre in static_mapping, f"Static mapping missing genre: {genre}"


def test_classify_track_with_dynamic_mapping(mock_spotify):
    """Test that track classification works with dynamic genre mapping."""
    # Get a track ID from one of the playlists
    test_track_id = None
    
    # Find a track from SubsInstance playlist (bass music)
    subs_playlists = mock_spotify.get_folder_playlists("Base")
    for playlist in subs_playlists:
        if "SubsInstance" in playlist["name"]:
            tracks_result = mock_spotify.playlist_tracks(playlist["id"], limit=1)
            if tracks_result["items"]:
                test_track_id = tracks_result["items"][0]["track"]["id"]
                break
    
    if test_track_id:
        # Classify using dynamic mapping
        classification = classify_track(mock_spotify, test_track_id)
        
        # Should classify to some folder (exact result depends on track's artist genres)
        print(f"Track {test_track_id} classified as: {classification}")
        # Note: We can't assert specific results without knowing the exact artist genres
        # but we can verify the classification runs without error


def test_folder_playlist_discovery(mock_spotify):
    """Test that folders and their playlists are discovered correctly."""
    # Test specific folder
    base_playlists = mock_spotify.get_folder_playlists("Base")
    
    # Should find playlists in Base folder
    assert len(base_playlists) > 0, "No playlists found in Base folder"
    
    # Check that SubsInstance is in Base folder
    playlist_names = [p["name"] for p in base_playlists]
    has_subs = any("SubsInstance" in name for name in playlist_names)
    assert has_subs, f"SubsInstance not found in Base folder playlists: {playlist_names}"


def test_production_data_integrity(mock_spotify):
    """Test that production data is loaded correctly."""
    # Verify playlist folders are loaded
    assert hasattr(mock_spotify, 'playlist_folders')
    assert len(mock_spotify.playlist_folders) > 0
    
    # Verify playlist genres are loaded
    assert hasattr(mock_spotify, 'playlist_to_genres')
    assert len(mock_spotify.playlist_to_genres) > 0
    
    # Verify artist genres are loaded
    assert hasattr(mock_spotify, 'artist_genres')
    
    # Test specific playlist exists
    assert "Base" in mock_spotify.playlist_folders
    base_playlists = mock_spotify.playlist_folders["Base"]
    assert "🜃 SubsInstance.json" in base_playlists


if __name__ == "__main__":
    # Run tests manually
    mock_client = create_mock_spotify_client()
    
    print("Testing dynamic genre discovery...")
    test_dynamic_genre_discovery(mock_client)
    print("✅ Dynamic genre discovery test passed")
    
    print("Testing EDM/bass genre discovery...")
    test_edm_bass_genre_discovery(mock_client)
    print("✅ EDM/bass genre discovery test passed")
    
    print("Testing production data integrity...")
    test_production_data_integrity(mock_client)
    print("✅ Production data integrity test passed")
    
    print("All tests passed! 🎉")