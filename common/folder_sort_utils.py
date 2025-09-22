"""
Utilities for folder-based playlist sorting and aggregator naming.

- Normalizes names using flow character utilities
- Parses configurable aggregator prefixes
- Generates and matches aggregator playlist display names
- Supports bracket-based naming like 「Alive」

This module intentionally avoids Spotify API dependencies; it is pure string logic
used by automations.
"""

from __future__ import annotations

from .flow_character_utils import normalize_and_clean

LEFT_BRACKET = "「"
RIGHT_BRACKET = "」"


def normalize_name_key(name: str) -> str:
    """Normalize a human-visible name to a stable lowercase key.

    This applies NFC normalization, strips zero-width characters, trims whitespace,
    and lowercases the result for case-insensitive matching.
    """
    cleaned = normalize_and_clean(name or "")
    return cleaned.strip().lower()


def strip_json_suffix(filename: str) -> str:
    """Remove a trailing .json suffix from a display filename if present."""
    name = filename or ""
    if name.endswith(".json"):
        return name[:-5]
    return name


def make_aggregator_name(folder_name: str) -> str:
    """Derive the aggregator playlist name for a folder using the standard brackets."""
    return f"{LEFT_BRACKET}{folder_name}{RIGHT_BRACKET}"


def is_aggregator_for_folder(
    playlist_name: str,
    folder_name: str,
) -> bool:
    """Check whether a playlist name matches the standard bracket aggregator name.

    Expected form: f"{LEFT_BRACKET}{folder_name}{RIGHT_BRACKET}"
    """
    if not folder_name:
        return False

    expected = f"{LEFT_BRACKET}{folder_name}{RIGHT_BRACKET}"
    return normalize_name_key(playlist_name) == normalize_name_key(expected)
