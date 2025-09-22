# Make targets for library synchronization

.PHONY: sync-prod-library sync-staging-library update-library-vcs

# Sync prod account playlists into data/library cache (manifest + playlist files)
sync-prod-library:
	SPOTIFY_ENV=prod uv run python -c "from common.library_sync import sync_prod_library_cache as f; import json; r=f(); print(json.dumps(r, indent=2))"

# Apply cached prod library to the current (staging/test) account
sync-staging-library:
	uv run python -c "from common.library_sync import sync_library_cache_to_current_account as f; import json; r=f(); print(json.dumps(r, indent=2))"

# Export prod playlists to URIs snapshot, commit and push to library-vcs submodule
update-library-vcs:
	@echo "🎵 Exporting playlist URIs snapshot..."
	SPOTIFY_ENV=prod uv run python scripts/export_library_uris.py --out data/playlist_uris.json
	@echo "📦 Copying to submodule and committing..."
	rsync -av --delete data/playlist_uris.json data/library-vcs/
	cd data/library-vcs && git add playlist_uris.json && git commit -m "library: update URIs snapshot $$(date '+%Y-%m-%d')" && git push
	@echo "🔗 Updating submodule pointer..."
	git add data/library-vcs && git commit -m "library-vcs: bump snapshot $$(date '+%Y-%m-%d')"
	@echo "✅ Library VCS updated and pushed!"
