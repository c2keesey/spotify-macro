"""
Extensible classification framework for testing and comparing genre classification algorithms.

Provides abstract base classes and common utilities for implementing and evaluating
different classification approaches in a consistent manner.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from pathlib import Path
import json
import time


@dataclass
class ClassificationResult:
    """Result of a single track classification."""
    track_id: str
    predicted_folders: List[str]
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    method: str = ""
    reasoning: str = ""
    processing_time_ms: float = 0.0
    
    @property
    def has_predictions(self) -> bool:
        """Check if any predictions were made."""
        return len(self.predicted_folders) > 0
    
    @property
    def max_confidence(self) -> float:
        """Get the maximum confidence score."""
        return max(self.confidence_scores.values()) if self.confidence_scores else 0.0


@dataclass
class TrainTestSplit:
    """Container for train/test split data."""
    train_playlists: Dict[str, List[str]]  # folder -> playlist_names
    test_playlists: Dict[str, List[str]]   # folder -> playlist_names
    train_tracks: List[Tuple[str, str]]    # [(track_id, folder), ...]
    test_tracks: List[Tuple[str, str]]     # [(track_id, folder), ...]
    
    @property
    def train_size(self) -> int:
        return len(self.train_tracks)
    
    @property
    def test_size(self) -> int:
        return len(self.test_tracks)
    
    @property
    def folders(self) -> Set[str]:
        return set(self.train_playlists.keys()) | set(self.test_playlists.keys())


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for a classifier."""
    classifier_name: str
    
    # Core metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    coverage: float = 0.0  # % of tracks that got predictions
    
    # Detailed metrics
    per_folder_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    confidence_distribution: Dict[str, List[float]] = field(default_factory=dict)
    
    # Performance metrics
    avg_processing_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0
    
    # Counts
    total_predictions: int = 0
    correct_predictions: int = 0
    total_tracks: int = 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics."""
        return {
            "classifier": self.classifier_name,
            "accuracy": round(self.accuracy, 3),
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "f1_score": round(self.f1_score, 3),
            "coverage": round(self.coverage, 3),
            "total_tracks": self.total_tracks,
            "correct_predictions": self.correct_predictions,
            "avg_processing_time_ms": round(self.avg_processing_time_ms, 2)
        }


class BaseClassifier(ABC):
    """Abstract base class for all classification algorithms."""
    
    def __init__(self, name: str):
        self.name = name
        self.is_trained = False
        self.train_data = None
        
    @abstractmethod
    def train(self, train_data: Dict[str, Any]) -> None:
        """
        Train the classifier on the provided training data.
        
        Args:
            train_data: Dictionary containing training data with:
                - artist_to_playlists: Artist ID -> playlist IDs mapping
                - single_playlist_artists: List of single-playlist artist IDs
                - playlist_folders: Folder -> playlist files mapping
                - playlists_dict: Playlist data loaded via PlaylistDataLoader
                - train_tracks: List of (track_id, folder) tuples for training
        """
        pass
    
    @abstractmethod
    def predict(self, track_id: str) -> ClassificationResult:
        """
        Predict the folder(s) for a given track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            ClassificationResult with predictions and confidence scores
        """
        pass
    
    def get_name(self) -> str:
        """Get the classifier name."""
        return self.name
    
    def is_ready(self) -> bool:
        """Check if the classifier is ready for predictions."""
        return self.is_trained
    
    def get_info(self) -> Dict[str, Any]:
        """Get classifier information."""
        return {
            "name": self.name,
            "is_trained": self.is_trained,
            "class": self.__class__.__name__
        }


class ClassificationFramework:
    """Framework for managing and comparing multiple classification algorithms."""
    
    def __init__(self):
        self.classifiers: List[BaseClassifier] = []
        self.train_test_split: Optional[TrainTestSplit] = None
        self.evaluation_results: Dict[str, EvaluationMetrics] = {}
        
    def add_classifier(self, classifier: BaseClassifier) -> None:
        """Add a classifier to the framework."""
        self.classifiers.append(classifier)
        
    def set_train_test_split(self, split: TrainTestSplit) -> None:
        """Set the train/test split data."""
        self.train_test_split = split
        
    def train_all_classifiers(self, train_data: Dict[str, Any]) -> None:
        """Train all registered classifiers."""
        if not self.classifiers:
            raise ValueError("No classifiers registered")
            
        print(f"Training {len(self.classifiers)} classifiers...")
        
        for classifier in self.classifiers:
            print(f"  Training {classifier.get_name()}...")
            start_time = time.time()
            classifier.train(train_data)
            training_time = (time.time() - start_time) * 1000
            print(f"    Training completed in {training_time:.1f}ms")
            
    def evaluate_classifier(self, classifier: BaseClassifier, test_tracks: List[Tuple[str, str]]) -> EvaluationMetrics:
        """Evaluate a single classifier on test data."""
        if not classifier.is_ready():
            raise ValueError(f"Classifier {classifier.get_name()} is not trained")
            
        print(f"Evaluating {classifier.get_name()} on {len(test_tracks)} tracks...")
        
        metrics = EvaluationMetrics(classifier_name=classifier.get_name())
        metrics.total_tracks = len(test_tracks)
        
        processing_times = []
        correct_predictions = 0
        predictions_made = 0
        
        # Track per-folder performance
        folder_stats = {}
        
        for track_id, actual_folder in test_tracks:
            # Get prediction
            start_time = time.time()
            result = classifier.predict(track_id)
            processing_time = (time.time() - start_time) * 1000
            processing_times.append(processing_time)
            
            # Update folder stats
            if actual_folder not in folder_stats:
                folder_stats[actual_folder] = {
                    "total": 0, "correct": 0, "predicted": 0
                }
            folder_stats[actual_folder]["total"] += 1
            
            # Check if prediction was made
            if result.has_predictions:
                predictions_made += 1
                
                # Check if prediction was correct
                if actual_folder in result.predicted_folders:
                    correct_predictions += 1
                    folder_stats[actual_folder]["correct"] += 1
                
                # Count predictions per folder
                for predicted_folder in result.predicted_folders:
                    if predicted_folder not in folder_stats:
                        folder_stats[predicted_folder] = {
                            "total": 0, "correct": 0, "predicted": 0
                        }
                    folder_stats[predicted_folder]["predicted"] += 1
        
        # Calculate core metrics
        metrics.correct_predictions = correct_predictions
        metrics.total_predictions = predictions_made
        metrics.coverage = predictions_made / len(test_tracks) if test_tracks else 0
        metrics.accuracy = correct_predictions / len(test_tracks) if test_tracks else 0
        metrics.precision = correct_predictions / predictions_made if predictions_made > 0 else 0
        metrics.recall = correct_predictions / len(test_tracks) if test_tracks else 0
        metrics.f1_score = (2 * metrics.precision * metrics.recall) / (metrics.precision + metrics.recall) if (metrics.precision + metrics.recall) > 0 else 0
        
        # Calculate per-folder metrics
        for folder, stats in folder_stats.items():
            if stats["total"] > 0:  # Only for folders with actual tracks
                folder_precision = stats["correct"] / stats["predicted"] if stats["predicted"] > 0 else 0
                folder_recall = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
                folder_f1 = (2 * folder_precision * folder_recall) / (folder_precision + folder_recall) if (folder_precision + folder_recall) > 0 else 0
                
                metrics.per_folder_metrics[folder] = {
                    "precision": folder_precision,
                    "recall": folder_recall,
                    "f1_score": folder_f1,
                    "total_tracks": stats["total"],
                    "correct_predictions": stats["correct"],
                    "total_predictions": stats["predicted"]
                }
        
        # Performance metrics
        metrics.avg_processing_time_ms = sum(processing_times) / len(processing_times) if processing_times else 0
        metrics.total_processing_time_ms = sum(processing_times)
        
        return metrics
        
    def evaluate_all_classifiers(self) -> Dict[str, EvaluationMetrics]:
        """Evaluate all classifiers on the test set."""
        if not self.train_test_split:
            raise ValueError("No train/test split data available")
            
        results = {}
        
        for classifier in self.classifiers:
            metrics = self.evaluate_classifier(classifier, self.train_test_split.test_tracks)
            results[classifier.get_name()] = metrics
            
        self.evaluation_results = results
        return results
        
    def get_comparison_summary(self) -> Dict[str, Any]:
        """Get a summary comparing all classifiers."""
        if not self.evaluation_results:
            return {}
            
        summary = {
            "classifiers": {},
            "rankings": {}
        }
        
        # Individual classifier summaries
        for name, metrics in self.evaluation_results.items():
            summary["classifiers"][name] = metrics.get_summary()
            
        # Rankings
        metric_names = ["accuracy", "precision", "recall", "f1_score", "coverage"]
        for metric_name in metric_names:
            sorted_classifiers = sorted(
                self.evaluation_results.items(),
                key=lambda x: getattr(x[1], metric_name),
                reverse=True
            )
            summary["rankings"][metric_name] = [
                {"name": name, "value": getattr(metrics, metric_name)}
                for name, metrics in sorted_classifiers
            ]
            
        return summary
        
    def print_comparison_report(self) -> None:
        """Print a detailed comparison report."""
        if not self.evaluation_results:
            print("No evaluation results available")
            return
            
        print("\n" + "="*80)
        print("CLASSIFICATION ALGORITHM COMPARISON REPORT")
        print("="*80)
        
        # Summary table
        print("\nSUMMARY:")
        print(f"{'Classifier':<25} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Coverage':<10}")
        print("-" * 80)
        
        for name, metrics in self.evaluation_results.items():
            print(f"{name:<25} {metrics.accuracy:<10.3f} {metrics.precision:<10.3f} {metrics.recall:<10.3f} {metrics.f1_score:<10.3f} {metrics.coverage:<10.3f}")
        
        # Best performer by metric
        print("\nBEST PERFORMERS:")
        metric_names = ["accuracy", "precision", "recall", "f1_score"]
        for metric_name in metric_names:
            best = max(self.evaluation_results.items(), key=lambda x: getattr(x[1], metric_name))
            print(f"  {metric_name.capitalize()}: {best[0]} ({getattr(best[1], metric_name):.3f})")
            
        # Per-folder performance for best classifier
        best_classifier = max(self.evaluation_results.items(), key=lambda x: x[1].f1_score)
        print(f"\nPER-FOLDER PERFORMANCE ({best_classifier[0]}):")
        print(f"{'Folder':<15} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Tracks':<10}")
        print("-" * 60)
        
        for folder, folder_metrics in best_classifier[1].per_folder_metrics.items():
            print(f"{folder:<15} {folder_metrics['precision']:<10.3f} {folder_metrics['recall']:<10.3f} {folder_metrics['f1_score']:<10.3f} {folder_metrics['total_tracks']:<10}")