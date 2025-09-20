# Repository Guidelines

## Project Structure & Module Organization

- `automations/` contains runnable flows; `automations/spotify` covers playlist flow, save-current, and staging classification, while `automations/template` documents the action contract.
- `common/` centralizes Spotify clients, caching, and env handling (`common/config.py`, `common/library_sync.py`); reuse these helpers instead of new globals.
- `scripts/` exposes cron-safe launchers that set the repo root and load `.env` automatically; prefer extending these rather than duplicating shell glue.
- Generated state lives under `data/library/` and `logs/`; treat them as caches that can be rebuilt, not as source.

## Build, Test, and Development Commands

- Use `uv` for all Python commands and package management tasks; do not mix in `pip` or `python -m venv`.
- `uv run python -m automations.spotify.save_current` saves the active track and emits desktop/Telegram notifications.

## Coding Style & Naming Conventions

- Follow PEP 8 with 4-space indents, snake_case symbols, and module docstrings mirroring `automations/spotify/save_current.py`.
- Annotate public functions and dataclasses
- Keep notification and log strings succinct, reusing emoji prefixes established in existing flows.
- Route new configuration through `common.config.get_config_value` so secrets remain in environment variables.

## Testing Guidelines

- Operate in `SPOTIFY_ENV=test` unless a change explicitly targets prod; the scripts export this by default.
- Place new cases in `tests/test_<feature>.py`; make fixtures write to the `*_test` cache files and clean them via the `cleanup` runner.
- For cron changes, run `./scripts/run_playlist_flow_cron.sh` locally and inspect `logs/playlist_flow_cron.log` for regressions before merging.

## Commit & Pull Request Guidelines

- Use imperative, scope-prefixed commit subjects (example: `playlist-flow: guard empty cycle`); wrap bodies at ~72 characters.
- Reference related issues or docs in the PR description and list exact commands run (env, script).
- Attach screenshots or log snippets when user-facing notifications or cron behavior changes.
- Confirm generated artifacts stay untracked; commit only the code or fixture updates needed for the change.

## Security & Configuration Tips

- Do not commit `.env*`, cache directories, or tokens; rotate credentials if they spill into logs.
- Reuse the helpers in `common/config.py` instead of hard-coding secrets or filesystem paths.
