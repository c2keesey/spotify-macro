#!/usr/bin/env python3
"""
Focused parameter optimization for composite classifier with key parameters only.

This script runs targeted optimization on the most impactful parameters with
a smaller data sample for faster iteration.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add paths for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "genre"))

from parameter_optimizer import ParameterOptimizer, ParameterSpace
from optimization_config import ConfigManager
from optimization_metrics import EnhancedEvaluator
from run_full_optimization import OptimizedCompositeClassifier, create_objective_function


def create_focused_parameter_spaces() -> Dict[str, ParameterSpace]:
    """Create focused parameter spaces for quick optimization."""
    spaces = {}
    
    # Focus on most impactful global parameters
    spaces['statistical_correlation_weight'] = ParameterSpace(
        name='statistical_correlation_weight',
        type='float',
        values=(0.5, 3.0),
        default=1.2,
        description='Weight for statistical genre-folder correlations'
    )
    
    spaces['keyword_matching_weight'] = ParameterSpace(
        name='keyword_matching_weight',
        type='float',
        values=(0.1, 1.5),
        default=0.6,
        description='Weight for genre keyword matching'
    )
    
    # Focus on key folder thresholds (most active folders)
    key_folders = ['House', 'Electronic', 'Base', 'Alive', 'Rave', 'Rock']
    for folder in key_folders:
        spaces[f'{folder}_threshold'] = ParameterSpace(
            name=f'{folder}_threshold',
            type='float',
            values=(0.05, 0.4),
            default=0.15,
            description=f'Confidence threshold for {folder} folder'
        )
        
        spaces[f'{folder}_strategy'] = ParameterSpace(
            name=f'{folder}_strategy',
            type='categorical',
            values=['enhanced_genre', 'simple_artist', 'balanced', 'conservative'],
            default='balanced',
            description=f'Classification strategy for {folder} folder'
        )
    
    # Key confidence parameters
    spaces['top_folder_selection_ratio'] = ParameterSpace(
        name='top_folder_selection_ratio',
        type='float',
        values=(0.5, 1.0),
        default=0.8,
        description='Ratio for selecting top-scoring folders'
    )
    
    spaces['max_confidence_cap'] = ParameterSpace(
        name='max_confidence_cap',
        type='float',
        values=(0.7, 0.95),
        default=0.85,
        description='Maximum confidence cap for predictions'
    )
    
    return spaces


class FastEvaluator(EnhancedEvaluator):
    """Fast evaluator with smaller data samples."""
    
    def __init__(self, max_tracks: int = 5000, random_seed: int = 42):
        super().__init__(random_seed=random_seed)
        
        # Sample down to manageable size
        if self.test_data and len(self.test_data) > max_tracks:
            import random
            random.seed(random_seed)
            self.test_data = random.sample(self.test_data, max_tracks)
            print(f"🔄 Sampled down to {len(self.test_data)} tracks for fast optimization")


def run_focused_optimization():
    """Run focused optimization on key parameters."""
    
    print("🎯 FOCUSED COMPOSITE CLASSIFIER OPTIMIZATION")
    print("=" * 60)
    print("Optimizing key parameters with fast evaluation...")
    
    # Initialize fast evaluator
    evaluator = FastEvaluator(max_tracks=5000)
    
    if not evaluator.test_data:
        print("❌ No test data available. Cannot run optimization.")
        return
    
    print(f"✅ Using {len(evaluator.test_data)} tracks for evaluation")
    
    # Create objective function
    objective_function = create_objective_function(evaluator)
    
    # Create focused parameter spaces
    parameter_spaces = create_focused_parameter_spaces()
    print(f"🔧 Optimizing {len(parameter_spaces)} key parameters")
    
    # Create results directory
    results_dir = Path("analysis/optimization/results")
    results_dir.mkdir(exist_ok=True)
    timestamp = int(time.time())
    
    # Run multiple optimization strategies
    optimization_runs = [
        {
            'name': 'Random Search - Key Parameters',
            'strategy': 'random',
            'trials': 100,
            'description': 'Random search on most impactful parameters'
        },
        {
            'name': 'Bayesian Optimization - Key Parameters',
            'strategy': 'bayesian',
            'trials': 150,
            'description': 'Intelligent optimization of key parameters'
        },
        {
            'name': 'Progressive Optimization - Key Parameters',
            'strategy': 'progressive',
            'trials': 200,
            'description': 'Multi-stage optimization of key parameters'
        }
    ]
    
    all_results = {}
    
    for i, run_config in enumerate(optimization_runs):
        print(f"\n{'='*50}")
        print(f"🚀 OPTIMIZATION RUN {i+1}/{len(optimization_runs)}")
        print(f"Name: {run_config['name']}")
        print(f"Strategy: {run_config['strategy']}")
        print(f"Trials: {run_config['trials']}")
        print("=" * 50)
        
        # Create optimizer
        optimizer = ParameterOptimizer(
            parameter_spaces=parameter_spaces,
            objective_function=objective_function,
            objective_direction='maximize',
            random_seed=42
        )
        
        # Run optimization
        start_time = time.time()
        
        try:
            if run_config['strategy'] == 'random':
                best_result = optimizer.random_search(
                    n_trials=run_config['trials'],
                    verbose=True
                )
            elif run_config['strategy'] == 'bayesian':
                best_result = optimizer.bayesian_optimization(
                    n_trials=run_config['trials'],
                    verbose=True
                )
            elif run_config['strategy'] == 'progressive':
                best_result = optimizer.progressive_optimization(
                    max_trials=run_config['trials'],
                    verbose=True
                )
            
            optimization_time = time.time() - start_time
            
            # Save results
            run_name = run_config['name'].lower().replace(' ', '_').replace('-', '_')
            results_file = results_dir / f"focused_{run_name}_{timestamp}.json"
            optimizer.save_results(str(results_file))
            
            # Store summary
            summary = optimizer.get_optimization_summary()
            summary['run_config'] = run_config
            summary['optimization_time'] = optimization_time
            all_results[run_config['name']] = summary
            
            print(f"\n✅ {run_config['name']} completed!")
            print(f"   Best objective: {best_result.objective_value:.4f}")
            print(f"   Time: {optimization_time:.1f}s")
            print(f"   Evaluations: {len(optimizer.optimization_history)}")
            
        except Exception as e:
            print(f"❌ Error in {run_config['name']}: {e}")
            all_results[run_config['name']] = {'error': str(e)}
    
    # Generate summary report
    print(f"\n{'='*50}")
    print("🏆 FOCUSED OPTIMIZATION RESULTS")
    print("=" * 50)
    
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
        print(f"   Speed: {evaluations/max(time_taken, 1):.1f} eval/sec")
        
        if score > best_score:
            best_score = score
            best_overall = name
    
    if best_overall:
        print(f"\n🥇 BEST RESULT: {best_overall}")
        print(f"   Objective Score: {best_score:.4f}")
        
        # Show best parameters
        best_result_data = all_results[best_overall]
        if 'best_parameters' in best_result_data:
            print(f"\n🔧 OPTIMAL PARAMETERS:")
            params = best_result_data['best_parameters']
            
            # Group by type
            global_params = {k: v for k, v in params.items() if not any(folder in k for folder in ['House', 'Electronic', 'Base', 'Alive', 'Rave', 'Rock'])}
            folder_params = {k: v for k, v in params.items() if k not in global_params}
            
            print("   Global Parameters:")
            for param, value in global_params.items():
                print(f"     {param}: {value:.3f}" if isinstance(value, float) else f"     {param}: {value}")
            
            print("   Folder Parameters:")
            for param, value in folder_params.items():
                print(f"     {param}: {value:.3f}" if isinstance(value, float) else f"     {param}: {value}")
    
    # Save comprehensive summary
    summary_file = results_dir / f"focused_optimization_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Results saved to: {summary_file}")
    print(f"🎉 Focused optimization completed!")
    
    return all_results


if __name__ == "__main__":
    run_focused_optimization()