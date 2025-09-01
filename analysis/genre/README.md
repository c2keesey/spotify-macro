# Genre Classification Directory

This directory contains all genre-based classification algorithms and testing infrastructure.

## 🏆 Production Classifiers

### `composite_classifier.py` - **MAIN PRODUCTION CLASSIFIER** ⭐
- **Status**: Production ready, optimized parameters available
- **Performance**: 94.7% F1 (with optimization), 73.4% F1 (baseline)
- **Features**: Multi-strategy approach, folder-specific optimization
- **Usage**: Primary classifier for all playlist classification

### `classification_framework.py` - **BASE FRAMEWORK**
- **Status**: Core infrastructure  
- **Purpose**: Abstract base classes and interfaces
- **Usage**: Foundation for all other classifiers

### `classification_metrics.py` - **EVALUATION UTILITIES**
- **Status**: Core infrastructure
- **Purpose**: Data loading, evaluation, metrics calculation
- **Usage**: Used by all classifiers for training and evaluation

## 🧪 Research Classifiers

### `enhanced_artist_genre_classifier.py`
- **Focus**: Genre-based classification with artist patterns
- **Performance**: Good baseline performance
- **Status**: Research/reference implementation

### `electronic_specialist_classifier.py` 
- **Focus**: Specialized for electronic music classification
- **Performance**: Strong on electronic genres, limited scope
- **Status**: Research/specialist use case

### `current_classifier.py`
- **Focus**: Original baseline system (artist-only)
- **Performance**: ~3% accuracy baseline
- **Status**: Historical reference

## 🔬 Testing Infrastructure

### `test_classification_comparison.py` - **MAIN TEST HARNESS** ⭐
- **Purpose**: Compare multiple classifiers systematically
- **Usage**: Primary testing and evaluation tool
- **Features**: Cross-validation, comprehensive metrics

### `test_enhanced_classifier.py`
- **Purpose**: Test enhanced genre classifier specifically
- **Usage**: Focused testing for genre-based approaches

### `test_tuned_classifier.py`
- **Purpose**: Test manually tuned parameters
- **Usage**: Parameter validation and tuning

## 📁 Legacy/Experimental (Moved to Archive)

The following files have been moved to `../archive/`:
- `debug_*.py` - Debugging utilities  
- `test_genre_*.py` - Individual genre tests
- `fast_classification_test.py` - Quick testing utility
- `test_with_real_mapping.py` - Legacy testing approaches
- `test_safe_genre_save.py` - Genre data testing
- `test_hybrid_systems_with_real_data.py` - Experimental hybrid approaches

## 🚀 Quick Usage Guide

### To Run Main Classifier:
```python
from analysis.genre.composite_classifier import CompositeClassifier

classifier = CompositeClassifier()
classifier.train(train_data)
result = classifier.predict(track_id)
```

### To Run Performance Comparison:
```bash
uv run analysis/genre/test_classification_comparison.py --verbose
```

### To Use Optimized Parameters:
See `../BEST_RESULTS.md` for optimal parameter configuration.

## 📊 Performance Summary

| Classifier | F1 Score | Coverage | Status |
|------------|----------|----------|--------|
| Optimized Composite | **94.7%** | 93.3% | ⭐ Production |
| Composite (baseline) | 73.4% | 97.5% | Superseded |
| Enhanced Genre | ~70% | ~85% | Research |
| Electronic Specialist | ~75% | ~60% | Specialist |
| Current/Baseline | ~3% | ~10% | Historical |

## 🔧 Configuration

The composite classifier supports extensive configuration:
- **Strategy selection** per folder (enhanced_genre, simple_artist, balanced, conservative)
- **Confidence thresholds** per folder
- **Scoring weights** for genre vs artist signals
- **Global parameters** for confidence calculation

See optimization results for optimal parameter values.

## 🧠 Framework Architecture

### Core Framework (`classification_framework.py`)
- **`BaseClassifier`**: Abstract base class for all classification algorithms
- **`ClassificationResult`**: Standardized result format with predictions and confidence scores
- **`EvaluationMetrics`**: Comprehensive metrics tracking (accuracy, precision, recall, F1-score, coverage)
- **`ClassificationFramework`**: Main framework for managing and comparing multiple classifiers

### Adding New Algorithms

```python
from analysis.genre.classification_framework import BaseClassifier, ClassificationResult

class MyNewClassifier(BaseClassifier):
    def __init__(self):
        super().__init__("My New Classifier")
        
    def train(self, train_data: Dict[str, Any]) -> None:
        # Train your algorithm using train_data
        self.is_trained = True
        
    def predict(self, track_id: str) -> ClassificationResult:
        # Return predictions for a track
        return ClassificationResult(
            track_id=track_id,
            predicted_folders=["Electronic", "House"],
            confidence_scores={"Electronic": 0.8, "House": 0.6},
            reasoning="Custom algorithm prediction"
        )
```

## 📈 Performance Evolution

1. **Original System**: ~3% accuracy (artist-only)
2. **Electronic Specialist**: ~75% F1, limited scope  
3. **Enhanced Genre**: ~70% F1, broader coverage
4. **Composite Classifier**: 73.4% F1, 97.5% coverage
5. **Optimized Composite**: **94.7% F1, 93.3% coverage** ⭐

## 🛠️ Testing & Evaluation

### Command-Line Options
```bash
# Full comparison with detailed output
uv run analysis/genre/test_classification_comparison.py --verbose

# Custom train/test ratio
uv run analysis/genre/test_classification_comparison.py --train-ratio 0.8

# Limit tracks for quick testing
uv run analysis/genre/test_classification_comparison.py --limit-tracks 50
```

### Data Integration
- **Cached Data**: Uses `data/cache/` for artist mappings and playlist data
- **Train/Test Split**: Playlist-level splitting prevents data leakage
- **Performance Tracking**: Comprehensive metrics with confidence analysis