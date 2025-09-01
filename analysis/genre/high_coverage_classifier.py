#!/usr/bin/env python3
"""
High-coverage classifier strategies for pre-sorting workflow.

This implements several new strategies focused on maximizing coverage
rather than precision, since manual refinement happens afterward.
"""

import time
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter

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


class HighCoverageClassifier(BaseClassifier):
    """
    Classifier focused on maximum coverage with multiple fallback strategies.
    """
    
    def __init__(self, strategy_name="aggressive_coverage"):
        super().__init__(f"High Coverage - {strategy_name}")
        self.strategy_name = strategy_name
        self.single_folder_artists = {}
        self.artist_folder_mapping = {}
        self.artist_genres = {}
        self.genre_folder_mapping = {}
        self.playlists_dict = None
        
        # Ultra-aggressive thresholds for maximum coverage
        self.aggressive_thresholds = {
            'House': 0.05,
            'Alive': 0.05, 
            'Rock': 0.08,
            'Electronic': 0.03,  # Very low for new artist discovery
            'Rave': 0.03,
            'Base': 0.05,
            'Vibes': 0.05,
            'Sierra': 0.05,
            'Ride': 0.05,
            'Funk Soul': 0.08,
            'Reggae': 0.08,
            'Spiritual': 0.05,
            'Soft': 0.10,
            'Chill': 0.03,
        }
        
        # Enhanced genre keywords for better discovery
        self.discovery_keywords = {
            'Electronic': ['electronic', 'electro', 'synthwave', 'ambient', 'techno', 'idm', 
                          'experimental electronic', 'electronica', 'downtempo', 'chillwave'],
            'House': ['house', 'tech house', 'deep house', 'progressive house', 'minimal house',
                     'funky house', 'jackin house', 'chicago house', 'tribal house'],
            'Base': ['dubstep', 'riddim', 'bass', 'trap', 'hybrid trap', 'future bass',
                    'neuro', 'drum and bass', 'dnb', 'bass music', 'heavy bass'],
            'Alive': ['melodic dubstep', 'emotional', 'uplifting', 'melodic bass', 'chillstep',
                     'future garage', 'liquid dnb', 'melodic trance'],
            'Rave': ['hardstyle', 'hardcore', 'gabber', 'psytrance', 'trance', 'hard dance'],
            'Rock': ['rock', 'indie rock', 'alternative rock', 'classic rock', 'hard rock',
                    'punk rock', 'progressive rock', 'psychedelic rock'],
            'Vibes': ['chill', 'lo-fi', 'indie', 'alternative', 'dream pop', 'shoegaze'],
            'Ride': ['hip hop', 'rap', 'r&b', 'neo soul', 'funk', 'groove'],
            'Reggae': ['reggae', 'dub', 'ska', 'dancehall', 'roots reggae'],
            'Sierra': ['folk', 'acoustic', 'singer-songwriter', 'indie folk', 'country'],
            'Funk Soul': ['funk', 'soul', 'disco', 'groove', 'neo-funk'],
            'Soft': ['acoustic', 'singer-songwriter', 'soft rock', 'folk pop'],
            'Chill': ['ambient', 'chillout', 'lounge', 'downtempo', 'trip hop'],
            'Spiritual': ['meditation', 'ambient', 'new age', 'world music', 'mantra']
        }
    
    def train(self, train_data: List[Tuple[str, str]]):
        """Train the classifier with track-folder mappings."""
        print(f"  Training {self.name}...")
        
        # Load playlist data for genre information
        self.playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
        
        # Build artist mappings
        artist_folder_sets = build_artist_folder_mapping(train_data, self.playlists_dict)
        self.single_folder_artists = get_single_folder_artists(artist_folder_sets)
        
        # Convert sets to confidence mappings
        self.artist_folder_mapping = {}
        for artist_name, folders in artist_folder_sets.items():
            if len(folders) > 1:
                # Multi-folder artist - equal confidence across folders
                confidence = 1.0 / len(folders)
                self.artist_folder_mapping[artist_name] = {folder: confidence for folder in folders}
            elif len(folders) == 1:
                # Single folder artist - high confidence
                folder = list(folders)[0]
                self.artist_folder_mapping[artist_name] = {folder: 0.9}
        
        # Build genre mappings from playlist data
        self._build_genre_mappings()
        
        print(f"    Single-folder artists: {len(self.single_folder_artists)}")
        print(f"    Artists with genre data: {len(self.artist_genres)}")
    
    def _build_genre_mappings(self):
        """Build genre to folder mappings from playlist data."""
        folder_genres = defaultdict(list)
        
        for playlist_id, playlist_data in self.playlists_dict.items():
            folder_name = playlist_data.get("folder")
            if not folder_name or folder_name not in self.discovery_keywords:
                continue
                
            for track in playlist_data["tracks"]:
                track_id = track["id"]
                artists = get_track_artists(track)
                
                for artist in artists:
                    artist_name = artist["name"]
                    genres = artist.get("genres", [])
                    
                    if genres:
                        self.artist_genres[artist_name] = genres
                        for genre in genres:
                            folder_genres[folder_name].append(genre.lower())
        
        # Build genre to folder probability mapping
        for folder, genres in folder_genres.items():
            genre_counts = Counter(genres)
            total = sum(genre_counts.values())
            
            for genre, count in genre_counts.items():
                if genre not in self.genre_folder_mapping:
                    self.genre_folder_mapping[genre] = {}
                self.genre_folder_mapping[genre][folder] = count / total
    
    def predict(self, track_id: str) -> Optional[str]:
        """Predict folder for a track using high-coverage strategy."""
        if self.strategy_name == "aggressive_coverage":
            return self._predict_aggressive_coverage(track_id)
        elif self.strategy_name == "discovery_mode":
            return self._predict_discovery_mode(track_id)
        elif self.strategy_name == "genre_fallback":
            return self._predict_genre_fallback(track_id)
        elif self.strategy_name == "multi_threshold":
            return self._predict_multi_threshold(track_id)
        else:
            return self._predict_aggressive_coverage(track_id)
    
    def _predict_aggressive_coverage(self, track_id: str) -> Optional[str]:
        """Strategy 1: Aggressive thresholds + artist + genre scoring."""
        track_data = self._get_track_data(track_id)
        if not track_data:
            return None
        
        track_artists = self._get_track_artists(track_data)
        all_genres = self._get_all_genres(track_artists)
        
        folder_scores = {}
        
        # Score each folder
        for folder in self.aggressive_thresholds.keys():
            # Artist score (primary)
            artist_score = self._calculate_artist_score(track_artists, folder)
            
            # Genre score (secondary)  
            genre_score = self._calculate_genre_score(all_genres, folder)
            
            # Combined score with artist preference
            combined_score = max(artist_score, genre_score * 0.7)
            
            # Check against aggressive threshold
            threshold = self.aggressive_thresholds[folder]
            if combined_score >= threshold:
                folder_scores[folder] = combined_score
        
        # Return highest scoring folder
        if folder_scores:
            return max(folder_scores, key=folder_scores.get)
        return None
    
    def _predict_discovery_mode(self, track_id: str) -> Optional[str]:
        """Strategy 2: Discovery mode - prioritize finding new artists."""
        track_data = self._get_track_data(track_id)
        if not track_data:
            return None
        
        track_artists = self._get_track_artists(track_data)
        all_genres = self._get_all_genres(track_artists)
        
        # First try artist lookup
        for artist in track_artists:
            artist_name = artist["name"]
            if artist_name in self.single_folder_artists:
                return self.single_folder_artists[artist_name]
        
        # If no artist match, use enhanced genre discovery
        folder_scores = {}
        for folder, keywords in self.discovery_keywords.items():
            score = 0.0
            
            # Keyword matching in genres
            for genre in all_genres:
                genre_lower = genre.lower()
                for keyword in keywords:
                    if keyword in genre_lower:
                        # Boost score based on keyword specificity
                        keyword_boost = len(keyword) / 20.0  # Longer keywords = more specific
                        score += 0.3 + keyword_boost
            
            # Lower threshold for discovery
            if score >= 0.1:  # Very permissive
                folder_scores[folder] = score
        
        if folder_scores:
            return max(folder_scores, key=folder_scores.get)
        return None
    
    def _predict_genre_fallback(self, track_id: str) -> Optional[str]:
        """Strategy 3: Artist first, then comprehensive genre fallback."""
        track_data = self._get_track_data(track_id)
        if not track_data:
            return None
        
        track_artists = self._get_track_artists(track_data)
        all_genres = self._get_all_genres(track_artists)
        
        # Step 1: Single-folder artist lookup (highest confidence)
        for artist in track_artists:
            artist_name = artist["name"]
            if artist_name in self.single_folder_artists:
                return self.single_folder_artists[artist_name]
        
        # Step 2: Multi-folder artist lookup with genre context
        folder_scores = {}
        for artist in track_artists:
            artist_name = artist["name"]
            if artist_name in self.artist_folder_mapping:
                for folder, confidence in self.artist_folder_mapping[artist_name].items():
                    folder_scores[folder] = folder_scores.get(folder, 0) + confidence * 0.8
        
        # Step 3: Genre-based scoring for all folders
        for folder in self.aggressive_thresholds.keys():
            genre_score = self._calculate_enhanced_genre_score(all_genres, folder)
            folder_scores[folder] = folder_scores.get(folder, 0) + genre_score * 0.6
        
        # Apply very low thresholds
        valid_folders = {f: s for f, s in folder_scores.items() if s >= 0.05}
        
        if valid_folders:
            return max(valid_folders, key=valid_folders.get)
        return None
    
    def _predict_multi_threshold(self, track_id: str) -> Optional[str]:
        """Strategy 4: Multiple threshold levels with cascading fallbacks."""
        track_data = self._get_track_data(track_id)
        if not track_data:
            return None
        
        track_artists = self._get_track_artists(track_data)
        all_genres = self._get_all_genres(track_artists)
        
        # Calculate scores for all folders
        folder_scores = {}
        for folder in self.aggressive_thresholds.keys():
            artist_score = self._calculate_artist_score(track_artists, folder)
            genre_score = self._calculate_genre_score(all_genres, folder)
            keyword_score = self._calculate_keyword_score(all_genres, folder)
            
            # Multi-factor scoring
            folder_scores[folder] = max(
                artist_score,                    # Direct artist match
                genre_score * 0.7,              # Genre analysis  
                keyword_score * 0.5             # Keyword fallback
            )
        
        # Try progressively lower thresholds
        thresholds = [0.15, 0.10, 0.05, 0.02]  # High to low confidence
        
        for threshold in thresholds:
            valid_folders = {f: s for f, s in folder_scores.items() if s >= threshold}
            if valid_folders:
                return max(valid_folders, key=valid_folders.get)
        
        return None
    
    def _calculate_artist_score(self, track_artists: List[Dict], folder: str) -> float:
        """Calculate artist-based score for a folder."""
        score = 0.0
        
        for artist in track_artists:
            artist_name = artist.get("name", "")
            if not artist_name:
                continue
            
            # Single-folder artist (highest confidence)
            if artist_name in self.single_folder_artists:
                if self.single_folder_artists[artist_name] == folder:
                    score = max(score, 0.9)
            
            # Multi-folder artist  
            elif artist_name in self.artist_folder_mapping:
                if folder in self.artist_folder_mapping[artist_name]:
                    artist_confidence = self.artist_folder_mapping[artist_name][folder]
                    score = max(score, artist_confidence * 0.8)
        
        return score
    
    def _calculate_genre_score(self, genres: List[str], folder: str) -> float:
        """Calculate genre-based score for a folder."""
        score = 0.0
        
        for genre in genres:
            genre_lower = genre.lower()
            if genre_lower in self.genre_folder_mapping:
                if folder in self.genre_folder_mapping[genre_lower]:
                    genre_confidence = self.genre_folder_mapping[genre_lower][folder]
                    score = max(score, genre_confidence * 0.6)
        
        return score
    
    def _calculate_keyword_score(self, genres: List[str], folder: str) -> float:
        """Calculate keyword-based score for a folder."""
        if folder not in self.discovery_keywords:
            return 0.0
        
        score = 0.0
        keywords = self.discovery_keywords[folder]
        
        for genre in genres:
            genre_lower = genre.lower()
            for keyword in keywords:
                if keyword in genre_lower:
                    # Score based on keyword specificity and match quality
                    match_score = len(keyword) / len(genre_lower)
                    score = max(score, match_score * 0.4)
        
        return score
    
    def _calculate_enhanced_genre_score(self, genres: List[str], folder: str) -> float:
        """Enhanced genre scoring combining multiple approaches."""
        genre_score = self._calculate_genre_score(genres, folder)
        keyword_score = self._calculate_keyword_score(genres, folder)
        
        # Combine with keyword boost
        return max(genre_score, keyword_score * 1.2)
    
    def _get_track_data(self, track_id: str) -> Optional[Dict]:
        """Get track data from playlist data."""
        for playlist_data in self.playlists_dict.values():
            for track in playlist_data["tracks"]:
                if track["id"] == track_id:
                    return track
        return None
    
    def _get_track_artists(self, track_data: Dict) -> List[Dict]:
        """Get artist information from track data."""
        artists = []
        if "artists" in track_data:
            for artist in track_data["artists"]:
                artists.append({
                    "id": artist.get("id", ""),
                    "name": artist.get("name", ""),
                    "genres": artist.get("genres", [])
                })
        return artists
    
    def _get_all_genres(self, track_artists: List[Dict]) -> List[str]:
        """Get all genres for track artists."""
        all_genres = []
        for artist in track_artists:
            artist_name = artist.get("name", "")
            if not artist_name:
                continue
                
            if artist_name in self.artist_genres:
                all_genres.extend(self.artist_genres[artist_name])
            # Also get genres directly from artist data
            if "genres" in artist and artist["genres"]:
                all_genres.extend(artist["genres"])
        return all_genres


def create_strategy_variants():
    """Create different strategy variants for testing."""
    strategies = [
        HighCoverageClassifier("aggressive_coverage"),
        HighCoverageClassifier("discovery_mode"), 
        HighCoverageClassifier("genre_fallback"),
        HighCoverageClassifier("multi_threshold")
    ]
    return strategies