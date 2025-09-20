# Library Cache Sync

This repository now keeps a single normalized cache of the prod Spotify
account's playlists under `data/library`. The cache is maintained by the
`sync_prod_library_cache` helper in `common/library_sync.py`.

## Directory Layout

```
data/
└── library/
    ├── manifest.json          # summary of authored playlists
    └── playlists/
        └── <playlist_id>.json # one file per playlist with lightweight tracks
```

`manifest.json` tracks the latest `snapshot_id`, the number of tracks, and the
timestamp of the most recent sync for each playlist. The per-playlist files
store simplified track entries (`added_at`, `added_by`, and core track fields)
that downstream code can normalize consistently.

## Usage

```python
from common.library_sync import sync_prod_library_cache

summary = sync_prod_library_cache(limit=5, include_tracks=False)  # metadata-only trial run
print(summary)
```

The sync is intentionally restricted to the prod environment to avoid
accidentally overwriting prod data while testing.

Pass explicit playlist IDs (or a small ``limit``) when you want to test against
just a subset of the library without touching the rest of the cache. Set
``include_tracks=False`` for metadata-only refreshes (faster, ideal for
playlist-flow), or keep it at the default ``True`` when you need track listings
available for artist matching and other automations. The sync always rebuilds
from live Spotify data, so legacy dumps in ``data/playlists`` are no longer
used.

Downstream consumers should rely on `PlaylistDataLoader.load_playlists_from_directory`,
which now reads directly from the manifest-aware cache.
