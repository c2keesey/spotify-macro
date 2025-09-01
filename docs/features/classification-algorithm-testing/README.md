# Feature: Classification Algorithm Testing Framework

## Description
Extensible framework for testing and comparing genre classification algorithms for automatic playlist sorting. Provides standardized testing environment with proper train/test splits, comprehensive metrics, and easy algorithm integration.

## Context
- **Branch**: `feature/playlist-downflow-single-artist` (developed as part of classification research)
- **Related Files**: 
  - `analysis/genre/classification_framework.py:1` - Core framework with BaseClassifier abstract class
  - `analysis/genre/classification_metrics.py:1` - Data loading, splitting, and evaluation utilities
  - `analysis/genre/current_classifier.py:1` - Current artist-only system implementation
  - `analysis/genre/electronic_specialist_classifier.py:1` - Electronic-Specialist hybrid classifier
  - `analysis/genre/test_classification_comparison.py:1` - Main testing harness CLI
  - `analysis/genre/README.md:1` - Comprehensive framework documentation

## Background
The existing genre classification system achieved 74% recall but only 12% precision. Research findings in `docs/genre_classification_research_findings.md` identified that Electronic-Specialist hybrid approach could achieve 76.0% accuracy with 63.4% precision (5x improvement). This framework was built to test and validate these findings systematically.

## Implementation Notes
- **Extensible Design**: Abstract `BaseClassifier` interface allows easy addition of new algorithms
- **Data Integration**: Leverages existing cached data (`data/cache/`, `data/playlist_folders.json`)
- **Train/Test Split**: Playlist-level splitting prevents data leakage (70/30 default)
- **Comprehensive Metrics**: Accuracy, precision, recall, F1-score, coverage, per-folder analysis
- **Performance**: Uses cached artist mappings for fast startup (2,130 single-folder artists)
- **Dependencies**: 
  - `common/playlist_data_utils.py` - Data loading utilities
  - `common/genre_classification_utils.py` - Existing classification functions
  - `data/cache/` - Cached artist and playlist mappings
  - `data/playlist_folders.json` - Folder structure definitions

## Related Issues
- Research findings documented in `docs/genre_classification_research_findings.md`
- Implementation plan in `docs/genre_classification_implementation_plan.md`
- Single artist downflow automation in `docs/features/playlist-downflow-single-artist/`
- Part of broader genre classification improvement initiative