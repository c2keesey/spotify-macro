#!/usr/bin/env python3
"""
Enhanced Artist-Genre classifier that combines artist patterns with Spotify genre data.

This classifier extends the Electronic-Specialist approach by incorporating:
1. Artist genre analysis
2. Genre similarity scoring  
3. Multi-artist genre consensus
4. Electronic subgenre mapping
5. Genre hierarchy relationships

Expected to significantly outperform the current artist-only approach.
"""

import time
import json
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

from analysis.genre.classification_framework import BaseClassifier, ClassificationResult
from analysis.genre.classification_metrics import (
    get_single_folder_artists,
    build_artist_folder_mapping,
    get_track_artists
)
from common.playlist_data_utils import PlaylistDataLoader


@dataclass
class GenreInfo:
    """Artist genre information."""
    artist_id: str
    artist_name: str
    genres: List[str]


class EnhancedArtistGenreClassifier(BaseClassifier):
    """
    Enhanced classifier using artist patterns + Spotify genre data.
    
    Features:
    1. Artist patterns (single-folder vs multi-folder) 
    2. Artist genre vectors
    3. Genre similarity scoring
    4. Multi-artist genre consensus
    5. Electronic subgenre mapping
    """
    
    def __init__(self):
        super().__init__("Enhanced Artist-Genre")
        self.single_folder_artists = {}
        self.artist_folder_mapping = {}
        self.artist_genres = {}  # artist_id -> GenreInfo
        self.genre_folder_mapping = {}  # genre -> folder preferences
        self.electronic_genre_keywords = {}  # folder -> relevant genre keywords
        self.playlists_dict = None
        
        # Electronic subgenre keyword mapping
        self.folder_genre_keywords = {
            'Alive': ['melodic dubstep', 'future bass', 'melodic bass', 'chillstep', 'emotional'],
            'Base': ['bass music', 'dubstep', 'riddim', 'hybrid trap', 'bass house'],
            'House': ['house', 'tech house', 'deep house', 'progressive house', 'melodic house'],
            'Rave': ['hardstyle', 'hardcore', 'gabber', 'psytrance', 'hard dance'],
            'Electronic': ['electronic', 'electro', 'synthwave', 'ambient electronic', 'experimental electronic'],
            'Rock': ['rock', 'alternative rock', 'indie rock', 'progressive rock'],
            'Reggae': ['reggae', 'dub', 'ska', 'dancehall'],
            'Funk Soul': ['funk', 'soul', 'neo soul', 'p funk'],
            'Vibes': ['chill', 'downtempo', 'trip hop', 'lo-fi'],
            'Spiritual': ['ambient', 'new age', 'meditation', 'drone'],
            'Soft': ['acoustic', 'folk', 'singer-songwriter'],
            'Sierra': ['indie', 'indie folk', 'indie pop'],
            'Chill': ['chillout', 'ambient', 'downtempo'],
            'Ride': ['driving', 'synthwave', 'retrowave']
        }
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """
        Train the enhanced classifier using training data + genre information.
        
        Args:
            train_data: Training data dictionary containing:
                - playlists_dict: Playlist data for track lookup
                - train_tracks: List of (track_id, folder) tuples
                - spotify_client: For genre data extraction (optional)
        """
        print(f"  Training {self.name}...")
        
        # Store playlist data
        self.playlists_dict = train_data.get("playlists_dict", {})
        
        # Build artist to folder mapping from training data
        train_tracks = train_data.get("train_tracks", [])
        self.artist_folder_mapping = build_artist_folder_mapping(train_tracks, self.playlists_dict)
        
        # Extract single-folder artists (highest confidence predictors)
        self.single_folder_artists = get_single_folder_artists(self.artist_folder_mapping)
        
        # Load artist genre information from data file
        self._load_artist_genres()
        
        # Build genre to folder mapping
        self._build_genre_folder_mapping()
        
        single_artist_count = len(self.single_folder_artists)
        total_artist_count = len(self.artist_folder_mapping)
        genre_artist_count = len(self.artist_genres)
        single_ratio = single_artist_count / total_artist_count if total_artist_count > 0 else 0
        
        print(f"    Single-folder artists: {single_artist_count}/{total_artist_count} ({single_ratio:.1%})")
        print(f"    Artists with genre data: {genre_artist_count}/{total_artist_count} ({genre_artist_count/total_artist_count:.1%})")
        
        self.is_trained = True
        
    def _load_artist_genres(self) -> None:
        """
        Load artist genre information from data file using PlaylistDataLoader.
        """
        print(f"    Loading artist genre data...")
        
        # Load artist genres using the data loader
        artist_genres_data = PlaylistDataLoader.load_artist_genres()
        
        # Convert to our internal format
        for artist_id, artist_data in artist_genres_data.items():
            if "genres" in artist_data:
                self.artist_genres[artist_id] = GenreInfo(
                    artist_id=artist_id,
                    artist_name=artist_data.get("name", "Unknown"),
                    genres=[g.lower() for g in artist_data["genres"]]
                )
        
        print(f"    Loaded genres for {len(self.artist_genres)} artists")
        
    def _build_genre_folder_mapping(self) -> None:
        """
        Build mapping from genres to folder preferences based on training data.
        """
        # For each folder, find the most common genres among its artists
        folder_genre_scores = defaultdict(lambda: Counter())
        
        for artist_id, folders in self.artist_folder_mapping.items():
            if artist_id in self.artist_genres:
                artist_genres = self.artist_genres[artist_id].genres
                
                for folder in folders:
                    for genre in artist_genres:
                        folder_genre_scores[folder][genre] += 1
        
        # Build reverse mapping: genre -> folder preferences
        for folder, genre_counter in folder_genre_scores.items():
            for genre, count in genre_counter.items():
                if genre not in self.genre_folder_mapping:
                    self.genre_folder_mapping[genre] = {}
                self.genre_folder_mapping[genre][folder] = count
        
    def predict(self, track_id: str) -> ClassificationResult:
        """
        Predict folder(s) for a track using enhanced artist+genre analysis.
        
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
            # Strategy 1: Single-folder artist lookup (highest confidence)
            prediction = self._classify_by_single_folder_artists(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 2: Enhanced genre analysis
            prediction = self._classify_by_genre_analysis(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 3: Multi-folder artist fallback (lower confidence)
            prediction = self._classify_by_multi_folder_artists(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # No classification found
            result.reasoning = "No artist or genre patterns found"
            
        except Exception as e:
            result.reasoning = f"Error during classification: {str(e)}"
            
        result.processing_time_ms = (time.time() - start_time) * 1000
        return result
        
    def _classify_by_single_folder_artists(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Classify track based on single-folder artists (highest confidence).
        """
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.single_folder_artists:
                folder = self.single_folder_artists[artist_id]
                
                # Check for genre boost
                confidence = 0.95
                if artist_id in self.artist_genres:
                    genre_boost = self._calculate_genre_boost(
                        self.artist_genres[artist_id].genres, 
                        folder
                    )
                    confidence = min(0.98, confidence + genre_boost)
                
                return {
                    "folders": [folder],
                    "confidence_scores": {folder: confidence},
                    "reasoning": f"Single-folder artist: {artist.get('name', 'Unknown')} (confidence: {confidence:.2f})"
                }
        
        return None
        
    def _classify_by_genre_analysis(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Classify track based on enhanced genre analysis.
        """
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        # Collect all genres from track artists
        all_genres = []
        artist_names = []
        
        for artist in track_artists:
            artist_id = artist.get("id")
            artist_name = artist.get("name", "Unknown")
            artist_names.append(artist_name)
            
            if artist_id in self.artist_genres:
                all_genres.extend(self.artist_genres[artist_id].genres)
        
        if not all_genres:
            return None
        
        # Calculate folder scores based on genre analysis
        folder_scores = defaultdict(float)
        
        # Score based on genre-folder associations
        for genre in all_genres:
            if genre in self.genre_folder_mapping:
                total_count = sum(self.genre_folder_mapping[genre].values())
                for folder, count in self.genre_folder_mapping[genre].items():
                    folder_scores[folder] += count / total_count
        
        # Score based on keyword matching
        for folder, keywords in self.folder_genre_keywords.items():
            for genre in all_genres:
                for keyword in keywords:
                    if keyword in genre:
                        folder_scores[folder] += 0.5  # Keyword boost
        
        if not folder_scores:
            return None
        
        # Find top scoring folder(s)
        max_score = max(folder_scores.values())
        if max_score < 0.3:  # Minimum confidence threshold
            return None
        
        # Get folders within 80% of max score
        threshold = max_score * 0.8
        top_folders = {folder: score for folder, score in folder_scores.items() 
                      if score >= threshold}
        
        # Normalize confidences
        total_score = sum(top_folders.values())
        confidence_scores = {folder: (score / total_score) * 0.85 
                           for folder, score in top_folders.items()}
        
        reasoning = f"Genre analysis: {', '.join(set(all_genres)[:3])} → {list(top_folders.keys())}"
        
        return {
            "folders": list(top_folders.keys()),
            "confidence_scores": confidence_scores,
            "reasoning": reasoning
        }
        
    def _classify_by_multi_folder_artists(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Classify track based on multi-folder artists (lower confidence fallback).
        """
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.artist_folder_mapping:
                folders = list(self.artist_folder_mapping[artist_id])
                if folders:
                    # Lower confidence for multi-folder artists
                    base_confidence = 0.6 / len(folders)
                    
                    # Apply genre boost if available
                    if artist_id in self.artist_genres:
                        confidence_scores = {}
                        for folder in folders:
                            genre_boost = self._calculate_genre_boost(
                                self.artist_genres[artist_id].genres, 
                                folder
                            )
                            confidence_scores[folder] = min(0.75, base_confidence + genre_boost)
                    else:
                        confidence_scores = {folder: base_confidence for folder in folders}
                    
                    return {
                        "folders": folders,
                        "confidence_scores": confidence_scores,
                        "reasoning": f"Multi-folder artist: {artist.get('name', 'Unknown')} ({len(folders)} folders)"
                    }
        
        return None
        
    def _calculate_genre_boost(self, artist_genres: List[str], target_folder: str) -> float:
        """
        Calculate confidence boost based on genre-folder keyword matching.
        
        Args:
            artist_genres: List of artist genres
            target_folder: Target folder name
            
        Returns:
            Confidence boost value (0.0 to 0.15)
        """
        if target_folder not in self.folder_genre_keywords:
            return 0.0
        
        folder_keywords = self.folder_genre_keywords[target_folder]
        boost = 0.0
        
        for genre in artist_genres:
            for keyword in folder_keywords:
                if keyword in genre:
                    boost += 0.05  # Small boost per keyword match
        
        return min(0.15, boost)  # Cap at 0.15
        
    def get_info(self) -> Dict[str, Any]:
        """Get enhanced classifier information."""
        info = super().get_info()
        info.update({
            "description": "Enhanced Artist-Genre classifier using artist patterns + Spotify genre data",
            "uses_audio_features": False,
            "uses_artist_patterns": True,
            "uses_genre_data": True,
            "single_folder_artists": len(self.single_folder_artists),
            "total_artists": len(self.artist_folder_mapping),
            "artists_with_genres": len(self.artist_genres),
            "strategies": [
                "Single-folder artist lookup (0.95+ confidence)",
                "Enhanced genre analysis (0.3-0.85 confidence)",
                "Multi-folder artist fallback (0.6 confidence)"
            ]
        })
        return info