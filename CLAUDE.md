# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Organization (Updated)

This repository has been reorganized for better structure and extensibility:

```
spotify-automation/
├── automations/          # Core automation functionality (renamed from macros/)
├── analysis/             # Research and analysis scripts (organized by category)
│   ├── genre/           # Genre classification research
│   ├── playlist/        # Playlist analysis and patterns
│   └── optimization/    # Performance optimization
├── data/                # Consolidated data management (renamed from _data/)
│   ├── processing/      # Data processing scripts (from download/)
│   ├── playlists/       # Playlist JSON files
│   └── cache/           # Cache files
├── visualization/       # Data visualization tools (renamed from visualize/)
├── common/              # Shared utilities (unchanged)
├── tests/               # Test suite (unchanged)
├── scripts/             # Shell scripts (unchanged)
└── workflows/           # macOS integration (unchanged)
```

## Project Overview

This is a comprehensive Spotify music collection management system featuring intelligent **bidirectional flow architecture**. The system automatically organizes music through two complementary processes:

- **⬆️ Upward Flow (Playlist Flow)**: Promotes curated music up playlist hierarchies using special naming conventions
- **⬇️ Downward Flow (Classification Flow)**: Intelligently distributes new music from staging to appropriate target playlists

The project provides a modular system for creating flow components that interact with Spotify's API and macOS system features, along with comprehensive analysis tools for optimizing flow patterns and collection organization.

## Bidirectional Flow Architecture

The system implements a sophisticated **bidirectional flow architecture** with five integrated components:

### 1. Flow System Core (`common/`)
- `config.py`: Centralized configuration management with environment variable loading
- `spotify_utils.py`: Shared Spotify API utilities with retry logic and rate limiting
- `genre_classification_utils.py`: Hybrid classification system for downward flow
- `utils/notifications.py`: Cross-platform notification utilities

### 2. Flow Components (`automations/`)
Each component is a self-contained module supporting the bidirectional flow system:

#### ⬆️ Upward Flow Components
- `spotify/playlist_flow/action.py`: Hierarchical music promotion using special naming conventions

#### ⬇️ Downward Flow Components  
- `spotify/daily_liked_songs/action.py`: Staging - collects recently liked songs
- `spotify/artist_matching/action.py`: Classification - single-playlist artist matching
- `spotify/save_current_with_genre.py`: Classification - genre-based distribution

#### Manual Operations
- `spotify/save_current.py`: Direct track saving to library

#### Development Support
- `template/`: Template structure for creating new flow components

### 3. Flow Analysis & Research (`analysis/`)
- `genre/`: Classification strategy research and optimization
- `playlist/`: Flow pattern analysis and hierarchy optimization
- `optimization/`: System performance and flow efficiency research

### 4. Flow Data Management (`data/`)
- `processing/`: Data pipeline supporting both flow directions
- `playlists/`: Playlist metadata for flow relationship mapping (200+ playlists)
- `cache/`: Performance caching for efficient flow operations

### 5. Flow Monitoring (`visualization/`)
- Data visualization tools for flow analysis and system monitoring
- Network analysis for understanding playlist relationships
- Performance metrics and flow efficiency reporting

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
python -m automations.spotify.save_current
python -m automations.spotify.save_current_with_genre
python -m automations.spotify.daily_liked_songs.action
python -m automations.spotify.playlist_flow.action
python -m automations.spotify.artist_matching.action

# Using shell scripts (recommended for production)
./scripts/run_spotify_save.sh
./scripts/run_spotify_genre_save.sh
./scripts/run_spotify_daily_liked.sh
./scripts/run_spotify_playlist_flow.sh
./scripts/run_spotify_artist_matching.sh

# Using installed entry points
save-spotify-track

# Using Makefile wrapper
make run macros.spotify.save_current
```

### Data Processing
```bash
# Download all user playlists
python -m data.processing.download_playlists

# Analyze playlist genres
python -m data.processing.map_playlist_genre
python -m data.processing.playlist_genres_aggregator

# Visualize playlist network
python -m visualization.visualize
```

### Analysis Tools
```bash
# Genre classification research
python -m analysis.genre.classify_playlist
python -m analysis.genre.test_genre_accuracy
python -m analysis.genre.hybrid_classification_systems

# Playlist analysis
python -m analysis.playlist.analyze_single_playlist_artists
python -m analysis.playlist.build_playlist_artist_mapping
python -m analysis.playlist.analyze_artist_folder_patterns

# Performance optimization
python -m analysis.optimization.optimize_classification
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

1. Copy the template structure: `cp -r automations/template automations/your_automation`
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

## ⬆️ Upward Flow: Playlist Flow System

The upward flow component automatically promotes curated music up playlist hierarchies using special character naming conventions:

### Flow Direction & Relationships
- **Child playlists**: Names ending with special characters (e.g., `Daily Mix 🎵`, `Favorites 🎵`)
- **Parent collections**: Names starting with special characters (e.g., `🎵 Main Collection`, `🎵 Rock Archive`)
- **Many-to-Many**: Complex relationships where playlists can flow to multiple parents
- **Transitive Flows**: Multi-hop chains for sophisticated organization

### Advanced Features
The system automatically moves songs from children to their matching parents, with comprehensive cycle detection, Unicode support, and performance optimization for large playlist collections.

