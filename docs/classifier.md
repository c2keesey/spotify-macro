# Staging Classification

Automated song classification using a multi-strategy approach.

## Overview

The staging classification system processes songs from a staging playlist (default: "new") and distributes them to appropriate target playlists.

## Classification Strategies

### Strategy 1: Artist Matching (100% accuracy)

If an artist appears in exactly one playlist across your library, new songs by that artist are automatically added to that playlist.

- Excludes parent playlists from uniqueness check (they receive songs via flow)
- Targets child playlists where artists are manually curated

### Strategy 2: Genre Classification (76% accuracy)

Falls back to genre-based classification using:
- Artist genres from Spotify API
- Configurable genre-to-folder mappings
- Audio feature analysis as secondary signal

### Strategy 3: Unclassified

Songs that can't be classified are moved to an "Unclassified" playlist for manual review.

## Usage

```bash
SPOTIFY_ENV=prod uv run python -m automations.spotify.staging_classification.action
```

## Related Automations

- **artist_matching**: Simpler version focused only on artist matching
- **single_artist_downflow**: Adds folder playlist routing on top of artist matching
- **folder_sorter**: Uses `data/playlist_folders.json` to sort into folder aggregators

## Configuration

Genre mappings can be customized via:
- `GENRE_MAPPING` environment variable (JSON)
- Dynamic discovery from playlist folder structure
- Default mappings in `common/genre_classification_utils.py`
