"""
Genre classification utilities for automatic playlist sorting.

Implements hybrid classification using artist genres and audio features
to automatically categorize songs into genre-specific playlists.
"""

import os
import json
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

from common.spotify_utils import spotify_api_call_with_retry
from common.config import get_config_value, SPOTIFY_ENV
from common.genre_cache import (
    load_cached_genre_mapping,
    save_genre_mapping_cache,
    is_cache_expired
)


# Default genre to folder mapping configuration
DEFAULT_GENRE_MAPPING = {
    "Rock": {
        "genres": ["rock", "metal", "punk", "alternative", "grunge", "indie rock", "hard rock", "classic rock"],
        "audio_features": {"energy": ">0.6", "acousticness": "<0.4"}
    },
    "Electronic": {
        "genres": ["electronic", "edm", "house", "techno", "ambient", "dubstep", "drum and bass", "trance"],
        "audio_features": {"danceability": ">0.5", "instrumentalness": ">0.3"}
    },
    "Jazz": {
        "genres": ["jazz", "blues", "swing", "bebop", "smooth jazz", "fusion"],
        "audio_features": {"acousticness": ">0.4", "instrumentalness": ">0.2"}
    },
    "Pop": {
        "genres": ["pop", "dance pop", "electropop", "synth-pop", "indie pop"],
        "audio_features": {"danceability": ">0.6", "valence": ">0.5"}
    },
    "Hip Hop": {
        "genres": ["hip hop", "rap", "trap", "drill", "gangsta rap", "conscious hip hop"],
        "audio_features": {"speechiness": ">0.3", "energy": ">0.5"}
    },
    "Country": {
        "genres": ["country", "americana", "bluegrass", "folk", "singer-songwriter"],
        "audio_features": {"acousticness": ">0.5", "valence": ">0.4"}
    },
    "R&B": {
        "genres": ["r&b", "soul", "funk", "neo soul", "contemporary r&b"],
        "audio_features": {"danceability": ">0.5", "energy": ">0.4"}
    },
    "Classical": {
        "genres": ["classical", "orchestral", "opera", "baroque", "romantic"],
        "audio_features": {"acousticness": ">0.7", "instrumentalness": ">0.8"}
    }
}


def get_safe_spotify_client():
    """
    Get a safe Spotify client - prefer mock client in test environment.
    
    Returns:
        Mock client if in test environment and _data exists, otherwise None
    """
    if SPOTIFY_ENV == "test":
        try:
            from tests.mock_spotify_client import create_mock_spotify_client
            from pathlib import Path
            
            # Check if _data directory exists
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "_data"
            
            if data_dir.exists():
                print("🧪 Using mock Spotify client with production data snapshot")
                return create_mock_spotify_client()
        except ImportError:
            pass
    
    return None


