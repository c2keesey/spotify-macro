#!/bin/bash

# Run the Spotify daily liked songs automation
# This script adds songs liked in the last 24 hours to a specified playlist

# Ensure we're using the correct working directory
cd "$(dirname "$0")/.." || exit 1

# Determine environment (default to prod for production automations)
SPOTIFY_ENV="${SPOTIFY_ENV:-prod}"

# Load environment-specific configuration
ENV_FILE=".env.$SPOTIFY_ENV"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    echo "Loaded environment: $SPOTIFY_ENV"
else
    echo "Error: Environment file not found at $ENV_FILE"
    echo "Available environments: test, prod"
    exit 1
fi

# Export environment variable for Python scripts
export SPOTIFY_ENV

# Default to Python in PATH if PYTHON_PATH not set
PYTHON="${PYTHON_PATH:-python3}"

# Activate the virtual environment if VENV_PATH is set
if [ -n "$VENV_PATH" ] && [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Run the Python module
"$PYTHON" -m automations.spotify.daily_liked_songs.action

# If result file exists, use it for notification
if [ -f /tmp/spotify_daily_liked_result.txt ]; then
    # Read title from the first line
    TITLE=$(head -n 1 /tmp/spotify_daily_liked_result.txt)
    # Read message from the second line
    MESSAGE=$(tail -n 1 /tmp/spotify_daily_liked_result.txt)
    
    # Display macOS notification
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\""
    
    # Clean up
    rm /tmp/spotify_daily_liked_result.txt
fi 