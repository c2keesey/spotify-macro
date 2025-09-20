#!/usr/bin/env python3
"""
Cache update script for playlist data.

This script updates the shared cache with fresh data from:
1. Local playlist JSON files (data/playlists/)
2. Spotify API (optional, for complete refresh)

Usage:
    python scripts/update_cache.py                  # Update from local files
    python scripts/update_cache.py --force-api     # Update from Spotify API
    python scripts/update_cache.py --cleanup       # Clean up test cache only
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.shared_cache import SharedPlaylistCache, cleanup_test_cache
from common.config import get_config_value


def update_cache_from_local(force_rebuild: bool = False):
    """Update cache from local playlist files"""
    print("🔄 Updating cache from local playlist data...")
    
    cache = SharedPlaylistCache()
    
    # Load or build cache
    artist_to_playlists, single_playlist_artists = cache.load_or_build_cache(
        force_rebuild=force_rebuild,
        verbose=True
    )
    
    # Print summary
    percentage = (len(single_playlist_artists) / len(artist_to_playlists)) * 100
    print(f"\n📊 Cache Summary:")
    print(f"   Total artists: {len(artist_to_playlists)}")
    print(f"   Single-playlist artists: {len(single_playlist_artists)} ({percentage:.1f}%)")
    
    # Show cache info
    cache_info = cache.get_cache_info()
    print(f"   Cache status: {cache_info['status']}")
    print(f"   Environment: {cache_info.get('environment', 'unknown')}")
    
    return True


def update_cache_from_api():
    """Update cache from Spotify API (downloads fresh data)"""
    print("🔄 Updating cache from Spotify API...")
    print("⚠️  This will download fresh data from Spotify (may take several minutes)")
    
    # This would require implementing API data download
    # For now, recommend running the playlist download script first
    print("📝 To update from API, run:")
    print("   1. uv run data/processing/download_playlists.py")
    print("   2. python scripts/update_cache.py --force")
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Update shared playlist cache")
    parser.add_argument("--force", action="store_true", 
                       help="Force cache rebuild even if current cache is valid")
    parser.add_argument("--force-api", action="store_true",
                       help="Update from Spotify API (downloads fresh data)")
    parser.add_argument("--cleanup", action="store_true",
                       help="Clean up test cache only")
    
    args = parser.parse_args()
    
    try:
        if args.cleanup:
            cleanup_test_cache()
            print("✅ Test cache cleaned up")
            return
        
        if args.force_api:
            success = update_cache_from_api()
        else:
            success = update_cache_from_local(force_rebuild=args.force)
        
        if success:
            print("✅ Cache update completed successfully")
        else:
            print("❌ Cache update failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Cache update failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()