"""
Module to automatically flow songs between playlists based on special character naming system.

Special characters at the beginning of playlist names indicate parent playlists.
The same characters at the end of playlist names indicate child playlists that flow into the parent.
"""

import re
import time
import unicodedata
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional

from common.config import PLAYLIST_FLOW_ENABLED, PLAYLIST_FLOW_SKIP_CYCLES
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.utils.notifications import send_notification_via_file
from common.library_sync import load_library_manifest
from common.telegram_utils import SpotifyTelegramNotifier

# Timeout configuration (in seconds)
OPERATION_TIMEOUT = 300  # 5 minutes total timeout
BATCH_TIMEOUT = 60  # 1 minute per batch timeout


def extract_folder_and_flow(playlist_name: str) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Extract folder name and flow characters from playlist name.
    
    Supports both folder naming convention [Genre] and flow characters.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        Tuple of (folder_name, parent_chars, child_chars) where:
        - folder_name: Genre extracted from [Genre] brackets, None if not found
        - parent_chars: Special chars before normal letters (flow parent indicators)
        - child_chars: Special chars after normal letters (flow child indicators)
    """
    # First extract folder from brackets
    folder_match = re.search(r'\[([^\]]+)\]', playlist_name)
    folder_name = folder_match.group(1) if folder_match else None
    
    # Then extract flow characters using existing logic
    parent_chars, child_chars = extract_flow_characters(playlist_name)
    
    return folder_name, parent_chars, child_chars


def extract_flow_characters(playlist_name: str) -> Tuple[List[str], List[str]]:
    """
    Extract special characters from playlist name that indicate flow relationships.
    
    Special characters must be:
    - Before any normal letters (parent indicators)
    - After all normal letters (child indicators)
    
    Handles Unicode edge cases:
    - Normalizes to NFC form to handle composite characters
    - Strips zero-width characters
    - Handles multi-byte emoji as single units
    - Supports multiple special characters at start/end for multi-flow relationships
    
    Ignores test prefixes like "🧪TEST_" when analyzing flow relationships.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        Tuple of (parent_chars, child_chars) where:
        - parent_chars: Special chars before normal letters (this playlist is parent for these chars)
        - child_chars: Special chars after normal letters (this playlist flows into parents with these chars)
    """
    def normalize_and_clean(text: str) -> str:
        """Normalize Unicode and strip problematic zero-width characters"""
        # Normalize to NFC form (canonical decomposition followed by canonical composition)
        normalized = unicodedata.normalize('NFC', text)
        
        # Strip problematic zero-width characters but keep ZWJ for emoji sequences
        zero_width_chars = [
            '\u200B',  # Zero Width Space
            '\u200C',  # Zero Width Non-Joiner
            # '\u200D',  # Zero Width Joiner - KEEP for emoji sequences
            '\u2060',  # Word Joiner
            '\uFEFF',  # Zero Width No-Break Space
        ]
        
        cleaned = normalized
        for zwc in zero_width_chars:
            cleaned = cleaned.replace(zwc, '')
        
        return cleaned
    
    def is_special_char(char: str) -> bool:
        """Check if character is special (not normal keyboard chars)"""
        # Normal keyboard chars: letters, digits, space, and common punctuation
        if char.isalnum() or char.isspace():
            return False
        # Common keyboard punctuation that should be treated as normal
        normal_punctuation = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
        return char not in normal_punctuation
    
    def is_normal_letter(char: str) -> bool:
        """Check if character is a normal letter (a-z, A-Z)"""
        return char.isalpha()
    
    def extract_grapheme_clusters(text: str) -> List[str]:
        """
        Extract grapheme clusters (user-perceived characters) from text.
        Handles multi-byte emoji and composite characters as single units.
        """
        try:
            # Use the grapheme library for proper Unicode grapheme cluster segmentation
            import grapheme
            return list(grapheme.graphemes(text))
        except ImportError:
            # Fallback to regex-based approach if grapheme not available
            import regex
            
            # Comprehensive pattern for emoji sequences
            emoji_pattern = regex.compile(
                r'(?:'
                # Regional indicator pairs (flags)
                r'[\U0001F1E6-\U0001F1FF]{2}|'
                # ZWJ sequences (complex emoji like families)
                r'\p{Emoji}(?:\uFE0F|\p{Emoji_Modifier})*(?:\u200D\p{Emoji}(?:\uFE0F|\p{Emoji_Modifier})*)+\uFE0F?|'
                # Single emoji with optional modifiers/selectors
                r'\p{Emoji}(?:\p{Emoji_Modifier}|\uFE0F)*|'
                # Keycap sequences (e.g., 1️⃣)
                r'[0-9#*]\uFE0F?\u20E3'
                r')',
                regex.UNICODE
            )
            
            clusters = []
            pos = 0
            
            while pos < len(text):
                # Check for emoji sequence at current position
                match = emoji_pattern.match(text, pos)
                if match:
                    clusters.append(match.group())
                    pos = match.end()
                else:
                    # Single character
                    clusters.append(text[pos])
                    pos += 1
            
            return clusters
    
    # Normalize and clean the playlist name
    clean_name = normalize_and_clean(playlist_name)
    
    # Strip test prefix if present to avoid interference with flow detection
    test_prefixes = ["🧪TEST_"]
    for prefix in test_prefixes:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break
    
    # Handle self-reference case early
    if not clean_name.strip():
        return [], []
    
    # Extract grapheme clusters to handle multi-byte characters properly
    try:
        clusters = extract_grapheme_clusters(clean_name)
    except ImportError:
        # Fallback if regex module not available - use simple character iteration
        clusters = list(clean_name)
    
    parent_chars = []
    child_chars = []
    
    # Find first normal letter position in clusters
    first_letter_pos = None
    for i, cluster in enumerate(clusters):
        if any(is_normal_letter(c) for c in cluster):
            first_letter_pos = i
            break
    
    # Find last normal letter position in clusters
    last_letter_pos = None
    for i in range(len(clusters) - 1, -1, -1):
        if any(is_normal_letter(c) for c in clusters[i]):
            last_letter_pos = i
            break
    
    # If no normal letters found, no flow indicators
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
        # Check if any parent char matches any child char
        if any(p_char == c_char for p_char in parent_chars for c_char in child_chars):
            return [], []  # Ignore self-reference
    
    return parent_chars, child_chars


def load_playlist_tracks(sp, playlist_id: str) -> List[str]:
    """
    Load all tracks for a specific playlist.
    Uses set for deduplication during loading to handle duplicate tracks.
    
    Args:
        sp: Spotify client
        playlist_id: ID of the playlist to load tracks for
        
    Returns:
        List of unique track IDs
    """
    tracks_set = set()  # Use set to automatically handle duplicates
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
            
            # Skip if no track data
            if not track:
                continue
                
            # Skip local files (not available on Spotify streaming)
            if track.get("is_local", False):
                continue
                
            # Skip tracks without valid ID (unavailable/removed tracks)
            track_id = track.get("id")
            if not track_id:
                continue
                
            # Skip tracks that are explicitly unavailable or have no availability info
            # Note: Some unavailable tracks may still have IDs but no playable_markets
            if hasattr(track, 'available_markets') and track.get("available_markets") is not None:
                if len(track.get("available_markets", [])) == 0:
                    continue
            
            tracks_set.add(track_id)  # Set automatically deduplicates
        
        if len(track_results["items"]) < track_limit:
            break
            
        track_offset += track_limit
    
    # Convert to list for API compatibility
    return list(tracks_set)


def build_playlist_relationships(sp) -> Tuple[Dict[str, Dict], Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build playlist relationship graph without loading track data (for memory efficiency).
    Supports both direct and transitive flow relationships using the library
    manifest produced by ``sync_prod_library_cache``.

    Args:
        sp: Spotify client

    Returns:
        Tuple of (playlists_dict, parent_to_children, child_to_parents) where:
        - playlists_dict: {playlist_id: {name, parent_chars, child_chars}} (no tracks yet)
        - parent_to_children: {parent_id: [child_ids]}
        - child_to_parents: {child_id: [parent_ids]}
    """
    manifest = load_library_manifest(strict=True)
    playlists_meta = manifest.get("playlists", {})

    if not playlists_meta:
        raise RuntimeError(
            "No playlists found in library cache. Run sync_prod_library_cache() first."
        )

    print(f"Loaded playlist metadata for {len(playlists_meta)} playlists from library cache")

    playlists_dict: Dict[str, Dict] = {}
    char_to_parents = defaultdict(list)
    char_to_children = defaultdict(list)

    for playlist_id, meta in playlists_meta.items():
        playlist_name = meta.get("name", "")

        parent_chars, child_chars = extract_flow_characters(playlist_name)

        if parent_chars or child_chars:
            print(
                f"Playlist: '{playlist_name}' -> Parent chars: {parent_chars}, Child chars: {child_chars}"
            )

        for char in parent_chars:
            print(f"  Mapping char '{char}' as parent for playlist '{playlist_name}'")
            char_to_parents[char].append(playlist_id)
        for char in child_chars:
            print(f"  Looking for parent with char '{char}' for playlist '{playlist_name}'")
            char_to_children[char].append(playlist_id)

        playlists_dict[playlist_id] = {
            "name": playlist_name,
            "parent_chars": parent_chars,
            "child_chars": child_chars,
            "tracks_loaded": False,
            "tracks": [],
        }

    # Build direct relationship mappings
    parent_to_children = defaultdict(list)
    child_to_parents = defaultdict(list)

    for char, parent_ids in char_to_parents.items():
        child_ids = char_to_children.get(char, [])
        for parent_id in parent_ids:
            for child_id in child_ids:
                if parent_id != child_id:  # Avoid self-loops
                    parent_to_children[parent_id].append(child_id)
                    child_to_parents[child_id].append(parent_id)

    direct_relationships = len(parent_to_children)

    # Build transitive relationships (multi-hop chains)
    # Find playlists that are both parents and children (intermediate nodes)
    transitive_added = 0

    for intermediate_id in playlists_dict:
        intermediate_data = playlists_dict[intermediate_id]
        
        # Skip if not both parent and child
        if not (intermediate_data["parent_chars"] and intermediate_data["child_chars"]):
            continue
            
        # For each character this playlist receives from (as parent)
        for parent_char in intermediate_data["parent_chars"]:
            # Find all children that flow into this intermediate playlist
            children_to_intermediate = char_to_children.get(parent_char, [])
            
            # For each character this playlist flows to (as child)  
            for child_char in intermediate_data["child_chars"]:
                # Find all parents this intermediate playlist flows to
                parents_from_intermediate = char_to_parents.get(child_char, [])
                
                # Create transitive relationships: children -> intermediate -> parents
                for child_id in children_to_intermediate:
                    for final_parent_id in parents_from_intermediate:
                        # Avoid self-loops and intermediate loops
                        if child_id != final_parent_id and child_id != intermediate_id and final_parent_id != intermediate_id:
                            # Check if direct relationship already exists
                            if final_parent_id not in child_to_parents.get(child_id, []):
                                parent_to_children[final_parent_id].append(child_id)
                                child_to_parents[child_id].append(final_parent_id)
                                transitive_added += 1
    
    # Remove duplicates that may have been created
    for parent_id in parent_to_children:
        parent_to_children[parent_id] = list(set(parent_to_children[parent_id]))
    for child_id in child_to_parents:
        child_to_parents[child_id] = list(set(child_to_parents[child_id]))
    
    total_relationships = len(parent_to_children)
    total_playlists = len(playlists_dict)
    
    print(f"Loaded {total_playlists} playlists")
    print(f"Found {direct_relationships} direct flow relationships")
    if transitive_added > 0:
        print(f"Added {transitive_added} transitive flow relationships")
    print(f"Total: {total_relationships} flow relationships")

    return playlists_dict, dict(parent_to_children), dict(child_to_parents)


