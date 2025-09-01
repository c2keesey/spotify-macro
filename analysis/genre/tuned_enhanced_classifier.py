#!/usr/bin/env python3
"""
Tuned Enhanced Artist-Genre classifier with improved confidence thresholds and 
folder-specific strategies.

Key improvements over the original Enhanced classifier:
1. Lower confidence thresholds (0.1 vs 0.3) for better coverage
2. Folder-specific classification strategies
3. Improved genre keyword mappings 
4. Better fallback mechanisms
5. Composite approach with different algorithms per folder type
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


class TunedEnhancedClassifier(BaseClassifier):
    """
    Tuned enhanced classifier with folder-specific strategies and improved thresholds.
    
    Features:
    1. Folder-specific confidence thresholds
    2. Enhanced genre keyword mappings
    3. Composite classification strategies per folder type
    4. Improved fallback mechanisms
    5. Better genre hierarchy understanding
    """
    
    def __init__(self):
        super().__init__("Tuned Enhanced Classifier")
        self.single_folder_artists = {}
        self.artist_folder_mapping = {}
        self.artist_genres = {}  # artist_id -> GenreInfo
        self.genre_folder_mapping = {}  # genre -> folder preferences
        self.playlists_dict = None
        
        # Folder-specific confidence thresholds (key improvement)
        self.folder_confidence_thresholds = {
            'Alive': 0.15,      # Higher threshold for melodic dubstep precision
            'Base': 0.12,       # Lower threshold for bass music variety  
            'House': 0.18,      # Higher threshold for house precision
            'Electronic': 0.08, # Very low threshold for broad electronic catch-all
            'Rave': 0.10,       # Low threshold for hardstyle/hardcore variety
            'Rock': 0.20,       # High threshold for rock precision
            'Reggae': 0.25,     # Very high threshold due to low volume
            'Funk Soul': 0.15,  # Medium threshold for funk/soul
            'Vibes': 0.10,      # Low threshold for chill/ambient variety
            'Spiritual': 0.08,  # Very low threshold due to small size
            'Soft': 0.30,       # Very high threshold for acoustic precision
            'Sierra': 0.12,     # Medium-low threshold for indie variety
            'Chill': 0.05,      # Extremely low threshold due to tiny size
            'Ride': 0.08        # Very low threshold due to small size
        }
        
        # Enhanced folder-specific genre keyword mapping
        self.folder_genre_keywords = {
            'Alive': {
                'primary': ['melodic dubstep', 'future bass', 'melodic bass', 'chillstep'],
                'secondary': ['emotional', 'uplifting', 'melodic', 'atmospheric'],
                'boost': 0.8  # Strong boost for primary keywords
            },
            'Base': {
                'primary': ['dubstep', 'riddim', 'bass music', 'hybrid trap', 'bass house'],
                'secondary': ['heavy', 'aggressive', 'bass', 'drop'],
                'boost': 0.7
            },
            'House': {
                'primary': ['house', 'tech house', 'deep house', 'progressive house'],
                'secondary': ['minimal', 'techno', 'disco house', 'funky house'],
                'boost': 0.9  # Very strong boost for house variants
            },
            'Electronic': {
                'primary': ['electronic', 'electro', 'synthwave', 'ambient electronic'],
                'secondary': ['experimental', 'downtempo', 'trip hop', 'idm'],
                'boost': 0.5  # Lower boost - catch-all category
            },
            'Rave': {
                'primary': ['hardstyle', 'hardcore', 'gabber', 'psytrance', 'hard dance'],
                'secondary': ['rave', 'hard', 'uptempo', 'frenchcore'],
                'boost': 0.8
            },
            'Rock': {
                'primary': ['rock', 'alternative rock', 'indie rock', 'progressive rock'],
                'secondary': ['metal', 'punk', 'grunge', 'classic rock'],
                'boost': 0.9
            },
            'Reggae': {
                'primary': ['reggae', 'dub', 'ska', 'dancehall'],
                'secondary': ['roots reggae', 'reggaeton', 'ragga'],
                'boost': 1.0  # Maximum boost for precise reggae detection
            },
            'Funk Soul': {
                'primary': ['funk', 'soul', 'neo soul', 'p funk'],
                'secondary': ['r&b', 'motown', 'disco', 'groove'],
                'boost': 0.8
            },
            'Vibes': {
                'primary': ['chill', 'downtempo', 'trip hop', 'lo-fi'],
                'secondary': ['ambient', 'chillout', 'lounge', 'jazz'],
                'boost': 0.6
            },
            'Spiritual': {
                'primary': ['ambient', 'new age', 'meditation', 'drone'],
                'secondary': ['healing', 'relaxation', 'nature', 'spiritual'],
                'boost': 0.7
            },
            'Soft': {
                'primary': ['acoustic', 'folk', 'singer-songwriter'],
                'secondary': ['indie folk', 'country', 'americana', 'soft rock'],
                'boost': 0.9
            },
            'Sierra': {
                'primary': ['indie', 'indie folk', 'indie pop', 'indie rock'],
                'secondary': ['alternative', 'bedroom pop', 'dream pop'],
                'boost': 0.7
            },
            'Chill': {
                'primary': ['chillout', 'ambient', 'downtempo'],
                'secondary': ['relaxing', 'peaceful', 'calm'],
                'boost': 0.6
            },
            'Ride': {
                'primary': ['synthwave', 'retrowave', 'outrun'],
                'secondary': ['driving', 'energetic', 'electronic rock'],
                'boost': 0.7
            }
        }
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """Train the tuned enhanced classifier."""
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
        print(f"    Using folder-specific thresholds: {len(self.folder_confidence_thresholds)} folders")
        
        self.is_trained = True
        
    def _load_artist_genres(self) -> None:
        """Load artist genre information from data file using PlaylistDataLoader."""
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
        """Build mapping from genres to folder preferences based on training data."""
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
        """Predict folder(s) for a track using tuned enhanced analysis."""
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
            
            # Strategy 2: Enhanced genre analysis with folder-specific thresholds
            prediction = self._classify_by_tuned_genre_analysis(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 3: Multi-folder artist fallback with improved confidence
            prediction = self._classify_by_improved_multi_folder_artists(track_id)
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
        """Classify track based on single-folder artists (highest confidence)."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.single_folder_artists:
                folder = self.single_folder_artists[artist_id]
                
                # High base confidence with genre boost
                confidence = 0.92
                if artist_id in self.artist_genres:
                    genre_boost = self._calculate_tuned_genre_boost(
                        self.artist_genres[artist_id].genres, 
                        folder
                    )
                    confidence = min(0.97, confidence + genre_boost)
                
                return {
                    "folders": [folder],
                    "confidence_scores": {folder: confidence},
                    "reasoning": f"Single-folder artist: {artist.get('name', 'Unknown')} (confidence: {confidence:.2f})"
                }
        
        return None
        
    def _classify_by_tuned_genre_analysis(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Classify track based on tuned genre analysis with folder-specific thresholds."""
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
        
        # Calculate folder scores with enhanced keyword matching
        folder_scores = defaultdict(float)
        
        # Score based on genre-folder associations (improved weighting)
        for genre in all_genres:
            if genre in self.genre_folder_mapping:
                total_count = sum(self.genre_folder_mapping[genre].values())
                for folder, count in self.genre_folder_mapping[genre].items():
                    # Stronger weighting for genre associations
                    folder_scores[folder] += (count / total_count) * 1.2
        
        # Enhanced keyword matching with primary/secondary distinctions
        for folder, keywords in self.folder_genre_keywords.items():
            primary_keywords = keywords.get('primary', [])
            secondary_keywords = keywords.get('secondary', [])
            boost_factor = keywords.get('boost', 0.5)
            
            for genre in all_genres:
                # Primary keyword matches (stronger boost)
                for keyword in primary_keywords:
                    if keyword in genre:
                        folder_scores[folder] += boost_factor
                
                # Secondary keyword matches (weaker boost)
                for keyword in secondary_keywords:
                    if keyword in genre:
                        folder_scores[folder] += boost_factor * 0.4
        
        if not folder_scores:
            return None
        
        # Apply folder-specific confidence thresholds
        valid_folders = {}
        for folder, score in folder_scores.items():
            threshold = self.folder_confidence_thresholds.get(folder, 0.15)
            if score >= threshold:
                valid_folders[folder] = score
        
        if not valid_folders:
            return None
        
        # Get top scoring folder(s) - more permissive top selection
        max_score = max(valid_folders.values())
        threshold = max_score * 0.7  # Lower threshold for multiple folders
        top_folders = {folder: score for folder, score in valid_folders.items() 
                      if score >= threshold}
        
        # Normalize confidences with higher base confidence
        total_score = sum(top_folders.values())
        confidence_scores = {folder: min(0.88, (score / total_score) * 0.75 + 0.15)
                           for folder, score in top_folders.items()}
        
        reasoning = f"Tuned genre analysis: {', '.join(set(all_genres)[:3])} → {list(top_folders.keys())}"
        
        return {
            "folders": list(top_folders.keys()),
            "confidence_scores": confidence_scores,
            "reasoning": reasoning
        }
        
    def _classify_by_improved_multi_folder_artists(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Classify track based on multi-folder artists with improved confidence."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.artist_folder_mapping:
                folders = list(self.artist_folder_mapping[artist_id])
                if folders:
                    # Improved base confidence calculation
                    base_confidence = min(0.65, 0.8 / len(folders))
                    
                    # Apply genre boost if available
                    if artist_id in self.artist_genres:
                        confidence_scores = {}
                        for folder in folders:
                            genre_boost = self._calculate_tuned_genre_boost(
                                self.artist_genres[artist_id].genres, 
                                folder
                            )
                            confidence_scores[folder] = min(0.78, base_confidence + genre_boost)
                    else:
                        confidence_scores = {folder: base_confidence for folder in folders}
                    
                    return {
                        "folders": folders,
                        "confidence_scores": confidence_scores,
                        "reasoning": f"Multi-folder artist: {artist.get('name', 'Unknown')} ({len(folders)} folders)"
                    }
        
        return None
        
    def _calculate_tuned_genre_boost(self, artist_genres: List[str], target_folder: str) -> float:
        """Calculate improved confidence boost based on genre-folder keyword matching."""
        if target_folder not in self.folder_genre_keywords:
            return 0.0
        
        folder_keywords = self.folder_genre_keywords[target_folder]
        primary_keywords = folder_keywords.get('primary', [])
        secondary_keywords = folder_keywords.get('secondary', [])
        
        boost = 0.0
        
        for genre in artist_genres:
            # Primary keyword matches (stronger boost)
            for keyword in primary_keywords:
                if keyword in genre:
                    boost += 0.08  # Increased boost per primary match
            
            # Secondary keyword matches (weaker boost)
            for keyword in secondary_keywords:
                if keyword in genre:
                    boost += 0.03  # Smaller boost per secondary match
        
        return min(0.20, boost)  # Increased cap to 0.20
        
    def get_info(self) -> Dict[str, Any]:
        """Get tuned classifier information."""
        info = super().get_info()
        info.update({
            "description": "Tuned Enhanced Artist-Genre classifier with folder-specific strategies",
            "uses_audio_features": False,
            "uses_artist_patterns": True,
            "uses_genre_data": True,
            "uses_folder_specific_thresholds": True,
            "single_folder_artists": len(self.single_folder_artists),
            "total_artists": len(self.artist_folder_mapping),
            "artists_with_genres": len(self.artist_genres),
            "improvements": [
                "Folder-specific confidence thresholds (0.05-0.30)",
                "Enhanced primary/secondary keyword matching",
                "Improved genre association weighting",
                "Better fallback confidence calculation",
                "Composite folder strategies"
            ],
            "strategies": [
                "Single-folder artist lookup (0.92-0.97 confidence)",
                "Tuned genre analysis (folder-specific thresholds)",
                "Improved multi-folder fallback (0.65-0.78 confidence)"
            ]
        })
        return info