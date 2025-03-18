#!/bin/bash

# Run the Spotify daily liked songs automation
# This script adds songs liked in the last 24 hours to a specified playlist

# Ensure we're using the correct working directory
cd "$(dirname "$0")/.." || exit 1

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to Python in PATH if PYTHON_PATH not set
PYTHON="${PYTHON_PATH:-python3}"

# Activate the virtual environment if VENV_PATH is set
if [ -n "$VENV_PATH" ] && [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Run the Python module
"$PYTHON" -m macros.spotify.daily_liked_songs.action

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