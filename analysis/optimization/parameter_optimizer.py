#!/usr/bin/env python3
"""
Comprehensive parameter optimization framework for classification algorithms.

This framework provides systematic optimization capabilities for all tunable parameters
in classification systems, with support for grid search, Bayesian optimization,
and multi-objective optimization.
"""

import json
import time
import itertools
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np

# Try to import optional optimization libraries
try:
    from sklearn.model_selection import ParameterGrid
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


@dataclass
class ParameterSpace:
    """Defines the search space for a parameter."""
    name: str
    type: str  # 'float', 'int', 'categorical', 'bool'
    values: Union[List[Any], Tuple[float, float]] = None  # For categorical or range
    default: Any = None
    description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def sample(self) -> Any:
        """Sample a value from this parameter space."""
        if self.type == 'categorical':
            return random.choice(self.values)
        elif self.type == 'bool':
            return random.choice([True, False])
        elif self.type == 'float':
            low, high = self.values
            return random.uniform(low, high)
        elif self.type == 'int':
            low, high = self.values
            return random.randint(low, high)
        else:
            raise ValueError(f"Unknown parameter type: {self.type}")
    
    def validate(self, value: Any) -> bool:
        """Validate a parameter value."""
        if self.type == 'categorical':
            return value in self.values
        elif self.type == 'bool':
            return isinstance(value, bool)
        elif self.type == 'float':
            low, high = self.values
            return isinstance(value, (int, float)) and low <= value <= high
        elif self.type == 'int':
            low, high = self.values
            return isinstance(value, int) and low <= value <= high
        return False


