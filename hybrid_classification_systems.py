#!/usr/bin/env python3
"""
Multiple hybrid classification systems for enhanced genre prediction.

Implements and tests different approaches combining:
- Artist-based classification (using playlist_to_artists.json)
- Audio features analysis 
- Genre mappings
- Confidence scoring
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import statistics
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    """Result of a classification attempt."""
    predicted_folders: List[str]
    confidence_scores: Dict[str, float]
    method: str
    reasoning: str

@dataclass
class TestResults:
    """Results of testing a classification system."""
    name: str
    accuracy: float
    precision: float
    recall: float
    coverage: float
    correct_predictions: int
    total_predictions: int
    total_tracks: int

class HybridClassificationSystem:
    """Base class for hybrid classification systems."""
    
    def __init__(self, name: str):
        self.name = name
        self.artist_analysis = self._load_artist_analysis()
        self.track_mapping = self._load_track_mapping()
        self.playlist_artists = self._load_playlist_artists()
        
    def _load_artist_analysis(self) -> Dict:
        """Load artist folder analysis results."""
        cache_dir = Path.home() / ".spotify_cache"
        results_file = cache_dir / "artist_folder_analysis.json"
        
        if results_file.exists():
            with open(results_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_track_mapping(self) -> Dict:
        """Load track to folder mapping."""
        cache_dir = Path.home() / ".spotify_cache"
        mapping_file = cache_dir / "track_folder_mapping.json"
        
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_playlist_artists(self) -> Dict:
        """Load playlist to artists mapping."""
        artists_file = Path('_data/playlist_to_artists.json')
        
        if artists_file.exists():
            with open(artists_file, 'r') as f:
                return json.load(f)
        return {}
    
    def classify_track(self, track_id: str, track_artists: List[str], 
                      audio_features: Optional[Dict] = None) -> ClassificationResult:
        """Classify a track using this system's approach."""
        raise NotImplementedError("Subclasses must implement classify_track")


class ArtistFirstSystem(HybridClassificationSystem):
    """System 1: Artist-first with audio feature fallback."""
    
    def __init__(self):
        super().__init__("Artist-First")
        self.single_folder_artists = self.artist_analysis.get('single_folder_artists', {})
    
    def classify_track(self, track_id: str, track_artists: List[str], 
                      audio_features: Optional[Dict] = None) -> ClassificationResult:
        """Classify using artist priority, then audio features."""
        
        # Step 1: Check single-folder artists
        artist_predictions = set()
        artist_confidences = {}
        
        for artist in track_artists:
            if artist in self.single_folder_artists:
                folder = self.single_folder_artists[artist]
                artist_predictions.add(folder)
                artist_confidences[folder] = 0.95  # High confidence for single-folder artists
        
        if artist_predictions:
            return ClassificationResult(
                predicted_folders=list(artist_predictions),
                confidence_scores=artist_confidences,
                method="single_folder_artist",
                reasoning=f"Artists {[a for a in track_artists if a in self.single_folder_artists]} are folder-specific"
            )
        
        # Step 2: Audio features fallback for electronic music
        if audio_features:
            audio_predictions = self._classify_by_audio_features(audio_features)
            if audio_predictions.predicted_folders:
                return audio_predictions
        
        # Step 3: No prediction
        return ClassificationResult(
            predicted_folders=[],
            confidence_scores={},
            method="no_prediction",
            reasoning="No single-folder artists found and insufficient audio features"
        )
    
    def _classify_by_audio_features(self, features: Dict) -> ClassificationResult:
        """Classify electronic music using audio features."""
        predictions = {}
        
        energy = features.get('energy', 0)
        danceability = features.get('danceability', 0)
        valence = features.get('valence', 0)
        tempo = features.get('tempo', 120)
        
        # Electronic sub-genre rules based on your library patterns
        if danceability > 0.7 and energy > 0.7:
            if tempo > 125:
                predictions['Rave'] = 0.6  # High energy + fast tempo
            else:
                predictions['House'] = 0.5  # High danceability, moderate tempo
        
        if energy > 0.8 and valence < 0.4:
            predictions['Base'] = 0.6  # High energy, dark mood
        
        if danceability > 0.5 and energy < 0.6 and valence > 0.5:
            predictions['Vibes'] = 0.4  # Danceable but chill
        
        return ClassificationResult(
            predicted_folders=list(predictions.keys()),
            confidence_scores=predictions,
            method="audio_features",
            reasoning=f"Audio features: energy={energy:.2f}, danceability={danceability:.2f}, valence={valence:.2f}"
        )


