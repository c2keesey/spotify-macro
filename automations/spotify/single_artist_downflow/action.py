"""
Single Artist Playlist Downflow Automation

Processes tracks by single-playlist artists in the 'new' playlist by:
1. Identifying tracks by artists that appear in only one playlist across your library
2. Adding those tracks to both the artist's specific playlist and the folder playlist
3. Removing the processed tracks from the 'new' playlist

This automation uses the playlist folder structure defined in data/playlist_folders.json
to determine which folder playlist to add tracks to.

IMPORTANT: This identifies "single-playlist artists" - artists that appear in only one 
playlist in your library (excluding parent playlists). When such artists' tracks are 
found in the 'new' playlist, they are automatically routed to the playlist where 
that artist is uniquely curated.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

from common.config import get_config_value
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.utils.notifications import send_notification_via_file
from common.telegram_utils import SpotifyTelegramNotifier
from common.shared_cache import get_cached_artist_data
from common.playlist_data_utils import PlaylistDataLoader
from common.flow_character_utils import extract_flow_characters, is_parent_playlist


def load_playlist_folders() -> Dict[str, List[str]]:
    """
    Load the playlist folder structure from data/playlist_folders.json
    
    Returns:
        Dictionary mapping folder names to lists of playlist filenames
    """
    folder_path = os.path.join(os.path.dirname(__file__), "../../../data/playlist_folders.json")
    
    try:
        with open(folder_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Playlist folders file not found at {folder_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing playlist folders JSON: {e}")
        return {}


def get_playlist_folder_mapping(playlists_dict: Dict[str, Dict], 
                               playlist_folders: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Create a mapping from playlist names to their folder names.
    
    Args:
        playlists_dict: Dictionary of playlist data
        playlist_folders: Dictionary mapping folder names to playlist filenames
        
    Returns:
        Dictionary mapping playlist names to folder names
    """
    playlist_to_folder = {}
    
    # Build reverse mapping from playlist filename to folder name
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            # Remove .json extension to get playlist name
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    return playlist_to_folder


def load_playlist_data_optimized() -> Dict[str, Dict]:
    """
    Load playlist data using cached local data for fast processing.
    
    Returns:
        Dictionary mapping playlist_id to playlist data including tracks
    """
    print("Loading playlist data from cache...")
    
    # Use cached local playlist data
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
        include_empty=False,
        verbose=True
    )
    
    return playlists_dict


def load_playlist_data_live(sp) -> Dict[str, Dict]:
    """
    Load all user playlists and their track data from Spotify API.
    Only use this for cache updates or when fresh data is needed.
    
    Args:
        sp: Spotify client
        
    Returns:
        Dictionary mapping playlist_id to playlist data including tracks
    """
    playlists_dict = {}
    
    # Get all user playlists
    offset = 0
    limit = 50
    
    print("Loading all user playlists from Spotify API...")
    
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
                "artists": artists,
                "uri": track.get("uri")
            }
            
            tracks.append(track_data)
        
        if len(track_results["items"]) < track_limit:
            break
            
        track_offset += track_limit
    
    return tracks


def find_source_playlist(playlists_dict: Dict[str, Dict], source_name: str = "new") -> Optional[str]:
    """
    Find the source playlist by name (case-insensitive).
    
    Args:
        playlists_dict: Dictionary of playlist data
        source_name: Name of the source playlist to find
        
    Returns:
        Playlist ID if found, None otherwise
    """
    return PlaylistDataLoader.find_playlist_by_name(playlists_dict, source_name, case_sensitive=False)


def find_playlist_by_name(playlists_dict: Dict[str, Dict], name: str) -> Optional[str]:
    """
    Find a playlist by exact name match.
    
    Args:
        playlists_dict: Dictionary of playlist data
        name: Name of the playlist to find
        
    Returns:
        Playlist ID if found, None otherwise
    """
    return PlaylistDataLoader.find_playlist_by_name(playlists_dict, name, case_sensitive=True)


"""
Deduplicated: use common.flow_character_utils for flow parsing and parent detection.
"""


# Note: Artist mapping functions moved to shared_cache.py and playlist_data_utils.py


def identify_single_playlist_artist_tracks(tracks: List[Dict], 
                                         single_playlist_artists: Set[str]) -> List[Dict]:
    """
    Identify tracks by artists that appear in only one playlist.
    
    Args:
        tracks: List of track dictionaries from the source playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        
    Returns:
        List of track dictionaries by single-playlist artists
    """
    single_playlist_tracks = []
    
    for track in tracks:
        # Check if any artist in this track is a single-playlist artist
        for artist in track["artists"]:
            artist_id = artist.get("id")
            if artist_id in single_playlist_artists:
                single_playlist_tracks.append(track)
                artist_name = artist.get("name")
                print(f"Found single-playlist artist track: '{track['name']}' by {artist_name}")
                break  # Only need to find one matching artist per track
    
    return single_playlist_tracks


