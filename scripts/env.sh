#!/bin/bash
# Environment switching utilities for Spotify automation framework
# Usage: source scripts/env.sh
# Then use: spotify-test, spotify-prod, spotify-status

spotify-test() {
    export SPOTIFY_ENV=test
    echo "✅ Switched to TEST environment"
    echo "Cache files will use '_test' suffix"
}

spotify-prod() {
    export SPOTIFY_ENV=prod
    echo "✅ Switched to PRODUCTION environment"  
    echo "Cache files will use '_prod' suffix"
}

spotify-status() {
    echo "Current environment: ${SPOTIFY_ENV:-prod}"
    echo "Environment file: .env.${SPOTIFY_ENV:-prod}"
    
    if [[ -f ".env.${SPOTIFY_ENV:-prod}" ]]; then
        echo "✅ Environment file exists"
    else
        echo "❌ Environment file missing - run setup first"
    fi
    
    echo ""
    echo "Available environments:"
    for env_file in .env.*; do
        if [[ -f "$env_file" && "$env_file" != ".env" ]]; then
            env_name=$(basename "$env_file" | sed 's/\.env\.//')
            if [[ "$env_name" == "${SPOTIFY_ENV:-prod}" ]]; then
                echo "  ➤ $env_name (current)"
            else
                echo "    $env_name"
            fi
        fi
    done
}

echo "Spotify environment utilities loaded!"
echo "Commands: spotify-test, spotify-prod, spotify-status"