class ConfidenceWeightedSystem(HybridClassificationSystem):
    """System 2: Weighted confidence from multiple sources."""
    
    def __init__(self):
        super().__init__("Confidence-Weighted")
        self.single_folder_artists = self.artist_analysis.get('single_folder_artists', {})
        self.multi_folder_artists = self.artist_analysis.get('multi_folder_artists', {})
        self.folder_artist_counts = self.artist_analysis.get('folder_artist_counts', {})
    
    def classify_track(self, track_id: str, track_artists: List[str], 
                      audio_features: Optional[Dict] = None) -> ClassificationResult:
        """Classify using weighted confidence from all sources."""
        
        folder_scores = defaultdict(float)
        reasoning_parts = []
        
        # Artist-based scoring
        for artist in track_artists:
            if artist in self.single_folder_artists:
                folder = self.single_folder_artists[artist]
                folder_scores[folder] += 0.9  # High weight for single-folder artists
                reasoning_parts.append(f"{artist}→{folder}(0.9)")
            
            elif artist in self.multi_folder_artists:
                folders = self.multi_folder_artists[artist]
                weight_per_folder = 0.3 / len(folders)  # Distribute weight across folders
                for folder in folders:
                    folder_scores[folder] += weight_per_folder
                    reasoning_parts.append(f"{artist}→{folder}({weight_per_folder:.2f})")
        
        # Audio features scoring
        if audio_features:
            audio_scores = self._score_by_audio_features(audio_features)
            for folder, score in audio_scores.items():
                folder_scores[folder] += score * 0.4  # Moderate weight for audio features
                reasoning_parts.append(f"audio→{folder}({score*0.4:.2f})")
        
        # Convert to sorted predictions
        if folder_scores:
            sorted_folders = sorted(folder_scores.items(), key=lambda x: x[1], reverse=True)
            # Only return folders with reasonable confidence
            predictions = [(folder, score) for folder, score in sorted_folders if score > 0.2]
            
            if predictions:
                return ClassificationResult(
                    predicted_folders=[f[0] for f in predictions],
                    confidence_scores=dict(predictions),
                    method="confidence_weighted",
                    reasoning="; ".join(reasoning_parts)
                )
        
        return ClassificationResult(
            predicted_folders=[],
            confidence_scores={},
            method="no_prediction",
            reasoning="Insufficient confidence from all sources"
        )
    
    def _score_by_audio_features(self, features: Dict) -> Dict[str, float]:
        """Score folders based on audio features."""
        scores = {}
        
        energy = features.get('energy', 0)
        danceability = features.get('danceability', 0)
        valence = features.get('valence', 0)
        tempo = features.get('tempo', 120)
        acousticness = features.get('acousticness', 0)
        
        # Electronic genres
        if danceability > 0.6 and energy > 0.6:
            if tempo > 130:
                scores['Rave'] = min(0.8, (danceability + energy) / 2)
            elif tempo > 120:
                scores['House'] = min(0.7, danceability * 0.8)
            else:
                scores['Electronic'] = min(0.6, (danceability + energy) / 2.5)
        
        if energy > 0.7 and valence < 0.5:
            scores['Base'] = min(0.7, energy * (1 - valence))
        
        # Chill genres
        if acousticness > 0.5 and energy < 0.5:
            if valence > 0.6:
                scores['Vibes'] = min(0.6, acousticness * valence)
            else:
                scores['Chill'] = min(0.5, acousticness)
        
        # Rock
        if energy > 0.6 and acousticness < 0.3 and danceability < 0.6:
            scores['Rock'] = min(0.6, energy * (1 - acousticness))
        
        return scores


