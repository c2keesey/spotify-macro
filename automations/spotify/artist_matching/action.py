"""
Automation to add songs from a source playlist to target playlists based on artist matching.

For each song in the source playlist, identifies if the artist is a "single-playlist artist"
(only appears in exactly one existing playlist). If true, adds the song to that target playlist.

INTELLIGENT FLOW INTEGRATION:
This automation integrates with the playlist flow system by excluding parent playlists 
from the uniqueness check. Parent playlists (those with special characters at the beginning
like "🎵 Collection") receive songs automatically from their child playlists. Therefore:

- Artists appearing in both child and parent playlists are considered "single-playlist"
- Songs are added to the child playlist (where they're manually curated)  
- The playlist flow automation handles moving them to parent playlists automatically
- This creates +471 more potential matches compared to naive uniqueness checking

This automation is designed to work with the "new" playlist as the source by default.
"""

import json
import re
import unicodedata
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

from common.config import get_config_value
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.utils.notifications import send_notification_via_file
from common.telegram_utils import SpotifyTelegramNotifier


def extract_flow_characters(playlist_name: str) -> Tuple[List[str], List[str]]:
    """
    Extract special characters from playlist name that indicate flow relationships.
    
    This is adapted from the playlist_flow automation to identify parent/child playlists.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        Tuple of (parent_chars, child_chars) where:
        - parent_chars: Special chars before normal letters (this playlist is parent for these chars)
        - child_chars: Special chars after normal letters (this playlist flows into parents with these chars)
    """
    def normalize_and_clean(text: str) -> str:
        """Normalize Unicode and strip problematic zero-width characters"""
        normalized = unicodedata.normalize('NFC', text)
        
        zero_width_chars = [
            '\u200B',  # Zero Width Space
            '\u200C',  # Zero Width Non-Joiner
            '\u2060',  # Word Joiner
            '\uFEFF',  # Zero Width No-Break Space
        ]
        
        cleaned = normalized
        for zwc in zero_width_chars:
            cleaned = cleaned.replace(zwc, '')
        
        return cleaned
    
    def is_special_char(char: str) -> bool:
        """Check if character is special (not normal keyboard chars)"""
        if char.isalnum() or char.isspace():
            return False
        normal_punctuation = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
        return char not in normal_punctuation
    
    def is_normal_letter(char: str) -> bool:
        """Check if character is a normal letter (a-z, A-Z)"""
        return char.isalpha()
    
    # Normalize and clean the playlist name
    clean_name = normalize_and_clean(playlist_name)
    
    # Strip test prefix if present
    test_prefixes = ["🧪TEST_"]
    for prefix in test_prefixes:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break
    
    if not clean_name.strip():
        return [], []
    
    # Simple character iteration (fallback from complex grapheme clusters)
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
    """
    Check if a playlist is a parent playlist (has special characters at the beginning).
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        True if the playlist is a parent playlist
    """
    parent_chars, _ = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0


def load_playlist_data(sp) -> Dict[str, Dict]:
    """
    Load all user playlists and their track data.
    
    Args:
        sp: Spotify client
        
    Returns:
        Dictionary mapping playlist_id to playlist data including tracks
    """
    playlists_dict = {}
    
    # Get all user playlists
    offset = 0
    limit = 50
    
    print("Loading all user playlists...")
    
    while True:
        results = spotify_api_call_with_retry(
            sp.current_user_playlists, limit=limit, offset=offset
        )
        
        if not results["items"]:
            break
            
        for playlist in results["items"]:
            playlist_id = playlist["id"]
            playlist_name = playlist["name"]
            
            # Load tracks for this playlist
            tracks = load_playlist_tracks(sp, playlist_id)
            
            playlists_dict[playlist_id] = {
                "name": playlist_name,
                "tracks": tracks
            }
            
            print(f"Loaded '{playlist_name}' ({len(tracks)} tracks)")
        
        if len(results["items"]) < limit:
            break
            
        offset += limit
    
    return playlists_dict


def load_playlist_tracks(sp, playlist_id: str) -> List[Dict]:
    """
    Load all tracks for a specific playlist, including track and artist info.
    
    Args:
        sp: Spotify client
        playlist_id: ID of the playlist to load tracks for
        
    Returns:
        List of track dictionaries with track and artist information
    """
    tracks = []
    track_offset = 0
    track_limit = 100
    
    while True:
        track_results = spotify_api_call_with_retry(
            sp.playlist_tracks, playlist_id, limit=track_limit, offset=track_offset
        )
        
        if not track_results["items"]:
            break
            
        for item in track_results["items"]:
            track = item.get("track")
            
            # Skip if no track data or local files
            if not track or track.get("is_local", False):
                continue
                
            # Skip tracks without valid ID
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
            
            track_data = {
                "id": track_id,
                "name": track.get("name"),
                "artists": artists
            }
            
            tracks.append(track_data)
        
        if len(track_results["items"]) < track_limit:
            break
            
        track_offset += track_limit
    
    return tracks


