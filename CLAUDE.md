# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a macOS automation framework focused on Spotify integrations. The project provides a modular system for creating automations that interact with Spotify's API and macOS system features like notifications and keyboard shortcuts.

## Core Architecture

The project uses a modular design with three main components:

### 1. Common Utilities (`common/`)
- `config.py`: Centralized configuration management with environment variable loading
- `spotify_utils.py`: Shared Spotify API utilities with retry logic and rate limiting
- `utils/notifications.py`: Cross-platform notification utilities

### 2. Automation Modules (`macros/`)
- Each automation is a self-contained module in its own directory
- Current automations:
  - `spotify/save_current.py`: Save currently playing track to library
  - `spotify/save_current_with_genre.py`: Save currently playing track and automatically sort into genre-specific playlists
  - `spotify/daily_liked_songs/action.py`: Add recently liked songs to a playlist
  - `spotify/playlist_flow/action.py`: Automatically flow songs between playlists using special naming conventions
- `template/`: Template structure for creating new automations

### 3. Data Processing (`download/`)
- Tools for downloading and analyzing Spotify playlist data
- Includes visualization capabilities and genre mapping

## Development Commands

### Environment Setup
```bash
# Set up virtual environment and dependencies
uv venv
uv pip install -r requirements.txt

# For development dependencies (includes pytest for testing)
uv pip install -e ".[dev]"
```

### Testing with Pytest

The project uses pytest for comprehensive testing of the playlist flow automation:

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run only fast tests (skip performance tests)
make test-fast

# Run only slow/performance tests
make test-slow

# Clean up test playlists only
make test-cleanup-only

# Show available pytest markers
make test-markers

# Run specific test categories
SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "cycle"
SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "unicode"
SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "performance"

# Run specific tests by name
SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -k "basic_flow"
SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -k "self_reference"
```

#### Test Categories and Markers

- `@pytest.mark.spotify` - Tests requiring Spotify API access
- `@pytest.mark.integration` - Integration tests (automatically applied to all playlist flow tests)
- `@pytest.mark.slow` - Slow-running tests (performance tests)
- `@pytest.mark.cycle` - Cycle detection tests
- `@pytest.mark.unicode` - Unicode character handling tests
- `@pytest.mark.performance` - Performance/load tests
- `@pytest.mark.cleanup` - Cleanup functionality tests

### Running Automations
```bash
# Direct Python execution
python -m macros.spotify.save_current
python -m macros.spotify.save_current_with_genre
python -m macros.spotify.daily_liked_songs.action
python -m macros.spotify.playlist_flow.action

# Using shell scripts (recommended for production)
./scripts/run_spotify_save.sh
./scripts/run_spotify_genre_save.sh
./scripts/run_spotify_daily_liked.sh
./scripts/run_spotify_playlist_flow.sh

# Using installed entry points
save-spotify-track

# Using Makefile wrapper
make run macros.spotify.save_current
```

### Data Processing
```bash
# Download all user playlists
python -m download.download_playlists

# Analyze playlist genres
python -m download.map_playlist_genre
python -m download.playlist_genres_aggregator

# Visualize playlist network
python -m visualize.visualize
```

## Configuration Requirements

All automations require a `.env` file in the project root with:

```env
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
VENV_PATH=/path/to/project/.venv  # Optional, defaults to PROJECT_ROOT/.venv

# Optional for daily liked songs automation
DAILY_LIKED_PLAYLIST_ID=playlist_id_here
DAILY_LIKED_PLAYLIST_NAME=Your Playlist Name
```

## Key Implementation Details

### Spotify API Integration
- All Spotify clients use OAuth2 with scoped permissions
- Cache files are automatically secured with 600 permissions
- Built-in retry logic handles rate limiting and server errors
- Separate cache files for different automations prevent conflicts

### macOS Integration
- Shell scripts handle environment activation and notifications
- Results are passed via temporary files for cross-process communication
- Compatible with Automator workflows for keyboard shortcuts
- LaunchAgent templates available for scheduled execution

### Error Handling
- All automations provide user-friendly error messages
- Failures are logged and communicated via notifications
- Robust handling of missing tracks, deleted playlists, and API errors

### Authentication & Cache Management
- **Cache Sharing Issue**: Different automations create separate cache files (e.g., `.playlist_flow_cache_test`, `.save_current_cache_test`)
- **Manual Re-auth**: When developing new features, you may need to re-authenticate via browser when cache names don't match
- **Recommendation**: Use existing cache names when possible, or plan for manual OAuth flow during development

## Creating New Automations

1. Copy the template structure: `cp -r macros/template macros/your_automation`
2. Copy the shell script: `cp scripts/template.sh scripts/run_your_automation.sh`
3. Implement your logic in the `action.py` file
4. Update shell script with correct module path
5. Add entry point to `pyproject.toml` if desired

## Package Management

The project uses UV for Python package management and supports both pip and UV workflows. Dependencies are pinned in both `requirements.txt` and `pyproject.toml` for consistency.

## Best Practices and Guidelines

- **Safe Defaults**: All genre classification automatically defaults to test environment with mock client
- **Environment Control**: Use `SPOTIFY_ENV=prod` to explicitly use production Spotify API
- **Default Behavior**: Without environment override, uses mock client with production data snapshot
- Run all scripts through test env unless otherwise specified

## Development Tips

- Use make targets to run tests

## Playlist Flow Feature

The playlist flow automation uses special characters in playlist names to create parent-child relationships:

- **Parent playlists**: Names ending with `>` (e.g., "Rock>")
- **Child playlists**: Names starting with `<` (e.g., "<Rock Favorites")  
- **Self-referencing**: Names with both `<` and `>` (e.g., "<Pop> Hits")

The system automatically moves songs from parent playlists to their children, with comprehensive cycle detection, Unicode support, and performance optimization for large playlist collections.

## Genre Classification Feature

The genre classification system automatically sorts saved songs into genre-specific playlists using folder naming conventions and hybrid classification:

### Folder Naming Convention
- **Format**: `[Genre] PlaylistName [FlowChars]`
- **Examples**: 
  - `[Rock] Collection 🎵` - Rock folder, parent playlist
  - `[Electronic] Daily Finds 🎵` - Electronic folder, child flows to parent
  - `[Jazz] Favorites` - Jazz folder, standalone playlist

### Classification System
- **Primary**: Artist genres from Spotify API
- **Secondary**: Audio features analysis (danceability, energy, valence, etc.)
- **Hybrid approach**: Uses artist genres first, falls back to audio features
- **Configurable**: Genre mappings can be customized via environment variables

### Supported Genres
Default mappings include Rock, Electronic, Jazz, Pop, Hip Hop, Country, R&B, and Classical with appropriate genre keywords and audio feature profiles.

### Usage
```bash
# Save current track with genre classification (uses safe defaults)
python -m macros.spotify.save_current_with_genre

# Test classification safely with mock data
python test_safe_genre_save.py

# Use production Spotify API (requires explicit environment)
SPOTIFY_ENV=prod python -m macros.spotify.save_current_with_genre

# Test classification on specific track
python -m macros.spotify.save_current_with_genre test [track_id]

# Run complete test workflow
python test_genre_save.py
```

## Current Focus

- Genre classification system is now fully implemented with comprehensive testing
- Playlist flow system is fully implemented with comprehensive testing