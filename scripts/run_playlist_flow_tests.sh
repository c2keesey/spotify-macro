#!/bin/bash

# Run playlist flow automation tests
# This script sets up the test environment and runs the test suite

# Ensure we're using the correct working directory
cd "$(dirname "$0")/.." || exit 1

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to test environment
export SPOTIFY_ENV=${SPOTIFY_ENV:-test}

# Default to Python in PATH if PYTHON_PATH not set
PYTHON="${PYTHON_PATH:-python3}"

# Activate the virtual environment if VENV_PATH is set
if [ -n "$VENV_PATH" ] && [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Get the test command (default to help)
TEST_COMMAND=${1:-help}

echo "🧪 Playlist Flow Test Runner"
echo "Environment: $SPOTIFY_ENV"
echo "Command: $TEST_COMMAND"
echo ""

# Run the test suite
case $TEST_COMMAND in
    "help")
        echo "Available test commands:"
        echo "  all         - Run all tests"
        echo "  basic       - Test basic flow functionality"
        echo "  cycle       - Test cycle detection"
        echo "  unicode     - Test Unicode/emoji handling"
        echo "  self        - Test self-referencing playlists"
        echo "  multi       - Test multi-hop chains"
        echo "  performance - Test with large playlists"
        echo "  cleanup     - Clean up all test playlists"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run_playlist_flow_tests.sh all"
        echo "  ./scripts/run_playlist_flow_tests.sh cleanup"
        echo "  SPOTIFY_ENV=prod ./scripts/run_playlist_flow_tests.sh basic"
        ;;
    *)
        echo "Running: uv run python -m tests.test_playlist_flow $TEST_COMMAND"
        uv run python -m tests.test_playlist_flow "$TEST_COMMAND"
        ;;
esac