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

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")


def get_env(key, default=None):
    """Get an environment variable, with optional default."""
    return os.environ.get(key, default)


# Common configuration values
CLIENT_ID = get_env("CLIENT_ID")
CLIENT_SECRET = get_env("CLIENT_SECRET")
VENV_PATH = get_env("VENV_PATH", str(PROJECT_ROOT / ".venv"))

# Ensure paths are initialized as strings in env
if not get_env("VENV_PATH"):
    os.environ["VENV_PATH"] = VENV_PATH

# Spotify Daily Liked Songs Configuration
DAILY_LIKED_PLAYLIST_ID = get_env("DAILY_LIKED_PLAYLIST_ID")
DAILY_LIKED_PLAYLIST_NAME = get_env("DAILY_LIKED_PLAYLIST_NAME", "Daily Liked Songs")
