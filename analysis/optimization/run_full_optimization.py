#!/usr/bin/env python3
"""
Full parameter optimization runner for composite classifier.

This script runs comprehensive parameter optimization on the composite classifier,
integrating with the existing classification framework and testing infrastructure.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add paths for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "genre"))

from parameter_optimizer import ParameterOptimizer, create_composite_classifier_parameter_spaces
from optimization_config import (
    create_composite_classifier_config, 
    create_lightweight_optimization_config,
    create_folder_strategy_optimization_config,
    create_threshold_tuning_config,
    ConfigManager
)
from optimization_metrics import EnhancedEvaluator

# Import existing classification components
from composite_classifier import CompositeClassifier
from classification_framework import BaseClassifier
from classification_metrics import load_test_data


class OptimizedCompositeClassifier(BaseClassifier):
    """
    Composite classifier with parameterized configuration.
    
    This wrapper allows the optimizer to modify classifier parameters dynamically.
    """
    
    def __init__(self, parameters: Dict[str, Any], train_data: Dict[str, Any]):
        """
        Initialize with optimized parameters.
        
        Args:
            parameters: Dictionary of parameter values from optimizer
            train_data: Training data dictionary with playlists_dict and train_tracks
        """
        self.parameters = parameters
        self.train_data = train_data
        
        # Create base composite classifier
        self.classifier = CompositeClassifier()
        
        # Apply optimized parameters
        self._apply_parameters()
        
        # Train the classifier
        self.classifier.train(train_data)
    
    def train(self, train_data: Dict[str, Any]):
        """Train method required by BaseClassifier interface."""
        # Training is handled in __init__, but update if called again
        self.train_data = train_data
        self.classifier.train(train_data)
    
    def _apply_parameters(self):
        """Apply optimization parameters to the classifier."""
        # Extract folder-specific parameters
        folders = [
            'Alive', 'Base', 'House', 'Electronic', 'Rave', 'Rock', 'Reggae',
            'Funk Soul', 'Vibes', 'Sierra', 'Spiritual', 'Soft', 'Chill', 'Ride'
        ]
        
        # Update folder strategies
        folder_strategies = {}
        for folder in folders:
            strategy_key = f'{folder}_strategy'
            threshold_key = f'{folder}_threshold'
            boost_key = f'{folder}_boost'
            
            folder_strategies[folder] = {
                'strategy': self.parameters.get(strategy_key, 'balanced'),
                'threshold': self.parameters.get(threshold_key, 0.15),
                'boost': self.parameters.get(boost_key, 0.7)
            }
        
        self.classifier.folder_strategies = folder_strategies
        
        # Update global scoring parameters
        scoring_params = [
            'statistical_correlation_weight',
            'keyword_matching_weight',
            'conservative_genre_reduction',
            'conservative_artist_reduction',
            'conservative_min_signal_threshold',
            'conservative_weak_penalty',
            'single_folder_confidence',
            'multi_folder_base_confidence',
            'top_folder_selection_ratio',
            'max_confidence_cap',
            'confidence_multiplier'
        ]
        
        for param in scoring_params:
            if param in self.parameters:
                setattr(self.classifier, param, self.parameters[param])
    
    def predict(self, track_id: str) -> Dict[str, Any]:
        """Predict folder for a track."""
        return self.classifier.predict(track_id)


def create_objective_function(evaluator: EnhancedEvaluator) -> callable:
    """Create objective function for optimization."""
    
    def composite_classifier_objective(parameters: Dict[str, Any]) -> float:
        """
        Objective function that evaluates composite classifier with given parameters.
        
        Args:
            parameters: Parameter values to test
            
        Returns:
            Objective score (higher is better)
        """
        try:
            # Create classifier factory
            def classifier_factory(train_tracks):
                return OptimizedCompositeClassifier(parameters, train_tracks)
            
            # Perform cross-validation evaluation
            cv_result = evaluator.cross_validate_classifier(
                classifier_factory, 
                n_folds=3, 
                detailed=False, 
                verbose=False
            )
            
            # Multi-objective scoring: F1 (40%) + Coverage (35%) + Accuracy (25%)
            weights = {
                'f1_score': 0.40,
                'coverage': 0.35,
                'accuracy': 0.25
            }
            
            objective_score = cv_result.mean_metrics.get_overall_score(weights)
            
            # Print progress
            print(f"   Params sample: {list(parameters.keys())[:3]}...")
            print(f"   F1: {cv_result.mean_metrics.f1_score:.3f}, "
                  f"Coverage: {cv_result.mean_metrics.coverage:.3f}, "
                  f"Objective: {objective_score:.3f}")
            
            return objective_score
            
        except Exception as e:
            print(f"❌ Error in objective function: {e}")
            return 0.0  # Return worst score on error
    
    return composite_classifier_objective


def run_optimization_suite():
    """Run comprehensive optimization suite with multiple strategies."""
    
    print("🚀 COMPOSITE CLASSIFIER OPTIMIZATION SUITE")
    print("=" * 60)
    print("Running comprehensive parameter optimization...")
    
    # Initialize components
    print("📊 Initializing evaluation framework...")
    evaluator = EnhancedEvaluator()
    
    if not evaluator.test_data:
        print("❌ No test data available. Cannot run optimization.")
        return
    
    print(f"✅ Loaded {len(evaluator.test_data)} tracks for evaluation")
    
    # Create objective function
    objective_function = create_objective_function(evaluator)
    
    # Create results directory
    results_dir = Path("analysis/optimization/results")
    results_dir.mkdir(exist_ok=True)
    timestamp = int(time.time())
    
    print(f"💾 Results will be saved to: {results_dir}")
    
    # Run multiple optimization strategies
    optimization_runs = [
        {
            'name': 'Progressive Full Optimization',
            'config': create_composite_classifier_config(),
            'strategy': 'progressive',
            'trials': 500,
            'description': 'Comprehensive 3-stage optimization of all parameters'
        },
        {
            'name': 'Bayesian Strategy Optimization', 
            'config': create_folder_strategy_optimization_config(),
            'strategy': 'bayesian',
            'trials': 150,
            'description': 'Intelligent optimization of folder strategies'
        },
        {
            'name': 'Threshold Fine-Tuning',
            'config': create_threshold_tuning_config(), 
            'strategy': 'bayesian',
            'trials': 200,
            'description': 'Fine-tune confidence thresholds'
        }
    ]
    
    all_results = {}
    
    for i, run_config in enumerate(optimization_runs):
        print(f"\n{'='*60}")
        print(f"🎯 OPTIMIZATION RUN {i+1}/{len(optimization_runs)}")
        print(f"Name: {run_config['name']}")
        print(f"Description: {run_config['description']}")
        print(f"Strategy: {run_config['strategy']}")
        print(f"Max Trials: {run_config['trials']}")
        print(f"Parameters: {len(run_config['config'].parameter_spaces)}")
        print("=" * 60)
        
        # Create optimizer
        optimizer = ParameterOptimizer(
            parameter_spaces=run_config['config'].parameter_spaces,
            objective_function=objective_function,
            objective_direction='maximize',
            random_seed=42
        )
        
        # Run optimization
        start_time = time.time()
        
        try:
            if run_config['strategy'] == 'progressive':
                best_result = optimizer.progressive_optimization(
                    max_trials=run_config['trials'],
                    verbose=True
                )
            elif run_config['strategy'] == 'bayesian':
                best_result = optimizer.bayesian_optimization(
                    n_trials=run_config['trials'],
                    verbose=True
                )
            elif run_config['strategy'] == 'grid':
                best_result = optimizer.grid_search(
                    n_combinations=run_config['trials'],
                    verbose=True
                )
            else:
                best_result = optimizer.random_search(
                    n_trials=run_config['trials'],
                    verbose=True
                )
            
            optimization_time = time.time() - start_time
            
            # Save results
            run_name = run_config['name'].lower().replace(' ', '_')
            results_file = results_dir / f"{run_name}_{timestamp}.json"
            optimizer.save_results(str(results_file))
            
            # Store summary
            summary = optimizer.get_optimization_summary()
            summary['run_config'] = run_config
            summary['optimization_time'] = optimization_time
            all_results[run_config['name']] = summary
            
            print(f"\n✅ {run_config['name']} completed!")
            print(f"   Best objective: {best_result.objective_value:.4f}")
            print(f"   Optimization time: {optimization_time:.1f}s")
            print(f"   Total evaluations: {len(optimizer.optimization_history)}")
            
        except Exception as e:
            print(f"❌ Error in {run_config['name']}: {e}")
            all_results[run_config['name']] = {'error': str(e)}
    
    # Generate final summary report
    print(f"\n{'='*60}")
    print("🏆 OPTIMIZATION SUMMARY REPORT")
    print("=" * 60)
    
    best_overall = None
    best_score = 0
    
    for name, result in all_results.items():
        if 'error' in result:
            print(f"❌ {name}: {result['error']}")
            continue
            
        score = result.get('best_objective', 0)
        evaluations = result.get('total_evaluations', 0)
        time_taken = result.get('optimization_time', 0)
        
        print(f"\n📊 {name}:")
        print(f"   Best Score: {score:.4f}")
        print(f"   Evaluations: {evaluations}")
        print(f"   Time: {time_taken:.1f}s")
        print(f"   Efficiency: {score/max(time_taken, 1):.6f} score/sec")
        
        if score > best_score:
            best_score = score
            best_overall = name
    
    if best_overall:
        print(f"\n🥇 BEST OVERALL: {best_overall}")
        print(f"   Score: {best_score:.4f}")
        
        # Load and display best parameters
        best_result_data = all_results[best_overall]
        if 'best_parameters' in best_result_data:
            print(f"   Key parameters:")
            params = best_result_data['best_parameters']
            
            # Show most impactful parameters
            key_params = [k for k in params.keys() if any(x in k.lower() for x in ['threshold', 'strategy', 'weight'])][:10]
            for param in key_params:
                print(f"     {param}: {params[param]}")
    
    # Save comprehensive summary
    summary_file = results_dir / f"optimization_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Complete results saved to: {summary_file}")
    print(f"🎉 Optimization suite completed! Check results directory for detailed data.")


def run_quick_test():
    """Run a quick optimization test to verify everything works."""
    
    print("🧪 Quick Optimization Test")
    print("=" * 40)
    
    # Create lightweight config for quick testing
    config = create_lightweight_optimization_config()
    evaluator = EnhancedEvaluator()
    
    if not evaluator.test_data:
        print("❌ No test data available")
        return
    
    # Create objective function
    objective_function = create_objective_function(evaluator)
    
    # Create optimizer
    optimizer = ParameterOptimizer(
        parameter_spaces=config.parameter_spaces,
        objective_function=objective_function,
        objective_direction='maximize'
    )
    
    print(f"Testing with {len(config.parameter_spaces)} parameters")
    print("Running 10 random evaluations...")
    
    # Run quick optimization
    best_result = optimizer.random_search(n_trials=10, verbose=True)
    
    print(f"\n✅ Quick test completed!")
    print(f"Best score: {best_result.objective_value:.4f}")
    print(f"Parameters tested: {len(optimizer.optimization_history)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run composite classifier optimization")
    parser.add_argument("--mode", choices=['full', 'quick'], default='full',
                       help="Optimization mode: 'full' for comprehensive, 'quick' for testing")
    parser.add_argument("--trials", type=int, default=500,
                       help="Maximum trials for full optimization")
    
    args = parser.parse_args()
    
    if args.mode == 'quick':
        run_quick_test()
    else:
        # Modify trial counts if specified
        if args.trials != 500:
            print(f"Using {args.trials} trials instead of default")
        
        run_optimization_suite()