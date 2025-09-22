# Make targets for library synchronization

.PHONY: sync-prod-library sync-staging-library

# Sync prod account playlists into data/library cache (manifest + playlist files)
sync-prod-library:
	SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache as f; import json; r=f(); print(json.dumps(r, indent=2))"

# Apply cached prod library to the current (staging/test) account
sync-staging-library:
	uv run python -c "from common.library_sync import sync_library_cache_to_current_account as f; import json; r=f(); print(json.dumps(r, indent=2))"
