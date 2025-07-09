#!/bin/bash

# Script to run the staging classification automation
# This script processes songs from a staging playlist using intelligent multi-strategy classification

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Set up environment
source "$PROJECT_ROOT/.venv/bin/activate"
cd "$PROJECT_ROOT"

# Export environment variables from .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

echo "Running staging classification automation..."

# Run the automation
python -m automations.spotify.staging_classification.action

# Check if the result file exists and read it
RESULT_FILE="/tmp/spotify_staging_classification_result.txt"
if [ -f "$RESULT_FILE" ]; then
    # Read the result
    RESULT=$(cat "$RESULT_FILE")
    
    # Display macOS notification
    osascript -e "display notification \"$RESULT\" with title \"Spotify Staging Classification\" sound name \"Glass\""
    
    # Clean up
    rm -f "$RESULT_FILE"
    
    echo "Staging classification completed!"
    echo "$RESULT"
else
    echo "No result file found - automation may have failed"
fi