def process_single_artist_downflow(sp, playlists_dict: Dict[str, Dict], 
                                 source_playlist_id: str,
                                 single_playlist_artists: Set[str],
                                 artist_to_playlists: Dict[str, Set[str]],
                                 playlist_to_folder: Dict[str, str]) -> Dict[str, int]:
    """
    Process tracks by single-playlist artists from the source playlist.
    
    Args:
        sp: Spotify client
        playlists_dict: Dictionary of playlist data
        source_playlist_id: ID of the source playlist
        single_playlist_artists: Set of artist IDs that appear in only one playlist
        artist_to_playlists: Mapping of artist_id to set of playlist_ids
        playlist_to_folder: Mapping from playlist names to folder names
        
    Returns:
        Dictionary with processing statistics
    """
    source_tracks = playlists_dict[source_playlist_id]["tracks"]
    source_name = playlists_dict[source_playlist_id]["name"]
    
    print(f"Processing {len(source_tracks)} tracks from '{source_name}'...")
    
    # Identify tracks by single-playlist artists
    single_playlist_tracks = identify_single_playlist_artist_tracks(source_tracks, single_playlist_artists)
    
    if not single_playlist_tracks:
        print("No tracks by single-playlist artists found in source playlist")
        return {"processed_tracks": 0, "playlists_updated": 0}
    
    processed_tracks = 0
    playlists_updated = 0
    tracks_to_remove = []
    
    # Process each track by single-playlist artists
    for track in single_playlist_tracks:
        track_id = track["id"]
        track_name = track["name"]
        
        # Find which artist makes this a single-playlist track
        target_playlist_id = None
        artist_name = None
        
        for artist in track["artists"]:
            artist_id = artist.get("id")
            if artist_id in single_playlist_artists:
                # This artist appears in only one playlist - find which one
                target_playlist_ids = artist_to_playlists[artist_id]
                
                if len(target_playlist_ids) == 1:
                    target_playlist_id = list(target_playlist_ids)[0]
                    artist_name = artist.get("name")
                    break
        
        if not target_playlist_id:
            print(f"  Warning: Could not find target playlist for '{track_name}' - skipping")
            continue
        
        # Don't add to source playlist itself or other staging playlists
        if target_playlist_id == source_playlist_id:
            print(f"  ⏭️  SKIPPED: '{track_name}' target is source playlist ('{source_name}')")
            continue
        
        target_playlist_name = playlists_dict[target_playlist_id]["name"]
        
        # Skip if target is a staging playlist like 'New'
        staging_playlists = ['New', 'new', 'NEW', 'Listen Later', 'Daily']  # Add other staging playlists as needed
        if target_playlist_name in staging_playlists:
            print(f"  ⏭️  SKIPPED: '{track_name}' target is staging playlist ('{target_playlist_name}')")
            continue
        
        print(f"Processing '{track_name}' by {artist_name} -> '{target_playlist_name}'")
        
        # Check if track is already in target playlist
        target_track_ids = {t["id"] for t in playlists_dict[target_playlist_id]["tracks"]}
        
        if track_id not in target_track_ids:
            try:
                # Add to target playlist
                print(f"  Adding '{track_name}' to '{target_playlist_name}'")
                spotify_api_call_with_retry(
                    sp.playlist_add_items, target_playlist_id, [track_id]
                )
                playlists_updated += 1
                
                # Find and add to folder playlist if it exists
                folder_name = playlist_to_folder.get(target_playlist_name)
                if folder_name:
                    folder_playlist_id = find_playlist_by_name(playlists_dict, folder_name)
                    if folder_playlist_id:
                        # Check if track is already in folder playlist
                        folder_track_ids = {t["id"] for t in playlists_dict[folder_playlist_id]["tracks"]}
                        
                        if track_id not in folder_track_ids:
                            print(f"  Adding '{track_name}' to folder playlist '{folder_name}'")
                            spotify_api_call_with_retry(
                                sp.playlist_add_items, folder_playlist_id, [track_id]
                            )
                            playlists_updated += 1
                        else:
                            print(f"  '{track_name}' already in folder playlist '{folder_name}'")
                    else:
                        print(f"  Warning: Folder playlist '{folder_name}' not found")
                else:
                    print(f"  No folder mapping found for '{target_playlist_name}'")
                
                # Mark track for removal from source playlist
                tracks_to_remove.append(track)
                processed_tracks += 1
                
            except Exception as e:
                print(f"  Error adding '{track_name}' to '{target_playlist_name}': {e}")
                continue
        else:
            print(f"  ⏭️  SKIPPED: '{track_name}' already in '{target_playlist_name}'")
    
    # Remove processed tracks from source playlist
    if tracks_to_remove:
        print(f"Removing {len(tracks_to_remove)} processed tracks from '{source_name}'...")
        try:
            # Remove tracks in chunks
            track_uris_to_remove = [track["uri"] for track in tracks_to_remove]
            chunk_size = 100
            
            for i in range(0, len(track_uris_to_remove), chunk_size):
                chunk = track_uris_to_remove[i:i + chunk_size]
                spotify_api_call_with_retry(
                    sp.playlist_remove_all_occurrences_of_items, source_playlist_id, chunk
                )
            
            print(f"Successfully removed {len(tracks_to_remove)} tracks from '{source_name}'")
            
        except Exception as e:
            print(f"Error removing tracks from '{source_name}': {e}")
    
    return {
        "processed_tracks": processed_tracks,
        "playlists_updated": playlists_updated,
        "tracks_removed": len(tracks_to_remove)
    }


