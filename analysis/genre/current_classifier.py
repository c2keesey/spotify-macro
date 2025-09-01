"""
Current classifier implementation wrapping the existing artist-only classification system.

This represents the baseline performance using the existing artist-genre-based
classification from common/genre_classification_utils.py.
"""

import time
from typing import Dict, List, Set, Any, Optional

from common.genre_classification_utils import (
    get_artist_genres, 
    classify_by_genres, 
    get_genre_mapping,
    get_safe_spotify_client
)
from common.spotify_utils import initialize_spotify_client
from analysis.genre.classification_framework import BaseClassifier, ClassificationResult
from analysis.genre.classification_metrics import get_track_artists, calculate_folder_confidence_scores


class CurrentArtistOnlyClassifier(BaseClassifier):
    """
    Current artist-only classification system using existing genre classification utils.
    
    This classifier uses the existing approach:
    1. Get artist genres from Spotify API
    2. Map genres to folders using genre mapping
    3. Return folder predictions based on genre matches
    """
    
    def __init__(self):
        super().__init__("Current Artist-Only")
        self.genre_mapping = None
        self.spotify_client = None
        self.playlists_dict = None
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """
        Train the classifier by loading genre mappings and setting up Spotify client.
        
        Args:
            train_data: Training data dictionary containing:
                - playlists_dict: Playlist data for track lookup
                - Other data not used by this classifier
        """
        print(f"  Training {self.name}...")
        
        # Store playlist data for track lookup
        self.playlists_dict = train_data.get("playlists_dict", {})
        
        # Get Spotify client (prefer mock client for testing)
        self.spotify_client = get_safe_spotify_client()
        if self.spotify_client is None:
            # Fall back to real client if no mock available
            try:
                scope = "playlist-read-private playlist-read-collaborative"
                self.spotify_client = initialize_spotify_client(scope, "classification_test_cache")
            except Exception as e:
                print(f"    Warning: Could not initialize Spotify client: {e}")
                self.spotify_client = None
        
        # Get genre mapping (uses dynamic discovery with cached data)
        self.genre_mapping = get_genre_mapping(self.spotify_client, use_dynamic=True)
        
        if self.genre_mapping:
            folder_count = len(self.genre_mapping)
            print(f"    Loaded genre mapping with {folder_count} folders")
        else:
            print("    Warning: No genre mapping loaded")
        
        self.is_trained = True
        
    def predict(self, track_id: str) -> ClassificationResult:
        """
        Predict folder(s) for a track using artist genres.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            ClassificationResult with predicted folders and confidence scores
        """
        start_time = time.time()
        
        result = ClassificationResult(
            track_id=track_id,
            predicted_folders=[],
            method=self.name,
            reasoning=""
        )
        
        if not self.is_trained:
            result.reasoning = "Classifier not trained"
            return result
            
        if not self.spotify_client:
            result.reasoning = "No Spotify client available"
            return result
            
        try:
            # Get artist genres using existing utility
            artist_genres = get_artist_genres(self.spotify_client, track_id)
            
            if not artist_genres:
                result.reasoning = "No artist genres found"
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Classify using existing genre classification
            if self.genre_mapping:
                predicted_folders = classify_by_genres(artist_genres, self.genre_mapping)
                
                if predicted_folders:
                    result.predicted_folders = predicted_folders
                    result.confidence_scores = calculate_folder_confidence_scores(
                        predicted_folders, 
                        {}  # No special confidence factors for current system
                    )
                    result.reasoning = f"Matched genres: {', '.join(artist_genres[:3])}"
                else:
                    result.reasoning = f"No folder matches for genres: {', '.join(artist_genres[:3])}"
            else:
                result.reasoning = "No genre mapping available"
            
        except Exception as e:
            result.reasoning = f"Error during classification: {str(e)}"
            
        result.processing_time_ms = (time.time() - start_time) * 1000
        return result
        
    def get_info(self) -> Dict[str, Any]:
        """Get classifier information."""
        info = super().get_info()
        info.update({
            "description": "Artist-only classification using existing genre mapping system",
            "uses_audio_features": False,
            "uses_artist_patterns": False,
            "genre_folders": list(self.genre_mapping.keys()) if self.genre_mapping else [],
            "has_spotify_client": self.spotify_client is not None
        })
        return info


