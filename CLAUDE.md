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

## Development Practices

- **Local Data Testing**: 
    - create local data tests first
    - Use centralized utilities in `common/playlist_data_utils.py` and `common/flow_character_utils.py`
    - Eliminates code duplication across test files
    - Real playlist data from `data/playlists/` for realistic testing

## Testing with Centralized Utilities

```python
from common.playlist_data_utils import PlaylistDataLoader

# Load playlist data 
playlists_dict = PlaylistDataLoader.load_playlists_from_directory(limit=50)

# Build artist mappings with flow integration
artist_to_playlists = PlaylistDataLoader.build_artist_to_playlists_mapping(
    playlists_dict, exclude_parent_playlists=True
)
```

## Documentation Practices

- keep docs minimal clear and concise