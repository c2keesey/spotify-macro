#!/bin/bash

# Cron-compatible wrapper for Spotify playlist flow automation
# Runs daily to flow songs between playlists based on special character naming system

# Set up logging
LOG_DIR="/Users/c2k/Projects/spotify-macro/logs"
LOG_FILE="$LOG_DIR/playlist_flow_cron.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG_FILE"
}

log "=== Playlist Flow Cron Job Starting ==="

# Change to project directory (cron runs from HOME by default)
PROJECT_DIR="/Users/c2k/Projects/spotify-macro"
cd "$PROJECT_DIR" || {
    log "ERROR: Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

log "Changed to project directory: $(pwd)"

# Load environment variables from .env file
if [ -f .env ]; then
    log "Loading environment variables from .env"
    # Use a safer method to load env vars (avoid issues with special characters)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^[[:space:]]*# ]] || [[ -z "$key" ]]; then
            continue
        fi
        # Remove quotes from value if present
        value=$(echo "$value" | sed 's/^["'\'']*//;s/["'\'']*$//')
        export "$key"="$value"
        log "Loaded env var: $key"
    done < .env
else
    log "WARNING: .env file not found"
fi

# Find uv executable (common locations for Homebrew installs)
UV_PATHS=(
    "/opt/homebrew/bin/uv"
    "/usr/local/bin/uv" 
    "$HOME/.cargo/bin/uv"
    "$(which uv 2>/dev/null)"
)

UV_CMD=""
for path in "${UV_PATHS[@]}"; do
    if [ -x "$path" ]; then
        UV_CMD="$path"
        log "Found uv at: $UV_CMD"
        break
    fi
done

if [ -z "$UV_CMD" ]; then
    log "ERROR: uv command not found in any of the expected locations"
    log "Searched: ${UV_PATHS[*]}"
    exit 1
fi

# Set environment for production (not test)
export SPOTIFY_ENV="prod"
log "Set SPOTIFY_ENV to: $SPOTIFY_ENV"

# Run the playlist flow automation
log "Starting playlist flow automation..."
if "$UV_CMD" run python -m automations.spotify.playlist_flow.action 2>&1 | while IFS= read -r line; do
    log "STDOUT: $line"
done; then
    log "Playlist flow automation completed successfully"
    SUCCESS=true
else
    EXIT_CODE=$?
    log "ERROR: Playlist flow automation failed with exit code: $EXIT_CODE"
    SUCCESS=false
fi

# Check for notification result file and process it
RESULT_FILE="/tmp/spotify_playlist_flow_result.txt"
if [ -f "$RESULT_FILE" ]; then
    log "Processing notification result file"
    
    # Read title and message
    TITLE=$(head -n 1 "$RESULT_FILE" 2>/dev/null || echo "Playlist Flow")
    MESSAGE=$(tail -n +2 "$RESULT_FILE" 2>/dev/null || echo "Cron job completed")
    
    log "Notification - Title: $TITLE"
    log "Notification - Message: $MESSAGE"
    
    # Only show macOS notifications for significant events (not "no changes" messages)
    if [[ ! "$TITLE" =~ "No New Songs" ]] && [[ ! "$MESSAGE" =~ "up to date" ]]; then
        log "Displaying macOS notification"
        osascript -e "display notification \"$MESSAGE\" with title \"Playlist Flow Cron: $TITLE\"" 2>/dev/null || {
            log "WARNING: Failed to display macOS notification"
        }
    else
        log "Skipping notification for routine 'no changes' result"
    fi
    
    # Clean up result file
    rm "$RESULT_FILE"
    log "Cleaned up result file"
else
    log "No result file found at: $RESULT_FILE"
fi

log "=== Playlist Flow Cron Job Finished ==="

# Add blank line for readability in log
echo "" >> "$LOG_FILE"

# Exit with appropriate code
if [ "$SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi