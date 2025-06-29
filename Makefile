run:
	uv run python $(filter-out $@,$(MAKECMDGOALS)) $(args)

# Environment management
.PHONY: env-test env-prod env-status

env-test:
	@echo "Switching to TEST environment"
	@export SPOTIFY_ENV=test

env-prod:
	@echo "Switching to PRODUCTION environment"
	@export SPOTIFY_ENV=prod

env-status:
	@echo "Current environment: $${SPOTIFY_ENV:-prod}"
	@echo "Available environments:"
	@ls -1 .env.* 2>/dev/null | sed 's/\.env\./  - /' || echo "  No environment files found"

# Environment-aware run targets
run-test:
	SPOTIFY_ENV=test uv run python $(filter-out $@,$(MAKECMDGOALS)) $(args)

run-prod:
	SPOTIFY_ENV=prod uv run python $(filter-out $@,$(MAKECMDGOALS)) $(args)

# Pytest-based Testing
.PHONY: test test-verbose test-fast test-slow test-cleanup-only test-markers

test:
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py

test-verbose:
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -v -s

test-fast:
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "not slow"

test-slow:
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "slow"

test-cleanup-only:
	SPOTIFY_ENV=test uv run python -m pytest --cleanup-only

test-markers:
	SPOTIFY_ENV=test uv run python -m pytest --markers

# Legacy test targets (deprecated - use pytest targets above)
.PHONY: test-all test-basic test-cycle test-unicode test-self test-multi test-performance test-cleanup

test-all:
	@echo "⚠️  Deprecated: Use 'make test' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py

test-basic:
	@echo "⚠️  Deprecated: Use 'make test -k basic' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -k "basic"

test-cycle:
	@echo "⚠️  Deprecated: Use 'make test -m cycle' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "cycle"

test-unicode:
	@echo "⚠️  Deprecated: Use 'make test -m unicode' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "unicode"

test-self:
	@echo "⚠️  Deprecated: Use 'make test -k self_reference' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -k "self_reference"

test-multi:
	@echo "⚠️  Deprecated: Use 'make test -k multi_hop' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -k "multi_hop"

test-performance:
	@echo "⚠️  Deprecated: Use 'make test -m performance' instead"
	SPOTIFY_ENV=test uv run python -m pytest tests/test_playlist_flow.py -m "performance"

test-cleanup:
	@echo "⚠️  Deprecated: Use 'make test-cleanup-only' instead"
	SPOTIFY_ENV=test uv run python -m pytest --cleanup-only

# Playlist Flow Automation
.PHONY: playlist-flow playlist-flow-test playlist-flow-prod

playlist-flow:
	SPOTIFY_ENV=test uv run python -m macros.spotify.playlist_flow.action

playlist-flow-test:
	SPOTIFY_ENV=test uv run python -m macros.spotify.playlist_flow.action

playlist-flow-prod:
	SPOTIFY_ENV=prod uv run python -m macros.spotify.playlist_flow.action