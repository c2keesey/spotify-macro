#!/usr/bin/env python3
"""
Enhanced evaluation framework with cross-validation for parameter optimization.

This module provides robust evaluation metrics, cross-validation, and
statistical analysis for parameter optimization of classification systems.
"""

import time
import random
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import json

# Import existing classification framework
import sys
sys.path.append(str(Path(__file__).parent.parent / "genre"))
try:
    from classification_framework import BaseClassifier
    from classification_metrics import load_test_data, split_train_test_playlists
except ImportError:
    # Fallback imports for direct execution
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from analysis.genre.classification_framework import BaseClassifier
    from analysis.genre.classification_metrics import load_test_data, split_train_test_playlists


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for a classification run."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    coverage: float = 0.0
    avg_confidence: float = 0.0
    
    # Per-folder metrics
    folder_accuracy: Dict[str, float] = field(default_factory=dict)
    folder_precision: Dict[str, float] = field(default_factory=dict)
    folder_recall: Dict[str, float] = field(default_factory=dict)
    folder_f1: Dict[str, float] = field(default_factory=dict)
    folder_coverage: Dict[str, float] = field(default_factory=dict)
    
    # Performance metrics
    evaluation_time: float = 0.0
    predictions_per_second: float = 0.0
    
    # Additional metrics
    total_tracks: int = 0
    total_predictions: int = 0
    correct_predictions: int = 0
    
    def get_overall_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Get weighted overall score."""
        if weights is None:
            weights = {'f1_score': 0.4, 'coverage': 0.3, 'accuracy': 0.3}
        
        score = 0.0
        for metric, weight in weights.items():
            if hasattr(self, metric):
                score += getattr(self, metric) * weight
        
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'overall': {
                'accuracy': self.accuracy,
                'precision': self.precision,
                'recall': self.recall,
                'f1_score': self.f1_score,
                'coverage': self.coverage,
                'avg_confidence': self.avg_confidence,
                'total_tracks': self.total_tracks,
                'total_predictions': self.total_predictions,
                'correct_predictions': self.correct_predictions
            },
            'folder_metrics': {
                'accuracy': self.folder_accuracy,
                'precision': self.folder_precision,
                'recall': self.folder_recall,
                'f1_score': self.folder_f1,
                'coverage': self.folder_coverage
            },
            'performance': {
                'evaluation_time': self.evaluation_time,
                'predictions_per_second': self.predictions_per_second
            }
        }


@dataclass
class CrossValidationResult:
    """Results from cross-validation evaluation."""
    fold_metrics: List[EvaluationMetrics]
    mean_metrics: EvaluationMetrics
    std_metrics: EvaluationMetrics
    confidence_intervals: Dict[str, Tuple[float, float]]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of cross-validation results."""
        return {
            'n_folds': len(self.fold_metrics),
            'mean_f1': self.mean_metrics.f1_score,
            'std_f1': self.std_metrics.f1_score,
            'mean_coverage': self.mean_metrics.coverage,
            'std_coverage': self.std_metrics.coverage,
            'confidence_intervals': self.confidence_intervals,
            'overall_score': self.mean_metrics.get_overall_score()
        }


