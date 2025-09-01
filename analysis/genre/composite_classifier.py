#!/usr/bin/env python3
"""
Composite classifier that intelligently combines different classification strategies
based on what works best for each folder type.

Strategy selection based on analysis:
- High-precision folders (House, Alive, Rock): Use enhanced genre analysis
- High-coverage folders (Electronic, Rave): Use simple artist patterns  
- Balanced approach for medium folders
"""

import time
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

try:
    from analysis.genre.classification_framework import BaseClassifier, ClassificationResult
    from analysis.genre.classification_metrics import (
        get_single_folder_artists,
        build_artist_folder_mapping,
        get_track_artists
    )
except ImportError:
    from classification_framework import BaseClassifier, ClassificationResult
    from classification_metrics import (
        get_single_folder_artists,
        build_artist_folder_mapping,
        get_track_artists
    )
from common.playlist_data_utils import PlaylistDataLoader
from common.spotify_utils import initialize_spotify_client


class CompositeClassifier(BaseClassifier):
    """
    Composite classifier using different strategies per folder based on optimal performance.
    """
    
    def __init__(self):
        super().__init__("Composite Strategy Classifier")
        self.single_folder_artists = {}
        self.artist_folder_mapping = {}
        self.artist_genres = {}
        self.genre_folder_mapping = {}
        self.playlists_dict = None
        self.spotify_client = None
        self.enable_realtime_genres = True  # Flag to enable/disable real-time fetching
        
        # Folder-specific strategy configuration
        self.folder_strategies = {
            # High-precision strategy (enhanced genre analysis with high thresholds)
            'House': {'strategy': 'enhanced_genre', 'threshold': 0.25, 'boost': 0.9},
            'Alive': {'strategy': 'enhanced_genre', 'threshold': 0.20, 'boost': 0.8},
            'Rock': {'strategy': 'enhanced_genre', 'threshold': 0.25, 'boost': 0.9},
            'Reggae': {'strategy': 'enhanced_genre', 'threshold': 0.30, 'boost': 1.0},
            
            # High-coverage strategy (simple artist patterns with low thresholds)
            'Electronic': {'strategy': 'simple_artist', 'threshold': 0.05, 'boost': 0.5},
            'Rave': {'strategy': 'simple_artist', 'threshold': 0.08, 'boost': 0.6},
            'Vibes': {'strategy': 'simple_artist', 'threshold': 0.08, 'boost': 0.6},
            
            # Balanced strategy (mixed approach)
            'Base': {'strategy': 'balanced', 'threshold': 0.15, 'boost': 0.7},
            'Funk Soul': {'strategy': 'balanced', 'threshold': 0.15, 'boost': 0.8},
            'Sierra': {'strategy': 'balanced', 'threshold': 0.12, 'boost': 0.7},
            
            # Conservative strategy for small folders
            'Spiritual': {'strategy': 'conservative', 'threshold': 0.10, 'boost': 0.7},
            'Soft': {'strategy': 'conservative', 'threshold': 0.25, 'boost': 0.9},
            'Chill': {'strategy': 'conservative', 'threshold': 0.05, 'boost': 0.6},
            'Ride': {'strategy': 'conservative', 'threshold': 0.08, 'boost': 0.7},
        }
        
        # Enhanced genre keywords for better precision
        self.folder_genre_keywords = {
            'Alive': ['melodic dubstep', 'future bass', 'melodic bass', 'chillstep', 'emotional'],
            'Base': ['dubstep', 'riddim', 'bass music', 'hybrid trap', 'bass house', 'heavy'],
            'House': ['house', 'tech house', 'deep house', 'progressive house', 'minimal'],
            'Electronic': ['electronic', 'electro', 'synthwave', 'ambient electronic', 'experimental'],
            'Rave': ['hardstyle', 'hardcore', 'gabber', 'psytrance', 'hard dance', 'rave'],
            'Rock': ['rock', 'alternative rock', 'indie rock', 'progressive rock', 'metal'],
            'Reggae': ['reggae', 'dub', 'ska', 'dancehall', 'roots reggae'],
            'Funk Soul': ['funk', 'soul', 'neo soul', 'p funk', 'r&b', 'groove'],
            'Vibes': ['chill', 'downtempo', 'trip hop', 'lo-fi', 'ambient', 'lounge'],
            'Spiritual': ['ambient', 'new age', 'meditation', 'drone', 'healing'],
            'Soft': ['acoustic', 'folk', 'singer-songwriter', 'indie folk'],
            'Sierra': ['indie', 'indie folk', 'indie pop', 'indie rock', 'alternative'],
            'Chill': ['chillout', 'ambient', 'downtempo', 'relaxing'],
            'Ride': ['synthwave', 'retrowave', 'outrun', 'driving', 'electronic rock']
        }
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """Train the composite classifier."""
        print(f"  Training {self.name}...")
        
        # Store playlist data
        self.playlists_dict = train_data.get("playlists_dict", {})
        
        # Build artist to folder mapping from training data
        train_tracks = train_data.get("train_tracks", [])
        self.artist_folder_mapping = build_artist_folder_mapping(train_tracks, self.playlists_dict)
        
        # Extract single-folder artists
        self.single_folder_artists = get_single_folder_artists(self.artist_folder_mapping)
        
        # Load artist genre information
        self._load_artist_genres()
        
        # Build genre to folder mapping
        self._build_genre_folder_mapping()
        
        single_artist_count = len(self.single_folder_artists)
        total_artist_count = len(self.artist_folder_mapping)
        genre_artist_count = len(self.artist_genres)
        
        print(f"    Single-folder artists: {single_artist_count}/{total_artist_count} ({single_artist_count/total_artist_count:.1%})")
        print(f"    Artists with genre data: {genre_artist_count}/{total_artist_count} ({genre_artist_count/total_artist_count:.1%})")
        print(f"    Using composite strategies for {len(self.folder_strategies)} folders")
        
        self.is_trained = True
        
        # Initialize Spotify client for real-time genre fetching if enabled
        if self.enable_realtime_genres:
            try:
                self.spotify_client = initialize_spotify_client("", "genre_fetching_cache")
                print(f"    ✅ Spotify client initialized for real-time genre fetching")
            except Exception as e:
                print(f"    ⚠️ Failed to initialize Spotify client for genre fetching: {e}")
                self.spotify_client = None
        
    def _load_artist_genres(self) -> None:
        """Load artist genre information."""
        artist_genres_data = PlaylistDataLoader.load_artist_genres()
        
        for artist_id, artist_data in artist_genres_data.items():
            if "genres" in artist_data:
                self.artist_genres[artist_id] = {
                    'name': artist_data.get("name", "Unknown"),
                    'genres': [g.lower() for g in artist_data["genres"]]
                }
        
    def _build_genre_folder_mapping(self) -> None:
        """Build mapping from genres to folder preferences."""
        folder_genre_scores = defaultdict(lambda: Counter())
        
        for artist_id, folders in self.artist_folder_mapping.items():
            if artist_id in self.artist_genres:
                artist_genres = self.artist_genres[artist_id]['genres']
                
                for folder in folders:
                    for genre in artist_genres:
                        folder_genre_scores[folder][genre] += 1
        
        # Build reverse mapping
        for folder, genre_counter in folder_genre_scores.items():
            for genre, count in genre_counter.items():
                if genre not in self.genre_folder_mapping:
                    self.genre_folder_mapping[genre] = {}
                self.genre_folder_mapping[genre][folder] = count
        
    def _fetch_artist_genres_realtime(self, artist_id: str, artist_name: str = "Unknown") -> List[str]:
        """Fetch artist genres from Spotify API in real-time."""
        if not self.spotify_client or not self.enable_realtime_genres:
            return []
        
        try:
            # Fetch artist data from Spotify API
            artist_data = self.spotify_client.artist(artist_id)
            
            if artist_data and 'genres' in artist_data:
                genres = [g.lower() for g in artist_data['genres']]
                
                # Cache the fetched genres for future use
                self.artist_genres[artist_id] = {
                    'name': artist_data.get('name', artist_name),
                    'genres': genres
                }
                
                print(f"    🆕 Fetched genres for {artist_name}: {genres[:3]}{'...' if len(genres) > 3 else ''}")
                return genres
            else:
                # No genres found, cache empty result to avoid repeated API calls
                self.artist_genres[artist_id] = {
                    'name': artist_name,
                    'genres': []
                }
                return []
                
        except Exception as e:
            print(f"    ⚠️ Failed to fetch genres for {artist_name} ({artist_id}): {e}")
            # Cache empty result to avoid repeated failed API calls
            self.artist_genres[artist_id] = {
                'name': artist_name,
                'genres': []
            }
            return []
        
    def predict(self, track_id: str) -> ClassificationResult:
        """Predict folder using composite strategy selection."""
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
            # Strategy 1: Single-folder artist lookup (always highest priority)
            prediction = self._classify_by_single_folder_artists(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 2: Composite strategy based on folder preferences
            prediction = self._classify_by_composite_strategy(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 3: Genre-only classification (enhanced fallback)
            prediction = self._classify_by_genre_only(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 4: Artist-only classification (enhanced fallback)
            prediction = self._classify_by_artist_only(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 5: Fallback to multi-folder artists
            prediction = self._classify_by_multi_folder_artists(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Strategy 6: Last resort - statistical folder popularity (very low confidence)
            prediction = self._classify_by_statistical_fallback(track_id)
            if prediction:
                result.predicted_folders = prediction["folders"]
                result.confidence_scores = prediction["confidence_scores"]
                result.reasoning = prediction["reasoning"]
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result
            
            result.reasoning = "No classification patterns found"
            
        except Exception as e:
            result.reasoning = f"Error during classification: {str(e)}"
            
        result.processing_time_ms = (time.time() - start_time) * 1000
        return result
        
    def _classify_by_single_folder_artists(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Single-folder artist classification (highest confidence)."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.single_folder_artists:
                folder = self.single_folder_artists[artist_id]
                
                # Normalize confidence based on folder strategy and characteristics
                folder_config = self.folder_strategies.get(folder, {})
                strategy = folder_config.get('strategy', 'balanced')
                
                # Base confidence varies by strategy
                if strategy == 'enhanced_genre':
                    base_confidence = 0.85  # High precision folders
                elif strategy == 'simple_artist':
                    base_confidence = 0.80  # High coverage folders
                elif strategy == 'conservative':
                    base_confidence = 0.90  # Conservative folders
                else:  # balanced
                    base_confidence = 0.82
                
                # Apply sigmoid normalization to prevent extreme values
                normalized_confidence = 1 / (1 + 2.71828 ** (-5 * (base_confidence - 0.5)))
                
                return {
                    "folders": [folder],
                    "confidence_scores": {folder: normalized_confidence},
                    "reasoning": f"Single-folder artist: {artist.get('name', 'Unknown')}"
                }
        
        return None
        
    def _classify_by_composite_strategy(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Apply composite strategy based on folder characteristics."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        # Collect all genres from track artists (with real-time fetching)
        all_genres = []
        for artist in track_artists:
            artist_id = artist.get("id")
            artist_name = artist.get("name", "Unknown")
            
            if artist_id in self.artist_genres:
                # Use cached genre data
                all_genres.extend(self.artist_genres[artist_id]['genres'])
            else:
                # Fetch genres in real-time for unknown artists
                fetched_genres = self._fetch_artist_genres_realtime(artist_id, artist_name)
                all_genres.extend(fetched_genres)
        
        if not all_genres:
            return None
        
        # Calculate scores for each folder using their specific strategy
        folder_scores = defaultdict(float)
        
        for folder, config in self.folder_strategies.items():
            strategy = config['strategy']
            boost = config['boost']
            
            if strategy == 'enhanced_genre':
                score = self._calculate_enhanced_genre_score(all_genres, folder, boost)
            elif strategy == 'simple_artist':
                score = self._calculate_simple_artist_score(track_artists, folder, boost)
            elif strategy == 'balanced':
                genre_score = self._calculate_enhanced_genre_score(all_genres, folder, boost)
                artist_score = self._calculate_simple_artist_score(track_artists, folder, boost)
                score = (genre_score + artist_score) / 2
            elif strategy == 'conservative':
                score = self._calculate_conservative_score(all_genres, track_artists, folder, boost)
            else:
                score = 0
            
            if score > 0:
                folder_scores[folder] = score
        
        if not folder_scores:
            return None
        
        # Apply folder-specific thresholds
        valid_folders = {}
        for folder, score in folder_scores.items():
            threshold = self.folder_strategies.get(folder, {}).get('threshold', 0.15)
            if score >= threshold:
                valid_folders[folder] = score
        
        if not valid_folders:
            return None
        
        # Select top folders
        max_score = max(valid_folders.values())
        threshold = max_score * 0.8
        top_folders = {folder: score for folder, score in valid_folders.items() 
                      if score >= threshold}
        
        # Normalize confidences
        total_score = sum(top_folders.values())
        confidence_scores = {folder: min(0.85, (score / total_score) * 0.8)
                           for folder, score in top_folders.items()}
        
        return {
            "folders": list(top_folders.keys()),
            "confidence_scores": confidence_scores,
            "reasoning": f"Composite strategy: {list(top_folders.keys())}"
        }
        
    def _calculate_enhanced_genre_score(self, genres: List[str], folder: str, boost: float) -> float:
        """Calculate enhanced genre-based score."""
        score = 0.0
        
        # Genre-folder mapping score
        for genre in genres:
            if genre in self.genre_folder_mapping and folder in self.genre_folder_mapping[genre]:
                count = self.genre_folder_mapping[genre][folder]
                total_count = sum(self.genre_folder_mapping[genre].values())
                score += (count / total_count) * 1.2
        
        # Keyword matching score
        if folder in self.folder_genre_keywords:
            keywords = self.folder_genre_keywords[folder]
            for genre in genres:
                for keyword in keywords:
                    if keyword in genre:
                        score += boost * 0.6
        
        return score
        
    def _calculate_simple_artist_score(self, track_artists: List[Dict], folder: str, boost: float) -> float:
        """Calculate simple artist-based score."""
        score = 0.0
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.artist_folder_mapping:
                folders = self.artist_folder_mapping[artist_id]
                if folder in folders:
                    # Higher score for artists who primarily appear in this folder
                    folder_ratio = 1.0 / len(folders)
                    score += folder_ratio * boost
        
        return score
        
    def _calculate_conservative_score(self, genres: List[str], track_artists: List[Dict], folder: str, boost: float) -> float:
        """Calculate conservative score combining both approaches."""
        genre_score = self._calculate_enhanced_genre_score(genres, folder, boost * 0.7)
        artist_score = self._calculate_simple_artist_score(track_artists, folder, boost * 0.8)
        
        # Conservative approach: both must contribute
        if genre_score > 0.1 and artist_score > 0.1:
            return (genre_score + artist_score) / 2
        else:
            return max(genre_score, artist_score) * 0.5
        
    def _classify_by_multi_folder_artists(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Fallback classification using multi-folder artists."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.artist_folder_mapping:
                folders = list(self.artist_folder_mapping[artist_id])
                if folders:
                    base_confidence = 0.6 / len(folders)
                    confidence_scores = {folder: base_confidence for folder in folders}
                    
                    return {
                        "folders": folders,
                        "confidence_scores": confidence_scores,
                        "reasoning": f"Multi-folder artist: {artist.get('name', 'Unknown')}"
                    }
        
        return None
        
    def _classify_by_genre_only(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Genre-only classification fallback for tracks with genre data but no artist matches."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        # Collect all genres from track artists (with real-time fetching)
        all_genres = []
        for artist in track_artists:
            artist_id = artist.get("id")
            artist_name = artist.get("name", "Unknown")
            
            if artist_id in self.artist_genres:
                # Use cached genre data
                all_genres.extend(self.artist_genres[artist_id]['genres'])
            else:
                # Fetch genres in real-time for unknown artists
                fetched_genres = self._fetch_artist_genres_realtime(artist_id, artist_name)
                all_genres.extend(fetched_genres)
        
        if not all_genres:
            return None
        
        # Calculate genre-based scores only
        folder_scores = defaultdict(float)
        
        for folder, keywords in self.folder_genre_keywords.items():
            for genre in all_genres:
                for keyword in keywords:
                    if keyword in genre:
                        # Higher score for exact matches
                        if keyword == genre:
                            folder_scores[folder] += 0.8
                        else:
                            folder_scores[folder] += 0.4
        
        # Also check genre-folder mapping
        for genre in all_genres:
            if genre in self.genre_folder_mapping:
                for folder, count in self.genre_folder_mapping[genre].items():
                    total_count = sum(self.genre_folder_mapping[genre].values())
                    folder_scores[folder] += (count / total_count) * 0.6
        
        if not folder_scores:
            return None
        
        # Apply minimum threshold for genre-only classification
        min_threshold = 0.3
        valid_folders = {folder: score for folder, score in folder_scores.items() 
                        if score >= min_threshold}
        
        if not valid_folders:
            return None
        
        # Normalize to reasonable confidence range
        max_score = max(valid_folders.values())
        confidence_scores = {folder: min(0.7, (score / max_score) * 0.6) 
                           for folder, score in valid_folders.items()}
        
        return {
            "folders": list(valid_folders.keys()),
            "confidence_scores": confidence_scores,
            "reasoning": f"Genre-only classification: {', '.join(all_genres[:3])}"
        }
        
    def _classify_by_artist_only(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Artist-only classification fallback using weak artist patterns."""
        track_artists = get_track_artists(track_id, self.playlists_dict)
        
        folder_scores = defaultdict(float)
        
        for artist in track_artists:
            artist_id = artist.get("id")
            if artist_id in self.artist_folder_mapping:
                folders = self.artist_folder_mapping[artist_id]
                # Weak signal: distribute confidence across all folders this artist appears in
                for folder in folders:
                    folder_scores[folder] += 0.3 / len(folders)
        
        if not folder_scores:
            return None
        
        # Very low threshold for artist-only fallback
        min_threshold = 0.15
        valid_folders = {folder: score for folder, score in folder_scores.items() 
                        if score >= min_threshold}
        
        if not valid_folders:
            return None
        
        # Keep confidence scores low for this fallback method
        confidence_scores = {folder: min(0.5, score) for folder, score in valid_folders.items()}
        
        return {
            "folders": list(valid_folders.keys()),
            "confidence_scores": confidence_scores,
            "reasoning": f"Artist-only fallback: weak patterns detected"
        }
        
    def _classify_by_statistical_fallback(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Last resort: assign to most popular folders with very low confidence."""
        # Only use this fallback if we have some training data
        if not hasattr(self, 'folder_strategies') or not self.folder_strategies:
            return None
        
        # Get the most popular folders based on training data size
        folder_popularity = {}
        for folder, config in self.folder_strategies.items():
            # Use strategy preference as a proxy for folder size/importance
            strategy = config.get('strategy', 'balanced')
            if strategy == 'simple_artist':  # High coverage folders
                folder_popularity[folder] = 0.3
            elif strategy == 'balanced':  # Medium folders
                folder_popularity[folder] = 0.2
            elif strategy == 'enhanced_genre':  # High precision folders
                folder_popularity[folder] = 0.15
            else:  # conservative
                folder_popularity[folder] = 0.1
        
        # Filter to top 3 most popular folders with very low confidence
        top_folders = sorted(folder_popularity.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Only assign if confidence threshold is very low and this is truly a last resort
        valid_folders = {}
        for folder, base_score in top_folders:
            # Very conservative - only assign to the most popular folder
            if folder == top_folders[0][0]:  
                valid_folders[folder] = 0.08  # Very low confidence
        
        if not valid_folders:
            return None
        
        return {
            "folders": list(valid_folders.keys()),
            "confidence_scores": valid_folders,
            "reasoning": f"Statistical fallback: assigned to popular folder"
        }
        
    def get_info(self) -> Dict[str, Any]:
        """Get composite classifier information."""
        info = super().get_info()
        info.update({
            "description": "Composite classifier using optimal strategies per folder",
            "uses_audio_features": False,
            "uses_artist_patterns": True,
            "uses_genre_data": True,
            "uses_composite_strategies": True,
            "single_folder_artists": len(self.single_folder_artists),
            "total_artists": len(self.artist_folder_mapping),
            "artists_with_genres": len(self.artist_genres),
            "strategies": {
                "enhanced_genre": ["House", "Alive", "Rock", "Reggae"],
                "simple_artist": ["Electronic", "Rave", "Vibes"],
                "balanced": ["Base", "Funk Soul", "Sierra"],
                "conservative": ["Spiritual", "Soft", "Chill", "Ride"]
            }
        })
        return info