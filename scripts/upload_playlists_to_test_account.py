#!/usr/bin/env python3
"""
Upload playlists from local JSON data to Spotify testing account.
This script reads playlist data from data/playlists/ and recreates them in the test account.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from tqdm import tqdm

from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.playlist_data_utils import PlaylistDataLoader

# Required scopes for creating and modifying playlists
SCOPE = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_folder_mapping() -> Dict[str, List[str]]:
    """Load the playlist folder mapping file."""
    folder_mapping_path = Path(__file__).parent.parent / "data" / "playlist_folders.json"
    
    if not folder_mapping_path.exists():
        logging.warning(f"Folder mapping file not found: {folder_mapping_path}")
        return {}
    
    try:
        with open(folder_mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading folder mapping: {e}")
        return {}


def get_playlists_to_upload(playlists_dict: Dict[str, Dict], folder_mapping: Dict[str, List[str]]) -> Set[str]:
    """Determine which playlists should be uploaded based on folder mapping and the 'New' playlist."""
    playlists_to_upload = set()
    
    # Get all playlists from folder mapping
    for folder_name, playlist_files in folder_mapping.items():
        for playlist_file in playlist_files:
            # Convert filename to playlist name (remove .json extension)
            playlist_name = playlist_file.replace('.json', '')
            playlists_to_upload.add(playlist_name)
    
    # Add the special 'New' playlist if it exists
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data.get('name', '')
        if playlist_name == 'New':
            playlists_to_upload.add(playlist_name)
            logging.info("Found the special 'New' playlist - adding to upload list")
    
    logging.info(f"Found {len(playlists_to_upload)} playlists to upload based on folder mapping and the 'New' playlist")
    return playlists_to_upload


def extract_track_uris(playlist_data: Dict) -> List[str]:
    """Extract Spotify track URIs from normalized playlist data."""
    track_uris = []
    
    # Use the normalized track data from PlaylistDataLoader
    for track in playlist_data.get('tracks', []):
        # Construct Spotify URI from track ID
        track_id = track.get('id')
        if track_id:
            track_uris.append(f"spotify:track:{track_id}")
    
    return track_uris


def get_playlist_track_count(sp, playlist_id: str) -> int:
    """Get the current track count of a playlist."""
    try:
        playlist_info = spotify_api_call_with_retry(sp.playlist, playlist_id, fields="tracks.total")
        return playlist_info.get('tracks', {}).get('total', 0)
    except Exception as e:
        logging.error(f"Error getting track count for playlist {playlist_id}: {e}")
        return 0


def playlist_needs_update(sp, playlist_id: str, expected_track_count: int) -> bool:
    """Check if a playlist needs to be updated based on track count."""
    current_track_count = get_playlist_track_count(sp, playlist_id)
    return current_track_count != expected_track_count


def update_playlist(sp, playlist_id: str, playlist_name: str, track_uris: List[str]) -> bool:
    """Update an existing playlist by replacing all its tracks."""
    try:
        # Clear existing tracks
        logging.info(f"Clearing existing tracks from '{playlist_name}'")
        
        # Get current tracks to remove them
        current_tracks = []
        results = spotify_api_call_with_retry(sp.playlist_tracks, playlist_id, limit=100)
        
        while results:
            for item in results['items']:
                if item['track'] and item['track']['id']:
                    current_tracks.append(item['track']['uri'])
            
            if results['next']:
                results = spotify_api_call_with_retry(sp.next, results)
            else:
                break
        
        # Remove tracks in batches
        if current_tracks:
            batch_size = 100
            for i in range(0, len(current_tracks), batch_size):
                batch = current_tracks[i:i + batch_size]
                spotify_api_call_with_retry(sp.playlist_remove_all_occurrences_of_items, playlist_id, batch)
        
        # Add new tracks
        if track_uris:
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                spotify_api_call_with_retry(sp.playlist_add_items, playlist_id, batch)
        
        logging.info(f"Updated playlist '{playlist_name}' with {len(track_uris)} tracks")
        return True
        
    except Exception as e:
        logging.error(f"Error updating playlist '{playlist_name}': {e}")
        return False


def create_playlist_in_test_account(sp, playlist_name: str, track_uris: List[str], description: str = None) -> Optional[str]:
    """Create a playlist in the test account and add tracks."""
    try:
        # Get current user info
        user_info = spotify_api_call_with_retry(sp.current_user)
        user_id = user_info['id']
        
        # Create playlist
        playlist_description = description or f"Copied from production account - {len(track_uris)} tracks"
        playlist = spotify_api_call_with_retry(
            sp.user_playlist_create,
            user_id,
            playlist_name,
            public=False,
            description=playlist_description
        )
        
        playlist_id = playlist['id']
        logging.info(f"Created playlist '{playlist_name}' (ID: {playlist_id})")
        
        # Add tracks in batches (Spotify API limit is 100 tracks per request)
        if track_uris:
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                try:
                    spotify_api_call_with_retry(
                        sp.playlist_add_items,
                        playlist_id,
                        batch
                    )
                    logging.info(f"Added {len(batch)} tracks to '{playlist_name}' (batch {i//batch_size + 1})")
                except Exception as e:
                    logging.error(f"Error adding tracks to '{playlist_name}': {e}")
                    continue
        
        return playlist_id
        
    except Exception as e:
        logging.error(f"Error creating playlist '{playlist_name}': {e}")
        return None


def get_existing_playlists(sp) -> Dict[str, str]:
    """Get existing playlists in the test account."""
    existing_playlists = {}
    
    try:
        # Get current user's playlists
        results = spotify_api_call_with_retry(sp.current_user_playlists, limit=50)
        
        while results:
            for playlist in results['items']:
                existing_playlists[playlist['name']] = playlist['id']
            
            if results['next']:
                results = spotify_api_call_with_retry(sp.next, results)
            else:
                break
                
    except Exception as e:
        logging.error(f"Error fetching existing playlists: {e}")
    
    return existing_playlists


def delete_playlist(sp, playlist_id: str, playlist_name: str) -> bool:
    """Delete a playlist (actually just unfollow it)."""
    try:
        spotify_api_call_with_retry(sp.current_user_unfollow_playlist, playlist_id)
        logging.info(f"Deleted playlist '{playlist_name}' (ID: {playlist_id})")
        return True
    except Exception as e:
        logging.error(f"Error deleting playlist '{playlist_name}': {e}")
        return False


def main():
    """Main function to upload playlists to test account."""
    
    # Initialize Spotify client
    try:
        sp = initialize_spotify_client(SCOPE)
        logging.info("Successfully initialized Spotify client")
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)
    
    # Load folder mapping to determine which playlists to upload
    folder_mapping = load_folder_mapping()
    if not folder_mapping:
        logging.error("No folder mapping found - cannot determine which playlists to upload")
        sys.exit(1)
    
    # Load playlist data using PlaylistDataLoader
    try:
        logging.info("Loading playlist data using PlaylistDataLoader...")
        playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
            include_empty=False,  # Skip empty playlists
            verbose=True
        )
        logging.info(f"Successfully loaded {len(playlists_dict)} playlists")
    except Exception as e:
        logging.error(f"Failed to load playlist data: {e}")
        sys.exit(1)
    
    if not playlists_dict:
        logging.error("No playlists found to upload")
        sys.exit(1)
    
    # Determine which playlists should be uploaded
    playlists_to_upload = get_playlists_to_upload(playlists_dict, folder_mapping)
    
    # Filter playlists_dict to only include ones we want to upload
    filtered_playlists = {}
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data.get('name')
        if playlist_name in playlists_to_upload:
            filtered_playlists[playlist_id] = playlist_data
    
    logging.info(f"Filtered to {len(filtered_playlists)} playlists that should be uploaded")
    
    # Get existing playlists
    existing_playlists = get_existing_playlists(sp)
    logging.info(f"Found {len(existing_playlists)} existing playlists in test account")
    
    # Process each playlist
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for playlist_id, playlist_data in tqdm(filtered_playlists.items(), desc="Processing playlists"):
        playlist_name = playlist_data.get('name')
        total_tracks = playlist_data.get('total_tracks', 0)
        
        # Skip empty playlists (should already be filtered, but double-check)
        if total_tracks == 0:
            logging.info(f"Skipping empty playlist: {playlist_name}")
            skipped_count += 1
            continue
        
        # Extract track URIs from normalized data
        track_uris = extract_track_uris(playlist_data)
        if not track_uris:
            logging.warning(f"No valid track URIs found in playlist: {playlist_name}")
            skipped_count += 1
            continue
        
        # Check if playlist already exists
        if playlist_name in existing_playlists:
            existing_playlist_id = existing_playlists[playlist_name]
            
            # Check if the playlist needs updating
            if playlist_needs_update(sp, existing_playlist_id, len(track_uris)):
                logging.info(f"Playlist '{playlist_name}' exists but needs updating")
                if update_playlist(sp, existing_playlist_id, playlist_name, track_uris):
                    updated_count += 1
                else:
                    error_count += 1
            else:
                logging.info(f"Playlist '{playlist_name}' already exists and is up to date - skipping")
                skipped_count += 1
        else:
            # Create new playlist
            new_playlist_id = create_playlist_in_test_account(sp, playlist_name, track_uris)
            if new_playlist_id:
                created_count += 1
                logging.info(f"Successfully created playlist '{playlist_name}' with {len(track_uris)} tracks")
            else:
                error_count += 1
    
    # Summary
    result_msg = f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}, Total: {len(filtered_playlists)}"
    logging.info(f"Upload complete!")
    logging.info(f"Created: {created_count}")
    logging.info(f"Updated: {updated_count}")
    logging.info(f"Skipped: {skipped_count}")
    logging.info(f"Errors: {error_count}")
    logging.info(f"Total processed: {len(filtered_playlists)}")
    
    return result_msg


def reset_test_account():
    """Delete all playlists in the test account."""
    logging.info("Resetting test account - deleting all playlists")
    
    try:
        sp = initialize_spotify_client(SCOPE)
        logging.info("Successfully initialized Spotify client")
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)
    
    # Get existing playlists
    existing_playlists = get_existing_playlists(sp)
    
    if not existing_playlists:
        logging.info("No playlists found to delete")
        return
    
    logging.info(f"Found {len(existing_playlists)} playlists to delete")
    
    # Delete each playlist
    deleted_count = 0
    for playlist_name, playlist_id in tqdm(existing_playlists.items(), desc="Deleting playlists"):
        if delete_playlist(sp, playlist_id, playlist_name):
            deleted_count += 1
    
    logging.info(f"Deleted {deleted_count} playlists")
    return f"Deleted {deleted_count} playlists"


def write_status_file(status: str, message: str = "", result_file: str = "/tmp/playlist_sync_result.txt"):
    """Write status to file for automation monitoring."""
    try:
        with open(result_file, 'w') as f:
            f.write(f"STATUS: {status}\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            if message:
                f.write(f"MESSAGE: {message}\n")
    except Exception as e:
        logging.error(f"Failed to write status file: {e}")


if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Smart playlist sync to Spotify test account")
    parser.add_argument("--reset", action="store_true", help="Reset test account by deleting all playlists first")
    parser.add_argument("--reset-only", action="store_true", help="Only reset test account, don't upload playlists")
    parser.add_argument("--quiet", action="store_true", help="Minimize output for automation")
    parser.add_argument("--status-file", default="/tmp/playlist_sync_result.txt", help="File to write completion status")
    
    args = parser.parse_args()
    
    # Write starting status
    write_status_file("STARTING", "Playlist sync initiated", args.status_file)
    
    if not args.quiet:
        print("🎵 Smart Playlist Sync Tool")
        print("Features:")
        print("  ✅ Only syncs playlists from folder mapping + the 'New' playlist")
        print("  ✅ Skips playlists already up to date")
        print("  ✅ Updates playlists that have changed")
        print("  ✅ Creates missing playlists")
        print("  ✅ Handles rate limits gracefully")
        print()
    
    try:
        if args.reset_only:
            reset_result = reset_test_account()
            write_status_file("COMPLETED", f"Test account reset completed. {reset_result}", args.status_file)
            if not args.quiet:
                print(f"✅ Test account reset completed. {reset_result}")
        elif args.reset:
            reset_result = reset_test_account()
            sync_result = main()
            combined_result = f"{reset_result}. {sync_result}"
            write_status_file("COMPLETED", f"Reset and sync completed. {combined_result}", args.status_file)
            if not args.quiet:
                print(f"✅ Reset and playlist sync completed. {combined_result}")
        else:
            result = main()
            write_status_file("COMPLETED", f"Playlist sync completed. {result}", args.status_file)
            if not args.quiet:
                print(f"✅ Playlist sync completed. {result}")
    except Exception as e:
        error_msg = f"Script failed: {str(e)}"
        write_status_file("FAILED", error_msg, args.status_file)
        logging.error(error_msg)
        if not args.quiet:
            print(f"❌ {error_msg}")
        sys.exit(1)