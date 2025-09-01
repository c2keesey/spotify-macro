# macOS Spotify Automations

Minimal, accurate, and organized set of Spotify automations for macOS.

What works today:
- Playlist Flow (child → parent via special characters)
- Artist Matching (single‑playlist artist routing from staging)
- Staging Classification (artist matching first, genre fallback)
- Daily Liked Songs (collects recently liked tracks)
- Save Current Track (optionally with simple genre sorting)

Requirements
- macOS, Python 3.8+
- UV (https://github.com/astral-sh/uv)
- Spotify app credentials in `.env.test` / `.env.prod`

Authenticate (SSH‑friendly)
- Test: `SPOTIFY_ENV=test uv run python scripts/spotify_auth.py url`
- Then complete: `SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth --code '<auth_code>'`
- Repeat for prod with `SPOTIFY_ENV=prod`

Run
- Playlist flow: `SPOTIFY_ENV=test uv run python -m automations.spotify.playlist_flow.action`
- Artist matching: `SPOTIFY_ENV=test uv run python -m automations.spotify.artist_matching.action`
- Staging classification: `SPOTIFY_ENV=test uv run python -m automations.spotify.staging_classification.action`
- Daily liked: `SPOTIFY_ENV=test uv run python -m automations.spotify.daily_liked_songs.action`
- Save current: `SPOTIFY_ENV=test uv run python -m automations.spotify.save_current`
- With genre: `SPOTIFY_ENV=test uv run python -m automations.spotify.save_current_with_genre`

Notes
- Telegram notifications are optional. If `telegram_toolkit` is not installed, notifications are disabled gracefully.
- Caches and large data are not packaged or committed.

3. Set up the virtual environment and install dependencies:

   ```
   uv venv
   uv pip install -r requirements.txt
   ```

4. Configure any specific requirements for automations you want to use (see below)

## Core Flow System

### ⬆️ Upward Flow: Playlist Flow Automation

Automatic hierarchical music promotion using special character naming conventions.

#### How It Works
- **Child playlists** (ending with special chars): `Daily Mix 🎵`, `Favorites 🎵`
- **Parent collections** (starting with special chars): `🎵 Main Collection`
- Songs automatically flow from children to their matching parents
- Supports complex many-to-many relationships and transitive flows

#### Features
- **Cycle Detection**: Prevents infinite loops in playlist relationships
- **Unicode Support**: Handles complex emoji and special characters
- **Performance Optimized**: 95% API call reduction through intelligent caching
- **Comprehensive Testing**: Robust edge case handling

### ⬇️ Downward Flow: Classification Automations

Intelligent distribution of new music from staging to appropriate target playlists.

#### Multi-Strategy Classification
1. **Artist Matching**: Single-playlist artist detection (✅ Implemented)
2. **Genre Classification**: Multi-class composite system with 66% F1 score (✅ Implemented)
3. **Audio Feature Analysis**: Electronic music specialist patterns (✅ Implemented)
4. **Integration Layer**: Cohesive classification pipeline (🔧 In Progress)

#### Process Flow
1. **Staging**: Liked songs collected in staging playlist (e.g., "new")
2. **Classification**: Multi-strategy analysis determines target playlists
3. **Distribution**: Songs placed in appropriate child playlists
4. **Promotion**: Upward flow automatically moves songs to parent collections

## Individual Automations

#### Spotify Add to Library

Save the currently playing Spotify track to your library with a keyboard shortcut.

#### Setup

1. Create Spotify Apps for both test and production:

   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Create two apps: one for testing, one for production
   - Set Redirect URIs:
     - **Test environment**: `http://127.0.0.1:8889/callback`
     - **Production environment**: `http://127.0.0.1:8888/callback`

2. Create environment-specific configuration files:

   **`.env.test`** (for testing):
   ```
   CLIENT_ID=your_test_client_id_here
   CLIENT_SECRET=your_test_client_secret_here
   VENV_PATH=/path/to/your/project/.venv
   ```

   **`.env.prod`** (for production):
   ```
   CLIENT_ID=your_prod_client_id_here
   CLIENT_SECRET=your_prod_client_secret_here
   VENV_PATH=/path/to/your/project/.venv
   ```

3. Authenticate (SSH-compatible process):

   ```bash
   # Test environment authentication
   SPOTIFY_ENV=test uv run python scripts/spotify_auth.py url
   # Open the URL in any browser, get the auth code from error page
   SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth --code '<auth_code>'
   
   # Production environment authentication
   SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py url
   SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py auth --code '<auth_code>'
   ```

4. Follow the instructions in `workflows/spotify_save_current.md` to set up the Automator workflow and keyboard shortcut

#### Spotify Genre Classification

Core component of the downward flow system with automatic genre-based playlist organization.

##### Classification Engine Features

- **Multi-Class Composite Classification**: 66% F1 score with 95% coverage across 14 folders
- **Multi-Class Output**: Tracks can be assigned to multiple folders (19% of tracks)
- **Optimized Parameters**: Multi-class threshold of 0.05 for optimal performance  
- **Folder-Specific Strategies**: Enhanced genre, simple artist, balanced, and conservative approaches
- **Training Data Utilization**: Leverages existing multi-folder tracks in training data
- **Flow Integration**: Works seamlessly with playlist hierarchy system

#### Setup

1. Ensure you've created a Spotify App as described above.

2. Run the genre classification system:

   ```
   ./scripts/run_spotify_genre_save.sh
   ```

3. See `docs/genre_classification_research_findings.md` for detailed research and implementation notes

#### Spotify Daily Liked Songs

Staging component for the downward flow system, automatically collecting recent likes for classification.

#### Setup

1. Ensure you've created a Spotify App as described above.

2. Run the script manually to authenticate and create the playlist:

   ```
   ./scripts/run_spotify_daily_liked.sh
   ```

3. Follow the instructions in `workflows/spotify_daily_liked.md` to set up automatic daily execution

#### Spotify Playlist Flow (Upward Flow Engine)

Core upward flow automation using special character naming conventions for hierarchical music promotion.

##### Flow Relationship Features

- **Parent/Child Relationships**: Special characters define flow direction
  - Child playlists: Names ending with special chars (e.g., `Daily Mix 🎵`)
  - Parent collections: Names starting with special chars (e.g., `🎵 Main Collection`)
- **Many-to-Many Support**: Complex flow relationships between multiple playlists
- **Transitive Flows**: Multi-hop chains for sophisticated organization
- **Cycle Detection**: Prevents infinite loops in playlist relationships
- **Unicode Support**: Handles complex emoji and special character sequences
- **Performance Optimized**: 95% API call reduction through intelligent caching

#### Setup

1. Ensure you've created a Spotify App as described above.

2. Run the playlist flow automation:

   ```
   ./scripts/run_spotify_playlist_flow.sh
   ```

3. See `CLAUDE.md` for detailed playlist flow feature documentation

#### Artist Matching Automation (Classification Component)

Core component of the downward flow system that intelligently distributes songs based on single-playlist artist patterns.

##### Artist Detection Features

- **Single-Playlist Artist Detection**: Identifies artists that appear in only one playlist for targeted curation
- **Flow-Aware Analysis**: Excludes parent playlists from uniqueness checking since they receive songs automatically
- **Smart Targeting**: Adds songs to child playlists where artists are manually curated
- **Hierarchy Integration**: Works seamlessly with upward flow to organize music hierarchically
- **Duplicate Prevention**: Checks for existing tracks before adding
- **Robust Error Handling**: Gracefully handles permission errors and API failures

##### Classification Process

1. **Mapping Phase**: Analyzes all playlists to build artist-to-playlist relationships
2. **Filtering Phase**: Excludes parent playlists (e.g., `🎵 Collection`) from uniqueness analysis
3. **Detection Phase**: Identifies artists appearing in exactly one child playlist
4. **Distribution Phase**: For each song in staging playlist:
   - Checks if any artist is a single-playlist artist
   - Places song in the target child playlist where that artist is curated
   - Allows upward flow automation to handle promotion to parent collections

##### Performance Impact

- **+471 More Single-Playlist Artists**: 22% increase in potential matches through parent exclusion
- **Intelligent Curation**: Songs flow naturally from discovery → specialization → collections
- **Automated Organization**: Respects playlist hierarchy and flow relationships
- **Reduced Manual Work**: Eliminates need for manual organization between related playlists

#### Setup

1. Ensure you've created a Spotify App as described above.

2. Run the artist matching automation:

   ```
   ./scripts/run_spotify_artist_matching.sh
   ```

3. Or run directly with Python:

   ```
   uv run python -m automations.spotify.artist_matching.action
   ```

#### Configuration

The automation works with any playlist named "new" as the source by default. You can modify the source playlist name in the code if needed.

#### Artist Distribution Analysis

Analysis tool for understanding collection patterns and optimizing both flow directions.

##### Analysis Features
- **Single-Playlist Artist Discovery**: Identifies artists for targeted classification
- **Curation Pattern Analysis**: Understands how music is distributed across playlists
- **Flow Optimization Data**: Provides insights for improving both upward and downward flow
- **Collection Health Metrics**: Tracks organization effectiveness and automation performance

#### Setup

1. Ensure you have downloaded your playlist data:

   ```
   python -m data.processing.download_playlists
   ```

2. Run the artist distribution analysis:

   ```
   python -m analysis.playlist.analyze_single_playlist_artists
   ```

## Creating a New Automation

To create a new automation:

1. Copy the template directory structure:

   ```
   cp -r automations/template automations/your_new_automation
   ```

2. Copy the template shell script:

   ```
   cp scripts/template.sh scripts/run_your_new_automation.sh
   ```

3. Implement your automation logic in `automations/your_new_automation/action.py`

4. Update the shell script to use your new module path

5. Make the shell script executable:

   ```
   chmod +x scripts/run_your_new_automation.sh
   ```

6. Create documentation in the workflows directory

7. Update this README if needed

## Project Structure

```
spotify-automation/
├── common/               # Shared utilities and helpers
│   ├── config.py         # Configuration management
│   ├── spotify_utils.py  # Spotify API utilities with retry logic
│   ├── genre_classification_utils.py  # Hybrid classification system
│   └── utils/            # Utility functions
│       └── notifications.py  # Notification utilities
├── automations/          # Individual automation modules
│   ├── spotify/          # Spotify-related automations
│   │   ├── save_current.py           # Save current track to library
│   │   ├── save_current_with_genre.py # Save with automatic genre classification
│   │   ├── daily_liked_songs/        # Add recent liked songs to playlist
│   │   ├── artist_matching/          # Single-playlist artist matching
│   │   └── playlist_flow/            # Automatic playlist flow system
│   └── template/         # Template for new automations
├── analysis/             # Research and analysis scripts
│   ├── genre/            # Genre classification research
│   ├── playlist/         # Playlist analysis and patterns
│   └── optimization/     # Performance optimization
├── data/                 # Data management and processing
│   ├── processing/       # Data processing scripts
│   ├── playlists/        # Playlist JSON files (200+ playlists)
│   └── cache/            # Cache files and management
├── visualization/        # Data visualization tools
├── tests/                # Comprehensive testing framework
├── scripts/              # Shell scripts for running automations
│   ├── run_spotify_save.sh              # Run the Spotify save automation
│   ├── run_spotify_genre_save.sh        # Run genre classification automation
│   ├── run_spotify_daily_liked.sh       # Run daily liked songs automation
│   ├── run_spotify_playlist_flow.sh     # Run playlist flow automation
│   ├── run_spotify_artist_matching.sh   # Run artist matching automation
│   └── template.sh                      # Template shell script
├── workflows/            # Documentation for Automator workflows
│   ├── launchagents/     # Template plist files for LaunchAgents
│   ├── spotify_save_current.md  # Setup guide for Spotify workflow
│   └── spotify_daily_liked.md   # Setup guide for Daily Liked Songs
├── docs/                 # Feature documentation and research
├── .env                  # Environment variables (create this)
├── pyproject.toml        # Project configuration
└── requirements.txt      # Python dependencies
```

## Environment Variables

Create environment-specific configuration files for test and production environments:

### `.env.test` (Test Environment)
```
# Required - Test Spotify App credentials
CLIENT_ID=your_test_spotify_client_id
CLIENT_SECRET=your_test_spotify_client_secret

# Optional
VENV_PATH=/path/to/your/virtual/environment
PYTHON_PATH=/path/to/python/executable

# Spotify Daily Liked Songs (optional)
DAILY_LIKED_PLAYLIST_ID=test_playlist_id
DAILY_LIKED_PLAYLIST_NAME=Test Daily Liked Songs
```

### `.env.prod` (Production Environment)
```
# Required - Production Spotify App credentials  
CLIENT_ID=your_prod_spotify_client_id
CLIENT_SECRET=your_prod_spotify_client_secret

# Optional
VENV_PATH=/path/to/your/virtual/environment
PYTHON_PATH=/path/to/python/executable

# Spotify Daily Liked Songs (optional)
DAILY_LIKED_PLAYLIST_ID=your_playlist_id
DAILY_LIKED_PLAYLIST_NAME=Daily Liked Songs
```

### Environment Control
- Set `SPOTIFY_ENV=test` or `SPOTIFY_ENV=prod` to control which environment to use
- Defaults to `test` for safety
- Authentication is cached separately per environment

## Running Automations

All automations can be run individually or as part of the integrated flow system:

### Manual Operations
```bash
# Save current track (environment-aware)
SPOTIFY_ENV=test ./scripts/run_spotify_save.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_save.sh

# Save with genre classification
SPOTIFY_ENV=test ./scripts/run_spotify_genre_save.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_genre_save.sh
```

### Downward Flow (Classification)
```bash
# Staging: Collect recent likes
SPOTIFY_ENV=test ./scripts/run_spotify_daily_liked.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_daily_liked.sh

# Classification: Artist-based distribution
SPOTIFY_ENV=test ./scripts/run_spotify_artist_matching.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_artist_matching.sh

# Classification: Genre-based distribution (integrated with save)
SPOTIFY_ENV=test ./scripts/run_spotify_genre_save.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_genre_save.sh
```

### Upward Flow (Promotion)
```bash
# Hierarchical promotion
SPOTIFY_ENV=test ./scripts/run_spotify_playlist_flow.sh
SPOTIFY_ENV=prod ./scripts/run_spotify_playlist_flow.sh
```

### Direct Python Execution
```bash
# Individual components
SPOTIFY_ENV=test uv run python -m automations.spotify.daily_liked_songs.action  # Staging
SPOTIFY_ENV=test uv run python -m automations.spotify.artist_matching.action    # Classification
SPOTIFY_ENV=test uv run python -m automations.spotify.playlist_flow.action      # Promotion

# Manual operations
SPOTIFY_ENV=test uv run python -m automations.spotify.save_current
SPOTIFY_ENV=test uv run python -m automations.spotify.save_current_with_genre

# Switch to production environment as needed
SPOTIFY_ENV=prod uv run python -m automations.spotify.save_current
```

### Authentication Management
```bash
# SSH-compatible authentication setup
SPOTIFY_ENV=test uv run python scripts/spotify_auth.py url      # Get auth URL
SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth --code '<code>'  # Complete auth

# Test authentication
SPOTIFY_ENV=test uv run python scripts/spotify_auth.py test
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py test

# Check authentication status
SPOTIFY_ENV=test uv run python scripts/spotify_auth.py status
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py status
```

### Flow System Integration (Future)
```bash
# Complete classification pipeline (planned)
./scripts/run_classification_flow.sh

# Coordinated bidirectional flow (planned)
./scripts/run_full_flow_system.sh
```

## Acknowledgments

- BPM and key data provided by [GetSongBPM.com](https://getsongbpm.com)
- Music metadata from [Last.fm](https://www.last.fm) and [Deezer](https://www.deezer.com) APIs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
