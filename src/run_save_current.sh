#!/bin/bash

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
    echo "Error: VENV_PATH is not set in .env file"
    exit 1
fi

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Run the Python script
python "$SCRIPT_PATH"

# Deactivate the virtual environment
deactivate

if [ -f /tmp/spotify_add_result.txt ]; then
    # Read the first line as title and the rest as message
    title=$(head -n 1 /tmp/spotify_add_result.txt)
    message=$(tail -n +2 /tmp/spotify_add_result.txt)
    
    osascript <<EOD
    display notification "$message" with title "$title"
EOD

    rm /tmp/spotify_add_result.txt
else
    osascript <<EOD
    display notification "Error: Could not read result" with title "Spotify Add to Library"
EOD
fi