def run_action():
    """
    Main action to process single artist playlists from 'new' playlist.
    
    Returns:
        tuple: (title, message) notification information
    """
    # Initialize Telegram notifier
    telegram = SpotifyTelegramNotifier("Single Artist Downflow")
    
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope, "single_artist_downflow_cache")
    
    try:
        # Load playlist folder structure
        print("Loading playlist folder structure...")
        playlist_folders = load_playlist_folders()
        
        # Load cached artist data (much faster than full API loading)
        print("Loading cached artist data...")
        artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
        
        print(f"Found {len(artist_to_playlists)} unique artists in non-parent playlists")
        print(f"Found {len(single_playlist_artists)} single-playlist artists")
        
        if not single_playlist_artists:
            title = "ℹ️ No Single-Playlist Artists"
            message = "No artists found that appear in only one playlist."
            telegram.send_info("No single-playlist artists", message)
            send_notification_via_file(title, message, "/tmp/spotify_single_artist_downflow_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        # Load minimal playlist data (just need the 'new' playlist and target playlists)
        print("Loading minimal playlist data...")
        playlists_dict = load_playlist_data_optimized()
        
        # Create playlist to folder mapping
        playlist_to_folder = get_playlist_folder_mapping(playlists_dict, playlist_folders)
        print(f"Mapped {len(playlist_to_folder)} playlists to folders")
        
        # Find source playlist
        source_playlist_id = find_source_playlist(playlists_dict, "new")
        
        if not source_playlist_id:
            title = "❌ Source Playlist Not Found"
            message = "Could not find playlist named 'new' to process."
            telegram.send_error("Source playlist not found", message)
            send_notification_via_file(title, message, "/tmp/spotify_single_artist_downflow_result.txt")
            print(f"{title}\n{message}")
            return title, message
        
        source_name = playlists_dict[source_playlist_id]["name"]
        source_track_count = len(playlists_dict[source_playlist_id]["tracks"])
        
        print(f"Found source playlist: '{source_name}' ({source_track_count} tracks)")
        
        # Process single artist downflow
        print("Processing single artist downflow...")
        results = process_single_artist_downflow(sp, playlists_dict, source_playlist_id, 
                                               single_playlist_artists, artist_to_playlists, 
                                               playlist_to_folder)
        
        # Prepare notification message
        if results["processed_tracks"] == 0:
            title = "ℹ️ No Single Artist Playlists Found"
            message = f"No single artist playlists found in '{source_name}' to process."
            telegram.send_info("No single artist playlists", message)
        else:
            title = f"✅ Processed {results['processed_tracks']} Tracks"
            message = (f"Successfully processed {results['processed_tracks']} tracks "
                      f"from single artist playlists in '{source_name}'.\n"
                      f"Updated {results['playlists_updated']} playlists.\n"
                      f"Removed {results['tracks_removed']} tracks from source playlist.")
            telegram.send_success(f"Processed {results['processed_tracks']} tracks", message)
    
    except Exception as e:
        title = "❌ Error"
        message = f"Single artist downflow failed: {str(e)}"
        telegram.send_error("Single artist downflow failed", str(e))
    
    # Send notification
    send_notification_via_file(title, message, "/tmp/spotify_single_artist_downflow_result.txt")
    print(f"{title}\n{message}")
    
    return title, message


def main():
    """Entry point for command-line use."""
    return run_action()


if __name__ == "__main__":
    main()
