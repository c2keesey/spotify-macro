"""
Mock Spotify client for testing using _data snapshot.

Provides a mock implementation of the Spotify client that uses the production
data snapshot from _data/ directory instead of making real API calls.
"""

import json
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class MockSpotifyClient:
    """Mock Spotify client that uses _data snapshot for testing."""
    
    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """
        Initialize mock client with data from _data directory.
        
        Args:
            data_dir: Path to _data directory, defaults to project root/_data
        """
        if data_dir is None:
            # Default to project root/_data
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "_data"
        
        self.data_dir = Path(data_dir)
        self._load_data()
    
    def _load_data(self):
        """Load all data files from _data directory."""
        # Load playlist folders
        playlist_folders_file = self.data_dir / "playlist_folders.json"
        if playlist_folders_file.exists():
            with open(playlist_folders_file, 'r') as f:
                self.playlist_folders = json.load(f)
        else:
            self.playlist_folders = {}
        
        # Load playlist to genres mapping
        playlist_genres_file = self.data_dir / "playlist_to_genres.json"
        if playlist_genres_file.exists():
            with open(playlist_genres_file, 'r') as f:
                self.playlist_to_genres = json.load(f)
        else:
            self.playlist_to_genres = {}
        
        # Load artist genres
        artist_genres_file = self.data_dir / "artist_genres.json"
        if artist_genres_file.exists():
            with open(artist_genres_file, 'r') as f:
                self.artist_genres = json.load(f)
        else:
            self.artist_genres = {}
        
        # Load individual playlist files
        self.playlists = {}
        playlists_dir = self.data_dir / "playlists"
        if playlists_dir.exists():
            for playlist_file in playlists_dir.glob("*.json"):
                with open(playlist_file, 'r') as f:
                    playlist_data = json.load(f)
                    # Use playlist name as key, removing .json extension
                    playlist_name = playlist_file.stem
                    self.playlists[playlist_name] = playlist_data
        
        # Create playlist ID to name mapping
        self._create_playlist_mappings()
    
    def _create_playlist_mappings(self):
        """Create mappings between playlist IDs, names, and data."""
        self.id_to_name = {}
        self.name_to_id = {}
        self.id_to_data = {}
        
        # Map from playlist_to_genres.json (has real IDs)
        for playlist_id, playlist_info in self.playlist_to_genres.items():
            playlist_name = playlist_info.get('playlist_name', '')
            if playlist_name:
                self.id_to_name[playlist_id] = playlist_name
                self.name_to_id[playlist_name] = playlist_id
                
                # Find corresponding playlist data file
                playlist_filename = f"{playlist_name}.json"
                if playlist_name in self.playlists:
                    self.id_to_data[playlist_id] = self.playlists[playlist_name]
    
    def current_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Mock current_user_playlists API call."""
        # Convert playlist data to Spotify API format
        items = []
        all_playlists = list(self.playlist_to_genres.items())
        
        # Apply pagination
        start = offset
        end = min(offset + limit, len(all_playlists))
        
        for playlist_id, playlist_info in all_playlists[start:end]:
            items.append({
                'id': playlist_id,
                'name': playlist_info.get('playlist_name', ''),
                'owner': {'id': 'mock_user'},
                'public': True,
                'tracks': {'total': 0}  # Will be filled by playlist_tracks if needed
            })
        
        return {
            'items': items,
            'next': f'next_page_{end}' if end < len(all_playlists) else None,
            'total': len(all_playlists),
            'limit': limit,
            'offset': offset
        }
    
    def playlist_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Mock playlist_tracks API call."""
        if playlist_id not in self.id_to_data:
            return {'items': [], 'next': None, 'total': 0}
        
        playlist_data = self.id_to_data[playlist_id]
        # Handle both formats: {tracks: {items: []}} and {tracks: []}
        tracks_data = playlist_data.get('tracks', [])
        if isinstance(tracks_data, dict):
            tracks = tracks_data.get('items', [])
        else:
            tracks = tracks_data
        
        # Apply pagination
        start = offset
        end = min(offset + limit, len(tracks))
        
        return {
            'items': tracks[start:end],
            'next': f'next_page_{end}' if end < len(tracks) else None,
            'total': len(tracks),
            'limit': limit,
            'offset': offset
        }
    
    def track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Mock track API call."""
        # Find track in any playlist
        for playlist_data in self.id_to_data.values():
            tracks_data = playlist_data.get('tracks', [])
            if isinstance(tracks_data, dict):
                tracks = tracks_data.get('items', [])
            else:
                tracks = tracks_data
                
            for track_item in tracks:
                # Handle flattened format where track data is in the item itself
                if track_item.get('track') == True:
                    # Flattened format - track data is in track_item
                    if track_item.get('id') == track_id:
                        return copy.deepcopy(track_item)
                else:
                    # Nested format - track data is in track_item['track']
                    track = track_item.get('track', {})
                    if track.get('id') == track_id:
                        return copy.deepcopy(track)
        return None
    
    def artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Mock artist API call."""
        if artist_id in self.artist_genres:
            artist_data = self.artist_genres[artist_id]
            # Extract genres from the artist data (which contains full artist object)
            if isinstance(artist_data, dict):
                genres = artist_data.get('genres', [])
                name = artist_data.get('name', f'Artist_{artist_id}')
            else:
                # Fallback if data format is different
                genres = artist_data if isinstance(artist_data, list) else []
                name = f'Artist_{artist_id}'
            
            return {
                'id': artist_id,
                'name': name,
                'genres': genres
            }
        return None
    
    def audio_features(self, track_ids: List[str]) -> List[Optional[Dict[str, float]]]:
        """Mock audio_features API call."""
        # Generate mock audio features based on track ID
        features = []
        for track_id in track_ids:
            # Generate deterministic but realistic audio features
            # This is a simplified mock - in reality you'd want more sophisticated generation
            hash_val = hash(track_id) % 1000
            features.append({
                'danceability': (hash_val % 100) / 100.0,
                'energy': ((hash_val * 2) % 100) / 100.0,
                'acousticness': ((hash_val * 3) % 100) / 100.0,
                'valence': ((hash_val * 4) % 100) / 100.0,
                'speechiness': ((hash_val * 5) % 100) / 100.0,
                'instrumentalness': ((hash_val * 6) % 100) / 100.0,
                'liveness': ((hash_val * 7) % 100) / 100.0,
                'loudness': -60 + ((hash_val * 8) % 60),
                'tempo': 60 + ((hash_val * 9) % 140),
                'time_signature': 4,
                'key': hash_val % 12,
                'mode': hash_val % 2,
                'duration_ms': 180000 + (hash_val * 1000)
            })
        return features
    
    def playlist_add_items(self, playlist_id: str, track_uris: List[str]) -> Dict[str, Any]:
        """Mock playlist_add_items API call."""
        # For testing, we don't actually modify the data
        # Just return success response
        return {'snapshot_id': f'mock_snapshot_{len(track_uris)}'}
    
    def playlist_remove_all_occurrences_of_items(self, playlist_id: str, track_uris: List[str]) -> Dict[str, Any]:
        """Mock playlist_remove_all_occurrences_of_items API call."""
        return {'snapshot_id': f'mock_snapshot_remove_{len(track_uris)}'}
    
    def get_folder_playlists(self, folder_name: str) -> List[Dict[str, str]]:
        """Get all playlists that belong to a specific folder."""
        folder_playlists = []
        
        if folder_name in self.playlist_folders:
            for playlist_filename in self.playlist_folders[folder_name]:
                # Remove .json extension to get playlist name
                playlist_name = playlist_filename.replace('.json', '')
                
                # Find the playlist ID
                playlist_id = self.name_to_id.get(playlist_name)
                if playlist_id:
                    folder_playlists.append({
                        'id': playlist_id,
                        'name': playlist_name
                    })
        
        return folder_playlists
    
    def get_playlist_genres(self, playlist_id: str) -> List[str]:
        """Get genres associated with a playlist based on its tracks."""
        if playlist_id in self.playlist_to_genres:
            genre_counts = self.playlist_to_genres[playlist_id].get('genre_song_counts', {})
            return list(genre_counts.keys())
        return []
    
    def get_deep_copy(self):
        """Return a deep copy of this client for safe testing."""
        new_client = MockSpotifyClient(self.data_dir)
        # Deep copy all data to prevent test interference
        new_client.playlist_folders = copy.deepcopy(self.playlist_folders)
        new_client.playlist_to_genres = copy.deepcopy(self.playlist_to_genres)
        new_client.artist_genres = copy.deepcopy(self.artist_genres)
        new_client.playlists = copy.deepcopy(self.playlists)
        new_client._create_playlist_mappings()
        return new_client


def create_mock_spotify_client(data_dir: Optional[Union[str, Path]] = None) -> MockSpotifyClient:
    """Factory function to create a mock Spotify client."""
    return MockSpotifyClient(data_dir)