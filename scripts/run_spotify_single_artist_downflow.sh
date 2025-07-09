#!/bin/bash

# Single Artist Downflow automation script
# Processes single artist playlists from 'new' playlist

cd "$(dirname "$0")/.."

echo "Starting Spotify Single Artist Downflow automation..."
echo "$(date): Running single artist downflow" >> logs/automation.log

# Run the automation
uv run automations/spotify/single_artist_downflow/action.py

# Clean up test cache if in test environment to ensure sync with prod
if [[ "${ENVIRONMENT}" == "test" ]]; then
    echo "Cleaning up test cache to ensure sync with prod..."
    uv run scripts/update_cache.py --cleanup
fi

echo "Single Artist Downflow automation completed at $(date)"