**Status**: ✅ Fully implemented with comprehensive testing and production deployment

## ⬇️ Downward Flow: Classification System

The downward flow components intelligently distribute new music from staging to appropriate target playlists using multi-strategy classification:

### Multi-Strategy Classification Pipeline

#### 1. Artist Matching Classification (✅ Implemented)
- **Single-playlist artist detection**: Identifies artists appearing in only one playlist
- **Flow-aware targeting**: Excludes parent playlists from uniqueness analysis
- **Smart distribution**: Places songs in child playlists where artists are manually curated
- **Performance**: +471 more single-playlist artists identified (22% increase)

#### 2. Genre Classification (✅ Implemented)
- **Hybrid approach**: Artist genres → Audio features → Fallback classification
- **Electronic music specialist**: Optimized for electronic sub-genres (House, Techno, Bass, etc.)
- **High accuracy**: 76% accuracy with 63.4% precision (5x improvement over basic systems)
- **Folder naming integration**: Works with `[Genre] PlaylistName [FlowChars]` convention

#### 3. Integrated Classification Pipeline (🔧 In Progress)
- **Staging collection**: Daily liked songs collected in staging playlist (e.g., "new")
- **Multi-strategy analysis**: Combines artist matching, genre analysis, and audio features
- **Target distribution**: Places songs in appropriate child playlists
- **Upward flow integration**: Automatic promotion to parent collections via playlist flow

### Folder Naming Convention
- **Format**: `[Genre] PlaylistName [FlowChars]`
- **Examples**: 
  - `[Rock] Collection 🎵` - Rock genre, parent collection
  - `[Electronic] Daily Finds 🎵` - Electronic genre, child flows to parent
  - `[Jazz] Favorites` - Jazz genre, standalone playlist

### Supported Classification Strategies
1. **Artist Patterns**: Single-playlist artist detection with flow hierarchy awareness
2. **Genre Analysis**: Hybrid system combining Spotify genres and audio features
3. **Audio Features**: Electronic music specialist with sub-genre patterns
4. **Confidence Scoring**: Weighted classification with fallback strategies

### Usage
```bash
# Individual classification components
./scripts/run_spotify_artist_matching.sh     # Artist-based classification
./scripts/run_spotify_genre_save.sh         # Genre-based classification
./scripts/run_spotify_daily_liked.sh        # Staging collection

# Direct Python execution
uv run python -m automations.spotify.artist_matching.action
uv run python -m automations.spotify.save_current_with_genre
uv run python -m automations.spotify.daily_liked_songs.action

# Development testing
SPOTIFY_ENV=test python -m automations.spotify.save_current_with_genre test [track_id]
```

**Status**: 🔧 Core components implemented, integration pipeline in development

## Flow System Integration

### Bidirectional Flow Workflow

The complete system workflow demonstrates seamless integration between upward and downward flow:

#### Complete Flow Cycle
1. **🎵 Liked Songs** → **Staging Playlist** (e.g., "new")
2. **Staging** → **Classification Pipeline** → **Target Child Playlists**
3. **Child Playlists** → **Upward Flow** → **Parent Collections**

#### Flow-Aware Classification Benefits

**Key Innovation**: Classification system excludes parent playlists from analysis because:
- **Parent collections** (e.g., `🎵 Jazz Collection`) receive songs automatically via upward flow
- **Child playlists** (e.g., `Daily Jazz 🎵`) contain manually curated music for targeted classification
- **Smart targeting**: Songs placed in child playlists where artists are actively curated
- **Automatic promotion**: Upward flow handles hierarchical organization

#### Performance Impact
Real-world testing shows significant improvements from flow integration:
- **+471 more single-playlist artists** identified (2,102 → 2,573)
- **22% increase** in classification potential
- **13 parent playlists** correctly excluded from uniqueness analysis
- **36 child playlists** properly targeted for intelligent curation

#### Integration Benefits
1. **Intelligent Hierarchy Respect**: Classification system understands and leverages playlist relationships
2. **Automated Organization**: Songs flow naturally from discovery → specialization → collections
3. **Reduced Manual Work**: Eliminates need for manual organization between related playlists
4. **Enhanced Discovery**: More artists eligible for automatic matching and distribution

## System Status

### ⬆️ Upward Flow Status
- **Playlist Flow System**: ✅ Fully implemented with comprehensive testing and production deployment
- **Hierarchy Management**: ✅ Complete with cycle detection, Unicode support, and performance optimization
- **Flow Relationships**: ✅ Many-to-many, transitive, and complex relationship support

### ⬇️ Downward Flow Status
- **Artist Matching Classification**: ✅ Fully implemented with flow hierarchy integration
- **Genre Classification**: ✅ Hybrid system complete with 76% accuracy and 5x precision improvement
- **Staging Collection**: ✅ Daily liked songs automation implemented
- **Integrated Pipeline**: 🔧 Core components implemented, integration layer in development

### Current Development Focus
1. **Classification Flow Integration**: Connecting staging → classification → distribution pipeline
2. **Automated Workflow Orchestration**: Coordinating bidirectional flow execution
3. **System Monitoring**: Flow efficiency metrics and performance optimization
4. **Testing Framework**: Comprehensive testing for integrated bidirectional workflows