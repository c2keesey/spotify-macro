"""
Local test for staging classification using existing data files.

This tests the classification logic without making API calls by using
the existing playlist data files in the data/ directory.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

# Import our classification logic and utilities
from automations.spotify.staging_classification.action import StagingClassificationResults

# We'll implement the needed functions here locally to avoid import issues

def is_special_char(char: str) -> bool:
    """Check if character is special (not normal keyboard chars)"""
    if char.isalnum() or char.isspace():
        return False
    normal_punctuation = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
    return char not in normal_punctuation

def is_normal_letter(char: str) -> bool:
    """Check if character is a normal letter (a-z, A-Z)"""
    return char.isalpha()

def extract_flow_characters(playlist_name: str) -> Tuple[List[str], List[str]]:
    """Extract special characters from playlist name that indicate flow relationships."""
    import unicodedata
    
    def normalize_and_clean(text: str) -> str:
        """Normalize Unicode and strip problematic zero-width characters"""
        normalized = unicodedata.normalize('NFC', text)
        zero_width_chars = ['\u200B', '\u200C', '\u2060', '\uFEFF']
        cleaned = normalized
        for zwc in zero_width_chars:
            cleaned = cleaned.replace(zwc, '')
        return cleaned
    
    clean_name = normalize_and_clean(playlist_name)
    
    # Strip test prefix if present
    test_prefixes = ["🧪TEST_"]
    for prefix in test_prefixes:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break
    
    if not clean_name.strip():
        return [], []
    
    clusters = list(clean_name)
    parent_chars = []
    child_chars = []
    
    # Find first normal letter position
    first_letter_pos = None
    for i, cluster in enumerate(clusters):
        if any(is_normal_letter(c) for c in cluster):
            first_letter_pos = i
            break
    
    # Find last normal letter position
    last_letter_pos = None
    for i in range(len(clusters) - 1, -1, -1):
        if any(is_normal_letter(c) for c in clusters[i]):
            last_letter_pos = i
            break
    
    if first_letter_pos is None or last_letter_pos is None:
        return parent_chars, child_chars
    
    # Parent chars: special chars before first normal letter
    for i in range(first_letter_pos):
        cluster = clusters[i]
        if is_special_char(cluster):
            parent_chars.append(cluster)
    
    # Child chars: special chars after last normal letter
    for i in range(last_letter_pos + 1, len(clusters)):
        cluster = clusters[i]
        if is_special_char(cluster):
            child_chars.append(cluster)
    
    # Check for self-reference and return empty if found
    if parent_chars and child_chars:
        if any(p_char == c_char for p_char in parent_chars for c_char in child_chars):
            return [], []
    
    return parent_chars, child_chars

def is_parent_playlist(playlist_name: str) -> bool:
    """Check if a playlist is a parent playlist (has special characters at the beginning)."""
    parent_chars, _ = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0


def load_local_playlist_data() -> Dict[str, Dict]:
    """
    Load playlist data from local JSON files.
    
    Returns:
        Dictionary mapping playlist_id to playlist data
    """
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "playlists"
    playlists_dict = {}
    
    print("Loading local playlist data...")
    
    for playlist_file in data_dir.glob("*.json"):
        if playlist_file.name == "__init__.py":
            continue
            
        try:
            with open(playlist_file, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
                
            playlist_id = playlist_data.get("playlist_id", playlist_file.stem)
            playlist_name = playlist_data.get("playlist_name", playlist_file.stem)
            
            # Convert track format to match our expected format
            tracks = []
            for track in playlist_data.get("tracks", []):
                # Handle different JSON structures
                if isinstance(track, dict):
                    # Check if it's a nested structure with track data
                    if "item_track" in track:
                        track = track["item_track"]
                    
                    # Skip local tracks
                    if track.get("is_local", False):
                        continue
                        
                    track_id = track.get("id")
                    if not track_id:
                        continue
                    
                    # Extract artist information
                    artists = []
                    for artist in track.get("artists", []):
                        artists.append({
                            "id": artist.get("id"),
                            "name": artist.get("name")
                        })
                    
                    tracks.append({
                        "id": track_id,
                        "name": track.get("name"),
                        "artists": artists
                    })
            
            playlists_dict[playlist_id] = {
                "name": playlist_name,
                "tracks": tracks
            }
            
            print(f"  Loaded '{playlist_name}' ({len(tracks)} tracks)")
            
        except Exception as e:
            print(f"  Error loading {playlist_file.name}: {e}")
    
    return playlists_dict


def build_local_artist_to_playlists_mapping(playlists_dict: Dict[str, Dict]) -> Dict[str, Set[str]]:
    """
    Build mapping of artist ID to set of playlist IDs they appear in.
    Excludes parent playlists just like the real system.
    """
    artist_to_playlists = defaultdict(set)
    excluded_parents = []
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        
        # Skip parent playlists - they get songs automatically from child playlists
        if is_parent_playlist(playlist_name):
            excluded_parents.append(playlist_name)
            continue
        
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_playlists[artist_id].add(playlist_id)
    
    if excluded_parents:
        print(f"Excluded {len(excluded_parents)} parent playlists from uniqueness check:")
        for parent_name in excluded_parents[:3]:  # Show first 3
            print(f"  🎵 {parent_name}")
        if len(excluded_parents) > 3:
            print(f"  ... and {len(excluded_parents) - 3} more parent playlists")
    
    return artist_to_playlists


def find_local_single_playlist_artists(artist_to_playlists: Dict[str, Set[str]]) -> Set[str]:
    """Find artists that appear in only one playlist."""
    single_playlist_artists = set()
    
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    return single_playlist_artists


def find_local_source_playlist(playlists_dict: Dict[str, Dict], source_name: str = "New") -> Optional[str]:
    """Find the source playlist by name."""
    source_name_lower = source_name.lower()
    
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data["name"].lower() == source_name_lower:
            return playlist_id
    
    return None


def mock_classify_track(sp, track_id: str) -> List[str]:
    """
    Mock genre classification for testing.
    Returns some example classifications based on track ID.
    """
    # Simple mock - return different genres based on track ID patterns
    if track_id.startswith("0") or track_id.startswith("1"):
        return ["Electronic"]
    elif track_id.startswith("2") or track_id.startswith("3"):
        return ["Bass"]
    elif track_id.startswith("4") or track_id.startswith("5"):
        return ["House"]
    elif track_id.startswith("6") or track_id.startswith("7"):
        return ["Reggae"]
    elif track_id.startswith("8") or track_id.startswith("9"):
        return ["Jazz"]
    else:
        return ["Chill"]


def mock_find_best_target_playlist(sp, genre: str, track_id: str, playlists_dict: Dict[str, Dict]) -> Optional[str]:
    """
    Mock target playlist finder for testing.
    Returns a playlist ID that matches the genre if available.
    """
    genre_lower = genre.lower()
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"].lower()
        
        # Skip parent playlists
        if is_parent_playlist(playlist_data["name"]):
            continue
            
        # Simple matching logic
        if genre_lower in playlist_name:
            return playlist_id
        elif genre_lower == "bass" and ("bass" in playlist_name or "dubstep" in playlist_name):
            return playlist_id
        elif genre_lower == "electronic" and ("edm" in playlist_name or "electronic" in playlist_name):
            return playlist_id
        elif genre_lower == "house" and ("house" in playlist_name or "chill" in playlist_name):
            return playlist_id
        elif genre_lower == "reggae" and ("reggae" in playlist_name or "chill" in playlist_name):
            return playlist_id
        elif genre_lower == "jazz" and ("jazz" in playlist_name or "chill" in playlist_name):
            return playlist_id
        elif genre_lower == "chill" and ("chill" in playlist_name or "soft" in playlist_name):
            return playlist_id
    
    return None


def mock_classify_staging_tracks(sp, playlists_dict: Dict[str, Dict], 
                               source_playlist_id: str,
                               single_playlist_artists: Set[str],
                               artist_to_playlists: Dict[str, Set[str]]) -> StagingClassificationResults:
    """
    Mock version of classify_staging_tracks that uses local data and mocked classification.
    """
    results = StagingClassificationResults()
    source_tracks = playlists_dict[source_playlist_id]["tracks"]
    source_name = playlists_dict[source_playlist_id]["name"]
    
    # Limit to first 20 tracks for testing
    test_tracks = source_tracks[:20]
    
    results.statistics['total_tracks'] = len(test_tracks)
    results.statistics['single_playlist_artists_available'] = len(single_playlist_artists)
    
    print(f"Testing classification on {len(test_tracks)} tracks from '{source_name}'...")
    print(f"Available single-playlist artists: {len(single_playlist_artists)}")
    
    for track in test_tracks:
        track_id = track["id"]
        track_name = track["name"]
        artists = track["artists"]
        
        # STRATEGY 1: Artist Matching (Priority 1)
        artist_matched = False
        for artist in artists:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            if artist_id in single_playlist_artists:
                target_playlist_ids = artist_to_playlists[artist_id]
                
                if len(target_playlist_ids) == 1:
                    target_playlist_id = list(target_playlist_ids)[0]
                    
                    if target_playlist_id == source_playlist_id:
                        continue
                    
                    # Check if track is already in target playlist
                    target_tracks = playlists_dict[target_playlist_id]["tracks"]
                    existing_track_ids = {t["id"] for t in target_tracks}
                    
                    if track_id not in existing_track_ids:
                        results.add_artist_match(target_playlist_id, track_id)
                        target_name = playlists_dict[target_playlist_id]["name"]
                        print(f"  🎯 Artist match: '{track_name}' → '{target_name}' (artist: {artist_name})")
                        artist_matched = True
                        break
        
        if artist_matched:
            continue
        
        # STRATEGY 2: Genre Classification (Priority 2)
        try:
            classifications = mock_classify_track(sp, track_id)
            
            if classifications:
                genre_matched = False
                for genre in classifications:
                    target_playlist_id = mock_find_best_target_playlist(sp, genre, track_id, playlists_dict)
                    
                    if target_playlist_id and target_playlist_id != source_playlist_id:
                        if target_playlist_id in playlists_dict:
                            target_tracks = playlists_dict[target_playlist_id]["tracks"]
                            existing_track_ids = {t["id"] for t in target_tracks}
                            
                            if track_id not in existing_track_ids:
                                results.add_genre_match(target_playlist_id, track_id)
                                target_name = playlists_dict[target_playlist_id]["name"]
                                print(f"  🎵 Genre match: '{track_name}' → '{target_name}' (genre: {genre})")
                                genre_matched = True
                                break
                
                if not genre_matched:
                    results.add_unclassified(track_id)
                    print(f"  ❓ No suitable playlist found for '{track_name}' (genres: {', '.join(classifications)})")
            else:
                results.add_unclassified(track_id)
                print(f"  ❓ No genre classification for '{track_name}'")
        
        except Exception as e:
            results.add_error(f"Genre classification failed for '{track_name}': {str(e)}")
            results.add_unclassified(track_id)
            print(f"  ❌ Genre classification error for '{track_name}': {e}")
    
    return results


def test_local_classification():
    """Test the classification logic using local data."""
    print("🧪 Testing Staging Classification with Local Data")
    print("=" * 50)
    
    # Load local data
    playlists_dict = load_local_playlist_data()
    print(f"✅ Loaded {len(playlists_dict)} playlists")
    
    # Find source playlist
    source_playlist_id = find_local_source_playlist(playlists_dict, "New")
    if not source_playlist_id:
        print("❌ Could not find 'New' playlist in local data")
        return
    
    source_name = playlists_dict[source_playlist_id]["name"]
    source_track_count = len(playlists_dict[source_playlist_id]["tracks"])
    print(f"✅ Found staging playlist: '{source_name}' ({source_track_count} tracks)")
    
    # Build artist mappings
    print("\n🎯 Building Artist Mappings")
    artist_to_playlists = build_local_artist_to_playlists_mapping(playlists_dict)
    print(f"✅ Found {len(artist_to_playlists)} unique artists in non-parent playlists")
    
    # Find single playlist artists
    single_playlist_artists = find_local_single_playlist_artists(artist_to_playlists)
    print(f"✅ Found {len(single_playlist_artists)} single-playlist artists")
    
    # Test classification
    print("\n🔍 Testing Classification Logic")
    results = mock_classify_staging_tracks(None, playlists_dict, source_playlist_id, 
                                         single_playlist_artists, artist_to_playlists)
    
    # Display results
    print("\n📊 Classification Results:")
    print(f"  Total tracks processed: {results.statistics['total_tracks']}")
    print(f"  Artist matches: {results.statistics['artist_classification_count']}")
    print(f"  Genre matches: {results.statistics['genre_classification_count']}")
    print(f"  Unclassified: {results.statistics['unclassified_count']}")
    
    # Show some example matches
    if results.artist_matches:
        print("\n🎯 Example Artist Matches:")
        for playlist_id, tracks in list(results.artist_matches.items())[:3]:
            playlist_name = playlists_dict[playlist_id]["name"]
            print(f"  {playlist_name}: {len(tracks)} tracks")
    
    if results.genre_matches:
        print("\n🎵 Example Genre Matches:")
        for playlist_id, tracks in list(results.genre_matches.items())[:3]:
            playlist_name = playlists_dict[playlist_id]["name"]
            print(f"  {playlist_name}: {len(tracks)} tracks")
    
    # Calculate efficiency
    total_classified = results.statistics['artist_classification_count'] + results.statistics['genre_classification_count']
    efficiency = (total_classified / results.statistics['total_tracks']) * 100 if results.statistics['total_tracks'] > 0 else 0
    
    print(f"\n✅ Classification Efficiency: {efficiency:.1f}%")
    print(f"   Artist matching (100% accuracy): {results.statistics['artist_classification_count']} songs")
    print(f"   Genre matching (76% accuracy): {results.statistics['genre_classification_count']} songs")
    print(f"   Unclassified: {results.statistics['unclassified_count']} songs")
    
    if results.errors:
        print(f"\n⚠️ Errors: {len(results.errors)}")
        for error in results.errors[:3]:
            print(f"  • {error}")


if __name__ == "__main__":
    test_local_classification()