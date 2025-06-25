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