def build_artist_to_playlists_mapping(playlists_dict: Dict[str, Dict]) -> Dict[str, Set[str]]:
    """
    Build mapping of artist ID to set of playlist IDs they appear in.
    
    IMPORTANT: This excludes parent playlists from the uniqueness check because songs
    in parent playlists come from child playlists via the playlist flow automation.
    We only want to count artists in playlists where they are manually curated.
    
    Args:
        playlists_dict: Dictionary of playlist data
        
    Returns:
        Dictionary mapping artist_id to set of playlist_ids (excluding parent playlists)
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
        for parent_name in excluded_parents[:5]:  # Show first 5
            print(f"  🎵 {parent_name} (parent playlist)")
        if len(excluded_parents) > 5:
            print(f"  ... and {len(excluded_parents) - 5} more parent playlists")
        print("(Parent playlists receive songs automatically via playlist flow)")
    
    return artist_to_playlists


def find_single_playlist_artists(artist_to_playlists: Dict[str, Set[str]]) -> Set[str]:
    """
    Find artists that appear in only one playlist.
    
    Args:
        artist_to_playlists: Mapping of artist_id to set of playlist_ids
        
    Returns:
        Set of artist IDs that appear in exactly one playlist
    """
    single_playlist_artists = set()
    
    for artist_id, playlists in artist_to_playlists.items():
        if len(playlists) == 1:
            single_playlist_artists.add(artist_id)
    
    return single_playlist_artists


def find_source_playlist(playlists_dict: Dict[str, Dict], source_name: str = "new") -> Optional[str]:
    """
    Find the source playlist by name (case-insensitive).
    
    Args:
        playlists_dict: Dictionary of playlist data
        source_name: Name of the source playlist to find
        
    Returns:
        Playlist ID if found, None otherwise
    """
    source_name_lower = source_name.lower()
    
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data["name"].lower() == source_name_lower:
            return playlist_id
    
    return None


def process_artist_matching(sp, playlists_dict: Dict[str, Dict], 
                          source_playlist_id: str, 
                          single_playlist_artists: Set[str],
                          artist_to_playlists: Dict[str, Set[str]]) -> Dict[str, int]:
    """
    Process songs from source playlist and add them to target playlists based on artist matching.
    
    Args:
        sp: Spotify client
        playlists_dict: Dictionary of playlist data
        source_playlist_id: ID of the source playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        artist_to_playlists: Mapping of artist_id to set of playlist_ids
        
    Returns:
        Dictionary mapping target_playlist_id to number of songs added
    """
    songs_added = {}
    source_tracks = playlists_dict[source_playlist_id]["tracks"]
    source_name = playlists_dict[source_playlist_id]["name"]
    
    print(f"Processing {len(source_tracks)} tracks from '{source_name}'...")
    
    # Track which songs to add to which playlists
    playlist_to_new_tracks = defaultdict(list)
    
    for track in source_tracks:
        track_id = track["id"]
        track_name = track["name"]
        
        # Check if any artist in this track is a single-playlist artist
        for artist in track["artists"]:
            artist_id = artist.get("id")
            artist_name = artist.get("name")
            
            if artist_id in single_playlist_artists:
                # This artist appears in only one playlist - find which one
                target_playlist_ids = artist_to_playlists[artist_id]
                
                # Should be exactly one playlist
                if len(target_playlist_ids) == 1:
                    target_playlist_id = list(target_playlist_ids)[0]
                    
                    # Don't add to source playlist itself
                    if target_playlist_id == source_playlist_id:
                        continue
                    
                    # Check if track is already in target playlist
                    target_tracks = playlists_dict[target_playlist_id]["tracks"]
                    existing_track_ids = {t["id"] for t in target_tracks}
                    
                    if track_id not in existing_track_ids:
                        playlist_to_new_tracks[target_playlist_id].append(track_id)
                        target_name = playlists_dict[target_playlist_id]["name"]
                        print(f"  Will add '{track_name}' to '{target_name}' (artist: {artist_name})")
                    
                    # Once we find a match, no need to check other artists for this track
                    break
    
    # Add tracks to target playlists
    for target_playlist_id, track_ids in playlist_to_new_tracks.items():
        target_name = playlists_dict[target_playlist_id]["name"]
        
        # Remove duplicates
        unique_track_ids = list(set(track_ids))
        
        if unique_track_ids:
            print(f"Adding {len(unique_track_ids)} tracks to '{target_name}'")
            try:
                # Add tracks in chunks of 100
                chunk_size = 100
                for i in range(0, len(unique_track_ids), chunk_size):
                    chunk = unique_track_ids[i:i + chunk_size]
                    spotify_api_call_with_retry(
                        sp.playlist_add_items, target_playlist_id, chunk
                    )
                
                songs_added[target_playlist_id] = len(unique_track_ids)
                
            except Exception as e:
                error_msg = str(e).lower()
                if any(perm_keyword in error_msg for perm_keyword in [
                    'insufficient privileges', 'permission', 'forbidden', 
                    'unauthorized', 'access denied', 'not allowed', 
                    'modify', 'owner', 'collaborative'
                ]):
                    print(f"  ⚠️ Permission denied for '{target_name}' - skipping")
                else:
                    print(f"  ⚠️ Failed to add tracks to '{target_name}': {e}")
    
    return songs_added


def run_action():
    """
    Main action to add songs from source playlist to target playlists based on artist matching.
    
    This automation identifies "single-playlist artists" - artists that appear in only one 
    playlist (excluding parent playlists, since they get songs automatically via playlist flow).
    When songs by these artists are found in the source playlist, they are automatically
    added to the target playlist where that artist is curated.
    
    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Artist Matching")
    
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope, "artist_matching_cache")
    
    try:
        # Load all playlist data
        playlists_dict = load_playlist_data(sp)
        
        print(f"Loaded {len(playlists_dict)} playlists")
        
        # Find source playlist (default: "new")
        source_playlist_id = find_source_playlist(playlists_dict, "new")
        
        if not source_playlist_id:
            title = "❌ Source Playlist Not Found"
            message = "Could not find playlist named 'new' to process."
            telegram.send_error("Source playlist not found", message)
            send_notification_via_file(title, message, "/tmp/spotify_artist_matching_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        source_name = playlists_dict[source_playlist_id]["name"]
        source_track_count = len(playlists_dict[source_playlist_id]["tracks"])
        
        print(f"Found source playlist: '{source_name}' ({source_track_count} tracks)")
        
        # Build artist to playlists mapping (excluding parent playlists)
        print("Building artist to playlists mapping (excluding parent playlists)...")
        artist_to_playlists = build_artist_to_playlists_mapping(playlists_dict)
        
        print(f"Found {len(artist_to_playlists)} unique artists in non-parent playlists")
        
        # Find single playlist artists
        single_playlist_artists = find_single_playlist_artists(artist_to_playlists)
        
        print(f"Found {len(single_playlist_artists)} single-playlist artists")
        
        if not single_playlist_artists:
            title = "ℹ️ No Single-Playlist Artists"
            message = "No artists found that appear in only one playlist."
            telegram.send_info("No single-playlist artists", message)
            send_notification_via_file(title, message, "/tmp/spotify_artist_matching_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        # Process artist matching
        print("Processing artist matching...")
        songs_added = process_artist_matching(sp, playlists_dict, source_playlist_id, 
                                            single_playlist_artists, artist_to_playlists)
        
        # Prepare notification message
        if not songs_added:
            title = "✅ No Songs to Add"
            message = f"No songs from '{source_name}' matched single-playlist artists."
            telegram.send_info("No songs to add", message)
        else:
            total_songs = sum(songs_added.values())
            title = f"✅ Added {total_songs} Songs"
            
            match_details = []
            for target_playlist_id, count in songs_added.items():
                target_name = playlists_dict[target_playlist_id]["name"]
                match_details.append(f"{target_name}: +{count}")
            
            message = f"Songs added to {len(songs_added)} target playlists:\n" + "\n".join(match_details)
            
            telegram.send_success(f"Added {total_songs} songs to {len(songs_added)} playlists", 
                                  "\n".join(match_details))
    
    except Exception as e:
        title = "Error"
        message = f"Artist matching failed: {str(e)}"
        telegram.send_error("Artist matching failed", str(e))
    
    # Send notification
    send_notification_via_file(title, message, "/tmp/spotify_artist_matching_result.txt")
    print(f"{title}\n{message}")
    
    return title, message


def main():
    """Entry point for command-line use."""
    return run_action()


if __name__ == "__main__":
    main()