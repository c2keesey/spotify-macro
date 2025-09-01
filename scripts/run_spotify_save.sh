#!/bin/bash

# Determine the project root directory
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

# Change to project directory and run the Python script
cd "$PROJECT_ROOT"
python -m automations.spotify.save_current

# Deactivate the virtual environment
deactivate

# Display notification from the temporary file
NOTIFICATION_FILE="/tmp/spotify_add_result.txt"
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
    display notification "Error: Could not read result" with title "Spotify Add to Library"
EOD
fi 