# Audio Features Investigation - Classification Algorithm Testing

## Summary

Investigation into audio features for the Electronic-Specialist classification algorithm revealed that Spotify's audio features endpoint was **deprecated on November 27, 2024**. This document outlines the findings and alternative approaches.

## Spotify API Audio Features Deprecation

### What Happened
- **Date**: November 27, 2024
- **Impact**: `/v1/audio-features` and `/v1/audio-analysis` endpoints deprecated
- **Access**: Only apps with approved quota extensions before the cutoff date retain access
- **Cause**: Spotify cited "security concerns" for the changes

### Features Lost
- **Energy**: 0-1 scale representing intensity and activity
- **Valence**: 0-1 scale for musical positiveness (happy vs sad)
- **Danceability**: 0-1 scale for dancing suitability
- **Tempo/BPM**: Beats per minute estimation
- **Acousticness**: 0-1 scale for acoustic vs electronic
- **Instrumentalness**: 0-1 scale for vocal vs instrumental

## Current Classification Framework Status

### Working Components
1. **Simple Electronic-Specialist**: Uses artist patterns only (74.3% accuracy)
2. **Current System**: Basic artist mapping (3.3% accuracy)
3. **Classification Framework**: Extensible design ready for audio features

### Audio Features Integration Ready
- Created `scripts/fetch_audio_features.py` with rate limiting
- Updated `get_track_audio_features()` to check cache first
- Classification framework detects audio features cache availability

### Test Results (Artist Patterns Only)
```
Classifier                     Accuracy   Precision  Recall     F1-Score   Coverage
Simple Electronic-Specialist     74.3%      82.3%     74.3%      78.1%      90.3%
Current System                     3.3%      30.2%      3.3%       5.9%      10.9%
```

## Alternative Audio Analysis Solutions

### 1. Open Source Libraries

**Essentia** (Recommended):
- Comprehensive audio analysis library (C++/Python)
- Features: BPM, tempo, energy, valence, rhythm analysis
- Installation: `pip install essentia-tensorflow`
- Used by academic research and industry

**LibROSA**:
- Python audio analysis library
- Features: Tempo estimation, spectral analysis, beat tracking
- Installation: `pip install librosa`
- Popular in MIR (Music Information Retrieval) community

### 2. Audio File Sources

**Academic Datasets**:
- **FMA (Free Music Archive)**: 100k+ tracks with metadata
- **MusicOSet**: Enhanced dataset with BPM, energy, danceability
- **POP909**: 909 popular songs with tempo/beat annotations

**Legal Downloads**:
- **Bandcamp**: "Pay what you want" (often $0), multiple formats
- **SoundCloud**: Search "Free Downloads"
- **Internet Archive**: Legal music collection

### 3. Spotify Downloaded Files
- **Status**: Heavily encrypted with DRM
- **Format**: Ogg Vorbis with encryption
- **Accessibility**: Not extractable outside Spotify app
- **Conclusion**: Not viable for analysis

## Recommendations

### Immediate Term
1. **Continue testing** with artist-pattern-based classification
2. **Use mock audio features** for algorithm development/testing
3. **Document** current 74.3% accuracy as baseline

### Medium Term
1. **Download FMA dataset** for real audio analysis
2. **Implement Essentia integration** for feature extraction
3. **Test full Electronic-Specialist classifier** with real audio features

### Long Term
1. **Build audio feature cache** from legal music sources
2. **Compare** Essentia features vs. Spotify's original features
3. **Potentially achieve better accuracy** with open-source analysis

## Implementation Notes

### Files Modified
- `scripts/fetch_audio_features.py`: Created with rate limiting
- `analysis/genre/classification_metrics.py`: Updated to check cache first
- `analysis/genre/test_classification_comparison.py`: Added cache detection

### Framework Ready For
- Cached audio features from any source
- Live Spotify API (if access restored)
- Essentia/LibROSA integration

## Next Steps Options

1. **Audio Dataset Route**: Download FMA, extract features with Essentia
2. **Mock Testing Route**: Create realistic synthetic audio features
3. **Hybrid Route**: Use existing artist patterns + gradually add audio analysis

## Key Insight

The **Electronic-Specialist approach remains valid** - the core insight about using artist patterns + audio features is sound. We just need alternative audio feature sources beyond Spotify's deprecated API.

---

*Investigation completed: January 2025*
*Framework status: Ready for audio features from any source*