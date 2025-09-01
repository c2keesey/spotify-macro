#!/usr/bin/env python3
"""
Fetch and cache audio features for all tracks in the music library.

This script fetches audio features from Spotify API for all tracks in playlists
and caches them locally for offline classification testing. Handles rate limiting
gracefully and provides progress tracking.
"""

import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.playlist_data_utils import PlaylistDataLoader
from common.config import CURRENT_ENV


def load_existing_cache(cache_file: Path) -> Dict[str, Dict]:
    """Load existing audio features cache if it exists."""
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"Warning: Could not load cache file {cache_file}, starting fresh")
    return {}


def save_cache(cache_file: Path, cache_data: Dict[str, Dict]) -> None:
    """Save audio features cache to file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)


def get_all_track_ids(playlists_dict: Dict[str, Dict]) -> Set[str]:
    """Extract all unique track IDs from playlist data."""
    track_ids = set()
    for playlist_data in playlists_dict.values():
        for track in playlist_data.get("tracks", []):
            track_id = track.get("id")
            if track_id:
                track_ids.add(track_id)
    return track_ids


def fetch_audio_features_batch(sp, track_ids: List[str], max_batch_size: int = 100) -> Dict[str, Dict]:
    """
    Fetch audio features for a batch of tracks.
    
    Args:
        sp: Spotify client
        track_ids: List of track IDs to fetch features for
        max_batch_size: Maximum batch size for API calls
        
    Returns:
        Dictionary mapping track_id -> audio features
    """
    features_dict = {}
    
    # Process in batches to respect API limits
    for i in range(0, len(track_ids), max_batch_size):
        batch = track_ids[i:i + max_batch_size]
        
        try:
            # Spotify audio_features endpoint accepts up to 100 track IDs
            features_list = spotify_api_call_with_retry(sp.audio_features, batch)
            
            if features_list:
                for track_id, features in zip(batch, features_list):
                    if features:  # Skip None results
                        features_dict[track_id] = features
                    else:
                        print(f"Warning: No audio features found for track {track_id}")
            
            # Progress indicator
            processed = min(i + max_batch_size, len(track_ids))
            print(f"Fetched audio features for {processed}/{len(track_ids)} tracks...")
            
        except Exception as e:
            print(f"Error fetching batch {i//max_batch_size + 1}: {e}")
            # Continue with next batch rather than failing entirely
            continue
    
    return features_dict


def main():
    parser = argparse.ArgumentParser(description="Fetch and cache audio features for all tracks")
    parser.add_argument("--limit", type=int, help="Limit number of playlists to process (for testing)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for API calls")
    parser.add_argument("--force", action="store_true", help="Force re-fetch all features (ignore cache)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    print(f"Environment: {CURRENT_ENV}")
    print("=" * 60)
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "data" / "cache"
    cache_file = cache_dir / "audio_features.json"
    
    # Load existing cache unless forcing re-fetch
    if args.force:
        print("Force mode: Starting with empty cache")
        audio_features_cache = {}
    else:
        print(f"Loading existing cache from {cache_file}")
        audio_features_cache = load_existing_cache(cache_file)
        print(f"Loaded {len(audio_features_cache)} cached audio features")
    
    # Load playlist data
    print("\nLoading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(limit=args.limit)
    print(f"Loaded {len(playlists_dict)} playlists")
    
    # Get all unique track IDs
    print("\nExtracting track IDs...")
    all_track_ids = get_all_track_ids(playlists_dict)
    print(f"Found {len(all_track_ids)} unique tracks")
    
    # Filter out already cached tracks
    missing_track_ids = [tid for tid in all_track_ids if tid not in audio_features_cache]
    print(f"Need to fetch features for {len(missing_track_ids)} tracks")
    
    if not missing_track_ids:
        print("All tracks already have cached audio features!")
        return
    
    # Initialize Spotify client
    print("\nInitializing Spotify client...")
    try:
        scope = "user-library-read playlist-read-private"
        sp = initialize_spotify_client(scope)
        print("✅ Spotify client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Spotify client: {e}")
        return
    
    # Fetch missing audio features
    print(f"\nFetching audio features for {len(missing_track_ids)} tracks...")
    print(f"Batch size: {args.batch_size}")
    print("This may take a while due to rate limiting...")
    
    start_time = time.time()
    
    try:
        new_features = fetch_audio_features_batch(sp, missing_track_ids, args.batch_size)
        
        # Update cache with new features
        audio_features_cache.update(new_features)
        
        # Save updated cache
        print(f"\nSaving cache with {len(audio_features_cache)} total features...")
        save_cache(cache_file, audio_features_cache)
        
        # Summary
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("FETCH COMPLETE")
        print("=" * 60)
        print(f"Total tracks processed: {len(all_track_ids)}")
        print(f"Features fetched: {len(new_features)}")
        print(f"Total cached features: {len(audio_features_cache)}")
        print(f"Time elapsed: {elapsed_time:.1f} seconds")
        print(f"Cache file: {cache_file}")
        
        if args.verbose:
            # Show sample of features
            print("\nSample audio features:")
            for track_id, features in list(new_features.items())[:3]:
                print(f"  {track_id}: energy={features.get('energy', 'N/A'):.3f}, "
                      f"valence={features.get('valence', 'N/A'):.3f}, "
                      f"danceability={features.get('danceability', 'N/A'):.3f}")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving partial cache...")
        save_cache(cache_file, audio_features_cache)
        print(f"Partial cache saved with {len(audio_features_cache)} features")
    
    except Exception as e:
        print(f"\n❌ Error during fetch: {e}")
        print(f"Saving partial cache with {len(audio_features_cache)} features...")
        save_cache(cache_file, audio_features_cache)


if __name__ == "__main__":
    main()