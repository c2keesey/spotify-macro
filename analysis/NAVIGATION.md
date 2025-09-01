# 🧭 Analysis Directory Navigation Guide

Quick reference for finding your way around the cleaned-up analysis directory.

## 🏆 Want the Best Results?

**Start here**: [`BEST_RESULTS.md`](./BEST_RESULTS.md)  
- **Performance**: 94.7% F1 Score (29% improvement!)
- **Optimal Parameters**: Complete configuration
- **Usage Instructions**: How to apply results

## 🚀 Want to Run Optimization?

**Go to**: [`optimization/`](./optimization/)
- **Quick Start**: `uv run analysis/optimization/run_focused_optimization.py`
- **Best Config**: `optimization/results/focused_bayesian_optimization_*.json`
- **Framework**: `optimization/parameter_optimizer.py`

## 🔬 Want to Test Classifiers?

**Go to**: [`genre/`](./genre/)
- **Main Test**: `uv run analysis/genre/test_classification_comparison.py`
- **Production Classifier**: `genre/composite_classifier.py`
- **Framework**: `genre/classification_framework.py`

## 📊 Want to Analyze Data?

**Go to**: [`playlist/`](./playlist/)
- **Artist Patterns**: `analyze_artist_folder_patterns.py`
- **Data Mapping**: `build_playlist_artist_mapping.py`
- **Cache Analysis**: `analyze_artist_patterns_from_cache.py`

## 📁 Directory Quick Reference

```
analysis/
├── 🏆 BEST_RESULTS.md          # Top performance & parameters
├── 📖 README.md                # Overview & structure
├── 🧭 NAVIGATION.md            # This file
├── 
├── 🎯 optimization/            # Parameter optimization (MAIN FOCUS)
│   ├── 📊 OPTIMIZATION_RESULTS.md
│   ├── 🔧 parameter_optimizer.py
│   ├── ⚙️  optimization_config.py  
│   ├── 📈 optimization_metrics.py
│   ├── 🚀 run_focused_optimization.py
│   └── 💾 results/
│       └── focused_bayesian_optimization_*.json
│
├── 🧬 genre/                   # Classification algorithms
│   ├── ⭐ composite_classifier.py    # Main production classifier
│   ├── 🏗️  classification_framework.py
│   ├── 📊 classification_metrics.py
│   ├── 🧪 test_classification_comparison.py
│   └── ...
│
├── 📊 playlist/               # Data analysis tools
│   ├── analyze_artist_folder_patterns.py
│   ├── build_playlist_artist_mapping.py
│   └── ...
│
└── 📦 archive/                # Moved experimental files
    ├── debug_*.py
    ├── test_genre_*.py
    └── ...
```

## 🎯 Common Tasks

### "I want to use the best classifier"
1. Read [`BEST_RESULTS.md`](./BEST_RESULTS.md) for parameters
2. Use `optimization/run_full_optimization.py` with optimal config
3. Or manually configure `genre/composite_classifier.py`

### "I want to run my own optimization"
1. Use `optimization/run_focused_optimization.py` (recommended)
2. Or `optimization/run_full_optimization.py` for comprehensive search
3. Check `optimization/results/` for outputs

### "I want to test different classifiers"
1. Run `genre/test_classification_comparison.py --verbose`
2. Add custom classifiers to `genre/` directory
3. Follow framework in `genre/classification_framework.py`

### "I want to understand the data patterns"
1. Check `playlist/analyze_artist_folder_patterns.py`
2. Use `playlist/build_playlist_artist_mapping.py`
3. Review cached data in `data/cache/`

### "I'm looking for old experimental code"
1. Check `archive/` directory
2. Most debug and experimental files moved there
3. Still functional, just not primary workflow

## 🎉 Success Metrics

- **Before**: 73.4% F1, scattered experimental files
- **After**: 94.7% F1, organized structure, clear best results
- **Organization**: Clean separation of production/research/archive
- **Documentation**: Clear navigation and usage guides

## 🔄 Maintenance

To keep this structure clean:
1. **New classifiers** → `genre/` directory
2. **New optimization** → `optimization/` directory  
3. **Experimental code** → Start in appropriate directory, move to `archive/` when superseded
4. **Update `BEST_RESULTS.md`** when new records are achieved

---

**TL;DR**: 
- **Best results**: [`BEST_RESULTS.md`](./BEST_RESULTS.md)
- **Run optimization**: `optimization/run_focused_optimization.py`
- **Test classifiers**: `genre/test_classification_comparison.py`
- **Everything else**: Check [`README.md`](./README.md)