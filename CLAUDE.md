# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Organization (Updated)

This repository has been reorganized for better structure and extensibility:

```
spotify-automation/
├── automations/          # Core automation functionality (renamed from macros/)
├── analysis/             # Research and analysis scripts (organized by category)
│   ├── genre/           # Genre classification research
│   ├── playlist/        # Playlist analysis and patterns
│   └── optimization/    # Performance optimization
├── data/                # Consolidated data management (renamed from _data/)
│   ├── processing/      # Data processing scripts (from download/)
│   ├── playlists/       # Playlist JSON files
│   └── cache/           # Cache files
├── visualization/       # Data visualization tools (renamed from visualize/)
├── common/              # Shared utilities (unchanged)
├── tests/               # Test suite (unchanged)
├── scripts/             # Shell scripts (unchanged)
└── workflows/           # macOS integration (unchanged)
```

## Development Practices

- **Local Data Testing**: 
    - create local data tests first
    - Use centralized utilities in `common/playlist_data_utils.py` and `common/flow_character_utils.py`
    - Eliminates code duplication across test files
    - Real playlist data from `data/playlists/` for realistic testing

- **Shared Cache System**:
    - Use `common/shared_cache.py` for artist mapping and playlist analysis
    - Cache automatically managed with 24-hour TTL
    - Test environment mirrors prod, cleans up after tests
    - **Performance**: Reduces startup from minutes to seconds for large libraries

## Testing with Centralized Utilities

```python
from common.playlist_data_utils import PlaylistDataLoader
from common.shared_cache import get_cached_artist_data

# Load playlist data 
playlists_dict = PlaylistDataLoader.load_playlists_from_directory(limit=50)

# Build artist mappings with flow integration
artist_to_playlists = PlaylistDataLoader.build_artist_to_playlists_mapping(
    playlists_dict, exclude_parent_playlists=True
)

# OR use cached data for performance (recommended for production features)
artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
```

## Cache Usage Patterns

**For Performance-Critical Features:**
```python
# Use cached data for fast startup
from common.shared_cache import get_cached_artist_data
artist_to_playlists, single_playlist_artists = get_cached_artist_data()

# Load minimal playlist data as needed
from common.playlist_data_utils import PlaylistDataLoader
playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
```

**Cache Management:**
```bash
# Update cache periodically
uv run scripts/update_cache.py

# Force cache rebuild
uv run scripts/update_cache.py --force

# Clean up test cache (automatic in test runs)
uv run scripts/update_cache.py --cleanup
```

## Test Account Management

**Automation-Friendly Playlist Sync:**
```bash
# Reset test account and sync all playlists
uv run scripts/sync_test_account.py reset-and-sync

# Only reset test account (delete all playlists)
uv run scripts/sync_test_account.py reset

# Only sync playlists (no reset)
uv run scripts/sync_test_account.py sync

# Check sync status (for monitoring)
uv run scripts/check_playlist_sync_status.py
uv run scripts/check_playlist_sync_status.py --wait --timeout 600
```

**From Python Code:**
```python
from scripts.sync_test_account import reset_test_account, sync_playlists

# Reset test account before testing
success, message = reset_test_account(timeout=600)
if success:
    print(f"✅ {message}")

# Sync playlists with optional reset
success, message = sync_playlists(reset_first=True, timeout=1800)
```

**Manual Control (Advanced):**
```bash
# Original script with enhanced options
uv run scripts/upload_playlists_to_test_account.py --reset --quiet
uv run scripts/upload_playlists_to_test_account.py --reset-only --status-file /tmp/my_sync.txt
```

## Feature Development Workflow

Follow the structured feature development process:

1. **Feature Selection**: Review `docs/backlog/todos.md` for available features
2. **Branch Creation**: Create feature branch `feature/[feature-name]`
3. **Feature Setup**: Copy `docs/features/template/` to `docs/features/[feature-name]/`
4. **Development**: Update feature README with context and use todos.md for tracking
5. **Completion**: Clean up feature folder after merge

See `docs/workflow.md` for complete workflow details.

## Environment Handling (CRITICAL)

**Always use `common/config.py` for environment detection:**
```python
# ✅ CORRECT - Use centralized config
from common.config import CURRENT_ENV
environment = CURRENT_ENV

# ❌ WRONG - Don't access environment variables directly
environment = os.environ.get("SPOTIFY_ENV")  # Inconsistent!
environment = get_config_value("environment")  # Wrong key!
```

**Environment Variables:**
- `SPOTIFY_ENV`: Controls which `.env.{environment}` file to load
- Values: `test` | `prod` (defaults to `test` for safety)
- **Critical**: All environment detection MUST use `CURRENT_ENV` from config.py

**Cache Environment Sync:**
- Test cache automatically cleaned after test runs
- Use `scripts/test_cleanup_hook.py` in CI/CD pipelines
- Cache tagged with environment to prevent cross-contamination

## Documentation Practices

- keep docs minimal clear and concise