def get_genre_mapping(sp=None, use_dynamic: bool = True, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Get genre mapping configuration from cache, environment, playlist analysis, or defaults.
    
    Args:
        sp: Spotify client (optional, for dynamic discovery)
        use_dynamic: Whether to use dynamic playlist-based genre discovery
        force_refresh: Whether to force refresh the cache
    
    Returns:
        Dictionary mapping folder names to genre configuration
    """
    # Try to load from environment variable or config file first
    custom_mapping = get_config_value("GENRE_MAPPING", None)
    
    if custom_mapping:
        try:
            if isinstance(custom_mapping, str):
                return json.loads(custom_mapping)
            return custom_mapping
        except (json.JSONDecodeError, TypeError):
            print("Warning: Invalid GENRE_MAPPING configuration, using defaults")
    
    # Try dynamic discovery if enabled 
    if use_dynamic:
        # Use provided client or try to get a safe one
        client = sp or get_safe_spotify_client()
        
        if client is not None:
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_mapping = load_cached_genre_mapping()
                if cached_mapping:
                    return cached_mapping
            
            # Cache miss or expired - do discovery
            try:
                print("Discovering genre mapping from playlists...")
                dynamic_mapping = discover_genres_from_playlists(client)
                if dynamic_mapping:
                    # Save to cache for future use
                    save_genre_mapping_cache(dynamic_mapping)
                    return dynamic_mapping
            except Exception as e:
                print(f"Warning: Dynamic genre discovery failed: {e}, using defaults")
    
    return DEFAULT_GENRE_MAPPING


def get_default_genre_mapping() -> Dict[str, Dict[str, Any]]:
    """
    Get genre mapping using safe defaults - automatically uses mock client in test environment.
    
    Returns:
        Genre mapping dictionary
    """
    return get_genre_mapping()


def get_artist_genres(sp, track_id: str) -> List[str]:
    """
    Get genres for a track based on its artists.
    
    Args:
        sp: Spotify client
        track_id: Spotify track ID
        
    Returns:
        List of genre strings from the track's artists
    """
    try:
        # Get track details
        track = spotify_api_call_with_retry(sp.track, track_id)
        if not track or not track.get('artists'):
            return []
        
        all_genres = []
        
        # Get genres from all artists
        for artist in track['artists']:
            artist_id = artist.get('id')
            if not artist_id:
                continue
                
            artist_details = spotify_api_call_with_retry(sp.artist, artist_id)
            if artist_details and artist_details.get('genres'):
                all_genres.extend(artist_details['genres'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_genres = []
        for genre in all_genres:
            if genre.lower() not in seen:
                seen.add(genre.lower())
                unique_genres.append(genre.lower())
        
        return unique_genres
        
    except Exception as e:
        print(f"Error getting artist genres for track {track_id}: {e}")
        return []


def get_audio_features(sp, track_id: str) -> Optional[Dict[str, float]]:
    """
    Get audio features for a track.
    
    Args:
        sp: Spotify client
        track_id: Spotify track ID
        
    Returns:
        Dictionary of audio features or None if not available
    """
    try:
        features = spotify_api_call_with_retry(sp.audio_features, [track_id])
        if features and features[0]:
            return features[0]
        return None
    except Exception as e:
        print(f"Error getting audio features for track {track_id}: {e}")
        return None


def classify_by_genres(genres: List[str], genre_mapping: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Classify a track based on its genres.
    
    Args:
        genres: List of genre strings from the track
        genre_mapping: Genre to folder mapping configuration
        
    Returns:
        List of matching folder names
    """
    matches = []
    
    for folder_name, config in genre_mapping.items():
        folder_genres = [g.lower() for g in config.get('genres', [])]
        
        # Check if any track genre matches any folder genre
        for track_genre in genres:
            for folder_genre in folder_genres:
                if folder_genre in track_genre or track_genre in folder_genre:
                    matches.append(folder_name)
                    break
            if folder_name in matches:
                break
    
    return matches


def evaluate_audio_feature_condition(value: float, condition: str) -> bool:
    """
    Evaluate an audio feature condition.
    
    Args:
        value: The actual feature value
        condition: Condition string like ">0.6" or "<0.4"
        
    Returns:
        True if condition is met, False otherwise
    """
    try:
        if condition.startswith('>'):
            threshold = float(condition[1:])
            return value > threshold
        elif condition.startswith('<'):
            threshold = float(condition[1:])
            return value < threshold
        elif condition.startswith('>='):
            threshold = float(condition[2:])
            return value >= threshold
        elif condition.startswith('<='):
            threshold = float(condition[2:])
            return value <= threshold
        elif condition.startswith('='):
            threshold = float(condition[1:])
            return abs(value - threshold) < 0.1  # Allow small tolerance
        else:
            # Try direct comparison
            threshold = float(condition)
            return abs(value - threshold) < 0.1
    except (ValueError, TypeError):
        return False


def classify_by_audio_features(audio_features: Dict[str, float], genre_mapping: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Classify a track based on its audio features.
    
    Args:
        audio_features: Dictionary of audio features
        genre_mapping: Genre to folder mapping configuration
        
    Returns:
        List of matching folder names
    """
    matches = []
    
    for folder_name, config in genre_mapping.items():
        feature_conditions = config.get('audio_features', {})
        
        if not feature_conditions:
            continue
        
        # Check if all conditions are met
        all_conditions_met = True
        conditions_checked = 0
        
        for feature_name, condition in feature_conditions.items():
            if feature_name in audio_features:
                conditions_checked += 1
                feature_value = audio_features[feature_name]
                if not evaluate_audio_feature_condition(feature_value, condition):
                    all_conditions_met = False
                    break
        
        # Only add if we checked at least one condition and all were met
        if conditions_checked > 0 and all_conditions_met:
            matches.append(folder_name)
    
    return matches


def classify_track(sp=None, track_id: str = None, genre_mapping: Optional[Dict[str, Dict[str, Any]]] = None) -> List[str]:
    """
    Classify a track using artist genres only (audio features removed for better accuracy).
    
    Args:
        sp: Spotify client (optional - will use safe client if None)
        track_id: Spotify track ID (required)
        genre_mapping: Optional custom genre mapping, uses default if None
        
    Returns:
        List of folder names the track should be classified into
    """
    if track_id is None:
        raise ValueError("track_id is required")
    
    # Use provided client or get a safe one
    client = sp or get_safe_spotify_client()
    if client is None:
        print("Warning: No Spotify client available, cannot classify track")
        return []
    
    if genre_mapping is None:
        genre_mapping = get_genre_mapping(client, use_dynamic=True)
    
    # Use only artist genres for classification
    artist_genres = get_artist_genres(client, track_id)
    if artist_genres:
        genre_matches = classify_by_genres(artist_genres, genre_mapping)
        return genre_matches
    
    # No classification found
    return []


def get_genre_playlists(sp, folder_name: str) -> List[Dict[str, str]]:
    """
    Find all playlists that belong to a specific genre folder.
    
    Args:
        sp: Spotify client
        folder_name: Name of the genre folder (e.g., "Rock")
        
    Returns:
        List of playlist dictionaries with 'id' and 'name' keys
    """
    # Try mock client method first
    if hasattr(sp, 'get_folder_playlists'):
        return sp.get_folder_playlists(folder_name)
    
    # Fall back to API scanning
    try:
        playlists = []
        offset = 0
        limit = 50
        
        while True:
            results = spotify_api_call_with_retry(
                sp.current_user_playlists, limit=limit, offset=offset
            )
            
            if not results or not results.get('items'):
                break
            
            for playlist in results['items']:
                playlist_name = playlist.get('name', '')
                
                # Check if playlist belongs to this folder
                if f'[{folder_name}]' in playlist_name:
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist_name
                    })
            
            # Check if there are more playlists
            if not results.get('next'):
                break
            
            offset += limit
        
        return playlists
        
    except Exception as e:
        print(f"Error getting genre playlists for {folder_name}: {e}")
        return []


def find_best_target_playlist(sp, folder_name: str, track_id: str) -> Optional[str]:
    """
    Find the best target playlist for a track within a genre folder.
    
    Strategy:
    1. Look for playlists with flow characters (prefer child playlists)
    2. Look for "Collection" or "Daily" playlists as good defaults
    3. Fall back to first available playlist in the folder
    
    Args:
        sp: Spotify client
        folder_name: Name of the genre folder
        track_id: Spotify track ID (for future smart matching)
        
    Returns:
        Playlist ID of the best target, or None if no suitable playlist found
    """
    playlists = get_genre_playlists(sp, folder_name)
    
    if not playlists:
        return None
    
    # Strategy 1: Prefer "Collection" playlists as they're often the main target
    for playlist in playlists:
        if 'Collection' in playlist['name']:
            return playlist['id']
    
    # Strategy 2: Look for "Daily" playlists as they're often for new additions
    for playlist in playlists:
        if 'Daily' in playlist['name']:
            return playlist['id']
    
    # Strategy 3: Fall back to the first playlist in the folder
    return playlists[0]['id']


def discover_genres_from_playlists(sp) -> Dict[str, Dict[str, Any]]:
    """
    Dynamically discover genre mappings from existing playlist folder structure.
    
    Args:
        sp: Spotify client (or mock client with get_folder_playlists method)
        
    Returns:
        Dictionary mapping folder names to genre configuration
    """
    dynamic_mapping = {}
    
    # Try to get folder structure from mock client first
    if hasattr(sp, 'playlist_folders'):
        folder_structure = sp.playlist_folders
    else:
        # Fall back to scanning playlists for folder patterns
        folder_structure = discover_folders_from_playlists(sp)
    
    for folder_name, playlist_files in folder_structure.items():
        # Get all genres from playlists in this folder
        folder_genres = set()
        
        for playlist_file in playlist_files:
            # Remove .json extension to get playlist name
            playlist_name = playlist_file.replace('.json', '')
            
            # Get playlist ID
            if hasattr(sp, 'name_to_id') and playlist_name in sp.name_to_id:
                playlist_id = sp.name_to_id[playlist_name]
                
                # Get genres for this playlist
                if hasattr(sp, 'get_playlist_genres'):
                    playlist_genres = sp.get_playlist_genres(playlist_id)
                    folder_genres.update(playlist_genres)
        
        # Create genre configuration for this folder
        if folder_genres:
            dynamic_mapping[folder_name] = {
                "genres": list(folder_genres),
                "audio_features": generate_audio_features_for_folder(folder_name, folder_genres)
            }
    
    return dynamic_mapping


def generate_audio_features_for_folder(folder_name: str, genres: List[str]) -> Dict[str, str]:
    """
    Generate audio feature conditions based on folder name and genres.
    
    Args:
        folder_name: Name of the folder (Electronic, Base, House, etc.)
        genres: List of genres in this folder
        
    Returns:
        Dictionary of audio feature conditions
    """
    # Map folder names to audio feature profiles
    folder_profiles = {
        "Electronic": {"danceability": ">0.5", "energy": ">0.6"},
        "Base": {"energy": ">0.7", "danceability": ">0.6"},  # Bass music = high energy
        "House": {"danceability": ">0.7", "energy": ">0.5"},
        "Rave": {"energy": ">0.8", "danceability": ">0.7"},
        "Funk Soul": {"danceability": ">0.6", "valence": ">0.5"},
        "Rock": {"energy": ">0.6", "acousticness": "<0.4"},
        "Reggae": {"danceability": ">0.5", "valence": ">0.6"},
        "Vibes": {"valence": ">0.4", "energy": ">0.3"},
        "Sierra": {"acousticness": ">0.4", "valence": ">0.4"},  # Nature/outdoor vibes
        "Soft": {"acousticness": ">0.5", "energy": "<0.5"},
        "Chill": {"energy": "<0.4", "valence": ">0.3"},
        "Spiritual": {"acousticness": ">0.4", "instrumentalness": ">0.3"}
    }
    
    return folder_profiles.get(folder_name, {"energy": ">0.5"})


def discover_folders_from_playlists(sp) -> Dict[str, List[str]]:
    """
    Discover folder structure by scanning playlist names for [Folder] patterns.
    
    Args:
        sp: Spotify client
        
    Returns:
        Dictionary mapping folder names to playlist names
    """
    folders = {}
    
    try:
        offset = 0
        limit = 50
        
        while True:
            results = spotify_api_call_with_retry(
                sp.current_user_playlists, limit=limit, offset=offset
            )
            
            if not results or not results.get('items'):
                break
            
            for playlist in results['items']:
                playlist_name = playlist.get('name', '')
                
                # Look for [Folder] pattern
                if '[' in playlist_name and ']' in playlist_name:
                    start = playlist_name.find('[') + 1
                    end = playlist_name.find(']')
                    if start > 0 and end > start:
                        folder_name = playlist_name[start:end]
                        
                        if folder_name not in folders:
                            folders[folder_name] = []
                        folders[folder_name].append(f"{playlist_name}.json")
            
            if not results.get('next'):
                break
            
            offset += limit
        
    except Exception as e:
        print(f"Error discovering folders from playlists: {e}")
    
    return folders


def add_track_to_genre_playlists(sp, track_id: str, classification_results: List[str]) -> Dict[str, bool]:
    """
    Add a track to appropriate genre playlists based on classification results.
    
    Args:
        sp: Spotify client
        track_id: Spotify track ID to add
        classification_results: List of genre folder names from classification
        
    Returns:
        Dictionary mapping folder names to success status
    """
    results = {}
    
    for folder_name in classification_results:
        try:
            target_playlist_id = find_best_target_playlist(sp, folder_name, track_id)
            
            if target_playlist_id:
                # Add track to playlist
                spotify_api_call_with_retry(
                    sp.playlist_add_items, target_playlist_id, [track_id]
                )
                results[folder_name] = True
                print(f"✅ Added track to {folder_name} playlist")
            else:
                results[folder_name] = False
                print(f"❌ No suitable playlist found for {folder_name}")
                
        except Exception as e:
            results[folder_name] = False
            print(f"❌ Error adding track to {folder_name}: {e}")
    
    return results