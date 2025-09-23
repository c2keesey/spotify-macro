## Folder Sorter

Automates sorting tracks from the `New` playlist into per-folder aggregator playlists using cached library data.

### What it does

- Builds a per-folder artist index from cached playlists listed in `data/playlist_folders.json`.
- Discovers or creates one aggregator per folder named with brackets: `「<Folder>」`.
- For each track in `New`, if any artist appears in any playlist within a folder, adds the track to that folder’s aggregator.
- Tracks can be added to multiple folder aggregators. Unmatched tracks are left untouched.
- When not using `--keep`, removes tracks from `New` if they were added to at least one aggregator.

### Key decisions

- **Aggregator naming**: standardized to bracket form only: `「<Folder>」`. No emoji/prefix support.
- **Classification source**: uses the manifest-driven cache in `data/library/` (no live reads for matching logic).
- **Creation**: missing aggregators are auto-created for each folder before processing.
- **Ordering**: additions preserve the order of tracks as they appear in `New` (oldest first by playlist position).
- **Safety**: works in `SPOTIFY_ENV=test` and `prod`. Only writes are: creating aggregators, adding to aggregators, and (optionally) removing from `New`.

### Data dependencies

- `data/playlist_folders.json`: source of truth for folder → playlists (filenames may end with `.json`; names are normalized).
- Cached library at `data/library/` (manifest + playlist JSON files). Populate via the sync utilities in `common/library_sync.py`.

### Configuration

- **SPOTIFY_NEW_PLAYLIST_NAME**: name of the source playlist (default: `New`).

### CLI

- `--keep`: do not remove matched tracks from `New`. If omitted, matched tracks are removed after successful adds.

### Usage

- With virtualenv/env handled by uv:

```bash
uv run python -m automations.spotify.folder_sorter.action --keep
uv run python -m automations.spotify.folder_sorter.action
```

- Or via the runner (loads `.env`, shows a macOS notification):

```bash
SPOTIFY_ENV=test ./scripts/run_spotify_folder_sort.sh --keep
SPOTIFY_ENV=prod ./scripts/run_spotify_folder_sort.sh --keep
```

### Output & notifications

- Writes a concise summary to `/tmp/spotify_folder_sort_result.txt` used by the runner for a macOS notification.
- Summary includes counts: scanned, matched, folders affected, added, removed-from-New, aggregators created, unresolved refs (folder entries not found in cache).

### Notes

- Order guarantee assumes the `New` playlist’s current ordering reflects chronological addition (Spotify app appends new tracks to the end by default). If you manually reorder `New`, processing follows that displayed order.

### TODOs

- [ ] automate flow
- [ ] run without keep
- [ ] create a latest playlist with similar logic but for latest n months of tracks
- [ ] single playlist artists automatic flow
- [ ] create new artist playlist or keep them in new?
- [ ] make sure reruns update properly (no dups, playlist_folders.json changing/reorged)

### Future

- [ ] auto create folders based on highest accuracy of classification
