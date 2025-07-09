# Test Account Sync Tools

Automation-friendly tools for managing Spotify test account playlist synchronization.

## Quick Start

```bash
# Reset test account and sync with prod data
uv run scripts/sync_test_account.py reset-and-sync

# Run your automation tests
uv run automations/spotify/single_artist_downflow/action.py

# Clean up test account
uv run scripts/sync_test_account.py reset
```

## Available Tools

### 1. `scripts/sync_test_account.py` (Main Wrapper)

**Command Line:**
```bash
# Actions
uv run scripts/sync_test_account.py reset              # Delete all playlists
uv run scripts/sync_test_account.py sync               # Sync playlists only  
uv run scripts/sync_test_account.py reset-and-sync     # Delete + sync

# Options
--timeout 1800                    # Set timeout (default: 30 minutes)
--verbose                         # Show detailed output
```

**Python Integration:**
```python
from scripts.sync_test_account import reset_test_account, sync_playlists

# Before testing
success, message = reset_test_account(timeout=600)
success, message = sync_playlists(reset_first=True, timeout=1800)

# Check results
if success:
    print(f"✅ {message}")
else:
    print(f"❌ {message}")
```

### 2. `scripts/check_playlist_sync_status.py` (Monitor)

```bash
# Check current status
uv run scripts/check_playlist_sync_status.py

# Wait for completion
uv run scripts/check_playlist_sync_status.py --wait --timeout 600

# Custom status file
uv run scripts/check_playlist_sync_status.py --status-file /tmp/my_sync.txt
```

### 3. `scripts/upload_playlists_to_test_account.py` (Enhanced)

```bash
# Automation-friendly options
uv run scripts/upload_playlists_to_test_account.py --reset --quiet
uv run scripts/upload_playlists_to_test_account.py --reset-only
uv run scripts/upload_playlists_to_test_account.py --status-file /tmp/sync.txt
```

## Features

### ✅ **Automation-Friendly**
- Status file monitoring for completion detection
- Clean return values (success/failure + message)
- Timeout handling with configurable limits
- Quiet mode for minimal output

### ✅ **Robust Error Handling**
- Process monitoring and cleanup
- Detailed error messages
- Graceful timeout handling
- Status file cleanup

### ✅ **Flexible Usage**
- Command line interface for manual use
- Python functions for integration
- Multiple operation modes (reset/sync/both)
- Configurable timeouts and monitoring

## Status File Format

Status files use simple key-value format:
```
STATUS: STARTING|COMPLETED|FAILED
TIMESTAMP: 2025-07-07T21:45:14.257057
MESSAGE: Deleted 13 playlists. Created: 87, Updated: 0, Skipped: 0, Errors: 0, Total: 87
```

## Testing Workflow Integration

**Typical Testing Pattern:**
```bash
# 1. Setup fresh test environment
uv run scripts/sync_test_account.py reset-and-sync

# 2. Run your automation
uv run automations/spotify/your_feature/action.py

# 3. Verify results manually or with tests

# 4. Clean up for next test
uv run scripts/sync_test_account.py reset
```

**CI/CD Integration:**
```bash
#!/bin/bash
# Setup
SPOTIFY_ENV=test uv run scripts/sync_test_account.py reset-and-sync

# Test
SPOTIFY_ENV=test uv run automations/spotify/single_artist_downflow/action.py

# Cleanup
SPOTIFY_ENV=test uv run scripts/sync_test_account.py reset
```

## Performance

- **Reset Only**: ~1-2 minutes (depends on existing playlists)
- **Full Sync**: ~5-10 minutes (87 playlists + 2300+ tracks)
- **Monitoring**: Real-time status updates every 10 seconds
- **Timeout**: Configurable (default: 30 minutes for full sync)

## Related Documentation

- `CLAUDE.md` - Updated with test account management patterns
- `docs/cache-system.md` - Cache integration and performance
- `docs/features/playlist-downflow-single-artist/` - Feature using these tools