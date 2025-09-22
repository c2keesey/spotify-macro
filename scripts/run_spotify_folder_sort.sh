#!/bin/bash

# Run the Spotify folder sorter automation
# Sorts tracks from "New" into folder aggregators based on cached library data

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

# Pass through args (like --keep)
"$PYTHON" -m automations.spotify.folder_sorter.action "$@"

# If result file exists, show macOS notification
if [ -f /tmp/spotify_folder_sort_result.txt ]; then
    TITLE=$(head -n 1 /tmp/spotify_folder_sort_result.txt)
    MESSAGE=$(tail -n 1 /tmp/spotify_folder_sort_result.txt)
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\""
    rm /tmp/spotify_folder_sort_result.txt
fi
