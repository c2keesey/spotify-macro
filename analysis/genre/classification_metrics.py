"""
Utilities for classification metrics, data splitting, and evaluation helpers.

Provides functions for creating train/test splits, loading cached data, and
calculating specialized metrics for genre classification.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

from common.playlist_data_utils import PlaylistDataLoader
try:
    from .classification_framework import TrainTestSplit
except ImportError:
    from classification_framework import TrainTestSplit


def load_test_data(limit_tracks: Optional[int] = None) -> Tuple[List[Dict], Dict[str, Dict]]:
    """
    Load test data for classification evaluation.
    
    Args:
        limit_tracks: Limit number of tracks (None for all)
        
    Returns:
        Tuple of (test_tracks, playlists_dict)
    """
    # Load playlist data
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    
    # Load folder mapping to get proper folder names
    import json
    try:
        with open('data/playlist_folders.json', 'r') as f:
            playlist_folders = json.load(f)
    except FileNotFoundError:
        print("⚠️ playlist_folders.json not found, using playlist names as folders")
        playlist_folders = {}
    
    # Create reverse mapping: playlist name -> folder name
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            # Remove .json extension to get playlist name
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    # Extract tracks with proper folder information
    test_tracks = []
    for playlist_id, playlist_data in playlists_dict.items():
        if 'tracks' not in playlist_data:
            continue
            
        playlist_name = playlist_data.get('name', playlist_id)
        
        # ONLY include playlists that are in the folder mapping
        if playlist_name not in playlist_to_folder:
            continue  # Skip playlists not in folder mapping (like "New", parent playlists, etc.)
        
        folder = playlist_to_folder[playlist_name]
        
        for track in playlist_data['tracks']:
            track_id = track.get('id')
            if not track_id:
                continue
                
            # Create test track entry
            test_track = {
                'track_id': track_id,
                'folders': [folder],
                'playlists': [playlist_id],
                'track_name': track.get('name', 'Unknown'),
                'artists': [artist.get('name', 'Unknown') for artist in track.get('artists', [])]
            }
            test_tracks.append(test_track)
    
    # Limit tracks if requested
    if limit_tracks:
        test_tracks = test_tracks[:limit_tracks]
    
    return test_tracks, playlists_dict


def split_train_test_playlists(playlists_dict: Dict[str, Dict], 
                              train_ratio: float = 0.7,
                              random_seed: int = 42) -> Tuple[List[str], List[str]]:
    """
    Split playlists into train and test sets.
    
    Args:
        playlists_dict: Dictionary of playlist data
        train_ratio: Ratio of playlists for training
        random_seed: Random seed for reproducibility
        
    Returns:
        Tuple of (train_playlist_ids, test_playlist_ids)
    """
    import random
    
    playlist_ids = list(playlists_dict.keys())
    random.seed(random_seed)
    random.shuffle(playlist_ids)
    
    split_point = int(len(playlist_ids) * train_ratio)
    train_playlists = playlist_ids[:split_point]
    test_playlists = playlist_ids[split_point:]
    
    return train_playlists, test_playlists


def load_cached_data() -> Dict[str, Any]:
    """
    Load all cached data files needed for classification.
    
    Returns:
        Dictionary containing all cached data:
        - artist_to_playlists: Artist ID -> playlist IDs mapping
        - single_playlist_artists: List of single-playlist artist IDs
        - playlist_folders: Folder -> playlist files mapping
        - playlist_to_artists: Playlist stats with artist frequencies
        - cache_metadata: Cache information
    """
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    cache_dir = data_dir / "cache"
    
    cached_data = {}
    
    # Load cache files
    cache_files = {
        "artist_to_playlists": cache_dir / "artist_to_playlists.json",
        "single_playlist_artists": cache_dir / "single_playlist_artists.json",
        "cache_metadata": cache_dir / "cache_metadata.json"
    }
    
    for key, file_path in cache_files.items():
        if file_path.exists():
            with open(file_path, 'r') as f:
                cached_data[key] = json.load(f)
        else:
            print(f"Warning: Cache file not found: {file_path}")
            cached_data[key] = {}
    
    # Load data files
    data_files = {
        "playlist_folders": data_dir / "playlist_folders.json",
        "playlist_to_artists": data_dir / "playlist_to_artists.json"
    }
    
    for key, file_path in data_files.items():
        if file_path.exists():
            with open(file_path, 'r') as f:
                cached_data[key] = json.load(f)
        else:
            print(f"Warning: Data file not found: {file_path}")
            cached_data[key] = {}
    
    return cached_data


def create_train_test_split(
    playlist_folders: Dict[str, List[str]], 
    playlists_dict: Dict[str, Dict],
    train_ratio: float = 0.7,
    random_seed: int = 42
) -> TrainTestSplit:
    """
    Create a train/test split by splitting playlists within each folder.
    
    Args:
        playlist_folders: Folder -> playlist files mapping
        playlists_dict: Playlist data loaded via PlaylistDataLoader
        train_ratio: Fraction of playlists to use for training
        random_seed: Random seed for reproducible splits
        
    Returns:
        TrainTestSplit object with train/test data
    """
    random.seed(random_seed)
    
    # Create playlist name to ID mapping
    playlist_name_to_id = {data["name"]: pid for pid, data in playlists_dict.items()}
    
    train_playlists = {}
    test_playlists = {}
    train_tracks = []
    test_tracks = []
    
    print(f"Creating train/test split with {train_ratio:.1%} training ratio...")
    
    for folder, playlist_files in playlist_folders.items():
        # Convert .json files to playlist names
        playlist_names = [pf.replace('.json', '') for pf in playlist_files]
        
        # Find matching playlists in our data
        available_playlists = []
        for name in playlist_names:
            if name in playlist_name_to_id:
                available_playlists.append(name)
        
        if not available_playlists:
            print(f"Warning: No playlists found for folder {folder}")
            continue
            
        # Shuffle and split
        random.shuffle(available_playlists)
        split_point = int(len(available_playlists) * train_ratio)
        
        train_playlist_names = available_playlists[:split_point]
        test_playlist_names = available_playlists[split_point:]
        
        # Ensure at least one playlist in each set if possible
        if len(available_playlists) >= 2:
            if not train_playlist_names:
                train_playlist_names = [available_playlists[0]]
                test_playlist_names = available_playlists[1:]
            elif not test_playlist_names:
                test_playlist_names = [available_playlists[-1]]
                train_playlist_names = available_playlists[:-1]
        
        train_playlists[folder] = train_playlist_names
        test_playlists[folder] = test_playlist_names
        
        # Extract tracks from each set
        for playlist_name in train_playlist_names:
            playlist_id = playlist_name_to_id[playlist_name]
            playlist_data = playlists_dict[playlist_id]
            for track in playlist_data["tracks"]:
                train_tracks.append((track["id"], folder))
        
        for playlist_name in test_playlist_names:
            playlist_id = playlist_name_to_id[playlist_name]
            playlist_data = playlists_dict[playlist_id]
            for track in playlist_data["tracks"]:
                test_tracks.append((track["id"], folder))
        
        print(f"  {folder}: {len(train_playlist_names)} train, {len(test_playlist_names)} test playlists")
    
    split = TrainTestSplit(
        train_playlists=train_playlists,
        test_playlists=test_playlists,
        train_tracks=train_tracks,
        test_tracks=test_tracks
    )
    
    print(f"Total split: {split.train_size} train tracks, {split.test_size} test tracks")
    return split


def build_artist_folder_mapping(
    train_tracks: List[Tuple[str, str]], 
    playlists_dict: Dict[str, Dict]
) -> Dict[str, Set[str]]:
    """
    Build artist -> folders mapping from training data.
    
    Args:
        train_tracks: List of (track_id, folder) tuples from training set
        playlists_dict: Playlist data loaded via PlaylistDataLoader
        
    Returns:
        Dictionary mapping artist_id to set of folder names
    """
    artist_to_folders = defaultdict(set)
    
    # Create track_id -> playlist_data mapping for efficiency
    track_to_playlist = {}
    for playlist_id, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            track_to_playlist[track["id"]] = playlist_data
    
    # Build artist to folders mapping from training tracks
    for track_id, folder in train_tracks:
        if track_id in track_to_playlist:
            playlist_data = track_to_playlist[track_id]
            # Find the track in the playlist
            for track in playlist_data["tracks"]:
                if track["id"] == track_id:
                    for artist in track["artists"]:
                        artist_id = artist["id"]
                        if artist_id:
                            artist_to_folders[artist_id].add(folder)
                    break
    
    return dict(artist_to_folders)


def get_single_folder_artists(
    artist_to_folders: Dict[str, Set[str]]
) -> Dict[str, str]:
    """
    Extract artists that appear in only one folder.
    
    Args:
        artist_to_folders: Artist ID -> set of folder names
        
    Returns:
        Dictionary mapping artist_id to single folder name
    """
    return {
        artist_id: list(folders)[0] 
        for artist_id, folders in artist_to_folders.items() 
        if len(folders) == 1
    }


def calculate_folder_confidence_scores(
    predicted_folders: List[str],
    confidence_factors: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate confidence scores for predicted folders.
    
    Args:
        predicted_folders: List of predicted folder names
        confidence_factors: Dictionary of confidence factors per folder
        
    Returns:
        Dictionary mapping folder name to confidence score
    """
    if not predicted_folders:
        return {}
    
    # Base confidence distributed among predictions
    base_confidence = 1.0 / len(predicted_folders)
    
    scores = {}
    for folder in predicted_folders:
        # Apply confidence factor if available
        factor = confidence_factors.get(folder, 1.0)
        scores[folder] = base_confidence * factor
    
    return scores


