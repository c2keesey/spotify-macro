#!/usr/bin/env python3
"""
Create folder playlists in Spotify test account.
This script reads the folder mapping and creates empty playlists named after each folder.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry

# Required scopes for creating playlists
SCOPE = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_folder_mapping() -> Dict[str, List[str]]:
    """Load the playlist folder mapping file."""
    folder_mapping_path = Path(__file__).parent.parent / "data" / "playlist_folders.json"
    
    if not folder_mapping_path.exists():
        logging.error(f"Folder mapping file not found: {folder_mapping_path}")
        return {}
    
    try:
        with open(folder_mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading folder mapping: {e}")
        return {}


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


def create_folder_playlist(sp, folder_name: str, playlist_count: int) -> Optional[str]:
    """Create an empty folder playlist."""
    try:
        # Get current user info
        user_info = spotify_api_call_with_retry(sp.current_user)
        user_id = user_info['id']
        
        # Create playlist with folder name
        description = f"📁 Folder playlist for {folder_name} - Contains {playlist_count} playlists"
        playlist = spotify_api_call_with_retry(
            sp.user_playlist_create,
            user_id,
            f"📁 {folder_name}",  # Prefix with folder emoji
            public=False,
            description=description
        )
        
        playlist_id = playlist['id']
        logging.info(f"Created folder playlist '📁 {folder_name}' (ID: {playlist_id})")
        
        return playlist_id
        
    except Exception as e:
        logging.error(f"Error creating folder playlist '{folder_name}': {e}")
        return None


def main():
    """Main function to create folder playlists."""
    
    # Initialize Spotify client
    try:
        sp = initialize_spotify_client(SCOPE)
        logging.info("Successfully initialized Spotify client")
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)
    
    # Load folder mapping
    folder_mapping = load_folder_mapping()
    if not folder_mapping:
        logging.error("No folder mapping found")
        sys.exit(1)
    
    logging.info(f"Found {len(folder_mapping)} folders to create")
    
    # Get existing playlists to avoid duplicates
    existing_playlists = get_existing_playlists(sp)
    logging.info(f"Found {len(existing_playlists)} existing playlists in test account")
    
    # Process each folder
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for folder_name, playlist_files in tqdm(folder_mapping.items(), desc="Creating folder playlists"):
        folder_playlist_name = f"📁 {folder_name}"
        playlist_count = len(playlist_files)
        
        # Check if folder playlist already exists
        if folder_playlist_name in existing_playlists:
            logging.info(f"Folder playlist '{folder_playlist_name}' already exists - skipping")
            skipped_count += 1
            continue
        
        # Create folder playlist
        playlist_id = create_folder_playlist(sp, folder_name, playlist_count)
        if playlist_id:
            created_count += 1
            logging.info(f"Successfully created folder playlist '{folder_playlist_name}' for {playlist_count} playlists")
        else:
            error_count += 1
    
    # Summary
    logging.info(f"Folder playlist creation complete!")
    logging.info(f"Created: {created_count}")
    logging.info(f"Skipped: {skipped_count}")
    logging.info(f"Errors: {error_count}")
    logging.info(f"Total folders: {len(folder_mapping)}")


def delete_folder_playlists():
    """Delete all folder playlists (those starting with 📁)."""
    logging.info("Deleting all folder playlists...")
    
    try:
        sp = initialize_spotify_client(SCOPE)
        logging.info("Successfully initialized Spotify client")
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)
    
    # Get existing playlists
    existing_playlists = get_existing_playlists(sp)
    
    # Filter for folder playlists
    folder_playlists = {name: playlist_id for name, playlist_id in existing_playlists.items() 
                       if name.startswith("📁")}
    
    if not folder_playlists:
        logging.info("No folder playlists found to delete")
        return
    
    logging.info(f"Found {len(folder_playlists)} folder playlists to delete")
    
    # Delete each folder playlist
    deleted_count = 0
    for playlist_name, playlist_id in tqdm(folder_playlists.items(), desc="Deleting folder playlists"):
        try:
            spotify_api_call_with_retry(sp.current_user_unfollow_playlist, playlist_id)
            logging.info(f"Deleted folder playlist '{playlist_name}' (ID: {playlist_id})")
            deleted_count += 1
        except Exception as e:
            logging.error(f"Error deleting folder playlist '{playlist_name}': {e}")
    
    logging.info(f"Deleted {deleted_count} folder playlists")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create folder playlists in Spotify test account")
    parser.add_argument("--delete", action="store_true", help="Delete all existing folder playlists")
    
    args = parser.parse_args()
    
    print("📁 Folder Playlist Creator")
    print("Creates empty playlists named after each folder in your mapping")
    print("Features:")
    print("  ✅ Creates one playlist per folder with 📁 prefix")
    print("  ✅ Includes folder stats in description")
    print("  ✅ Skips existing folder playlists")
    print("  ✅ Handles rate limits gracefully")
    print()
    
    if args.delete:
        delete_folder_playlists()
    else:
        main()