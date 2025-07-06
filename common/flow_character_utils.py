"""
Centralized flow character extraction utilities.

Handles playlist name parsing for flow relationships in the bidirectional flow system:
- Parent playlists: Special characters at the beginning (e.g., "🎵 Collection")  
- Child playlists: Special characters at the end (e.g., "Daily Mix 🎵")
- Flow relationships: Characters indicate hierarchical organization

This module consolidates the flow character logic used across multiple files.
"""

import unicodedata
from typing import List, Tuple


def normalize_and_clean(text: str) -> str:
    """
    Normalize Unicode and strip problematic zero-width characters.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Cleaned and normalized text
    """
    normalized = unicodedata.normalize('NFC', text)
    
    # Remove zero-width characters that can cause parsing issues
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
    """
    Check if character is special (not normal keyboard chars).
    
    Special characters are used to indicate flow relationships in playlist names.
    
    Args:
        char: Character to check
        
    Returns:
        True if character is special (used for flow relationships)
    """
    if char.isalnum() or char.isspace():
        return False
    
    # Normal punctuation that doesn't indicate flow relationships
    normal_punctuation = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
    return char not in normal_punctuation


def is_normal_letter(char: str) -> bool:
    """
    Check if character is a normal letter (a-z, A-Z).
    
    Args:
        char: Character to check
        
    Returns:
        True if character is a normal letter
    """
    return char.isalpha()


def extract_flow_characters(playlist_name: str) -> Tuple[List[str], List[str]]:
    """
    Extract special characters from playlist name that indicate flow relationships.
    
    Flow character positions indicate hierarchy:
    - Parent chars: Special chars before normal letters (this playlist is parent for these chars)
    - Child chars: Special chars after normal letters (this playlist flows into parents with these chars)
    
    Examples:
    - "🎵 Collection" → parent_chars=["🎵"], child_chars=[]
    - "Daily Mix 🎵" → parent_chars=[], child_chars=["🎵"] 
    - "🎵 Mix 🎶" → parent_chars=["🎵"], child_chars=["🎶"]
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        Tuple of (parent_chars, child_chars) where:
        - parent_chars: Special chars before normal letters
        - child_chars: Special chars after normal letters
    """
    # Normalize and clean the playlist name
    clean_name = normalize_and_clean(playlist_name)
    
    # Strip test prefix if present (for test environments)
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
        # No normal letters found - this shouldn't be a flow playlist
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
    # (playlists shouldn't flow to themselves)
    if parent_chars and child_chars:
        if any(p_char == c_char for p_char in parent_chars for c_char in child_chars):
            return [], []
    
    return parent_chars, child_chars


def is_parent_playlist(playlist_name: str) -> bool:
    """
    Check if a playlist is a parent playlist.
    
    Parent playlists have special characters at the beginning of their name
    and receive songs automatically from their child playlists.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        True if the playlist is a parent playlist
    """
    parent_chars, _ = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0


def is_child_playlist(playlist_name: str) -> bool:
    """
    Check if a playlist is a child playlist.
    
    Child playlists have special characters at the end of their name
    and flow their songs to parent playlists automatically.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        True if the playlist is a child playlist
    """
    _, child_chars = extract_flow_characters(playlist_name)
    return len(child_chars) > 0


def is_flow_playlist(playlist_name: str) -> bool:
    """
    Check if a playlist participates in the flow system.
    
    Flow playlists have either parent or child characters (or both).
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        True if the playlist participates in flow relationships
    """
    parent_chars, child_chars = extract_flow_characters(playlist_name)
    return len(parent_chars) > 0 or len(child_chars) > 0


def get_flow_relationship(playlist_name: str) -> str:
    """
    Get the flow relationship type of a playlist.
    
    Args:
        playlist_name: Name of the playlist
        
    Returns:
        Flow relationship type: "parent", "child", "bidirectional", or "none"
    """
    parent_chars, child_chars = extract_flow_characters(playlist_name)
    
    has_parent = len(parent_chars) > 0
    has_child = len(child_chars) > 0
    
    if has_parent and has_child:
        return "bidirectional"
    elif has_parent:
        return "parent"
    elif has_child:
        return "child"
    else:
        return "none"


def find_flow_matches(
    playlist_name: str, 
    all_playlist_names: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Find potential flow matches for a playlist.
    
    Args:
        playlist_name: Name of the playlist to find matches for
        all_playlist_names: List of all available playlist names
        
    Returns:
        Tuple of (potential_parents, potential_children)
    """
    parent_chars, child_chars = extract_flow_characters(playlist_name)
    
    potential_parents = []
    potential_children = []
    
    for other_name in all_playlist_names:
        if other_name == playlist_name:
            continue
            
        other_parent_chars, other_child_chars = extract_flow_characters(other_name)
        
        # Check if this playlist's child chars match other's parent chars
        if child_chars and other_parent_chars:
            if any(c_char in other_parent_chars for c_char in child_chars):
                potential_parents.append(other_name)
        
        # Check if this playlist's parent chars match other's child chars
        if parent_chars and other_child_chars:
            if any(p_char in other_child_chars for p_char in parent_chars):
                potential_children.append(other_name)
    
    return potential_parents, potential_children


def validate_flow_relationship(
    parent_name: str,
    child_name: str
) -> bool:
    """
    Validate that two playlists can have a valid flow relationship.
    
    Args:
        parent_name: Name of the potential parent playlist
        child_name: Name of the potential child playlist
        
    Returns:
        True if the flow relationship is valid
    """
    parent_parent_chars, parent_child_chars = extract_flow_characters(parent_name)
    child_parent_chars, child_child_chars = extract_flow_characters(child_name)
    
    # Parent must have parent chars, child must have child chars
    if not parent_parent_chars or not child_child_chars:
        return False
    
    # Child's chars must match parent's chars
    return any(c_char in parent_parent_chars for c_char in child_child_chars)