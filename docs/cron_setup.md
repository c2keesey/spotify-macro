# Cron Job Setup for Automations

This guide explains how to set up cron jobs for the Spotify automations.

## Prerequisites

1. **Authenticate with Spotify** (required before any automation can run):
   ```bash
   SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py auth
   ```

2. **Sync the library cache** (required for playlist_flow, folder_sorter, etc.):
   ```bash
   SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache; sync_prod_library_cache()"
   ```

## Running Automations

### Playlist Flow
```bash
SPOTIFY_ENV=prod uv run python -m automations.spotify.playlist_flow.action
```

### Folder Sorter
```bash
SPOTIFY_ENV=prod uv run python -m automations.spotify.folder_sorter.action
```

### Daily Liked Songs
```bash
SPOTIFY_ENV=prod uv run python -m automations.spotify.daily_liked_songs.action
```

### Save Current Track
```bash
SPOTIFY_ENV=prod uv run python -m automations.spotify.save_current
```

## Example Cron Setup

Edit your crontab:
```bash
crontab -e
```

Add entries like:
```bash
# Run playlist flow daily at 9 AM
0 9 * * * cd /path/to/spotify-macro && SPOTIFY_ENV=prod uv run python -m automations.spotify.playlist_flow.action >> logs/playlist_flow.log 2>&1

# Run folder sorter daily at 10 AM
0 10 * * * cd /path/to/spotify-macro && SPOTIFY_ENV=prod uv run python -m automations.spotify.folder_sorter.action >> logs/folder_sorter.log 2>&1
```

## Troubleshooting

### Authentication expired
Run the auth script again:
```bash
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py auth
```

### Library cache out of date
Re-sync the cache:
```bash
SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache; sync_prod_library_cache(force_full_refresh=True)"
```

### Check auth status
```bash
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py status
```