def get_track_audio_features(track_id: str, sp=None) -> Optional[Dict[str, float]]:
    """
    Get audio features for a track from cache or Spotify API.
    
    Args:
        track_id: Spotify track ID
        sp: Spotify client instance (optional if using cache)
        
    Returns:
        Dictionary of audio features or None if not available
    """
    # First try to load from cache
    try:
        from pathlib import Path
        import json
        
        project_root = Path(__file__).parent.parent.parent
        cache_file = project_root / "data" / "cache" / "audio_features.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                if track_id in cache:
                    return cache[track_id]
    except Exception as e:
        print(f"Warning: Could not load audio features cache: {e}")
    
    # Fallback to API if cache miss and client available
    if sp:
        try:
            if hasattr(sp, 'get_track_audio_features'):
                # Mock client method
                return sp.get_track_audio_features(track_id)
            else:
                # Real Spotify client
                from common.spotify_utils import spotify_api_call_with_retry
                features = spotify_api_call_with_retry(sp.audio_features, [track_id])
                return features[0] if features and features[0] else None
        except Exception as e:
            print(f"Error getting audio features for {track_id}: {e}")
    
    return None


def get_track_artists(track_id: str, playlists_dict: Dict[str, Dict]) -> List[Dict[str, str]]:
    """
    Get artist information for a track from playlist data.
    
    Args:
        track_id: Spotify track ID
        playlists_dict: Playlist data loaded via PlaylistDataLoader
        
    Returns:
        List of artist dictionaries with 'id' and 'name' keys
    """
    for playlist_id, playlist_data in playlists_dict.items():
        for track in playlist_data["tracks"]:
            if track["id"] == track_id:
                return track["artists"]
    return []