class ElectronicSpecialistSystem(HybridClassificationSystem):
    """System 3: Specialized for electronic music classification."""
    
    def __init__(self):
        super().__init__("Electronic-Specialist")
        self.single_folder_artists = self.artist_analysis.get('single_folder_artists', {})
        
        # Define electronic folders
        self.electronic_folders = {'Electronic', 'Rave', 'House', 'Base', 'Alive', 'Vibes'}
        
        # Electronic-specific artist patterns from your data
        self.electronic_artists = self._build_electronic_artist_patterns()
    
    def _build_electronic_artist_patterns(self) -> Dict[str, Dict]:
        """Build patterns specific to electronic artists."""
        patterns = {}
        
        # High-confidence electronic folder mappings based on your top artists
        electronic_specialists = {
            'Base': ['Subtronics', 'CharlestheFirst', 'Mersiv', 'Ternion Sound', 'REAPER', 'EAZYBAKED', 'Noisia', 'Of The Trees'],
            'Rave': ['ILLENIUM', 'Rezz', 'NGHTMRE', 'Virtual Riot', 'PEEKABOO', 'Excision', 'Seven Lions'],
            'House': ['Tchami', 'Malaa', 'Disclosure', 'Habstrakt', 'Chris Lake', 'Ghastly', 'Dr. Fresch'],
            'Electronic': ['ODESZA', 'Tycho', 'Attom', 'Dabin', 'Kasbo', 'Grabbitz', 'Louis The Child'],
            'Alive': ['Ben Böhmer', 'Lane 8', 'Laffey', 'Sleepy Fish']
        }
        
        for folder, artists in electronic_specialists.items():
            for artist in artists:
                patterns[artist] = {'primary_folder': folder, 'confidence': 0.95}
        
        return patterns
    
    def classify_track(self, track_id: str, track_artists: List[str], 
                      audio_features: Optional[Dict] = None) -> ClassificationResult:
        """Classify with electronic music specialization."""
        
        folder_scores = defaultdict(float)
        reasoning_parts = []
        
        # Check for electronic specialists first
        for artist in track_artists:
            if artist in self.electronic_artists:
                pattern = self.electronic_artists[artist]
                folder = pattern['primary_folder']
                confidence = pattern['confidence']
                folder_scores[folder] += confidence
                reasoning_parts.append(f"{artist}→{folder}(specialist:{confidence})")
            
            elif artist in self.single_folder_artists:
                folder = self.single_folder_artists[artist]
                if folder in self.electronic_folders:
                    folder_scores[folder] += 0.8
                    reasoning_parts.append(f"{artist}→{folder}(single:0.8)")
                else:
                    folder_scores[folder] += 0.9  # Non-electronic but confident
                    reasoning_parts.append(f"{artist}→{folder}(single:0.9)")
        
        # Electronic-specific audio feature analysis
        if audio_features and not folder_scores:
            electronic_scores = self._classify_electronic_by_audio(audio_features)
            for folder, score in electronic_scores.items():
                folder_scores[folder] += score
                reasoning_parts.append(f"audio→{folder}({score:.2f})")
        
        # Return best predictions
        if folder_scores:
            sorted_folders = sorted(folder_scores.items(), key=lambda x: x[1], reverse=True)
            predictions = [(folder, score) for folder, score in sorted_folders if score > 0.3]
            
            if predictions:
                return ClassificationResult(
                    predicted_folders=[f[0] for f in predictions],
                    confidence_scores=dict(predictions),
                    method="electronic_specialist",
                    reasoning="; ".join(reasoning_parts)
                )
        
        return ClassificationResult(
            predicted_folders=[],
            confidence_scores={},
            method="no_prediction",
            reasoning="No electronic patterns matched"
        )
    
    def _classify_electronic_by_audio(self, features: Dict) -> Dict[str, float]:
        """Detailed electronic classification using audio features."""
        scores = {}
        
        energy = features.get('energy', 0)
        danceability = features.get('danceability', 0)
        valence = features.get('valence', 0)
        tempo = features.get('tempo', 120)
        loudness = features.get('loudness', -10)
        
        # Base: Heavy, dark, aggressive electronic
        if energy > 0.75 and valence < 0.4 and loudness > -8:
            scores['Base'] = 0.8
        
        # Rave: High energy, fast tempo, festival vibes
        if energy > 0.7 and danceability > 0.6 and tempo > 128:
            scores['Rave'] = 0.75
        
        # House: Danceable, moderate tempo, groove-focused
        if danceability > 0.7 and 120 <= tempo <= 130 and energy > 0.5:
            scores['House'] = 0.7
        
        # Alive: Uplifting, melodic, emotional electronic
        if valence > 0.5 and energy > 0.4 and danceability > 0.4:
            scores['Alive'] = 0.6
        
        # Electronic: General electronic music
        if danceability > 0.5 and energy > 0.4:
            scores['Electronic'] = 0.5
        
        return scores


class EnsembleSystem(HybridClassificationSystem):
    """System 4: Ensemble combining all three previous systems."""
    
    def __init__(self):
        super().__init__("Ensemble")
        self.artist_first = ArtistFirstSystem()
        self.confidence_weighted = ConfidenceWeightedSystem()
        self.electronic_specialist = ElectronicSpecialistSystem()
    
    def classify_track(self, track_id: str, track_artists: List[str], 
                      audio_features: Optional[Dict] = None) -> ClassificationResult:
        """Classify using ensemble of all systems."""
        
        # Get predictions from all systems
        results = [
            self.artist_first.classify_track(track_id, track_artists, audio_features),
            self.confidence_weighted.classify_track(track_id, track_artists, audio_features),
            self.electronic_specialist.classify_track(track_id, track_artists, audio_features)
        ]
        
        # Combine predictions with voting
        folder_votes = defaultdict(list)
        all_reasoning = []
        
        for result in results:
            for folder in result.predicted_folders:
                confidence = result.confidence_scores.get(folder, 0.5)
                folder_votes[folder].append(confidence)
            all_reasoning.append(f"{result.method}: {result.reasoning}")
        
        # Calculate ensemble scores
        ensemble_scores = {}
        for folder, confidences in folder_votes.items():
            # Average confidence weighted by number of systems voting
            avg_confidence = statistics.mean(confidences)
            vote_strength = len(confidences) / len(results)  # Fraction of systems voting
            ensemble_scores[folder] = avg_confidence * vote_strength
        
        if ensemble_scores:
            sorted_predictions = sorted(ensemble_scores.items(), key=lambda x: x[1], reverse=True)
            # Only keep predictions with reasonable ensemble score
            final_predictions = [(folder, score) for folder, score in sorted_predictions if score > 0.3]
            
            if final_predictions:
                return ClassificationResult(
                    predicted_folders=[f[0] for f in final_predictions],
                    confidence_scores=dict(final_predictions),
                    method="ensemble",
                    reasoning=" | ".join(all_reasoning)
                )
        
        return ClassificationResult(
            predicted_folders=[],
            confidence_scores={},
            method="ensemble_no_prediction",
            reasoning="No system consensus"
        )


