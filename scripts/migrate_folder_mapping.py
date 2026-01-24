#!/usr/bin/env python3
"""
One-time migration script: Convert playlist_folders.json to ID-based YAML.

Reads the name-based JSON mapping, resolves each playlist name to its ID
via the library manifest, and writes a new YAML file with IDs and
human-readable name comments.

Usage:
    python scripts/migrate_folder_mapping.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from common.folder_sort_utils import normalize_name_key, strip_json_suffix


def load_json_folders(json_path: Path) -> dict[str, list[str]]:
    """Load the original JSON folder mapping."""
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Strip .json suffix from playlist names
    normalized: dict[str, list[str]] = {}
    for folder_name, items in raw.items():
        normalized[folder_name] = [strip_json_suffix(x) for x in items]
    return normalized


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load the library manifest and return playlists dict."""
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}\n"
            "Run library sync first: SPOTIFY_ENV=prod uv run python -c "
            "'from common.library_sync import sync_prod_library_cache; sync_prod_library_cache()'"
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return manifest.get("playlists", {})


def build_name_to_id_index(playlists: dict[str, dict]) -> dict[str, tuple[str, str]]:
    """Build normalized name -> (playlist_id, original_name) index."""
    index: dict[str, tuple[str, str]] = {}
    for pid, entry in playlists.items():
        name = entry.get("name") or pid
        key = normalize_name_key(name)
        index[key] = (pid, name)
    return index


def write_yaml_with_comments(
    yaml_path: Path,
    folders: dict[str, list[str]],
    name_to_id: dict[str, tuple[str, str]],
) -> list[str]:
    """
    Write the YAML file with playlist IDs and name comments.

    Returns list of unresolved playlist names.
    """
    unresolved: list[str] = []
    lines: list[str] = []

    for folder_name, playlist_names in folders.items():
        lines.append(f"{folder_name}:")

        for name in playlist_names:
            key = normalize_name_key(name)
            if key in name_to_id:
                pid, original_name = name_to_id[key]
                lines.append(f"  - {pid}  # {original_name}")
            else:
                unresolved.append(f"{folder_name}:{name}")
                lines.append(f"  # UNRESOLVED: {name}")

        lines.append("")  # Blank line between folders

    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return unresolved


def main():
    json_path = PROJECT_ROOT / "data" / "playlist_folders.json"
    manifest_path = PROJECT_ROOT / "data" / "library" / "manifest.json"
    yaml_path = PROJECT_ROOT / "data" / "playlist_folders.yaml"

    print(f"Loading folder mapping from {json_path}")
    folders = load_json_folders(json_path)

    print(f"Loading manifest from {manifest_path}")
    playlists = load_manifest(manifest_path)
    print(f"  Found {len(playlists)} playlists in manifest")

    print("Building name index...")
    name_to_id = build_name_to_id_index(playlists)

    print(f"Writing YAML to {yaml_path}")
    unresolved = write_yaml_with_comments(yaml_path, folders, name_to_id)

    total_playlists = sum(len(names) for names in folders.values())
    resolved = total_playlists - len(unresolved)

    print(f"\nMigration complete:")
    print(f"  Folders: {len(folders)}")
    print(f"  Playlists resolved: {resolved}/{total_playlists}")

    if unresolved:
        print(f"\n  Unresolved ({len(unresolved)}):")
        for item in unresolved:
            print(f"    - {item}")
        return 1

    print(f"\nOutput written to: {yaml_path}")
    print("Verify the output, then delete data/playlist_folders.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
