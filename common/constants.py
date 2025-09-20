"""
Constants for the Spotify automation system.

This module centralizes all constant values used across the system
to make configuration and maintenance easier.
"""

# Playlist folder constants
FOLDER_PLAYLIST_PREFIX = "📁"  # Prefix for folder playlists (e.g., "📁 House")

# Classification constants
UNCLASSIFIED_PLAYLIST_NAME = "Unclassified"
STAGING_PLAYLIST_NAME = "New"  # Default staging playlist name

# Genre folder names (must match data/playlist_folders.json)
GENRE_FOLDERS = [
    "House",
    "Electronic",
    "Bass",
    "Alive",
    "Rave",
    "Rock",
    "Vibes",
    "Sierra",
    "Ride",
    "Funk Soul",
    "Reggae",
    "Spiritual",
    "Soft",
    "Chill",
]

# Default descriptions for folder playlists
FOLDER_PLAYLIST_DESCRIPTIONS = {
    "House": "House music tracks automatically classified from the staging playlist",
    "Electronic": "Electronic music tracks automatically classified from the staging playlist",
    "Bass": "Bass-heavy tracks automatically classified from the staging playlist",
    "Alive": "Uplifting and energetic tracks automatically classified from the staging playlist",
    "Rave": "High-energy rave tracks automatically classified from the staging playlist",
    "Rock": "Rock music tracks automatically classified from the staging playlist",
    "Vibes": "Good vibes and chill tracks automatically classified from the staging playlist",
    "Sierra": "Nature and outdoor-inspired tracks automatically classified from the staging playlist",
    "Ride": "Smooth riding tracks automatically classified from the staging playlist",
    "Funk Soul": "Funk and soul music tracks automatically classified from the staging playlist",
    "Reggae": "Reggae music tracks automatically classified from the staging playlist",
    "Spiritual": "Spiritual and meditative tracks automatically classified from the staging playlist",
    "Soft": "Soft and gentle tracks automatically classified from the staging playlist",
    "Chill": "Chill and relaxing tracks automatically classified from the staging playlist",
}