def detect_cycles(child_to_parents: Dict[str, List[str]]) -> List[List[str]]:
    """
    Detect cycles in the playlist flow graph using DFS.
    
    Args:
        child_to_parents: Mapping of child playlist IDs to their parents
        
    Returns:
        List of cycles, where each cycle is a list of playlist IDs
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(playlist_id: str) -> bool:
        if playlist_id in rec_stack:
            # Found a cycle - extract it from the path
            cycle_start = path.index(playlist_id)
            cycle = path[cycle_start:] + [playlist_id]
            cycles.append(cycle)
            return True
            
        if playlist_id in visited:
            return False
            
        visited.add(playlist_id)
        rec_stack.add(playlist_id)
        path.append(playlist_id)
        
        # Visit all parents (following the flow direction)
        for parent_id in child_to_parents.get(playlist_id, []):
            if dfs(parent_id):
                return True
        
        rec_stack.remove(playlist_id)
        path.pop()
        return False
    
    # Check all playlists for cycles
    for playlist_id in child_to_parents:
        if playlist_id not in visited:
            dfs(playlist_id)
    
    return cycles


def clear_playlist_tracks(playlists_dict: Dict[str, Dict], playlist_ids: List[str]):
    """
    Clear tracks from memory for specified playlists to reduce memory usage.
    
    Args:
        playlists_dict: Dictionary of playlist data
        playlist_ids: List of playlist IDs to clear tracks for
    """
    for playlist_id in playlist_ids:
        if playlists_dict[playlist_id].get("tracks_loaded", False):
            playlists_dict[playlist_id]["tracks"] = []
            playlists_dict[playlist_id]["tracks_loaded"] = False


def flow_songs_to_parents(sp, playlists_dict: Dict[str, Dict], 
                         parent_to_children: Dict[str, List[str]], 
                         cycles: List[List[str]], 
                         start_time: Optional[float] = None) -> Dict[str, int]:
    """
    Flow songs from child playlists to their parents, avoiding cycles.
    Processes playlists in batches to optimize memory usage for large datasets.
    Includes timeout handling for long-running operations.
    
    Args:
        sp: Spotify client
        playlists_dict: Dictionary of playlist data (tracks loaded on-demand)
        parent_to_children: Mapping of parent to child playlist IDs
        cycles: List of detected cycles
        start_time: Start time of the operation (for timeout calculation)
        
    Returns:
        Dictionary of parent_id -> number of songs added
    """
    if start_time is None:
        start_time = time.time()
    # Create set of playlist IDs involved in cycles for easy lookup
    cycle_playlists = set()
    if PLAYLIST_FLOW_SKIP_CYCLES:
        for cycle in cycles:
            cycle_playlists.update(cycle)
    
    songs_added = {}
    
    # Filter out relationships involving cycles if configured to skip them
    filtered_parent_to_children = {}
    for parent_id, child_ids in parent_to_children.items():
        if PLAYLIST_FLOW_SKIP_CYCLES and parent_id in cycle_playlists:
            continue
        filtered_child_ids = [child_id for child_id in child_ids 
                             if not (PLAYLIST_FLOW_SKIP_CYCLES and child_id in cycle_playlists)]
        if filtered_child_ids:
            filtered_parent_to_children[parent_id] = filtered_child_ids
    
    if not filtered_parent_to_children:
        print("No flow operations to process after filtering cycles")
        return songs_added
    
    # Process in batches to manage memory usage
    batch_size = 10  # Process 10 parent playlists at a time
    parent_ids = list(filtered_parent_to_children.keys())
    total_batches = (len(parent_ids) + batch_size - 1) // batch_size
    
    print(f"Processing {len(parent_ids)} flow operations in {total_batches} batches (batch size: {batch_size})")
    
    for batch_num in range(0, len(parent_ids), batch_size):
        # Check for overall timeout
        elapsed_time = time.time() - start_time
        if elapsed_time > OPERATION_TIMEOUT:
            print(f"\n⚠️ Operation timeout reached ({OPERATION_TIMEOUT}s). Processed {batch_num // batch_size} of {total_batches} batches.")
            remaining_batches = total_batches - (batch_num // batch_size)
            print(f"⚠️ {remaining_batches} batches remaining. Consider running again to complete.")
            break
        
        batch_end = min(batch_num + batch_size, len(parent_ids))
        current_batch = parent_ids[batch_num:batch_end]
        batch_number = (batch_num // batch_size) + 1
        batch_start_time = time.time()
        
        print(f"\nProcessing batch {batch_number}/{total_batches} ({len(current_batch)} parent playlists)...")
        print(f"Overall progress: {elapsed_time:.1f}s elapsed, {OPERATION_TIMEOUT - elapsed_time:.1f}s remaining")
        
        # Collect all playlist IDs needed for this batch
        batch_playlist_ids = set()
        for parent_id in current_batch:
            batch_playlist_ids.add(parent_id)
            batch_playlist_ids.update(filtered_parent_to_children[parent_id])
        
        # Load tracks for playlists in this batch
        print(f"Loading tracks for {len(batch_playlist_ids)} playlists in batch {batch_number}...")
        for i, playlist_id in enumerate(batch_playlist_ids, 1):
            # Check for batch timeout
            batch_elapsed = time.time() - batch_start_time
            if batch_elapsed > BATCH_TIMEOUT:
                print(f"    ⚠️ Batch timeout reached ({BATCH_TIMEOUT}s). Loaded {i-1} of {len(batch_playlist_ids)} playlists.")
                print(f"    ⚠️ Skipping remaining playlists in this batch.")
                break
                
            if not playlists_dict[playlist_id].get("tracks_loaded", False):
                playlist_name = playlists_dict[playlist_id]["name"]
                print(f"  [{i}/{len(batch_playlist_ids)}] Loading tracks for '{playlist_name}'...")
                try:
                    tracks = load_playlist_tracks(sp, playlist_id)
                    playlists_dict[playlist_id]["tracks"] = tracks
                    playlists_dict[playlist_id]["tracks_loaded"] = True
                    print(f"    Loaded {len(tracks)} tracks")
                except Exception as e:
                    print(f"    ⚠️ Failed to load tracks for '{playlist_name}': {e}")
                    # Set empty tracks to prevent retry and continue processing
                    playlists_dict[playlist_id]["tracks"] = []
                    playlists_dict[playlist_id]["tracks_loaded"] = True
        
        # Process flow operations for this batch
        print(f"Processing flow operations for batch {batch_number}...")
        for parent_id in current_batch:
            # Check for batch timeout during processing
            batch_elapsed = time.time() - batch_start_time
            if batch_elapsed > BATCH_TIMEOUT:
                print(f"    ⚠️ Batch timeout reached during processing. Stopping batch {batch_number}.")
                break
                
            child_ids = filtered_parent_to_children[parent_id]
            parent_data = playlists_dict[parent_id]
            
            # Skip if parent tracks weren't loaded due to timeout
            if not parent_data.get("tracks_loaded", False):
                print(f"  Skipping '{parent_data['name']}' - tracks not loaded")
                continue
                
            existing_tracks = set(parent_data["tracks"])
            new_tracks_set = set()  # Use set for O(1) lookups during deduplication
            
            for child_id in child_ids:
                child_data = playlists_dict[child_id]
                
                # Skip if child tracks weren't loaded due to timeout
                if not child_data.get("tracks_loaded", False):
                    continue
                
                # Use set operations for efficient deduplication
                child_tracks_set = set(child_data["tracks"])
                new_from_child = child_tracks_set - existing_tracks - new_tracks_set
                new_tracks_set.update(new_from_child)
            
            # Convert to list only when needed for API calls
            new_tracks = list(new_tracks_set) if new_tracks_set else []
            
            if new_tracks:
                print(f"  Adding {len(new_tracks)} tracks to '{parent_data['name']}'")
                try:
                    # Add tracks to parent playlist in chunks of 100
                    chunk_size = 100
                    total_chunks = (len(new_tracks) + chunk_size - 1) // chunk_size
                    for i in range(0, len(new_tracks), chunk_size):
                        chunk = new_tracks[i:i + chunk_size]
                        chunk_num = (i // chunk_size) + 1
                        print(f"    Adding chunk {chunk_num}/{total_chunks} ({len(chunk)} tracks)")
                        spotify_api_call_with_retry(
                            sp.playlist_add_items, parent_id, chunk
                        )
                    
                    songs_added[parent_id] = len(new_tracks)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check for permission-related errors
                    if any(perm_keyword in error_msg for perm_keyword in [
                        'insufficient privileges', 'permission', 'forbidden', 
                        'unauthorized', 'access denied', 'not allowed', 
                        'modify', 'owner', 'collaborative'
                    ]):
                        print(f"    ⚠️ Permission denied for '{parent_data['name']}' - skipping (playlist not owned or insufficient permissions)")
                    else:
                        print(f"    ⚠️ Failed to add tracks to '{parent_data['name']}': {e}")
        
        # Clear tracks from memory for this batch to free up memory
        # (except if this is the last batch, leave parent tracks loaded for final reporting)
        if batch_number < total_batches:
            print(f"Clearing tracks from memory for batch {batch_number} to optimize memory usage...")
            clear_playlist_tracks(playlists_dict, list(batch_playlist_ids))
    
    print(f"\nCompleted all {total_batches} batches")
    return songs_added


def run_action():
    """
    Main action to flow songs between playlists based on special character naming.
    
    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Playlist Flow")
    
    # Check if playlist flow is enabled
    if not PLAYLIST_FLOW_ENABLED:
        title = "Playlist Flow Disabled"
        message = "Playlist flow automation is disabled in configuration."
        telegram.send_info("Playlist flow is disabled", "Enable in configuration to use this feature")
        send_notification_via_file(title, message, "/tmp/spotify_playlist_flow_result.txt")
        print(f"{title}\n{message}")
        return title, message
    
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope, "playlist_flow_cache")
    
    try:
        # Build the playlist relationship graph (metadata only for memory efficiency)
        print("Building playlist relationship graph...")
        print("Looking for special characters (non-keyboard chars) at start/end of playlist names")
        playlists_dict, parent_to_children, child_to_parents = build_playlist_relationships(sp)
        
        print(f"Found {len(playlists_dict)} total playlists")
        if len(playlists_dict) <= 20:  # Only show all names for small lists
            print("All playlist names:")
            for playlist_id, data in playlists_dict.items():
                print(f"  - '{data['name']}'")
        else:
            print(f"Sample playlist names (showing first 10 of {len(playlists_dict)}):")
            for i, (playlist_id, data) in enumerate(playlists_dict.items()):
                if i >= 10:
                    break
                print(f"  - '{data['name']}'")
            print("  ...")
        print(f"Found {len(parent_to_children)} parent-child relationships")
        
        # Debug: Print some example relationships
        if parent_to_children:
            print("Sample flow relationships:")
            for parent_id, child_ids in list(parent_to_children.items())[:3]:
                parent_name = playlists_dict[parent_id]["name"]
                child_names = [playlists_dict[child_id]["name"] for child_id in child_ids]
                print(f"  Parent '{parent_name}' <- {child_names}")
        
        if not parent_to_children:
            title = "No Flow Relationships Found"
            message = "No playlists found with special character flow relationships."
            return title, message
        
        # Detect cycles
        print("Detecting cycles...")
        cycles = detect_cycles(child_to_parents)
        print(f"Found {len(cycles)} cycles")
        
        if cycles:
            for i, cycle in enumerate(cycles):
                cycle_names = [playlists_dict[pid]["name"] for pid in cycle]
                print(f"Cycle {i+1}: {' -> '.join(cycle_names)}")
        
        # Flow songs from children to parents
        print("Flowing songs from children to parents...")
        operation_start_time = time.time()
        songs_added = flow_songs_to_parents(sp, playlists_dict, parent_to_children, cycles, operation_start_time)
        
        # Prepare notification message
        if not songs_added:
            if cycles:
                title = "⚠️ Playlist Flow Skipped"
                cycle_names = []
                for cycle in cycles:
                    cycle_names.extend([playlists_dict[pid]["name"] for pid in cycle])
                message = f"Skipped flow due to {len(cycles)} cycle(s) involving: {', '.join(set(cycle_names))}"
                telegram.send_info("Playlist flow skipped due to cycles", f"Found {len(cycles)} cycle(s) that would cause infinite loops")
            else:
                title = "✅ No New Songs to Flow"
                message = "All parent playlists are up to date with their children."
                telegram.send_info("No new songs to flow", "All parent playlists are up to date")
        else:
            total_songs = sum(songs_added.values())
            title = f"✅ Flowed {total_songs} Songs"
            
            flow_details = []
            for parent_id, count in songs_added.items():
                parent_name = playlists_dict[parent_id]["name"]
                flow_details.append(f"{parent_name}: +{count}")
            
            message = f"Songs flowed to {len(songs_added)} parent playlists:\n" + "\n".join(flow_details)
            
            if cycles:
                message += f"\n\nNote: Skipped {len(cycles)} cycle(s) to prevent infinite loops."
            
            telegram.send_success(f"Flowed {total_songs} songs to {len(songs_added)} playlists", 
                                  "\n".join(flow_details))
    
    except Exception as e:
        title = "Error"
        message = f"Playlist flow failed: {str(e)}"
        telegram.send_error("Playlist flow failed", str(e))
    
    # Send notification
    send_notification_via_file(title, message, "/tmp/spotify_playlist_flow_result.txt")
    print(f"{title}\n{message}")
    
    return title, message


def main():
    """Entry point for command-line use."""
    return run_action()


if __name__ == "__main__":
    main()
