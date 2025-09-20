"""
Genre mapping cache system for dynamic genre discovery.

Caches discovered genre mappings to avoid expensive re-discovery on every run.
Automatically refreshes cache monthly or when explicitly requested.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from common.config import SPOTIFY_ENV


def get_cache_file_path() -> Path:
    """
    Get the path to the genre mapping cache file.
    
    Returns:
        Path to cache file (environment-specific)
    """
    env = SPOTIFY_ENV
    cache_dir = Path.home() / ".spotify_cache"
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"genre_mapping_cache_{env}.json"
    return cache_file


def load_cached_genre_mapping() -> Optional[Dict[str, Any]]:
    """
    Load cached genre mapping if it exists and is not expired.
    
    Returns:
        Cached genre mapping dict or None if not available/expired
    """
    cache_file = get_cache_file_path()
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired (30 days)
        cache_timestamp = cache_data.get('timestamp', 0)
        cache_date = datetime.fromtimestamp(cache_timestamp)
        expiry_date = cache_date + timedelta(days=30)
        
        if datetime.now() > expiry_date:
            print(f"Genre mapping cache expired (created: {cache_date.strftime('%Y-%m-%d')})")
            return None
        
        print(f"Using cached genre mapping (created: {cache_date.strftime('%Y-%m-%d')})")
        return cache_data.get('genre_mapping', {})
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error loading genre mapping cache: {e}")
        return None


def save_genre_mapping_cache(genre_mapping: Dict[str, Any]) -> bool:
    """
    Save genre mapping to cache with timestamp.
    
    Args:
        genre_mapping: Genre mapping dictionary to cache
        
    Returns:
        True if successfully saved, False otherwise
    """
    cache_file = get_cache_file_path()
    
    try:
        cache_data = {
            'timestamp': time.time(),
            'created': datetime.now().isoformat(),
            'genre_mapping': genre_mapping
        }
        
        # Write to temporary file first, then rename (atomic operation)
        temp_file = cache_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        temp_file.rename(cache_file)
        
        # Set restrictive permissions
        os.chmod(cache_file, 0o600)
        
        print(f"Saved genre mapping cache to {cache_file}")
        return True
        
    except Exception as e:
        print(f"Error saving genre mapping cache: {e}")
        return False


def clear_genre_mapping_cache() -> bool:
    """
    Clear the genre mapping cache file.
    
    Returns:
        True if successfully cleared, False otherwise
    """
    cache_file = get_cache_file_path()
    
    try:
        if cache_file.exists():
            cache_file.unlink()
            print(f"Cleared genre mapping cache: {cache_file}")
        return True
    except Exception as e:
        print(f"Error clearing genre mapping cache: {e}")
        return False


def is_cache_expired() -> bool:
    """
    Check if the genre mapping cache is expired.
    
    Returns:
        True if cache is expired or doesn't exist, False otherwise
    """
    cache_file = get_cache_file_path()
    
    if not cache_file.exists():
        return True
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        cache_timestamp = cache_data.get('timestamp', 0)
        cache_date = datetime.fromtimestamp(cache_timestamp)
        expiry_date = cache_date + timedelta(days=30)
        
        return datetime.now() > expiry_date
        
    except Exception:
        return True


def get_cache_info() -> Dict[str, Any]:
    """
    Get information about the current cache state.
    
    Returns:
        Dictionary with cache information
    """
    cache_file = get_cache_file_path()
    
    if not cache_file.exists():
        return {
            'exists': False,
            'expired': True,
            'path': str(cache_file)
        }
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        cache_timestamp = cache_data.get('timestamp', 0)
        cache_date = datetime.fromtimestamp(cache_timestamp)
        expiry_date = cache_date + timedelta(days=30)
        is_expired = datetime.now() > expiry_date
        
        return {
            'exists': True,
            'expired': is_expired,
            'created': cache_date.isoformat(),
            'expires': expiry_date.isoformat(),
            'path': str(cache_file),
            'size_kb': round(cache_file.stat().st_size / 1024, 2),
            'genre_count': len(cache_data.get('genre_mapping', {}))
        }
        
    except Exception as e:
        return {
            'exists': True,
            'expired': True,
            'error': str(e),
            'path': str(cache_file)
        }


def force_refresh_cache(sp) -> bool:
    """
    Force refresh of the genre mapping cache.
    
    Args:
        sp: Spotify client for discovery
        
    Returns:
        True if successfully refreshed, False otherwise
    """
    from common.genre_classification_utils import discover_genres_from_playlists
    
    try:
        print("Force refreshing genre mapping cache...")
        clear_genre_mapping_cache()
        
        # Discover new mapping
        genre_mapping = discover_genres_from_playlists(sp)
        
        if genre_mapping:
            return save_genre_mapping_cache(genre_mapping)
        else:
            print("No genre mapping discovered during refresh")
            return False
            
    except Exception as e:
        print(f"Error during cache refresh: {e}")
        return False