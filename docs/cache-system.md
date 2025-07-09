# Shared Cache System

The shared cache system provides high-performance data access for playlist analysis and artist mapping across all automations.

## Overview

**Performance Benefits:**
- Reduces startup time from minutes to seconds
- Loads 363 playlists instantly vs API calls
- Caches 5498 artists and 2573 single-playlist artists
- 24-hour TTL with automatic rebuilds

**Files:**
- `common/shared_cache.py` - Main cache implementation
- `common/playlist_data_utils.py` - Data loading utilities
- `data/cache/` - Cache storage directory
- `scripts/update_cache.py` - Cache management script

## Usage Patterns

### For New Automations (Recommended)

```python
from common.shared_cache import get_cached_artist_data
from common.playlist_data_utils import PlaylistDataLoader

# Fast startup with cached artist data
artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)

# Load minimal playlist data as needed
playlists_dict = PlaylistDataLoader.load_playlists_from_directory()

# Find specific playlists
source_playlist_id = PlaylistDataLoader.find_playlist_by_name(playlists_dict, "new")
```

### For Testing and Analysis

```python
from common.playlist_data_utils import PlaylistDataLoader

# Load limited dataset for testing
playlists_dict = PlaylistDataLoader.load_playlists_from_directory(limit=50)

# Build fresh mappings (slower but complete control)
artist_to_playlists = PlaylistDataLoader.build_artist_to_playlists_mapping(
    playlists_dict, exclude_parent_playlists=True
)
```

## Cache Management

### Automatic Management
- Cache rebuilds automatically when expired (24 hours)
- Test environment cleans up after runs
- Production cache persists across runs

### Manual Management

```bash
# Check cache status
uv run scripts/update_cache.py

# Force cache rebuild
uv run scripts/update_cache.py --force

# Clean up test cache (happens automatically)
uv run scripts/update_cache.py --cleanup
```

### Environment Synchronization

**Test Environment:**
- Mirrors production data
- Automatically cleaned up after test runs
- Uses `SPOTIFY_ENV=test` environment variable

**Production Environment:**
- Long-lived cache for performance
- Updated periodically or on data changes
- Uses `SPOTIFY_ENV=prod` environment variable

## Cache Structure

### Artist to Playlists Mapping
```json
{
  "artist_id_1": ["playlist_id_a", "playlist_id_b"],
  "artist_id_2": ["playlist_id_c"]
}
```

### Single Playlist Artists
```json
{
  "single_playlist_artists": ["artist_id_2", "artist_id_3"],
  "total_count": 2573
}
```

### Cache Metadata
```json
{
  "created_at": "2025-07-07T21:28:07.374993",
  "last_updated": "2025-07-07T21:28:07.374993", 
  "environment": "test",
  "total_playlists": 363,
  "total_artists": 5498,
  "cache_version": "1.0"
}
```

## Integration Guidelines

### Environment Detection (CRITICAL)

**Always use centralized config:**
```python
# ✅ CORRECT
from common.config import CURRENT_ENV
environment = CURRENT_ENV

# ❌ WRONG - Causes environment detection bugs
import os
environment = os.environ.get("SPOTIFY_ENV")
environment = get_config_value("environment")  # Wrong key!
```

### Cache Integration in Shell Scripts

```bash
#!/bin/bash
cd "$(dirname "$0")/.."

# Run automation
uv run automations/your_feature/action.py

# Clean up test cache if in test environment
if [[ "${SPOTIFY_ENV}" == "test" ]]; then
    uv run scripts/update_cache.py --cleanup
fi
```

### CI/CD Integration

```bash
# In test pipelines
SPOTIFY_ENV=test uv run your_test_script.py
uv run scripts/test_cleanup_hook.py  # Automatic cleanup
```

## Performance Metrics

**Before Cache (Single Artist Downflow):**
- Startup: 2+ minutes (timeout)
- API calls: 200+ playlists × multiple requests
- Memory: High (loading all data)

**After Cache:**
- Startup: ~10 seconds
- API calls: Only for actual operations
- Memory: Efficient (cached data structure)

## Troubleshooting

### Cache Not Loading
1. Check `data/cache/` directory exists
2. Verify cache files are present and valid JSON
3. Check cache expiration (24 hours)
4. Force rebuild: `uv run scripts/update_cache.py --force`

### Environment Issues
1. Ensure `SPOTIFY_ENV` is set correctly
2. Use `CURRENT_ENV` from `common/config.py`
3. Check `.env.test` or `.env.prod` files exist

### Performance Issues
1. Cache may be expired - check metadata
2. Large playlist changes may require rebuild
3. Verify cached data matches current library state

## Migration Guide

**Existing Features:** Replace direct API loading with cached data:

```python
# Before
playlists_dict = load_all_playlists_from_api(sp)  # Slow
artist_mapping = build_artist_mapping(playlists_dict)  # Slow

# After  
artist_mapping, single_artists = get_cached_artist_data()  # Fast
playlists_dict = PlaylistDataLoader.load_playlists_from_directory()  # Fast
```

**New Features:** Start with cache-first approach for optimal performance.