"""
Configuration management for all macros and automations.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
MACROS_DIR = PROJECT_ROOT / "macros"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"

# Determine which environment to load - default to test for safety
SPOTIFY_ENV = os.environ.get("SPOTIFY_ENV", "test")

# Load environment-specific configuration
env_file = PROJECT_ROOT / f".env.{SPOTIFY_ENV}"
if env_file.exists():
    load_dotenv(env_file, override=True)  # Override any existing env vars
    print(f"Loaded environment: {SPOTIFY_ENV}")
else:
    # Fall back to default .env file
    load_dotenv(PROJECT_ROOT / ".env")
    print(f"Using default .env (environment '{SPOTIFY_ENV}' not found)")


def get_env(key, default=None):
    """Get an environment variable, with optional default."""
    return os.environ.get(key, default)


def get_config_value(key, default=None):
    """Get a configuration value from environment or return default."""
    return get_env(key, default)


# Common configuration values
CLIENT_ID = get_env("CLIENT_ID")
CLIENT_SECRET = get_env("CLIENT_SECRET")
VENV_PATH = get_env("VENV_PATH", str(PROJECT_ROOT / ".venv"))

# Export environment for use by other modules
CURRENT_ENV = SPOTIFY_ENV

# Ensure paths are initialized as strings in env
if not get_env("VENV_PATH"):
    os.environ["VENV_PATH"] = VENV_PATH

# Spotify Daily Liked Songs Configuration
DAILY_LIKED_PLAYLIST_ID = get_env("DAILY_LIKED_PLAYLIST_ID")
DAILY_LIKED_PLAYLIST_NAME = get_env("DAILY_LIKED_PLAYLIST_NAME", "Daily Liked Songs")

# Spotify Playlist Flow Configuration
PLAYLIST_FLOW_ENABLED = get_env("PLAYLIST_FLOW_ENABLED", "true").lower() == "true"
PLAYLIST_FLOW_SPECIAL_CHARS = get_env("PLAYLIST_FLOW_SPECIAL_CHARS", "♪♫♬♩♭♯♮🎵🎶⚡◆◇★☆♦♥♠♣❇️✅♻️🔱💠")
PLAYLIST_FLOW_SKIP_CYCLES = get_env("PLAYLIST_FLOW_SKIP_CYCLES", "true").lower() == "true"
PLAYLIST_FLOW_CACHE_TTL_HOURS = int(get_env("PLAYLIST_FLOW_CACHE_TTL_HOURS", "24"))
PLAYLIST_FLOW_USE_CACHE = get_env("PLAYLIST_FLOW_USE_CACHE", "true").lower() == "true"

# Genre Classification Configuration
GENRE_CLASSIFICATION_ENABLED = get_env("GENRE_CLASSIFICATION_ENABLED", "true").lower() == "true"
GENRE_CLASSIFICATION_FALLBACK_PLAYLIST = get_env("GENRE_CLASSIFICATION_FALLBACK_PLAYLIST", "Unclassified")
GENRE_CLASSIFICATION_USE_AUDIO_FEATURES = get_env("GENRE_CLASSIFICATION_USE_AUDIO_FEATURES", "true").lower() == "true"
