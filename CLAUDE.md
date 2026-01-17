# Spotify Macro

Spotify playlist automation system using hierarchical "flow" relationships.

## Quick Reference

### Running Automations
```bash
# All commands require SPOTIFY_ENV=prod or SPOTIFY_ENV=test
SPOTIFY_ENV=prod uv run python -m automations.spotify.<module>.action

# Available modules:
# - playlist_flow.action
# - folder_sorter.action
# - staging_classification.action
# - artist_matching.action
# - daily_liked_songs.action
# - save_current (no .action suffix)
```

### Authentication
```bash
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py auth
SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py status
```

### Library Cache
Most automations require the library cache to be populated:
```bash
SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache; sync_prod_library_cache()"
```

## Key Concepts

### Flow Characters
Playlist names use special characters to indicate hierarchy:
- Char at START = parent (receives songs): `🎵 Collection`
- Char at END = child (sends songs): `Daily Mix 🎵`

### Folder Structure
`data/playlist_folders.json` maps folder names to playlists for sorting.

## Code Layout

- `automations/spotify/` - Each automation has `action.py` with `run_action()` entry point
- `common/` - Shared utilities:
  - `spotify_utils.py` - Client init, retry logic
  - `library_sync.py` - Cache sync to `data/library/`
  - `flow_character_utils.py` - Parse flow chars from names
  - `playlist_data_utils.py` - Load cached playlist data

## Environment

- Uses `uv` for Python package management
- Requires `.env.prod` or `.env.test` with `CLIENT_ID` and `CLIENT_SECRET`
- Cache files stored in `common/.spotify_master_cache_{env}`
