#!/bin/bash

# Run the Spotify playlist flow automation
# This script flows songs between playlists based on special character naming system

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
"$PYTHON" -m automations.spotify.playlist_flow.action

# If result file exists, use it for notification
if [ -f /tmp/spotify_playlist_flow_result.txt ]; then
    # Read title from the first line
    TITLE=$(head -n 1 /tmp/spotify_playlist_flow_result.txt)
    # Read message from the second line  
    MESSAGE=$(tail -n 1 /tmp/spotify_playlist_flow_result.txt)
    
    # Display macOS notification
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\""
    
    # Clean up
    rm /tmp/spotify_playlist_flow_result.txt
fi