def print_data_summary(cached_data: Dict[str, Any], split: TrainTestSplit) -> None:
    """
    Print a summary of the loaded data and train/test split.
    
    Args:
        cached_data: Cached data dictionary
        split: Train/test split object
    """
    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    
    # Cache metadata
    metadata = cached_data.get("cache_metadata", {})
    print(f"Cache Environment: {metadata.get('environment', 'unknown')}")
    print(f"Total Playlists: {metadata.get('total_playlists', 'unknown')}")
    print(f"Total Artists: {metadata.get('total_artists', 'unknown')}")
    print(f"Cache Updated: {metadata.get('last_updated', 'unknown')}")
    
    # Single playlist artists
    single_artists = cached_data.get("single_playlist_artists", {})
    if isinstance(single_artists, dict) and "single_playlist_artists" in single_artists:
        single_count = len(single_artists["single_playlist_artists"])
        print(f"Single-Playlist Artists: {single_count}")
    
    # Folder breakdown
    print(f"\nFolders: {len(split.folders)}")
    for folder in sorted(split.folders):
        train_count = len(split.train_playlists.get(folder, []))
        test_count = len(split.test_playlists.get(folder, []))
        print(f"  {folder}: {train_count} train + {test_count} test playlists")
    
    print(f"\nTrain/Test Split:")
    print(f"  Training tracks: {split.train_size:,}")
    print(f"  Test tracks: {split.test_size:,}")
    print(f"  Total tracks: {split.train_size + split.test_size:,}")
    
    train_ratio = split.train_size / (split.train_size + split.test_size) if (split.train_size + split.test_size) > 0 else 0
    print(f"  Train ratio: {train_ratio:.1%}")
    print("="*60)


def save_evaluation_results(
    results: Dict[str, Any], 
    output_file: str = "classification_evaluation_results.json"
) -> None:
    """
    Save evaluation results to a JSON file.
    
    Args:
        results: Evaluation results dictionary
        output_file: Output file path
    """
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "data" / output_file
    
    # Convert results to JSON-serializable format
    json_results = {}
    for classifier_name, metrics in results.items():
        if hasattr(metrics, 'get_summary'):
            json_results[classifier_name] = {
                "summary": metrics.get_summary(),
                "per_folder_metrics": metrics.per_folder_metrics,
                "total_processing_time_ms": metrics.total_processing_time_ms
            }
        else:
            json_results[classifier_name] = results
    
    with open(output_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"Evaluation results saved to: {output_path}")