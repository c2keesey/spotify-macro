#!/bin/bash

# Shell script to run the genre-aware Spotify save automation
# This script saves the currently playing track and automatically sorts it into genre-specific playlists

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Determine environment (default to prod for production automations)
SPOTIFY_ENV="${SPOTIFY_ENV:-prod}"

# Load environment-specific configuration
ENV_FILE="$PROJECT_ROOT/.env.$SPOTIFY_ENV"
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

# Set up virtual environment
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/.venv}"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH"
    echo "Please run: uv venv"
    exit 1
fi

# Activate virtual environment and run the script
source "$VENV_PATH/bin/activate"

# Change to project directory to ensure proper imports
cd "$PROJECT_ROOT"

# Run the genre-aware save automation
python -m automations.spotify.save_current_with_genre

# Check if the automation created a result file
RESULT_FILE="/tmp/spotify_genre_save_result.txt"
if [ -f "$RESULT_FILE" ]; then
    # Read the result and display notification (macOS)
    if command -v osascript >/dev/null 2>&1; then
        TITLE=$(head -n 1 "$RESULT_FILE")
        MESSAGE=$(tail -n +2 "$RESULT_FILE")
        osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\""
    fi
    
    # Clean up the temporary file
    rm "$RESULT_FILE"
fi