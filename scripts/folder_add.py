#!/usr/bin/env python3
"""
Add a playlist to a folder in playlist_folders.yaml by name.

Resolves the playlist name via the library manifest and appends the ID
with a name comment to the specified folder section.

Usage:
    python scripts/folder_add.py <folder> <playlist_name>

Examples:
    python scripts/folder_add.py House "CRANK 🜍🜂"
    python scripts/folder_add.py Electronic "Horizon ⏣ ⌬"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from common.folder_sort_utils import normalize_name_key


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load the library manifest and return playlists dict."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return manifest.get("playlists", {})


def find_playlist_by_name(
    playlists: dict[str, dict],
    search_name: str,
) -> tuple[str, str] | None:
    """
    Find a playlist by name (case-insensitive, normalized).

    Returns (playlist_id, original_name) or None if not found.
    """
    search_key = normalize_name_key(search_name)

    for pid, entry in playlists.items():
        name = entry.get("name") or pid
        if normalize_name_key(name) == search_key:
            return (pid, name)

    return None


def parse_yaml(yaml_path: Path) -> tuple[dict[str, list[tuple[str, str]]], list[str]]:
    """
    Parse the YAML file into folder -> list of (id, comment) tuples.

    Returns (folders_dict, original_lines) for reconstruction.
    """
    if not yaml_path.exists():
        return {}, []

    with open(yaml_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    folders: dict[str, list[tuple[str, str]]] = {}
    current_folder: str | None = None

    # Pattern for folder line: "FolderName:"
    folder_pattern = re.compile(r"^([A-Za-z][A-Za-z0-9 ]*):$")
    # Pattern for ID line: "  - ID  # comment" or "  - ID"
    id_pattern = re.compile(r"^\s+-\s+(\S+)(?:\s+#\s*(.*))?$")

    for line in lines:
        folder_match = folder_pattern.match(line)
        if folder_match:
            current_folder = folder_match.group(1)
            folders[current_folder] = []
            continue

        if current_folder is not None:
            id_match = id_pattern.match(line)
            if id_match:
                playlist_id = id_match.group(1)
                comment = id_match.group(2) or ""
                folders[current_folder].append((playlist_id, comment))

    return folders, lines


def write_yaml(yaml_path: Path, folders: dict[str, list[tuple[str, str]]]) -> None:
    """Write folders dict back to YAML with proper formatting."""
    lines: list[str] = []

    for folder_name, entries in folders.items():
        lines.append(f"{folder_name}:")
        for pid, comment in entries:
            if comment:
                lines.append(f"  - {pid}  # {comment}")
            else:
                lines.append(f"  - {pid}")
        lines.append("")

    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Add a playlist to a folder in playlist_folders.yaml"
    )
    parser.add_argument("folder", help="Folder name (e.g., 'House', 'Electronic')")
    parser.add_argument("playlist_name", help="Playlist name to add")
    args = parser.parse_args()

    yaml_path = PROJECT_ROOT / "data" / "playlist_folders.yaml"
    manifest_path = PROJECT_ROOT / "data" / "library" / "manifest.json"

    # Load manifest
    playlists = load_manifest(manifest_path)

    # Find playlist by name
    result = find_playlist_by_name(playlists, args.playlist_name)
    if not result:
        print(f"Error: Playlist '{args.playlist_name}' not found in manifest")
        print(f"  (Searched {len(playlists)} playlists)")
        return 1

    playlist_id, original_name = result

    # Parse existing YAML
    folders, _ = parse_yaml(yaml_path)

    # Check if folder exists
    if args.folder not in folders:
        print(f"Error: Folder '{args.folder}' not found in {yaml_path}")
        print(f"  Available folders: {', '.join(folders.keys())}")
        return 1

    # Check if playlist already in folder
    existing_ids = {entry[0] for entry in folders[args.folder]}
    if playlist_id in existing_ids:
        print(f"Error: Playlist '{original_name}' already in folder '{args.folder}'")
        return 1

    # Add the playlist
    folders[args.folder].append((playlist_id, original_name))

    # Write back
    write_yaml(yaml_path, folders)

    print(f"Added '{original_name}' ({playlist_id}) to folder '{args.folder}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
