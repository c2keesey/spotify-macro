#!/usr/bin/env python3
"""
Configuration management for parameter optimization.

This module handles parameter space definitions, configuration loading/saving,
and parameter validation for the optimization framework.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from parameter_optimizer import ParameterSpace


@dataclass
class OptimizationConfig:
    """Configuration for optimization runs."""
    name: str
    description: str
    parameter_spaces: Dict[str, ParameterSpace]
    objective_function: str  # Name/identifier of objective function
    objective_direction: str = 'maximize'
    optimization_strategy: str = 'progressive'
    max_trials: int = 100
    random_seed: int = 42
    cv_folds: int = 3
    timeout_seconds: Optional[int] = None
    early_stopping_patience: int = 20
    constraints: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'parameter_spaces': {name: asdict(space) for name, space in self.parameter_spaces.items()},
            'objective_function': self.objective_function,
            'objective_direction': self.objective_direction,
            'optimization_strategy': self.optimization_strategy,
            'max_trials': self.max_trials,
            'random_seed': self.random_seed,
            'cv_folds': self.cv_folds,
            'timeout_seconds': self.timeout_seconds,
            'early_stopping_patience': self.early_stopping_patience,
            'constraints': self.constraints
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationConfig':
        """Create from dictionary."""
        # Reconstruct parameter spaces
        parameter_spaces = {}
        for name, space_data in data['parameter_spaces'].items():
            parameter_spaces[name] = ParameterSpace(**space_data)
        
        return cls(
            name=data['name'],
            description=data['description'],
            parameter_spaces=parameter_spaces,
            objective_function=data['objective_function'],
            objective_direction=data.get('objective_direction', 'maximize'),
            optimization_strategy=data.get('optimization_strategy', 'progressive'),
            max_trials=data.get('max_trials', 100),
            random_seed=data.get('random_seed', 42),
            cv_folds=data.get('cv_folds', 3),
            timeout_seconds=data.get('timeout_seconds'),
            early_stopping_patience=data.get('early_stopping_patience', 20),
            constraints=data.get('constraints', {})
        )


class ConfigManager:
    """Manages optimization configurations."""
    
    def __init__(self, config_dir: str = "analysis/optimization/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_config(self, config: OptimizationConfig, filename: Optional[str] = None):
        """Save configuration to file."""
        if filename is None:
            filename = f"{config.name.lower().replace(' ', '_')}.json"
        
        filepath = self.config_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        print(f"💾 Configuration saved to {filepath}")
    
    def load_config(self, filename: str) -> OptimizationConfig:
        """Load configuration from file."""
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return OptimizationConfig.from_dict(data)
    
    def list_configs(self) -> List[str]:
        """List available configuration files."""
        return [f.name for f in self.config_dir.glob("*.json")]


def create_composite_classifier_config() -> OptimizationConfig:
    """Create optimization configuration for composite classifier."""
    from parameter_optimizer import create_composite_classifier_parameter_spaces
    
    return OptimizationConfig(
        name="Composite Classifier Optimization",
        description="Comprehensive parameter optimization for the composite classifier system",
        parameter_spaces=create_composite_classifier_parameter_spaces(),
        objective_function="composite_classifier_f1_score",
        objective_direction="maximize",
        optimization_strategy="progressive",
        max_trials=300,
        cv_folds=3,
        early_stopping_patience=30,
        constraints={
            # Example constraints
            "max_optimization_time_hours": 24,
            "min_coverage_threshold": 0.8,  # Require at least 80% coverage
            "folder_strategy_balance": True,  # Encourage strategy diversity across folders
        }
    )


def create_lightweight_optimization_config() -> OptimizationConfig:
    """Create a lightweight optimization config for quick testing."""
    from parameter_optimizer import ParameterSpace
    
    # Focus on just a few key parameters for quick optimization
    key_spaces = {}
    
    # Global scoring parameters only
    key_spaces['statistical_correlation_weight'] = ParameterSpace(
        name='statistical_correlation_weight',
        type='float',
        values=(0.5, 3.0),
        default=1.2,
        description='Weight for statistical genre-folder correlations'
    )
    
    key_spaces['keyword_matching_weight'] = ParameterSpace(
        name='keyword_matching_weight',
        type='float',
        values=(0.1, 1.5),
        default=0.6,
        description='Weight for genre keyword matching'
    )
    
    # Just a few key folder thresholds
    key_folders = ['House', 'Electronic', 'Base', 'Alive']
    for folder in key_folders:
        key_spaces[f'{folder}_threshold'] = ParameterSpace(
            name=f'{folder}_threshold',
            type='float',
            values=(0.05, 0.4),
            default=0.15,
            description=f'Confidence threshold for {folder} folder'
        )
    
    return OptimizationConfig(
        name="Lightweight Composite Optimization",
        description="Quick optimization of key composite classifier parameters",
        parameter_spaces=key_spaces,
        objective_function="composite_classifier_f1_score",
        objective_direction="maximize",
        optimization_strategy="random",
        max_trials=50,
        cv_folds=2,
        early_stopping_patience=10
    )


def create_folder_strategy_optimization_config() -> OptimizationConfig:
    """Create config focused only on folder strategy selection."""
    from parameter_optimizer import ParameterSpace
    
    folders = [
        'Alive', 'Base', 'House', 'Electronic', 'Rave', 'Rock', 'Reggae',
        'Funk Soul', 'Vibes', 'Sierra', 'Spiritual', 'Soft', 'Chill', 'Ride'
    ]
    
    strategies = ['enhanced_genre', 'simple_artist', 'balanced', 'conservative']
    
    strategy_spaces = {}
    for folder in folders:
        strategy_spaces[f'{folder}_strategy'] = ParameterSpace(
            name=f'{folder}_strategy',
            type='categorical',
            values=strategies,
            default='balanced',
            description=f'Classification strategy for {folder} folder'
        )
    
    return OptimizationConfig(
        name="Folder Strategy Optimization",
        description="Optimize strategy selection for each folder",
        parameter_spaces=strategy_spaces,
        objective_function="composite_classifier_f1_score",
        objective_direction="maximize",
        optimization_strategy="grid",
        max_trials=4**len(folders),  # All combinations
        cv_folds=3
    )


def create_threshold_tuning_config() -> OptimizationConfig:
    """Create config focused only on threshold optimization."""
    from parameter_optimizer import ParameterSpace
    
    folders = [
        'Alive', 'Base', 'House', 'Electronic', 'Rave', 'Rock', 'Reggae',
        'Funk Soul', 'Vibes', 'Sierra', 'Spiritual', 'Soft', 'Chill', 'Ride'
    ]
    
    threshold_spaces = {}
    for folder in folders:
        threshold_spaces[f'{folder}_threshold'] = ParameterSpace(
            name=f'{folder}_threshold',
            type='float',
            values=(0.01, 0.5),
            default=0.15,
            description=f'Confidence threshold for {folder} folder'
        )
    
    return OptimizationConfig(
        name="Threshold Optimization",
        description="Fine-tune confidence thresholds for each folder",
        parameter_spaces=threshold_spaces,
        objective_function="composite_classifier_f1_score",
        objective_direction="maximize",
        optimization_strategy="bayesian",
        max_trials=200,
        cv_folds=3
    )


if __name__ == "__main__":
    # Demo configuration creation and management
    print("🔧 Configuration Management Demo")
    print("=" * 40)
    
    # Create config manager
    manager = ConfigManager()
    
    # Create and save different configurations
    configs = [
        create_composite_classifier_config(),
        create_lightweight_optimization_config(),
        create_folder_strategy_optimization_config(),
        create_threshold_tuning_config()
    ]
    
    for config in configs:
        print(f"Creating config: {config.name}")
        manager.save_config(config)
    
    print(f"\nAvailable configurations:")
    for config_file in manager.list_configs():
        print(f"  - {config_file}")
    
    # Demo loading
    if configs:
        first_config = manager.load_config(manager.list_configs()[0])
        print(f"\nLoaded config: {first_config.name}")
        print(f"Parameters: {len(first_config.parameter_spaces)}")
        print(f"Max trials: {first_config.max_trials}")