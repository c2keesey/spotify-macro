# Playlist Flow

**Status:** Not implemented yet

## Overview

The playlist flow automation manages hierarchical relationships between Spotify playlists, automatically promoting songs from child playlists to their parent collections.

## Key Features

### Playlist Hierarchy

- **Parent playlists**: Identified by special characters at the beginning (e.g., "🎵 Collection")
- **Child playlists**: Identified by special characters at the end (e.g., "Daily Mix 🎵")

### Core Functionality

1. **Upward Flow**: Songs from child playlists automatically promoted to their parent collections
2. **Cycle Detection**: Prevents infinite loops in complex playlist hierarchies
3. **Caching**: Uses sophisticated caching to avoid API rate limits during large operations

### Automation Features

- **Cron scheduling**: Runs daily at 9 AM via automated cron jobs
- **Flow character parsing**: Complex Unicode handling for playlist relationship detection
- **Telegram notifications**: Sends detailed reports of playlist operations
