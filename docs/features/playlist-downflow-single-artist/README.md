# Feature: Playlist Downflow Single Artist Processing

## Description
Automated processing of single-playlist artist tracks from the 'new' playlist. Routes tracks by artists that appear in only one playlist to both their artist-specific playlist and corresponding folder playlist, then removes them from 'new'.

## Context
- **Branch**: `feature/playlist-downflow-single-artist`
- **Status**: ✅ **Completed with Performance Optimization**
- **Implementation**: `automations/spotify/single_artist_downflow/action.py`
- **Shell Script**: `scripts/run_spotify_single_artist_downflow.sh`

## Key Features

### ✅ Smart Artist Detection
- **Single-Playlist Artists**: Identifies artists that appear in only one playlist (46.8% of all artists)
- **Parent Playlist Exclusion**: Excludes parent playlists from uniqueness calculation
- **Flow Character Integration**: Uses existing playlist flow character logic

### ✅ Performance Optimization
- **Shared Cache System**: Uses `common/shared_cache.py` for instant startup
- **Performance**: Reduced from 2+ minutes to ~10 seconds
- **Cached Data**: 5498 artists mapped, 2573 single-playlist artists identified

### ✅ Dual Playlist Routing
- **Artist Playlists**: Adds tracks to the artist's specific playlist
- **Folder Playlists**: Also adds to corresponding folder playlist via `data/playlist_folders.json`
- **Conflict Detection**: Skips tracks already in target playlists

### ✅ Environment Management
- **Test/Prod Sync**: Test environment mirrors prod data
- **Automatic Cleanup**: Test cache cleaned after runs
- **Environment Detection**: Uses `common/config.py` centralized system

## Implementation Files

```
automations/spotify/single_artist_downflow/
├── action.py                    # Main automation logic
scripts/
├── run_spotify_single_artist_downflow.sh  # Shell wrapper with cleanup
├── update_cache.py              # Cache management
└── test_cleanup_hook.py         # Test environment cleanup
common/
├── shared_cache.py              # Performance cache system
└── playlist_data_utils.py       # Data loading utilities
```

## Performance Metrics

**Before Optimization:**
- Startup time: 2+ minutes (often timed out)
- API calls: 200+ playlists loaded individually
- Memory usage: High (full library in memory)

**After Optimization:**
- Startup time: ~10 seconds
- Cache hits: Artist mappings loaded instantly
- Memory usage: Efficient cached data structures

## Cache Integration

```python
# Fast cached artist data loading
from common.shared_cache import get_cached_artist_data
artist_to_playlists, single_playlist_artists = get_cached_artist_data()

# Minimal playlist data loading
from common.playlist_data_utils import PlaylistDataLoader
playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
```

## Usage

**Single Artist Downflow Automation:**
```bash
# Run automation
./scripts/run_spotify_single_artist_downflow.sh

# Manual cache management
uv run scripts/update_cache.py          # Check/update cache
uv run scripts/update_cache.py --force  # Force rebuild
```

**Test Account Management:**
```bash
# Reset test account with fresh prod data (before testing)
uv run scripts/sync_test_account.py reset-and-sync

# Clean up test account (after testing)
uv run scripts/sync_test_account.py reset

# Monitor sync progress
uv run scripts/check_playlist_sync_status.py --wait
```

## Statistics

- **Total Artists**: 5,498 in library
- **Single-Playlist Artists**: 2,573 (46.8%)
- **Playlists Processed**: 363 total playlists
- **Parent Playlists Excluded**: 13 (flow automation targets)

## Testing Results

✅ **Cache System**: Load/rebuild/cleanup all functional
✅ **Environment Sync**: Test mirrors prod correctly  
✅ **Performance**: 20x+ speed improvement (2+ minutes → ~10 seconds)
✅ **Artist Detection**: Correctly identifies single-playlist artists
✅ **Track Processing**: Successfully processes tracks from 'new' playlist
✅ **Conflict Detection**: Skips tracks already in target playlists (smart behavior)
✅ **Automation Integration**: Works with enhanced test account sync tools

## Related Documentation

- `docs/cache-system.md` - Comprehensive cache documentation
- `CLAUDE.md` - Updated with cache usage patterns and environment handling