class CurrentSystemWithGenreMappingClassifier(BaseClassifier):
    """
    Enhanced version of current system that uses existing genre mapping but with local data.
    
    This version uses playlist data to get artist information instead of making API calls,
    making it more suitable for testing scenarios.
    """
    
    def __init__(self):
        super().__init__("Current System (Local Data)")
        self.genre_mapping = None
        self.spotify_client = None
        self.playlists_dict = None
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """
        Train the classifier by loading genre mappings.
        
        Args:
            train_data: Training data dictionary
        """
        print(f"  Training {self.name}...")
        
        # Store playlist data for track lookup
        self.playlists_dict = train_data.get("playlists_dict", {})
        
        # Get Spotify client for genre mapping (but not for predictions)
        self.spotify_client = get_safe_spotify_client()
        
        # Get genre mapping
        self.genre_mapping = get_genre_mapping(self.spotify_client, use_dynamic=True)
        
        if self.genre_mapping:
            folder_count = len(self.genre_mapping)
            print(f"    Loaded genre mapping with {folder_count} folders")
        else:
            print("    Warning: No genre mapping loaded")
        
        self.is_trained = True
        
    def predict(self, track_id: str) -> ClassificationResult:
        """
        Predict folder(s) for a track using artist genres from local data.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            ClassificationResult with predicted folders and confidence scores
        """
        start_time = time.time()
        
        result = ClassificationResult(
            track_id=track_id,
            predicted_folders=[],
            method=self.name,
            reasoning=""
        )
        
        if not self.is_trained:
            result.reasoning = "Classifier not trained"
            return result
            
        try:
            # Get artist information from local playlist data
            track_artists = get_track_artists(track_id, self.playlists_dict)
            
            if not track_artists:
                result.reasoning = "No artists found in local data"
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # For testing purposes, we'll simulate artist genres using a simple mapping
            # In a real scenario, this would use cached artist genre data
            artist_genres = self._get_simulated_artist_genres(track_artists)
            
            if not artist_genres:
                result.reasoning = "No artist genres available"
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Classify using existing genre classification
            if self.genre_mapping:
                predicted_folders = classify_by_genres(artist_genres, self.genre_mapping)
                
                if predicted_folders:
                    result.predicted_folders = predicted_folders
                    result.confidence_scores = calculate_folder_confidence_scores(
                        predicted_folders, 
                        {}  # No special confidence factors for current system
                    )
                    result.reasoning = f"Matched genres: {', '.join(artist_genres[:3])}"
                else:
                    result.reasoning = f"No folder matches for genres: {', '.join(artist_genres[:3])}"
            else:
                result.reasoning = "No genre mapping available"
            
        except Exception as e:
            result.reasoning = f"Error during classification: {str(e)}"
            
        result.processing_time_ms = (time.time() - start_time) * 1000
        return result
        
    def _get_simulated_artist_genres(self, track_artists: List[Dict[str, str]]) -> List[str]:
        """
        Simulate artist genres for testing purposes.
        
        In a real implementation, this would use cached artist genre data.
        For now, we'll use a simple mapping based on artist names.
        
        Args:
            track_artists: List of artist dictionaries
            
        Returns:
            List of simulated genre strings
        """
        # Simple artist name to genre mapping for testing
        genre_mapping = {
            # Electronic artists
            "deadmau5": ["electronic", "house", "progressive house"],
            "skrillex": ["electronic", "dubstep", "edm"],
            "odesza": ["electronic", "indie electronic", "ambient"],
            "flume": ["electronic", "future bass", "indie electronic"],
            "zhu": ["electronic", "house", "deep house"],
            "charlesthefirst": ["electronic", "bass", "dubstep"],
            "subtronics": ["electronic", "bass", "dubstep"],
            "clozee": ["electronic", "bass", "world"],
            "liquid stranger": ["electronic", "bass", "dubstep"],
            "ben böhmer": ["electronic", "melodic house", "ambient"],
            
            # Rock artists
            "metallica": ["rock", "metal", "thrash metal"],
            "red hot chili peppers": ["rock", "alternative rock", "funk rock"],
            "foo fighters": ["rock", "alternative rock", "grunge"],
            "pearl jam": ["rock", "alternative rock", "grunge"],
            
            # Hip-hop artists
            "kendrick lamar": ["hip hop", "rap", "conscious rap"],
            "drake": ["hip hop", "rap", "pop rap"],
            "j. cole": ["hip hop", "rap", "conscious rap"],
            
            # Pop artists
            "the weeknd": ["pop", "r&b", "alternative r&b"],
            "billie eilish": ["pop", "alternative pop", "indie pop"],
            "dua lipa": ["pop", "dance pop", "disco pop"]
        }
        
        genres = []
        for artist in track_artists:
            artist_name = artist.get("name", "").lower()
            if artist_name in genre_mapping:
                genres.extend(genre_mapping[artist_name])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_genres = []
        for genre in genres:
            if genre not in seen:
                seen.add(genre)
                unique_genres.append(genre)
        
        return unique_genres
        
    def get_info(self) -> Dict[str, Any]:
        """Get classifier information."""
        info = super().get_info()
        info.update({
            "description": "Current system using local data for artist lookup",
            "uses_audio_features": False,
            "uses_artist_patterns": False,
            "uses_local_data": True,
            "genre_folders": list(self.genre_mapping.keys()) if self.genre_mapping else []
        })
        return info