# Cron Job Setup for Playlist Flow

This guide explains how to set up the daily cron job for the Spotify playlist flow automation.

## Current Setup

The cron job has been configured to run daily at 9:00 AM:

```bash
0 9 * * * /Users/c2k/Projects/spotify-macro/scripts/run_playlist_flow_cron.sh
```

## First-Time Setup Required

**IMPORTANT**: Before the cron job can run successfully, you need to authenticate with Spotify manually once to create the auth cache file.

### Steps:

1. **Run the automation manually first** (to create auth cache):
   ```bash
   cd /Users/c2k/Projects/spotify-macro
   ./scripts/run_spotify_playlist_flow.sh
   ```
   
2. **Complete the OAuth flow** in your browser when prompted

3. **Verify the cache file was created**:
   ```bash
   ls -la common/.playlist_flow_cache*
   ```
   You should see a file like `common/.playlist_flow_cache_prod`

4. **Test the cron script** (optional):
   ```bash
   ./scripts/run_playlist_flow_cron.sh
   ```

## Script Features

The cron-compatible script (`run_playlist_flow_cron.sh`) includes:

- ✅ **Full path resolution** - Finds `uv` in common Homebrew locations
- ✅ **Working directory handling** - Changes to project directory first
- ✅ **Environment variable loading** - Safely loads from `.env` file
- ✅ **Comprehensive logging** - Logs to `logs/playlist_flow_cron.log`
- ✅ **Error handling** - Graceful failure with detailed error messages
- ✅ **Smart notifications** - Only shows notifications for significant events
- ✅ **Production environment** - Uses `SPOTIFY_ENV=prod` by default

## Monitoring

### Check if cron job is scheduled:
```bash
crontab -l
```

### View recent logs:
```bash
tail -f /Users/c2k/Projects/spotify-macro/logs/playlist_flow_cron.log
```

### Check system cron logs:
```bash
tail -f /var/log/system.log | grep cron
```

## Log Location

All cron job output is logged to:
```
/Users/c2k/Projects/spotify-macro/logs/playlist_flow_cron.log
```

The log includes:
- Timestamp for each operation
- Environment loading status
- Authentication cache usage
- Playlist flow results
- Error messages and troubleshooting info

## Troubleshooting

### Common Issues:

1. **Authentication expired**: 
   - Run the manual script again to refresh auth cache
   - Check for "User authentication requires interaction" in logs

2. **Environment issues**:
   - Verify `.env` file exists in project root
   - Check log for "Loading environment variables from .env"

3. **Path issues**:
   - Script automatically finds `uv` in common locations
   - Check log for "Found uv at: /path/to/uv"

4. **Permission issues**:
   - Ensure script is executable: `chmod +x scripts/run_playlist_flow_cron.sh`
   - Check file permissions on `.env` and cache files

## Modifying the Schedule

To change when the cron job runs:

```bash
# Edit cron jobs
crontab -e

# Or replace the schedule (preserving other jobs)
(crontab -l | grep -v playlist_flow; echo "0 21 * * * /Users/c2k/Projects/spotify-macro/scripts/run_playlist_flow_cron.sh") | crontab -
```

Common cron schedule examples:
- `0 9 * * *` - Daily at 9 AM
- `0 21 * * *` - Daily at 9 PM  
- `0 9 * * 1` - Every Monday at 9 AM
- `0 9 1 * *` - First day of every month at 9 AM

## Removing the Cron Job

To remove the playlist flow cron job:

```bash
(crontab -l | grep -v playlist_flow) | crontab -
```