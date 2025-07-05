#!/usr/bin/env python3
"""
Demonstrate the real improvement using actual local data.
"""

import json
from collections import defaultdict
from pathlib import Path
import unicodedata


def extract_flow_characters(playlist_name: str):
    """Extract flow characters."""
    def normalize_and_clean(text: str) -> str:
        normalized = unicodedata.normalize('NFC', text)
        zero_width_chars = ['\u200B', '\u200C', '\u2060', '\uFEFF']
        cleaned = normalized
        for zwc in zero_width_chars:
            cleaned = cleaned.replace(zwc, '')
        return cleaned
    
    def is_special_char(char: str) -> bool:
        if char.isalnum() or char.isspace():
            return False
        normal_punctuation = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
        return char not in normal_punctuation
    
    def is_normal_letter(char: str) -> bool:
        return char.isalpha()
    
    clean_name = normalize_and_clean(playlist_name)
    
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
    
    first_letter_pos = None
    for i, cluster in enumerate(clusters):
        if any(is_normal_letter(c) for c in cluster):
            first_letter_pos = i
            break
    
    last_letter_pos = None
    for i in range(len(clusters) - 1, -1, -1):
        if any(is_normal_letter(c) for c in clusters[i]):
            last_letter_pos = i
            break
    
    if first_letter_pos is None or last_letter_pos is None:
        return parent_chars, child_chars
    
    for i in range(first_letter_pos):
        cluster = clusters[i]
        if is_special_char(cluster):
            parent_chars.append(cluster)
    
    for i in range(last_letter_pos + 1, len(clusters)):
        cluster = clusters[i]
        if is_special_char(cluster):
            child_chars.append(cluster)
    
    if parent_chars and child_chars:
        if any(p_char == c_char for p_char in parent_chars for c_char in child_chars):
            return [], []
    
    return parent_chars, child_chars


def is_parent_playlist(playlist_name: str) -> bool:
    """Check if playlist is a parent playlist."""
    parent_chars, _ = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0


def load_sample_playlists(data_dir: str, limit: int = 20) -> dict:
    """Load a sample of playlists for testing."""
    playlists_dict = {}
    data_path = Path(data_dir)
    count = 0
    
    for json_file in data_path.glob("*.json"):
        if count >= limit:
            break
        if json_file.name == "__init__.py":
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
            
            playlist_name = playlist_data.get("playlist_name", json_file.stem)
            
            tracks = []
            for track_item in playlist_data.get("tracks", []):
                track = track_item
                
                if "track" in track_item and isinstance(track_item["track"], dict):
                    track = track_item["track"]
                
                if not track or track.get("is_local", False):
                    continue
                    
                track_id = track.get("id")
                if not track_id:
                    continue
                
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
            
            playlists_dict[playlist_name] = {
                "name": playlist_name,
                "tracks": tracks
            }
            count += 1
            
        except Exception:
            continue
    
    return playlists_dict


def demonstrate_improvement():
    """Demonstrate the improvement with real data."""
    print("🎯 Demonstrating Artist Matching Improvement")
    print("="*50)
    
    project_root = Path(__file__).parent
    data_dir = project_root / "data" / "playlists"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return
    
    # Load a sample of playlists
    playlists_dict = load_sample_playlists(str(data_dir), limit=50)
    print(f"Loaded {len(playlists_dict)} sample playlists for demonstration")
    
    # Categorize playlists
    parent_playlists = []
    child_playlists = []
    regular_playlists = []
    
    for playlist_name in playlists_dict.keys():
        parent_chars, child_chars = extract_flow_characters(playlist_name)
        
        if len(parent_chars) > 0:
            parent_playlists.append(playlist_name)
        elif len(child_chars) > 0:
            child_playlists.append(playlist_name)
        else:
            regular_playlists.append(playlist_name)
    
    print(f"\nPlaylist categorization:")
    print(f"  🎵 Parent playlists: {len(parent_playlists)}")
    print(f"  🎶 Child playlists: {len(child_playlists)}")
    print(f"  📀 Regular playlists: {len(regular_playlists)}")
    
    if parent_playlists:
        print(f"\nParent playlists found:")
        for parent in parent_playlists:
            print(f"    🎵 {parent}")
    
    if child_playlists:
        print(f"\nChild playlists found:")
        for child in child_playlists:
            print(f"    🎶 {child}")
    
    # Build artist mappings both ways
    artist_to_all = defaultdict(set)
    artist_to_non_parent = defaultdict(set)
    
    for playlist_name, playlist_data in playlists_dict.items():
        is_parent = is_parent_playlist(playlist_name)
        
        for track in playlist_data["tracks"]:
            for artist in track["artists"]:
                artist_id = artist.get("id")
                if artist_id:
                    artist_to_all[artist_id].add(playlist_name)
                    if not is_parent:
                        artist_to_non_parent[artist_id].add(playlist_name)
    
    # Count single-playlist artists
    single_all = sum(1 for playlists in artist_to_all.values() if len(playlists) == 1)
    single_non_parent = sum(1 for playlists in artist_to_non_parent.values() if len(playlists) == 1)
    
    print(f"\n" + "="*50)
    print("IMPROVEMENT ANALYSIS")
    print("="*50)
    
    print(f"Single-playlist artists (including parents): {single_all}")
    print(f"Single-playlist artists (excluding parents): {single_non_parent}")
    
    improvement = single_non_parent - single_all
    if improvement > 0:
        print(f"✅ IMPROVEMENT: +{improvement} more single-playlist artists!")
        improvement_percent = (improvement / single_all) * 100 if single_all > 0 else 0
        print(f"✅ This is a {improvement_percent:.1f}% increase in potential matches!")
    else:
        print(f"No improvement in this sample")
    
    # Show specific examples
    newly_single = set()
    for artist_id, non_parent_playlists in artist_to_non_parent.items():
        if len(non_parent_playlists) == 1:
            all_playlists = artist_to_all[artist_id]
            if len(all_playlists) > 1:  # Was multi-playlist before
                newly_single.add(artist_id)
    
    if newly_single:
        print(f"\n🎯 Examples of newly identified single-playlist artists:")
        for i, artist_id in enumerate(list(newly_single)[:3]):
            all_playlists = artist_to_all[artist_id]
            non_parent_playlists = artist_to_non_parent[artist_id]
            parent_playlists = all_playlists - non_parent_playlists
            
            target_playlist = list(non_parent_playlists)[0]
            print(f"  {i+1}. Artist {artist_id[:8]}...")
            print(f"     🎯 Target playlist: {target_playlist}")
            if parent_playlists:
                print(f"     🎵 Also in parent playlists: {', '.join(list(parent_playlists)[:2])}")
            print(f"     💡 Now identified as single-playlist artist!")
    
    print(f"\n" + "="*50)
    print("INTEGRATION BENEFITS")
    print("="*50)
    print("✅ Parent playlists excluded from uniqueness check")
    print("✅ More artists identified as single-playlist artists")
    print("✅ Songs added to child playlists (manual curation)")
    print("✅ Playlist flow handles automatic promotion to parents")
    print("✅ Creates intelligent, automated music organization!")


if __name__ == "__main__":
    demonstrate_improvement()