class EnhancedEvaluator:
    """
    Enhanced evaluation framework with cross-validation and statistical analysis.
    """
    
    def __init__(self, 
                 cache_dir: str = "data/cache",
                 random_seed: int = 42):
        """
        Initialize the evaluator.
        
        Args:
            cache_dir: Directory for cached data
            random_seed: Random seed for reproducibility
        """
        self.cache_dir = Path(cache_dir)
        self.random_seed = random_seed
        
        # Set random seeds
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # Load test data once
        self.test_data = None
        self.playlists_dict = None
        self._load_test_data()
    
    def _load_test_data(self):
        """Load test data for evaluation."""
        try:
            self.test_data, self.playlists_dict = load_test_data(limit_tracks=None)
            print(f"✅ Loaded {len(self.test_data)} tracks for evaluation")
        except Exception as e:
            print(f"❌ Error loading test data: {e}")
            self.test_data = []
            self.playlists_dict = {}
    
    def evaluate_classifier(self, 
                          classifier: BaseClassifier,
                          test_tracks: Optional[List[Dict]] = None,
                          detailed: bool = True) -> EvaluationMetrics:
        """
        Evaluate a classifier on test tracks.
        
        Args:
            classifier: Classifier to evaluate
            test_tracks: Test tracks (uses self.test_data if None)
            detailed: Whether to compute detailed per-folder metrics
            
        Returns:
            Evaluation metrics
        """
        if test_tracks is None:
            test_tracks = self.test_data
        
        if not test_tracks:
            print("⚠️ No test tracks available")
            return EvaluationMetrics()
        
        start_time = time.time()
        
        # Initialize counters
        total_tracks = len(test_tracks)
        total_predictions = 0
        correct_predictions = 0
        confidence_sum = 0.0
        
        # Per-folder metrics
        folder_stats = defaultdict(lambda: {
            'total': 0, 'predicted': 0, 'correct': 0, 
            'true_positive': 0, 'false_positive': 0, 'false_negative': 0
        })
        
        # Track all folders seen
        all_folders = set()
        
        # Evaluate each track
        for track in test_tracks:
            track_id = track['track_id']
            actual_folders = set(track['folders'])
            all_folders.update(actual_folders)
            
            # Get prediction
            try:
                result = classifier.predict(track_id)
                
                # Handle both dictionary and ClassificationResult formats
                if hasattr(result, 'predicted_folders'):
                    # ClassificationResult object
                    predicted_folders = set(result.predicted_folders)
                    confidence_scores = result.confidence_scores
                else:
                    # Dictionary format
                    predicted_folders = set(result.get('folders', []))
                    confidence_scores = result.get('confidence_scores', {})
                
                # Overall metrics
                total_predictions += len(predicted_folders)
                
                # Track confidence
                if confidence_scores:
                    confidence_sum += np.mean(list(confidence_scores.values()))
                
                # Accuracy calculation
                if predicted_folders and actual_folders:
                    intersection = predicted_folders & actual_folders
                    if intersection:
                        correct_predictions += 1
                
                # Per-folder statistics
                for folder in all_folders.union(predicted_folders):
                    stats = folder_stats[folder]
                    
                    if folder in actual_folders:
                        stats['total'] += 1
                        
                        if folder in predicted_folders:
                            stats['true_positive'] += 1
                            stats['correct'] += 1
                        else:
                            stats['false_negative'] += 1
                    else:
                        if folder in predicted_folders:
                            stats['false_positive'] += 1
                    
                    if folder in predicted_folders:
                        stats['predicted'] += 1
                        
            except Exception as e:
                print(f"⚠️ Error evaluating track {track_id}: {e}")
                continue
        
        evaluation_time = time.time() - start_time
        
        # Calculate overall metrics
        accuracy = correct_predictions / total_tracks if total_tracks > 0 else 0.0
        coverage = correct_predictions / total_tracks if total_tracks > 0 else 0.0
        avg_confidence = confidence_sum / total_tracks if total_tracks > 0 else 0.0
        predictions_per_second = total_tracks / evaluation_time if evaluation_time > 0 else 0.0
        
        # Calculate precision and recall
        if total_predictions > 0:
            precision = correct_predictions / total_predictions
        else:
            precision = 0.0
        
        if correct_predictions > 0:
            recall = coverage  # Same as accuracy in this case
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            recall = 0.0
            f1_score = 0.0
        
        # Create metrics object
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            coverage=coverage,
            avg_confidence=avg_confidence,
            evaluation_time=evaluation_time,
            predictions_per_second=predictions_per_second,
            total_tracks=total_tracks,
            total_predictions=total_predictions,
            correct_predictions=correct_predictions
        )
        
        # Calculate per-folder metrics if requested
        if detailed:
            for folder, stats in folder_stats.items():
                if stats['total'] > 0:
                    # Folder-specific precision, recall, F1
                    tp = stats['true_positive']
                    fp = stats['false_positive']
                    fn = stats['false_negative']
                    
                    folder_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                    folder_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                    folder_f1 = (2 * folder_precision * folder_recall / 
                                (folder_precision + folder_recall)) if (folder_precision + folder_recall) > 0 else 0.0
                    folder_accuracy = tp / stats['total'] if stats['total'] > 0 else 0.0
                    folder_coverage = tp / stats['total'] if stats['total'] > 0 else 0.0
                    
                    metrics.folder_precision[folder] = folder_precision
                    metrics.folder_recall[folder] = folder_recall
                    metrics.folder_f1[folder] = folder_f1
                    metrics.folder_accuracy[folder] = folder_accuracy
                    metrics.folder_coverage[folder] = folder_coverage
        
        return metrics
    
    def cross_validate_classifier(self, 
                                classifier_factory: Callable[[List], BaseClassifier],
                                n_folds: int = 3,
                                detailed: bool = True,
                                verbose: bool = True) -> CrossValidationResult:
        """
        Perform cross-validation evaluation of a classifier.
        
        Args:
            classifier_factory: Function that creates classifier from training data
            n_folds: Number of cross-validation folds
            detailed: Whether to compute detailed metrics
            verbose: Whether to print progress
            
        Returns:
            Cross-validation results
        """
        if verbose:
            print(f"🔄 Performing {n_folds}-fold cross-validation")
        
        # Create folds by splitting playlists
        playlist_ids = list(self.playlists_dict.keys())
        random.shuffle(playlist_ids)
        
        fold_size = len(playlist_ids) // n_folds
        folds = []
        
        for i in range(n_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < n_folds - 1 else len(playlist_ids)
            test_playlists = playlist_ids[start_idx:end_idx]
            train_playlists = playlist_ids[:start_idx] + playlist_ids[end_idx:]
            folds.append((train_playlists, test_playlists))
        
        fold_metrics = []
        
        for fold_idx, (train_playlists, test_playlists) in enumerate(folds):
            if verbose:
                print(f"  Fold {fold_idx + 1}/{n_folds}")
            
            # Create train/test tracks in the correct format
            train_track_tuples = []
            test_tracks = []
            
            for track in self.test_data:
                track_playlists = track.get('playlists', [])
                track_id = track['track_id']
                folders = track['folders']
                
                if any(pid in test_playlists for pid in track_playlists):
                    test_tracks.append(track)
                else:
                    # Convert to tuple format: (track_id, folder)
                    for folder in folders:
                        train_track_tuples.append((track_id, folder))
            
            # Prepare training data in the format expected by composite classifier
            train_data = {
                'playlists_dict': self.playlists_dict,
                'train_tracks': train_track_tuples
            }
            
            # Create and train classifier
            try:
                classifier = classifier_factory(train_data)
                
                # Evaluate on test fold
                metrics = self.evaluate_classifier(classifier, test_tracks, detailed=detailed)
                fold_metrics.append(metrics)
                
                if verbose:
                    print(f"    F1: {metrics.f1_score:.3f}, Coverage: {metrics.coverage:.3f}")
                    
            except Exception as e:
                print(f"⚠️ Error in fold {fold_idx + 1}: {e}")
                # Add empty metrics for failed fold
                fold_metrics.append(EvaluationMetrics())
        
        # Calculate mean and std metrics
        mean_metrics, std_metrics = self._calculate_cv_statistics(fold_metrics)
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(fold_metrics)
        
        return CrossValidationResult(
            fold_metrics=fold_metrics,
            mean_metrics=mean_metrics,
            std_metrics=std_metrics,
            confidence_intervals=confidence_intervals
        )
    
    def _calculate_cv_statistics(self, fold_metrics: List[EvaluationMetrics]) -> Tuple[EvaluationMetrics, EvaluationMetrics]:
        """Calculate mean and standard deviation across folds."""
        if not fold_metrics:
            return EvaluationMetrics(), EvaluationMetrics()
        
        # Extract values for each metric
        metrics_values = {
            'accuracy': [m.accuracy for m in fold_metrics],
            'precision': [m.precision for m in fold_metrics],
            'recall': [m.recall for m in fold_metrics],
            'f1_score': [m.f1_score for m in fold_metrics],
            'coverage': [m.coverage for m in fold_metrics],
            'avg_confidence': [m.avg_confidence for m in fold_metrics]
        }
        
        # Calculate means and stds
        mean_metrics = EvaluationMetrics(
            accuracy=np.mean(metrics_values['accuracy']),
            precision=np.mean(metrics_values['precision']),
            recall=np.mean(metrics_values['recall']),
            f1_score=np.mean(metrics_values['f1_score']),
            coverage=np.mean(metrics_values['coverage']),
            avg_confidence=np.mean(metrics_values['avg_confidence'])
        )
        
        std_metrics = EvaluationMetrics(
            accuracy=np.std(metrics_values['accuracy']),
            precision=np.std(metrics_values['precision']),
            recall=np.std(metrics_values['recall']),
            f1_score=np.std(metrics_values['f1_score']),
            coverage=np.std(metrics_values['coverage']),
            avg_confidence=np.std(metrics_values['avg_confidence'])
        )
        
        return mean_metrics, std_metrics
    
    def _calculate_confidence_intervals(self, 
                                     fold_metrics: List[EvaluationMetrics],
                                     confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for metrics."""
        from scipy import stats
        
        intervals = {}
        alpha = 1 - confidence_level
        
        metrics_to_analyze = ['accuracy', 'precision', 'recall', 'f1_score', 'coverage']
        
        for metric in metrics_to_analyze:
            values = [getattr(m, metric) for m in fold_metrics]
            
            if len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values, ddof=1)
                t_critical = stats.t.ppf(1 - alpha/2, len(values) - 1)
                margin_error = t_critical * std_val / np.sqrt(len(values))
                
                intervals[metric] = (mean_val - margin_error, mean_val + margin_error)
            else:
                intervals[metric] = (values[0] if values else 0.0, values[0] if values else 0.0)
        
        return intervals
    
    def compare_classifiers(self, 
                          classifier_configs: List[Tuple[str, Callable]],
                          n_folds: int = 3,
                          verbose: bool = True) -> Dict[str, CrossValidationResult]:
        """
        Compare multiple classifiers using cross-validation.
        
        Args:
            classifier_configs: List of (name, factory_function) tuples
            n_folds: Number of cross-validation folds
            verbose: Whether to print progress
            
        Returns:
            Dictionary of classifier name -> CrossValidationResult
        """
        results = {}
        
        if verbose:
            print(f"🏁 Comparing {len(classifier_configs)} classifiers")
            print("=" * 50)
        
        for name, factory in classifier_configs:
            if verbose:
                print(f"\n📊 Evaluating: {name}")
            
            try:
                result = self.cross_validate_classifier(factory, n_folds, verbose=verbose)
                results[name] = result
                
                if verbose:
                    summary = result.get_summary()
                    print(f"   Mean F1: {summary['mean_f1']:.3f} ± {summary['std_f1']:.3f}")
                    print(f"   Mean Coverage: {summary['mean_coverage']:.3f} ± {summary['std_coverage']:.3f}")
                    
            except Exception as e:
                print(f"❌ Error evaluating {name}: {e}")
        
        return results
    
    def create_objective_function(self, 
                                classifier_factory: Callable[[Dict[str, Any], Dict[str, Any]], BaseClassifier],
                                n_folds: int = 3,
                                weights: Optional[Dict[str, float]] = None) -> Callable[[Dict[str, Any]], float]:
        """
        Create an objective function for parameter optimization.
        
        Args:
            classifier_factory: Function that creates classifier from parameters and training data
            n_folds: Number of cross-validation folds
            weights: Weights for different metrics in objective
            
        Returns:
            Objective function that takes parameters and returns score
        """
        if weights is None:
            weights = {'f1_score': 0.4, 'coverage': 0.3, 'accuracy': 0.3}
        
        def objective_function(parameters: Dict[str, Any]) -> float:
            """Objective function for optimization."""
            try:
                # Create classifier factory with parameters
                def parameterized_factory(train_data):
                    return classifier_factory(parameters, train_data)
                
                # Perform cross-validation
                cv_result = self.cross_validate_classifier(
                    parameterized_factory, 
                    n_folds=n_folds, 
                    detailed=False, 
                    verbose=False
                )
                
                # Return weighted score
                return cv_result.mean_metrics.get_overall_score(weights)
                
            except Exception as e:
                print(f"⚠️ Error in objective function: {e}")
                return 0.0  # Return worst score on error
        
        return objective_function


if __name__ == "__main__":
    # Demo usage
    print("🧪 Enhanced Evaluation Framework Demo")
    print("=" * 40)
    
    # Create evaluator
    evaluator = EnhancedEvaluator()
    
    if evaluator.test_data:
        print(f"✅ Loaded {len(evaluator.test_data)} test tracks")
        
        # Demo: Create a simple dummy classifier for testing
        class DummyClassifier(BaseClassifier):
            def __init__(self, train_tracks):
                self.folders = ['Electronic', 'House', 'Base']
            
            def predict(self, track_id):
                # Random prediction for demo
                import random
                folder = random.choice(self.folders)
                return {
                    'folders': [folder],
                    'confidence_scores': {folder: random.uniform(0.5, 0.9)}
                }
        
        # Test single evaluation
        dummy = DummyClassifier([])
        metrics = evaluator.evaluate_classifier(dummy, evaluator.test_data[:50])
        
        print(f"\nDummy classifier metrics:")
        print(f"  F1: {metrics.f1_score:.3f}")
        print(f"  Coverage: {metrics.coverage:.3f}")
        print(f"  Accuracy: {metrics.accuracy:.3f}")
        
        print("\n✅ Enhanced evaluation framework ready!")
    else:
        print("❌ No test data available")