def test_classification_system(system: HybridClassificationSystem, 
                             test_tracks: Dict[str, List[str]]) -> TestResults:
    """Test a classification system against known track-folder mappings."""
    
    print(f"\n🧪 Testing {system.name} System")
    print("=" * 50)
    
    correct_predictions = 0
    total_predictions = 0
    total_tracks = len(test_tracks)
    
    # Track prediction performance
    precision_numerator = 0  # correct predictions
    precision_denominator = 0  # total predictions made
    recall_numerator = 0  # correct predictions
    recall_denominator = 0  # total actual folders
    
    for track_id, actual_folders in test_tracks.items():
        # For testing, we'll use mock artists and audio features
        # In practice, you'd get these from Spotify API
        mock_artists = ["TestArtist"]  # This would come from track data
        mock_audio_features = {
            'energy': 0.7,
            'danceability': 0.6,
            'valence': 0.5,
            'tempo': 125
        }
        
        result = system.classify_track(track_id, mock_artists, mock_audio_features)
        predicted_folders = set(result.predicted_folders)
        actual_folders_set = set(actual_folders)
        
        # Calculate metrics
        if predicted_folders:
            total_predictions += 1
            precision_denominator += len(predicted_folders)
            recall_denominator += len(actual_folders_set)
            
            # Check for any correct predictions
            correct = predicted_folders.intersection(actual_folders_set)
            if correct:
                correct_predictions += 1
                precision_numerator += len(correct)
                recall_numerator += len(correct)
    
    # Calculate final metrics
    accuracy = correct_predictions / total_tracks if total_tracks > 0 else 0
    precision = precision_numerator / precision_denominator if precision_denominator > 0 else 0
    recall = recall_numerator / recall_denominator if recall_denominator > 0 else 0
    coverage = total_predictions / total_tracks if total_tracks > 0 else 0
    
    results = TestResults(
        name=system.name,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        coverage=coverage,
        correct_predictions=correct_predictions,
        total_predictions=total_predictions,
        total_tracks=total_tracks
    )
    
    print(f"✅ {system.name} Results:")
    print(f"   🎯 Accuracy: {accuracy:.1%} ({correct_predictions}/{total_tracks})")
    print(f"   🎯 Precision: {precision:.1%}")
    print(f"   🎯 Recall: {recall:.1%}")
    print(f"   📊 Coverage: {coverage:.1%} ({total_predictions}/{total_tracks})")
    
    return results


def main():
    """Test all hybrid classification systems."""
    print("🎵 Hybrid Classification Systems Testing")
    print("=" * 60)
    
    # Load test data
    cache_dir = Path.home() / ".spotify_cache"
    mapping_file = cache_dir / "track_folder_mapping.json"
    
    if not mapping_file.exists():
        print("❌ No track mapping found. Run build_track_folder_mapping.py first")
        return
    
    with open(mapping_file, 'r') as f:
        track_mapping = json.load(f)
    
    print(f"📊 Testing with {len(track_mapping)} tracks")
    
    # Initialize all systems
    systems = [
        ArtistFirstSystem(),
        ConfidenceWeightedSystem(),
        ElectronicSpecialistSystem(),
        EnsembleSystem()
    ]
    
    # Test each system
    all_results = []
    for system in systems:
        results = test_classification_system(system, track_mapping)
        all_results.append(results)
    
    # Compare results
    print(f"\n📈 SYSTEM COMPARISON")
    print("=" * 60)
    print(f"{'System':<20} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'Coverage':<10}")
    print("-" * 60)
    
    for result in all_results:
        print(f"{result.name:<20} {result.accuracy:<10.1%} {result.precision:<10.1%} {result.recall:<10.1%} {result.coverage:<10.1%}")
    
    # Find best system
    best_system = max(all_results, key=lambda x: x.accuracy)
    print(f"\n🏆 Best System: {best_system.name} with {best_system.accuracy:.1%} accuracy")


if __name__ == "__main__":
    main()