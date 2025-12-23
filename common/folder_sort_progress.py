"""
Progress tracking for folder sorter.

Tracks which tracks have been manually processed after sorting,
allowing the sorting algorithm to be rerun without losing manual curation work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from common.config import PROJECT_ROOT


def get_progress_file_path() -> Path:
    """Get the path to the progress state file."""
    return PROJECT_ROOT / "data" / "folder_sort_progress.json"


@dataclass
class FolderSortProgress:
    """Tracks which tracks have been processed for each folder."""

    processed_tracks: Dict[str, List[str]] = field(default_factory=dict)
    """Mapping of track_uri -> list of folder names where it's been processed"""

    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    """Timestamp of last update"""

    def mark_processed(self, track_uri: str, folder_name: str) -> None:
        """Mark a track as processed for a specific folder.

        Args:
            track_uri: Spotify track URI
            folder_name: Folder name (e.g., "Alive", "Electronic")
        """
        if track_uri not in self.processed_tracks:
            self.processed_tracks[track_uri] = []

        if folder_name not in self.processed_tracks[track_uri]:
            self.processed_tracks[track_uri].append(folder_name)
            self.last_updated = datetime.now().isoformat()

    def is_processed(self, track_uri: str, folder_name: str) -> bool:
        """Check if a track has been processed for a specific folder.

        Args:
            track_uri: Spotify track URI
            folder_name: Folder name

        Returns:
            True if track is marked as processed for this folder
        """
        if track_uri not in self.processed_tracks:
            return False

        return folder_name in self.processed_tracks[track_uri]

    def get_processed_tracks_for_folder(self, folder_name: str) -> Set[str]:
        """Get all track URIs processed for a specific folder.

        Args:
            folder_name: Folder name

        Returns:
            Set of track URIs processed for this folder
        """
        result = set()
        for track_uri, folders in self.processed_tracks.items():
            if folder_name in folders:
                result.add(track_uri)
        return result

    def unmark_processed(self, track_uri: str, folder_name: str) -> None:
        """Remove a track from the processed list for a specific folder.

        Args:
            track_uri: Spotify track URI
            folder_name: Folder name
        """
        if track_uri in self.processed_tracks:
            if folder_name in self.processed_tracks[track_uri]:
                self.processed_tracks[track_uri].remove(folder_name)
                self.last_updated = datetime.now().isoformat()

                # Clean up empty entries
                if not self.processed_tracks[track_uri]:
                    del self.processed_tracks[track_uri]

    def clear(self) -> None:
        """Clear all progress data."""
        self.processed_tracks = {}
        self.last_updated = datetime.now().isoformat()

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed tracks.

        Returns:
            Dictionary with stats: total_tracks, total_folder_assignments, folders
        """
        total_assignments = sum(len(folders) for folders in self.processed_tracks.values())

        # Count unique folders
        all_folders = set()
        for folders in self.processed_tracks.values():
            all_folders.update(folders)

        return {
            "total_tracks": len(self.processed_tracks),
            "total_folder_assignments": total_assignments,
            "unique_folders": len(all_folders),
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "processed_tracks": self.processed_tracks,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> FolderSortProgress:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            processed_tracks=data.get("processed_tracks", {}),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )


def load_progress_state(progress_file: Path = None) -> FolderSortProgress:
    """Load progress state from file.

    Args:
        progress_file: Optional path to progress file (uses default if not provided)

    Returns:
        FolderSortProgress instance (empty if file doesn't exist)
    """
    if progress_file is None:
        progress_file = get_progress_file_path()

    if not progress_file.exists():
        return FolderSortProgress()

    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return FolderSortProgress.from_dict(data)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load progress state: {e}")
        return FolderSortProgress()


def save_progress_state(progress: FolderSortProgress, progress_file: Path = None) -> None:
    """Save progress state to file.

    Args:
        progress: Progress state to save
        progress_file: Optional path to progress file (uses default if not provided)
    """
    if progress_file is None:
        progress_file = get_progress_file_path()

    # Ensure directory exists
    progress_file.parent.mkdir(parents=True, exist_ok=True)

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress.to_dict(), f, indent=2, ensure_ascii=False)


def mark_tracks_as_processed(
    track_uris: List[str],
    folder_name: str,
    progress: FolderSortProgress
) -> int:
    """Mark multiple tracks as processed for a folder.

    Args:
        track_uris: List of track URIs
        folder_name: Folder name
        progress: Progress state to update

    Returns:
        Number of tracks marked
    """
    count = 0
    for uri in track_uris:
        if not progress.is_processed(uri, folder_name):
            progress.mark_processed(uri, folder_name)
            count += 1
    return count


def is_track_processed(track_uri: str, folder_name: str, progress: FolderSortProgress) -> bool:
    """Check if a track is processed for a folder.

    Convenience function that wraps progress.is_processed().

    Args:
        track_uri: Track URI
        folder_name: Folder name
        progress: Progress state

    Returns:
        True if processed
    """
    return progress.is_processed(track_uri, folder_name)


def get_processed_tracks_for_folder(folder_name: str, progress: FolderSortProgress) -> Set[str]:
    """Get all processed tracks for a folder.

    Convenience function that wraps progress.get_processed_tracks_for_folder().

    Args:
        folder_name: Folder name
        progress: Progress state

    Returns:
        Set of track URIs
    """
    return progress.get_processed_tracks_for_folder(folder_name)
