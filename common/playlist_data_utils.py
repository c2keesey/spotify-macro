"""
Centralized utilities for loading and processing local playlist data.

Consolidates repeated patterns across tests and analysis scripts for:
- Loading playlist JSON files from data directory
- Normalizing track data structures
- Building artist-to-playlist mappings
- Finding single playlist artists
- Parent/child playlist filtering

This module eliminates 400+ lines of duplicated code across multiple files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from collections import defaultdict

from .flow_character_utils import is_parent_playlist


class PlaylistDataLoader:
    """Centralized playlist data loading and processing utilities."""
    
    @staticmethod
    def get_data_directory() -> Path:
        """Get the standard data directory path."""
        current_file = Path(__file__).resolve()
        # Navigate up to project root, then to data directory
        project_root = current_file.parent.parent
        return project_root / "data" / "playlists"
    
    @staticmethod
    def load_playlists_from_directory(
        data_dir: Optional[Union[str, Path]] = None,
        limit: Optional[int] = None,
        normalize_tracks: bool = True,
        include_empty: bool = False,
        verbose: bool = False
    ) -> Dict[str, Dict]:
        """
        Load playlist data from JSON files with consistent normalization.
        
        Args:
            data_dir: Directory containing playlist JSON files. Uses default if None.
            limit: Maximum number of playlists to load. No limit if None.
            normalize_tracks: Whether to normalize track data structures.
            include_empty: Whether to include playlists with no tracks.
            verbose: Whether to print loading progress.
            
        Returns:
            Dictionary mapping playlist_id to playlist data including normalized tracks.
        """
        if data_dir is None:
            data_dir = PlaylistDataLoader.get_data_directory()
        else:
            data_dir = Path(data_dir)
        
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        playlists_dict = {}
        loaded_count = 0
        
        if verbose:
            print("Loading playlist data from local files...")
        
        for playlist_file in data_dir.glob("*.json"):
            # Skip Python cache files
            if playlist_file.name == "__init__.py":
                continue
                
            # Check limit
            if limit is not None and loaded_count >= limit:
                break
            
            try:
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    playlist_data = json.load(f)
                
                playlist_id = playlist_data.get("playlist_id", playlist_file.stem)
                playlist_name = playlist_data.get("playlist_name", playlist_file.stem)
                
                # Process tracks
                tracks = []
                if normalize_tracks:
                    for track_data in playlist_data.get("tracks", []):
                        normalized_track = PlaylistDataLoader.normalize_track_data(track_data)
                        if normalized_track:
                            tracks.append(normalized_track)
                else:
                    tracks = playlist_data.get("tracks", [])
                
                # Skip empty playlists if requested
                if not include_empty and len(tracks) == 0:
                    if verbose:
                        print(f"  Skipped '{playlist_name}' (empty)")
                    continue
                
                playlists_dict[playlist_id] = {
                    "name": playlist_name,
                    "tracks": tracks,
                    "total_tracks": len(tracks),
                    "original_data": playlist_data  # Keep original for reference
                }
                
                loaded_count += 1
                
                if verbose:
                    print(f"  Loaded '{playlist_name}' ({len(tracks)} tracks)")
                    
            except Exception as e:
                if verbose:
                    print(f"  Error loading {playlist_file.name}: {e}")
                continue
        
        if verbose:
            print(f"✅ Loaded {len(playlists_dict)} playlists")
        
        return playlists_dict
    
    @staticmethod
    def normalize_track_data(track_item: Dict) -> Optional[Dict]:
        """
        Normalize track data structure handling all JSON variations.
        
        Handles different structures:
        - Direct track data
        - Nested under 'track' key
        - Nested under 'item_track' key
        - Playlist item wrappers
        
        Args:
            track_item: Raw track data from JSON
            
        Returns:
            Normalized track dictionary or None if invalid
        """
        if not isinstance(track_item, dict):
            return None
        
        # Handle different nesting structures
        track = track_item
        
        # Check for nested structures
        if "track" in track_item and isinstance(track_item["track"], dict):
            track = track_item["track"]
        elif "item_track" in track_item:
            track = track_item["item_track"]
        
        # Skip invalid tracks
        if not track or not isinstance(track, dict):
            return None
        
        # Skip local files
        if track.get("is_local", False):
            return None
        
        # Must have valid ID
        track_id = track.get("id")
        if not track_id:
            return None
        
        # Extract and normalize artist information
        artists = []
        for artist in track.get("artists", []):
            if isinstance(artist, dict):
                artist_data = {
                    "id": artist.get("id"),
                    "name": artist.get("name")
                }
                # Only include artists with valid IDs
                if artist_data["id"]:
                    artists.append(artist_data)
        
        # Must have at least one valid artist
        if not artists:
            return None
        
        return {
            "id": track_id,
            "name": track.get("name", "Unknown"),
            "artists": artists,
            "duration_ms": track.get("duration_ms"),
            "popularity": track.get("popularity"),
            "explicit": track.get("explicit", False),
            "preview_url": track.get("preview_url"),
            "external_urls": track.get("external_urls", {}),
            "album": track.get("album", {})
        }
    
    @staticmethod
    def build_artist_to_playlists_mapping(
        playlists_dict: Dict[str, Dict],
        exclude_parent_playlists: bool = False,
        verbose: bool = False
    ) -> Dict[str, Set[str]]:
        """
        Build mapping of artist ID to set of playlist IDs they appear in.
        
        Args:
            playlists_dict: Dictionary of playlist data
            exclude_parent_playlists: Whether to exclude parent playlists from mapping
            verbose: Whether to print exclusion details
            
        Returns:
            Dictionary mapping artist_id to set of playlist_ids
        """
        artist_to_playlists = defaultdict(set)
        excluded_parents = []
        
        for playlist_id, playlist_data in playlists_dict.items():
            playlist_name = playlist_data["name"]
            
            # Skip parent playlists if requested
            if exclude_parent_playlists and is_parent_playlist(playlist_name):
                excluded_parents.append(playlist_name)
                continue
            
            for track in playlist_data["tracks"]:
                for artist in track["artists"]:
                    artist_id = artist.get("id")
                    if artist_id:
                        artist_to_playlists[artist_id].add(playlist_id)
        
        if verbose and excluded_parents:
            print(f"Excluded {len(excluded_parents)} parent playlists from uniqueness check:")
            for parent_name in excluded_parents[:3]:  # Show first 3
                print(f"  🎵 {parent_name}")
            if len(excluded_parents) > 3:
                print(f"  ... and {len(excluded_parents) - 3} more parent playlists")
            print("(Parent playlists receive songs automatically via playlist flow)")
        
        return artist_to_playlists
    
    @staticmethod
    def find_single_playlist_artists(
        artist_to_playlists: Dict[str, Set[str]]
    ) -> Set[str]:
        """
        Find artists that appear in exactly one playlist.
        
        Args:
            artist_to_playlists: Mapping of artist_id to set of playlist_ids
            
        Returns:
            Set of artist IDs that appear in exactly one playlist
        """
        single_playlist_artists = set()
        
        for artist_id, playlists in artist_to_playlists.items():
            if len(playlists) == 1:
                single_playlist_artists.add(artist_id)
        
        return single_playlist_artists
    
    @staticmethod
    def find_playlist_by_name(
        playlists_dict: Dict[str, Dict],
        playlist_name: str,
        case_sensitive: bool = False
    ) -> Optional[str]:
        """
        Find playlist ID by name.
        
        Args:
            playlists_dict: Dictionary of playlist data
            playlist_name: Name to search for
            case_sensitive: Whether to use case-sensitive matching
            
        Returns:
            Playlist ID if found, None otherwise
        """
        target_name = playlist_name if case_sensitive else playlist_name.lower()
        
        for playlist_id, playlist_data in playlists_dict.items():
            candidate_name = playlist_data["name"]
            if not case_sensitive:
                candidate_name = candidate_name.lower()
                
            if candidate_name == target_name:
                return playlist_id
        
        return None
    
    @staticmethod
    def get_playlist_statistics(playlists_dict: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Generate comprehensive statistics about loaded playlists.
        
        Args:
            playlists_dict: Dictionary of playlist data
            
        Returns:
            Dictionary containing various statistics
        """
        total_playlists = len(playlists_dict)
        total_tracks = sum(len(p["tracks"]) for p in playlists_dict.values())
        
        # Count unique artists
        all_artists = set()
        for playlist_data in playlists_dict.values():
            for track in playlist_data["tracks"]:
                for artist in track["artists"]:
                    artist_id = artist.get("id")
                    if artist_id:
                        all_artists.add(artist_id)
        
        # Track count distribution
        track_counts = [len(p["tracks"]) for p in playlists_dict.values()]
        avg_tracks = sum(track_counts) / len(track_counts) if track_counts else 0
        
        # Parent/child playlist counts
        parent_count = sum(1 for p in playlists_dict.values() if is_parent_playlist(p["name"]))
        child_count = total_playlists - parent_count
        
        return {
            "total_playlists": total_playlists,
            "total_tracks": total_tracks,
            "unique_artists": len(all_artists),
            "average_tracks_per_playlist": avg_tracks,
            "max_tracks": max(track_counts) if track_counts else 0,
            "min_tracks": min(track_counts) if track_counts else 0,
            "parent_playlists": parent_count,
            "child_playlists": child_count,
            "empty_playlists": sum(1 for count in track_counts if count == 0)
        }
    
    @staticmethod
    def sample_playlists(
        playlists_dict: Dict[str, Dict],
        sample_size: int,
        strategy: str = "random"
    ) -> Dict[str, Dict]:
        """
        Sample a subset of playlists for testing.
        
        Args:
            playlists_dict: Dictionary of playlist data
            sample_size: Number of playlists to sample
            strategy: Sampling strategy ("random", "largest", "smallest", "diverse")
            
        Returns:
            Sampled subset of playlists
        """
        import random
        
        if sample_size >= len(playlists_dict):
            return playlists_dict
        
        playlist_items = list(playlists_dict.items())
        
        if strategy == "random":
            sampled_items = random.sample(playlist_items, sample_size)
        elif strategy == "largest":
            sorted_items = sorted(playlist_items, key=lambda x: len(x[1]["tracks"]), reverse=True)
            sampled_items = sorted_items[:sample_size]
        elif strategy == "smallest":
            sorted_items = sorted(playlist_items, key=lambda x: len(x[1]["tracks"]))
            sampled_items = sorted_items[:sample_size]
        elif strategy == "diverse":
            # Mix of large, medium, and small playlists
            sorted_items = sorted(playlist_items, key=lambda x: len(x[1]["tracks"]), reverse=True)
            third = sample_size // 3
            sampled_items = (
                sorted_items[:third] +  # Largest
                sorted_items[len(sorted_items)//2:len(sorted_items)//2 + third] +  # Medium
                sorted_items[-third:]  # Smallest
            )
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")
        
        return dict(sampled_items)