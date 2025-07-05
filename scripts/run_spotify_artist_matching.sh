#!/bin/bash
# Shell script for running the Spotify artist matching automation
# Adds songs from 'new' playlist to target playlists based on single-playlist artist matching

# Determine the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from the root directory
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Activate the virtual environment
if [ -z "$VENV_PATH" ]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
    echo "VENV_PATH not set in .env file, using default: $VENV_PATH"
fi

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Run the Python script
python -m automations.spotify.artist_matching.action

# Deactivate the virtual environment
deactivate

# Display notification from the temporary file
NOTIFICATION_FILE="/tmp/spotify_artist_matching_result.txt"
if [ -f "$NOTIFICATION_FILE" ]; then
    # Read the first line as title and the rest as message
    title=$(head -n 1 "$NOTIFICATION_FILE")
    message=$(tail -n +2 "$NOTIFICATION_FILE")
    
    osascript <<EOD
    display notification "$message" with title "$title"
EOD

    rm "$NOTIFICATION_FILE"
else
    osascript <<EOD
    display notification "Error: Could not read result" with title "Automation Error"
EOD
fi 