#!/usr/bin/env python3
"""
Enhanced classifier that combines existing artist/genre patterns with audio features
from multiple music APIs (Last.fm, GetSongBPM, Deezer).
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
    from analysis.genre.composite_classifier import CompositeClassifier
except ImportError:
    from classification_framework import BaseClassifier, ClassificationResult
    from classification_metrics import (
        get_single_folder_artists,
        build_artist_folder_mapping,
        get_track_artists
    )
    from composite_classifier import CompositeClassifier

from common.music_api_clients import MusicFeatureFetcher
from common.music_api_config import get_lastfm_api_key, get_getsongbpm_api_key

class EnhancedAudioClassifier(BaseClassifier):
    """
    Enhanced classifier that combines artist/genre patterns with audio features.
    Falls back to existing CompositeClassifier when audio features aren't available.
    """
    
    def __init__(self):
        super().__init__("Enhanced Audio Feature Classifier")
        
        # Initialize the base composite classifier for fallback
        self.base_classifier = CompositeClassifier()
        
        # Initialize music feature fetcher
        lastfm_key = get_lastfm_api_key()
        getsongbpm_key = get_getsongbpm_api_key()
        self.music_fetcher = MusicFeatureFetcher(lastfm_api_key=lastfm_key, getsongbpm_api_key=getsongbpm_key)
        
        # Audio feature patterns learned from training data
        self.folder_audio_patterns = {}
        
        # Audio feature weights for classification
        self.audio_feature_weights = {
            'bpm': {
                'House': (120, 130, 0.8),      # BPM range, weight
                'Electronic': (100, 140, 0.6),
                'Rave': (140, 180, 0.9),
                'Rock': (90, 130, 0.5),
                'Chill': (60, 100, 0.7),
                'Vibes': (70, 110, 0.6),
                'Alive': (100, 140, 0.5),      # Melodic dubstep range
                'Base': (70, 110, 0.6),        # Dubstep range
            },
            'duration_ms': {
                'Alive': (180000, 300000, 0.4),  # 3-5 minutes for melodic tracks
                'Base': (120000, 240000, 0.3),   # 2-4 minutes for heavy drops
                'House': (180000, 420000, 0.3),  # 3-7 minutes for progressive
                'Electronic': (120000, 360000, 0.2),  # Wide range
            },
            'explicit': {
                'Rock': (True, 0.3),            # Rock more likely explicit
                'Spiritual': (False, 0.6),      # Spiritual less likely explicit
                'Soft': (False, 0.4),
            }
        }
        
        # Genre keywords that boost classification with audio features
        self.enhanced_genre_keywords = {
            'House': ['house', 'tech house', 'deep house', 'progressive house', 'minimal', 'techno'],
            'Electronic': ['electronic', 'electro', 'synthwave', 'ambient electronic', 'experimental', 'synth'],
            'Rave': ['hardstyle', 'hardcore', 'gabber', 'psytrance', 'hard dance', 'rave', 'trance'],
            'Alive': ['melodic dubstep', 'future bass', 'melodic bass', 'chillstep', 'emotional', 'melodic'],
            'Base': ['dubstep', 'riddim', 'bass music', 'hybrid trap', 'bass house', 'heavy', 'drop'],
            'Rock': ['rock', 'alternative rock', 'indie rock', 'progressive rock', 'metal', 'punk'],
            'Reggae': ['reggae', 'dub', 'ska', 'dancehall', 'roots reggae', 'reggaeton'],
            'Funk Soul': ['funk', 'soul', 'neo soul', 'p funk', 'r&b', 'groove', 'motown'],
            'Vibes': ['chill', 'downtempo', 'trip hop', 'lo-fi', 'ambient', 'lounge', 'atmospheric'],
            'Spiritual': ['ambient', 'new age', 'meditation', 'drone', 'healing', 'sacred', 'zen'],
            'Soft': ['acoustic', 'folk', 'singer-songwriter', 'indie folk', 'ballad', 'mellow'],
            'Sierra': ['indie', 'indie folk', 'indie pop', 'indie rock', 'alternative', 'indietronica'],
            'Chill': ['chillout', 'ambient', 'downtempo', 'relaxing', 'calm', 'peaceful'],
            'Ride': ['synthwave', 'retrowave', 'outrun', 'driving', 'electronic rock', '80s']
        }
        
    def train(self, train_data: Dict[str, Any]) -> None:
        """Train both the base classifier and learn audio feature patterns."""
        print(f"  Training {self.name}...")
        
        # Train the base composite classifier
        self.base_classifier.train(train_data)
        
        # Learn audio feature patterns from training data
        self._learn_audio_patterns(train_data)
        
        self.is_trained = True
        print(f"    ✅ Enhanced classifier ready with audio feature integration")
        
    def _learn_audio_patterns(self, train_data: Dict[str, Any]) -> None:
        """Learn audio feature patterns from a sample of training data."""
        print(f"    🎵 Learning audio patterns from training data...")
        
        train_tracks = train_data.get("train_tracks", [])
        playlists_dict = train_data.get("playlists_dict", {})
        
        if not train_tracks:
            print(f"    ⚠️ No training tracks available for audio pattern learning")
            return
            
        # Sample a subset of training tracks to learn patterns (to avoid API limits)
        sample_size = min(50, len(train_tracks))  # Sample 50 tracks max
        sample_tracks = train_tracks[:sample_size]
        
        folder_features = defaultdict(list)
        analyzed_count = 0
        
        for track_id, folder_name in sample_tracks:
            # Get track info
            track_artists = get_track_artists(track_id, playlists_dict)
            if not track_artists:
                continue
                
            # Get first artist name for API lookup
            artist_name = track_artists[0].get('name', '')
            
            # Get track name
            track_name = None
            for playlist_data in playlists_dict.values():
                for track in playlist_data.get('tracks', []):
                    if track.get('id') == track_id:
                        track_name = track.get('name', '')
                        break
                if track_name:
                    break
                    
            if not track_name or not artist_name:
                continue
                
            # Fetch audio features
            try:
                features = self.music_fetcher.get_combined_features(artist_name, track_name)
                if any(features.values()):  # If we got any features
                    folder_features[folder_name].append(features)
                    analyzed_count += 1
                    
                    if analyzed_count % 10 == 0:
                        print(f"      📊 Analyzed {analyzed_count} tracks...")
                        
            except Exception as e:
                print(f"      ⚠️ Error fetching features for {artist_name} - {track_name}: {e}")
                continue
                
        # Store learned patterns
        self.folder_audio_patterns = {}
        for folder, features_list in folder_features.items():
            if features_list:
                self.folder_audio_patterns[folder] = self._summarize_audio_features(features_list)
                
        print(f"    📊 Learned audio patterns for {len(self.folder_audio_patterns)} folders from {analyzed_count} tracks")
        
    def _summarize_audio_features(self, features_list: List[Dict]) -> Dict[str, Any]:
        """Summarize audio features for a folder."""
        summary = {
            'bpm_values': [],
            'duration_values': [],
            'explicit_count': 0,
            'total_count': len(features_list),
            'common_tags': Counter()
        }
        
        for features in features_list:
            if features.get('bpm'):
                summary['bpm_values'].append(features['bpm'])
            if features.get('duration_ms'):
                summary['duration_values'].append(features['duration_ms'])
            if features.get('explicit'):
                summary['explicit_count'] += 1
            if features.get('tags'):
                summary['common_tags'].update(features['tags'])
                
        # Calculate statistics
        if summary['bpm_values']:
            summary['avg_bpm'] = sum(summary['bpm_values']) / len(summary['bpm_values'])
            summary['bpm_range'] = (min(summary['bpm_values']), max(summary['bpm_values']))
            
        if summary['duration_values']:
            summary['avg_duration'] = sum(summary['duration_values']) / len(summary['duration_values'])
            
        summary['explicit_ratio'] = summary['explicit_count'] / summary['total_count']
        summary['top_tags'] = [tag for tag, count in summary['common_tags'].most_common(10)]
        
        return summary
        
    def predict(self, track_id: str) -> ClassificationResult:
        """Predict using enhanced audio features + base classifier."""
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
            # Get base classification first
            base_result = self.base_classifier.predict(track_id)
            
            # If base classifier found strong matches, start with those
            if base_result.predicted_folders:
                result.predicted_folders = base_result.predicted_folders.copy()
                result.confidence_scores = getattr(base_result, 'confidence_scores', {}).copy()
                result.reasoning = f"Base: {base_result.reasoning}"
                
                # Try to enhance with audio features
                enhancement = self._enhance_with_audio_features(track_id, result.predicted_folders)
                if enhancement:
                    # Merge enhancements
                    for folder, boost in enhancement['boosts'].items():
                        if folder in result.confidence_scores:
                            # Boost existing confidence
                            result.confidence_scores[folder] = min(0.95, result.confidence_scores[folder] + boost)
                        else:
                            # Add new folder suggestion
                            result.confidence_scores[folder] = boost
                    
                    # Update predicted folders based on enhanced confidence
                    threshold = 0.15
                    result.predicted_folders = [folder for folder, conf in result.confidence_scores.items() 
                                              if conf >= threshold]
                    
                    result.reasoning += f" + Audio: {enhancement['reasoning']}"
                    
            else:
                # Base classifier found nothing, try audio-only classification
                audio_prediction = self._classify_by_audio_features_only(track_id)
                if audio_prediction:
                    result.predicted_folders = audio_prediction['folders']
                    result.confidence_scores = audio_prediction['confidence_scores']
                    result.reasoning = f"Audio-only: {audio_prediction['reasoning']}"
                else:
                    result.reasoning = "No patterns found (base + audio)"
                    
        except Exception as e:
            result.reasoning = f"Error during enhanced classification: {str(e)}"
            
        result.processing_time_ms = (time.time() - start_time) * 1000
        return result
        
    def _enhance_with_audio_features(self, track_id: str, candidate_folders: List[str]) -> Optional[Dict[str, Any]]:
        """Enhance existing predictions with audio feature analysis."""
        # Get track info for API lookup
        track_artists = get_track_artists(track_id, self.base_classifier.playlists_dict)
        if not track_artists:
            return None
            
        artist_name = track_artists[0].get('name', '')
        track_name = None
        
        # Get track name
        for playlist_data in self.base_classifier.playlists_dict.values():
            for track in playlist_data.get('tracks', []):
                if track.get('id') == track_id:
                    track_name = track.get('name', '')
                    break
            if track_name:
                break
                
        if not track_name or not artist_name:
            return None
            
        try:
            # Fetch audio features
            audio_features = self.music_fetcher.get_combined_features(artist_name, track_name)
            
            if not any(audio_features.values()):
                return None
                
            # Calculate boosts for candidate folders
            folder_boosts = {}
            reasoning_parts = []
            
            for folder in candidate_folders:
                boost = self._calculate_audio_boost(audio_features, folder)
                if boost > 0.05:  # Minimum meaningful boost
                    folder_boosts[folder] = boost
                    reasoning_parts.append(f"{folder}(+{boost:.2f})")
                    
            if folder_boosts:
                return {
                    'boosts': folder_boosts,
                    'reasoning': ', '.join(reasoning_parts)
                }
                
        except Exception as e:
            print(f"    ⚠️ Error enhancing with audio features: {e}")
            
        return None
        
    def _classify_by_audio_features_only(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Classify using only audio features (fallback when no artist patterns found)."""
        # Get track info for API lookup
        track_artists = get_track_artists(track_id, self.base_classifier.playlists_dict)
        if not track_artists:
            return None
            
        artist_name = track_artists[0].get('name', '')
        track_name = None
        
        # Get track name
        for playlist_data in self.base_classifier.playlists_dict.values():
            for track in playlist_data.get('tracks', []):
                if track.get('id') == track_id:
                    track_name = track.get('name', '')
                    break
            if track_name:
                break
                
        if not track_name or not artist_name:
            return None
            
        try:
            # Fetch audio features
            audio_features = self.music_fetcher.get_combined_features(artist_name, track_name)
            
            if not any(audio_features.values()):
                return None
                
            # Calculate scores for all folders based on audio features
            folder_scores = {}
            for folder in self.enhanced_genre_keywords.keys():
                score = self._calculate_audio_score(audio_features, folder)
                if score > 0.1:  # Minimum threshold for audio-only classification
                    folder_scores[folder] = score
                    
            if not folder_scores:
                return None
                
            # Keep only meaningful scores
            max_score = max(folder_scores.values())
            threshold = max(0.15, max_score * 0.6)  # Adaptive threshold
            
            valid_folders = {folder: score for folder, score in folder_scores.items() 
                           if score >= threshold}
            
            if not valid_folders:
                return None
                
            # Convert to confidence scores (lower for audio-only)
            confidence_scores = {folder: min(0.7, score * 0.8) 
                               for folder, score in valid_folders.items()}
            
            feature_summary = []
            if audio_features.get('bpm'):
                feature_summary.append(f"BPM:{audio_features['bpm']}")
            if audio_features.get('tags'):
                feature_summary.append(f"Tags:{len(audio_features['tags'])}")
                
            return {
                'folders': list(valid_folders.keys()),
                'confidence_scores': confidence_scores,
                'reasoning': f"Audio features: {', '.join(feature_summary)}"
            }
            
        except Exception as e:
            print(f"    ⚠️ Error in audio-only classification: {e}")
            return None
            
    def _calculate_audio_boost(self, audio_features: Dict[str, Any], folder: str) -> float:
        """Calculate confidence boost for a folder based on audio features."""
        boost = 0.0
        
        # BPM matching
        if audio_features.get('bpm') and folder in self.audio_feature_weights['bpm']:
            min_bpm, max_bpm, weight = self.audio_feature_weights['bpm'][folder]
            if min_bpm <= audio_features['bpm'] <= max_bpm:
                boost += weight * 0.1  # 10% boost for BPM match
                
        # Duration matching
        if audio_features.get('duration_ms') and folder in self.audio_feature_weights['duration_ms']:
            min_dur, max_dur, weight = self.audio_feature_weights['duration_ms'][folder]
            if min_dur <= audio_features['duration_ms'] <= max_dur:
                boost += weight * 0.05  # 5% boost for duration match
                
        # Explicit content matching
        if audio_features.get('explicit') is not None and folder in self.audio_feature_weights['explicit']:
            expected_explicit, weight = self.audio_feature_weights['explicit'][folder]
            if audio_features['explicit'] == expected_explicit:
                boost += weight * 0.05  # 5% boost for explicit match
                
        # Genre tag matching
        if audio_features.get('tags') and folder in self.enhanced_genre_keywords:
            folder_keywords = self.enhanced_genre_keywords[folder]
            matching_tags = [tag for tag in audio_features['tags'] 
                           if any(keyword in tag for keyword in folder_keywords)]
            if matching_tags:
                boost += min(0.15, len(matching_tags) * 0.03)  # Up to 15% boost for tag matches
                
        return boost
        
    def _calculate_audio_score(self, audio_features: Dict[str, Any], folder: str) -> float:
        """Calculate total audio score for a folder."""
        score = 0.0
        
        # More aggressive scoring for audio-only classification
        
        # BPM scoring
        if audio_features.get('bpm') and folder in self.audio_feature_weights['bpm']:
            min_bpm, max_bpm, weight = self.audio_feature_weights['bpm'][folder]
            if min_bpm <= audio_features['bpm'] <= max_bpm:
                score += weight * 0.4  # Strong BPM match
                
        # Genre tag scoring
        if audio_features.get('tags') and folder in self.enhanced_genre_keywords:
            folder_keywords = self.enhanced_genre_keywords[folder]
            matching_tags = [tag for tag in audio_features['tags'] 
                           if any(keyword in tag for keyword in folder_keywords)]
            if matching_tags:
                score += min(0.6, len(matching_tags) * 0.15)  # Strong tag matches
                
        # Duration scoring
        if audio_features.get('duration_ms') and folder in self.audio_feature_weights['duration_ms']:
            min_dur, max_dur, weight = self.audio_feature_weights['duration_ms'][folder]
            if min_dur <= audio_features['duration_ms'] <= max_dur:
                score += weight * 0.2  # Moderate duration match
                
        return score
        
    def get_info(self) -> Dict[str, Any]:
        """Get enhanced classifier information."""
        info = super().get_info()
        info.update({
            "description": "Enhanced classifier combining artist patterns with audio features",
            "uses_audio_features": True,
            "uses_artist_patterns": True,
            "uses_genre_data": True,
            "available_apis": list(self.music_fetcher.clients.keys()),
            "learned_audio_patterns": len(self.folder_audio_patterns),
            "base_classifier": self.base_classifier.get_info()["name"]
        })
        return info