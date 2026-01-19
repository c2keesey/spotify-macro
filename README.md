# Spotify Macro

A collection of Spotify playlist automations built around a hierarchical "flow" system.

## Concept

Playlists are organized using special characters in their names to indicate relationships:

- **Parent playlists**: Special char at the start (e.g., `🎵 Collection`)
- **Child playlists**: Special char at the end (e.g., `Daily Mix 🎵`)

Songs flow automatically from child playlists to their matching parent playlists.

## Automations

| Name | Description |
|------|-------------|
| **playlist_flow** | Flow songs from child to parent playlists based on special characters |
| **folder_sorter** | Sort "New" playlist into folder aggregators using artist matching |
| **staging_classification** | Classify songs using artist matching + genre analysis |
| **artist_matching** | Add tracks by single-playlist artists to their home playlist |
| **daily_liked_songs** | Add recently liked songs to a designated playlist |
| **save_current** | Save the currently playing track to your library |

## Setup

1. Create a Spotify app at https://developer.spotify.com/dashboard
2. Add redirect URIs: `http://127.0.0.1:8888/callback` (prod) and `http://127.0.0.1:8889/callback` (test)
3. Create `.env.prod` (and optionally `.env.test`):
   ```
   CLIENT_ID=your_client_id
   CLIENT_SECRET=your_client_secret
   ```

4. Authenticate:
   ```bash
   SPOTIFY_ENV=prod uv run python scripts/spotify_auth.py auth
   ```

5. Sync library cache (required for most automations):
   ```bash
   SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache; sync_prod_library_cache()"
   ```

## Usage

```bash
# Run playlist flow
SPOTIFY_ENV=prod uv run python -m automations.spotify.playlist_flow.action

# Run folder sorter (--keep to not remove from New)
SPOTIFY_ENV=prod uv run python -m automations.spotify.folder_sorter.action

# Save current track
SPOTIFY_ENV=prod uv run python -m automations.spotify.save_current
```

## Project Structure

```
automations/spotify/     # Automation modules
common/                  # Shared utilities (auth, API, caching)
data/library/            # Cached playlist data
docs/                    # Additional documentation
scripts/                 # CLI tools (auth, sync)
```

## Documentation

- [Playlist Flow](docs/playlist_flow.md) - Hierarchical playlist relationships
- [Folder Sorter](docs/folder_sorter.md) - Sorting into folder aggregators
- [Classification](docs/classifier.md) - Multi-strategy song classification
- [Library Cache](docs/library_cache.md) - Local playlist caching
- [Cron Setup](docs/cron_setup.md) - Scheduling automations
