# Genre-Based Playlist Classification Implementation Plan

## Overview
Implement a hybrid genre classification system that automatically sorts saved songs into genre-specific playlists using folder naming conventions, artist genres, and audio features.

## Current State
- **Environment**: Test environment set up (`SPOTIFY_ENV=test`)
- **Issue**: OAuth cache sharing problem - different automations create separate cache files
- **Status**: Ready to implement once authentication is resolved

## Problem Statement
Currently, saved songs go to a single playlist via the daily liked songs automation. Goal is to automatically sort them into genre-specific playlists for better organization.

## Solution: Hybrid Folder-Based Classification

### 1. Folder Naming Convention (Bracket Style)
**Format**: `[Genre] PlaylistName [FlowChars]`

**Examples**:
```
[Rock] Collection 🎵        # Rock folder, parent playlist
[Rock] Daily Finds 🎵       # Rock folder, child flows to Rock parent
[Electronic] Ambient ♫     # Electronic folder  
[Electronic] House ♫       # Electronic folder
[Jazz] Smooth Collection    # Jazz folder (no flow chars = standalone)
[Pop] Hits                  # Pop folder
```

### 2. Classification Logic (Hybrid Approach)

**Primary**: Artist Genres (from Spotify API)
- Use existing genre infrastructure from `download/artist_genres.py`
- Fast, leverages current codebase
- Genre → folder mapping via configuration

**Secondary**: Audio Features (for refinement)
- Use `sp.audio_features()` API
- 13 audio features (danceability, energy, valence, acousticness, etc.)
- Feature profiles for different genres
- Fallback when artist genres are missing/generic

**Tertiary**: Default playlist for unclassifiable tracks

### 3. Configuration System

```python
# Genre to folder mapping
FOLDER_GENRE_MAPPING = {
    "Rock": {
        "genres": ["rock", "metal", "punk", "alternative", "grunge"],
        "audio_features": {"energy": ">0.6", "acousticness": "<0.4"}
    },
    "Electronic": {
        "genres": ["electronic", "edm", "house", "techno", "ambient"],
        "audio_features": {"danceability": ">0.5", "instrumentalness": ">0.3"}
    },
    "Jazz": {
        "genres": ["jazz", "blues", "swing", "bebop"],
        "audio_features": {"acousticness": ">0.4", "instrumentalness": ">0.2"}
    },
    "Pop": {
        "genres": ["pop", "dance pop", "electropop"],
        "audio_features": {"danceability": ">0.6", "valence": ">0.5"}
    }
}
```

## Implementation Tasks

### Phase 1: Foundation (2-3 hours)
1. **Fix OAuth/Cache Issue**
   - Resolve credential sharing between automations
   - Use existing cache names or implement shared cache system
   - Test authentication in SSH environment

2. **Create Test Playlists** 
   - Set up folder-named test playlists: `🧪TEST_[Rock] Collection 🎵`
   - Populate with genre-appropriate sample songs
   - Create unsorted test playlist with mixed genres

3. **Extend Folder Parsing**
   - Modify `extract_flow_characters()` in `playlist_flow/action.py`
   - Add folder extraction: `extract_folder_and_flow(playlist_name)`
   - Parse `[Genre]` pattern while preserving existing flow logic

### Phase 2: Classification Engine (4-6 hours)
4. **Implement Genre Classification**
   ```python
   def classify_track(track_id):
       # Get artist genres (existing infrastructure)
       genres = get_artist_genres(track_id)
       
       # Try genre-based classification first
       if genres:
           folders = map_genres_to_folders(genres)
           if folders:
               return folders
       
       # Fallback to audio features
       audio_features = sp.audio_features(track_id)
       return classify_by_audio_features(audio_features)
   ```

5. **Audio Features Integration**
   - Add `sp.audio_features()` API calls
   - Implement feature-based classification logic
   - Define genre feature profiles

6. **Configuration System**
   - Environment variable configuration for genre mappings
   - Configurable thresholds and fallback behavior
   - Support for user-customizable mappings

### Phase 3: Integration (2-3 hours)
7. **Modify Save Automation**
   - Update `save_current.py` or create new variant
   - Integration with classification logic
   - Support multiple target playlists per song

8. **Testing & Validation**
   - Test with unsorted playlist → genre classification
   - Verify folder detection and flow relationships work together
   - Performance testing with multiple genres

### Phase 4: Polish (1-2 hours)
9. **Error Handling & Logging**
   - Graceful fallbacks for missing genres/features
   - Clear logging of classification decisions
   - Handle edge cases (instrumental tracks, local files, etc.)

10. **Documentation**
    - Update CLAUDE.md with new genre classification system
    - Usage examples and configuration guide
    - Integration with existing workflow documentation

## Files to Create/Modify

### New Files
- `tests/genre_classification_test_setup.py` ✅ (created)
- `docs/genre_classification_implementation_plan.md` ✅ (this file)
- `macros/spotify/genre_classification/` (new automation module)
- `common/genre_classification_utils.py` (shared classification logic)

### Files to Modify
- `macros/spotify/playlist_flow/action.py` (extend folder parsing)
- `macros/spotify/save_current.py` (add classification integration)
- `common/config.py` (add genre classification configuration)
- `CLAUDE.md` (add documentation for new system)

## Technical Considerations

### API Usage
- **Existing**: Artist genres API (already implemented)
- **New**: Audio features API (`sp.audio_features()`)
- **Scopes**: Current scopes sufficient for implementation

### Performance
- Leverage existing genre caching infrastructure
- Batch audio features requests (up to 100 tracks per call)
- Cache classification results to avoid repeated analysis

### User Experience
- Minimal configuration required (use sensible defaults)
- Clear feedback on classification decisions
- Easy override/customization of genre mappings

## Dependencies
- All required Spotify API functionality already available
- No new external dependencies needed
- Builds on existing playlist flow and genre analysis infrastructure

## Testing Strategy
1. **Unit Tests**: Folder parsing, classification logic
2. **Integration Tests**: End-to-end save → classify → sort workflow  
3. **Manual Tests**: Real-world usage with diverse music library
4. **Performance Tests**: Large-scale classification scenarios

## Success Criteria
- Songs automatically sorted into appropriate genre folders
- Maintains compatibility with existing playlist flow system
- Configurable and customizable by user
- Handles edge cases gracefully (unknown genres, missing data)
- Performance suitable for daily automation use

## Next Steps (When Resuming)
1. **Immediate**: Fix OAuth/authentication issue for test environment
2. **Create test playlists** with folder naming convention
3. **Implement folder parsing extension** to existing flow system
4. **Build classification engine** with hybrid approach
5. **Test and iterate** with real music data

---

*Generated during development session on 2025-06-29*  
*Current status: Ready for implementation pending authentication fix*