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

# Run the Python script
"$PYTHON_PATH" "$SCRIPT_PATH"

if [ -f /tmp/spotify_add_result.txt ]; then
    result=$(cat /tmp/spotify_add_result.txt)
    osascript -e "display notification \"$result\" with title \"Spotify Add to Library\""
    rm /tmp/spotify_add_result.txt
else
    osascript -e "display notification \"Error: Could not read result\" with title \"Spotify Add to Library\""
fi