@dataclass
class OptimizationResult:
    """Result of a parameter optimization run."""
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    objective_value: float
    evaluation_time: float
    fold_results: List[Dict[str, float]] = field(default_factory=list)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the optimization result."""
        return {
            "objective_value": self.objective_value,
            "evaluation_time": self.evaluation_time,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "n_folds": len(self.fold_results)
        }


class ParameterOptimizer:
    """
    Comprehensive parameter optimization framework.
    
    Supports multiple optimization strategies:
    - Grid search: Exhaustive search over parameter combinations
    - Random search: Random sampling from parameter space
    - Bayesian optimization: Intelligent search using Optuna (if available)
    """
    
    def __init__(self, 
                 parameter_spaces: Dict[str, ParameterSpace],
                 objective_function: Callable[[Dict[str, Any]], float],
                 objective_direction: str = 'maximize',
                 random_seed: int = 42):
        """
        Initialize the parameter optimizer.
        
        Args:
            parameter_spaces: Dictionary of parameter name -> ParameterSpace
            objective_function: Function that takes parameters and returns objective value
            objective_direction: 'maximize' or 'minimize' the objective
            random_seed: Random seed for reproducibility
        """
        self.parameter_spaces = parameter_spaces
        self.objective_function = objective_function
        self.objective_direction = objective_direction
        self.random_seed = random_seed
        
        # Results storage
        self.optimization_history: List[OptimizationResult] = []
        self.best_result: Optional[OptimizationResult] = None
        
        # Set random seed
        random.seed(random_seed)
        np.random.seed(random_seed)
        
    def grid_search(self, 
                   n_combinations: Optional[int] = None,
                   verbose: bool = True) -> OptimizationResult:
        """
        Perform grid search optimization.
        
        Args:
            n_combinations: Maximum number of combinations to try (None = all)
            verbose: Whether to print progress
            
        Returns:
            Best optimization result found
        """
        if verbose:
            print("🔍 Starting Grid Search Optimization")
            print("=" * 50)
        
        # Generate all parameter combinations
        param_names = list(self.parameter_spaces.keys())
        param_values = []
        
        for param_name in param_names:
            space = self.parameter_spaces[param_name]
            if space.type == 'categorical':
                param_values.append(space.values)
            elif space.type == 'bool':
                param_values.append([True, False])
            elif space.type in ['float', 'int']:
                # For continuous parameters, create discrete grid
                low, high = space.values
                if space.type == 'int':
                    values = list(range(low, high + 1))
                else:
                    # Create 5-point grid for float parameters
                    values = np.linspace(low, high, 5).tolist()
                param_values.append(values)
        
        # Generate all combinations
        all_combinations = list(itertools.product(*param_values))
        
        # Limit combinations if requested
        if n_combinations and len(all_combinations) > n_combinations:
            all_combinations = random.sample(all_combinations, n_combinations)
        
        if verbose:
            print(f"Testing {len(all_combinations)} parameter combinations")
        
        # Evaluate each combination
        for i, combination in enumerate(all_combinations):
            params = dict(zip(param_names, combination))
            
            if verbose and i % max(1, len(all_combinations) // 10) == 0:
                print(f"Progress: {i+1}/{len(all_combinations)} ({(i+1)/len(all_combinations)*100:.1f}%)")
            
            self._evaluate_parameters(params, verbose=False)
        
        if verbose:
            print(f"\n✅ Grid search completed")
            print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        return self.best_result
    
    def random_search(self, 
                     n_trials: int = 100,
                     verbose: bool = True) -> OptimizationResult:
        """
        Perform random search optimization.
        
        Args:
            n_trials: Number of random trials to perform
            verbose: Whether to print progress
            
        Returns:
            Best optimization result found
        """
        if verbose:
            print("🎲 Starting Random Search Optimization")
            print("=" * 50)
            print(f"Testing {n_trials} random parameter combinations")
        
        for i in range(n_trials):
            # Sample random parameters
            params = {}
            for param_name, space in self.parameter_spaces.items():
                params[param_name] = space.sample()
            
            if verbose and i % max(1, n_trials // 10) == 0:
                print(f"Progress: {i+1}/{n_trials} ({(i+1)/n_trials*100:.1f}%)")
            
            self._evaluate_parameters(params, verbose=False)
        
        if verbose:
            print(f"\n✅ Random search completed")
            print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        return self.best_result
    
    def bayesian_optimization(self, 
                            n_trials: int = 100,
                            verbose: bool = True) -> OptimizationResult:
        """
        Perform Bayesian optimization using Optuna.
        
        Args:
            n_trials: Number of trials to perform
            verbose: Whether to print progress
            
        Returns:
            Best optimization result found
        """
        if not OPTUNA_AVAILABLE:
            print("⚠️  Optuna not available, falling back to random search")
            return self.random_search(n_trials, verbose)
        
        if verbose:
            print("🧠 Starting Bayesian Optimization (Optuna)")
            print("=" * 50)
        
        # Create Optuna study
        direction = 'maximize' if self.objective_direction == 'maximize' else 'minimize'
        study = optuna.create_study(direction=direction, sampler=optuna.samplers.TPESampler(seed=self.random_seed))
        
        def optuna_objective(trial):
            # Sample parameters using Optuna
            params = {}
            for param_name, space in self.parameter_spaces.items():
                if space.type == 'categorical':
                    params[param_name] = trial.suggest_categorical(param_name, space.values)
                elif space.type == 'bool':
                    params[param_name] = trial.suggest_categorical(param_name, [True, False])
                elif space.type == 'float':
                    low, high = space.values
                    params[param_name] = trial.suggest_float(param_name, low, high)
                elif space.type == 'int':
                    low, high = space.values
                    params[param_name] = trial.suggest_int(param_name, low, high)
            
            # Evaluate parameters
            result = self._evaluate_parameters(params, verbose=False)
            return result.objective_value
        
        # Run optimization
        study.optimize(optuna_objective, n_trials=n_trials, show_progress_bar=verbose)
        
        if verbose:
            print(f"\n✅ Bayesian optimization completed")
            print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        return self.best_result
    
    def progressive_optimization(self, 
                               strategy: str = 'coarse_to_fine',
                               max_trials: int = 300,
                               verbose: bool = True) -> OptimizationResult:
        """
        Perform progressive optimization with multiple stages.
        
        Args:
            strategy: Optimization strategy ('coarse_to_fine', 'multi_stage')
            max_trials: Total number of trials across all stages
            verbose: Whether to print progress
            
        Returns:
            Best optimization result found
        """
        if verbose:
            print("🎯 Starting Progressive Optimization")
            print("=" * 50)
        
        if strategy == 'coarse_to_fine':
            # Stage 1: Coarse random search (30% of budget)
            stage1_trials = int(max_trials * 0.3)
            if verbose:
                print(f"Stage 1: Coarse random search ({stage1_trials} trials)")
            self.random_search(stage1_trials, verbose=verbose)
            
            # Stage 2: Focused grid search around best result (40% of budget)
            stage2_trials = int(max_trials * 0.4)
            if verbose:
                print(f"\nStage 2: Focused search around best result ({stage2_trials} trials)")
            
            best_params = self.best_result.parameters
            self._focused_search_around_best(best_params, stage2_trials, verbose=verbose)
            
            # Stage 3: Fine-tuning with Bayesian optimization (30% of budget)
            stage3_trials = max_trials - stage1_trials - stage2_trials
            if verbose:
                print(f"\nStage 3: Bayesian fine-tuning ({stage3_trials} trials)")
            self.bayesian_optimization(stage3_trials, verbose=verbose)
        
        if verbose:
            print(f"\n✅ Progressive optimization completed")
            print(f"Final best objective value: {self.best_result.objective_value:.4f}")
        
        return self.best_result
    
    def _focused_search_around_best(self, 
                                  best_params: Dict[str, Any], 
                                  n_trials: int,
                                  focus_radius: float = 0.2,
                                  verbose: bool = True):
        """Search in a focused region around the best parameters found so far."""
        for i in range(n_trials):
            params = {}
            
            for param_name, space in self.parameter_spaces.items():
                best_value = best_params.get(param_name, space.default)
                
                if space.type == 'categorical':
                    # For categorical, sample from nearby values or best value
                    if random.random() < 0.7:  # 70% chance to keep best value
                        params[param_name] = best_value
                    else:
                        params[param_name] = space.sample()
                        
                elif space.type == 'bool':
                    # For boolean, mostly keep best value
                    if random.random() < 0.8:
                        params[param_name] = best_value
                    else:
                        params[param_name] = not best_value
                        
                elif space.type in ['float', 'int']:
                    low, high = space.values
                    range_size = high - low
                    focus_range = range_size * focus_radius
                    
                    # Sample around best value within focus radius
                    new_low = max(low, best_value - focus_range)
                    new_high = min(high, best_value + focus_range)
                    
                    if space.type == 'float':
                        params[param_name] = random.uniform(new_low, new_high)
                    else:
                        params[param_name] = random.randint(int(new_low), int(new_high))
            
            if verbose and i % max(1, n_trials // 5) == 0:
                print(f"  Focused search progress: {i+1}/{n_trials}")
            
            self._evaluate_parameters(params, verbose=False)
    
    def _evaluate_parameters(self, 
                           parameters: Dict[str, Any], 
                           verbose: bool = True) -> OptimizationResult:
        """Evaluate a set of parameters and update best result."""
        start_time = time.time()
        
        # Validate parameters
        for param_name, value in parameters.items():
            if param_name in self.parameter_spaces:
                if not self.parameter_spaces[param_name].validate(value):
                    if verbose:
                        print(f"⚠️  Invalid parameter value: {param_name}={value}")
                    # Use default value
                    parameters[param_name] = self.parameter_spaces[param_name].default
        
        # Evaluate objective function
        try:
            objective_value = self.objective_function(parameters)
            evaluation_time = time.time() - start_time
            
            # Create result
            result = OptimizationResult(
                parameters=parameters.copy(),
                metrics={},  # Will be filled by objective function if needed
                objective_value=objective_value,
                evaluation_time=evaluation_time
            )
            
            # Update history
            self.optimization_history.append(result)
            
            # Update best result
            if self.best_result is None:
                self.best_result = result
            else:
                is_better = (
                    (self.objective_direction == 'maximize' and objective_value > self.best_result.objective_value) or
                    (self.objective_direction == 'minimize' and objective_value < self.best_result.objective_value)
                )
                if is_better:
                    self.best_result = result
            
            if verbose:
                print(f"Parameters: {parameters}")
                print(f"Objective: {objective_value:.4f} (time: {evaluation_time:.2f}s)")
                print(f"Current best: {self.best_result.objective_value:.4f}")
                print("-" * 40)
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"❌ Error evaluating parameters {parameters}: {e}")
            
            # Return worst possible result
            worst_value = float('-inf') if self.objective_direction == 'maximize' else float('inf')
            return OptimizationResult(
                parameters=parameters.copy(),
                metrics={},
                objective_value=worst_value,
                evaluation_time=time.time() - start_time
            )
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get a summary of the optimization process."""
        if not self.optimization_history:
            return {"message": "No optimization runs completed"}
        
        objective_values = [r.objective_value for r in self.optimization_history]
        
        return {
            "total_evaluations": len(self.optimization_history),
            "best_objective": self.best_result.objective_value,
            "best_parameters": self.best_result.parameters,
            "objective_stats": {
                "mean": np.mean(objective_values),
                "std": np.std(objective_values),
                "min": np.min(objective_values),
                "max": np.max(objective_values)
            },
            "total_optimization_time": sum(r.evaluation_time for r in self.optimization_history),
            "average_evaluation_time": np.mean([r.evaluation_time for r in self.optimization_history])
        }
    
    def save_results(self, filepath: str):
        """Save optimization results to file."""
        results = {
            "parameter_spaces": {name: asdict(space) for name, space in self.parameter_spaces.items()},
            "best_result": asdict(self.best_result) if self.best_result else None,
            "optimization_history": [asdict(r) for r in self.optimization_history],
            "optimization_summary": self.get_optimization_summary(),
            "configuration": {
                "objective_direction": self.objective_direction,
                "random_seed": self.random_seed
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Optimization results saved to {filepath}")
    
    @classmethod
    def load_results(cls, filepath: str) -> 'ParameterOptimizer':
        """Load optimization results from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct parameter spaces
        parameter_spaces = {}
        for name, space_data in data["parameter_spaces"].items():
            parameter_spaces[name] = ParameterSpace(**space_data)
        
        # Create optimizer (dummy objective function)
        optimizer = cls(
            parameter_spaces=parameter_spaces,
            objective_function=lambda x: 0,  # Dummy
            objective_direction=data["configuration"]["objective_direction"],
            random_seed=data["configuration"]["random_seed"]
        )
        
        # Restore results
        if data["best_result"]:
            optimizer.best_result = OptimizationResult(**data["best_result"])
        
        optimizer.optimization_history = [
            OptimizationResult(**result_data) 
            for result_data in data["optimization_history"]
        ]
        
        return optimizer


def create_composite_classifier_parameter_spaces() -> Dict[str, ParameterSpace]:
    """
    Create parameter spaces for the composite classifier.
    
    Returns:
        Dictionary of parameter spaces for optimization
    """
    spaces = {}
    
    # Folder names for threshold and boost parameters
    folders = [
        'Alive', 'Base', 'House', 'Electronic', 'Rave', 'Rock', 'Reggae',
        'Funk Soul', 'Vibes', 'Sierra', 'Spiritual', 'Soft', 'Chill', 'Ride'
    ]
    
    # Strategy types
    strategies = ['enhanced_genre', 'simple_artist', 'balanced', 'conservative']
    
    # Per-folder strategy selection
    for folder in folders:
        spaces[f'{folder}_strategy'] = ParameterSpace(
            name=f'{folder}_strategy',
            type='categorical',
            values=strategies,
            default='balanced',
            description=f'Classification strategy for {folder} folder'
        )
        
        # Per-folder confidence thresholds
        spaces[f'{folder}_threshold'] = ParameterSpace(
            name=f'{folder}_threshold',
            type='float',
            values=(0.01, 0.5),
            default=0.15,
            description=f'Confidence threshold for {folder} folder'
        )
        
        # Per-folder boost multipliers
        spaces[f'{folder}_boost'] = ParameterSpace(
            name=f'{folder}_boost',
            type='float',
            values=(0.1, 2.0),
            default=0.7,
            description=f'Boost multiplier for {folder} folder'
        )
    
    # Global scoring parameters
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
    
    # Conservative strategy parameters
    spaces['conservative_genre_reduction'] = ParameterSpace(
        name='conservative_genre_reduction',
        type='float',
        values=(0.3, 1.0),
        default=0.7,
        description='Genre boost reduction factor in conservative mode'
    )
    
    spaces['conservative_artist_reduction'] = ParameterSpace(
        name='conservative_artist_reduction',
        type='float',
        values=(0.3, 1.0),
        default=0.8,
        description='Artist boost reduction factor in conservative mode'
    )
    
    spaces['conservative_min_signal_threshold'] = ParameterSpace(
        name='conservative_min_signal_threshold',
        type='float',
        values=(0.01, 0.3),
        default=0.1,
        description='Minimum signal strength required in conservative mode'
    )
    
    spaces['conservative_weak_penalty'] = ParameterSpace(
        name='conservative_weak_penalty',
        type='float',
        values=(0.1, 1.0),
        default=0.5,
        description='Penalty multiplier for weak signals in conservative mode'
    )
    
    # Confidence calculation parameters
    spaces['single_folder_confidence'] = ParameterSpace(
        name='single_folder_confidence',
        type='float',
        values=(0.8, 0.99),
        default=0.95,
        description='Confidence for single-folder artist matches'
    )
    
    spaces['multi_folder_base_confidence'] = ParameterSpace(
        name='multi_folder_base_confidence',
        type='float',
        values=(0.3, 0.8),
        default=0.6,
        description='Base confidence for multi-folder artist matches'
    )
    
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
    
    spaces['confidence_multiplier'] = ParameterSpace(
        name='confidence_multiplier',
        type='float',
        values=(0.5, 1.2),
        default=0.8,
        description='Multiplier for confidence score normalization'
    )
    
    # Multi-class threshold parameter
    spaces['multi_class_threshold'] = ParameterSpace(
        name='multi_class_threshold',
        type='float',
        values=(0.05, 0.3),
        default=0.15,
        description='Minimum confidence threshold for multi-class assignments'
    )
    
    return spaces


if __name__ == "__main__":
    # Example usage
    print("Parameter Optimizer Framework")
    print("=" * 40)
    
    # Create example parameter spaces
    spaces = create_composite_classifier_parameter_spaces()
    print(f"Created {len(spaces)} parameter spaces for optimization")
    
    # Example objective function (dummy)
    def dummy_objective(params):
        # Simulate some objective function
        return random.uniform(0.5, 0.9)
    
    # Create optimizer
    optimizer = ParameterOptimizer(
        parameter_spaces=spaces,
        objective_function=dummy_objective,
        objective_direction='maximize'
    )
    
    print("\nOptimizer created successfully!")
    print(f"Available optimization methods: grid_search, random_search, bayesian_optimization, progressive_optimization")