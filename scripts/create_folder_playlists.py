#!/usr/bin/env python3
"""
Create missing folder playlists for genre classification system.

This script creates folder playlists (with 📁 prefix) for each genre folder
defined in the system. It's idempotent - won't create duplicates if playlists
already exist.

Usage:
    SPOTIFY_ENV=prod uv run python scripts/create_folder_playlists.py
    SPOTIFY_ENV=test uv run python scripts/create_folder_playlists.py --dry-run
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
import argparse

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import CURRENT_ENV
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.constants import (
    FOLDER_PLAYLIST_PREFIX, 
    GENRE_FOLDERS, 
    FOLDER_PLAYLIST_DESCRIPTIONS
)


def get_existing_playlists(sp) -> Dict[str, Dict]:
    """
    Get all existing user playlists from Spotify API.
    
    Returns:
        Dictionary mapping playlist_name -> playlist_data
    """
    existing_playlists = {}
    
    print("📚 Fetching existing playlists...")
    
    # Get all user playlists (handle pagination)
    playlists = spotify_api_call_with_retry(sp.current_user_playlists, limit=50)
    
    while playlists:
        for playlist in playlists['items']:
            playlist_name = playlist['name']
            existing_playlists[playlist_name] = {
                'id': playlist['id'],
                'name': playlist_name,
                'description': playlist.get('description', ''),
                'public': playlist.get('public', False),
                'tracks_total': playlist['tracks']['total']
            }
        
        # Get next page if available
        if playlists['next']:
            playlists = spotify_api_call_with_retry(sp.next, playlists)
        else:
            break
    
    print(f"Found {len(existing_playlists)} existing playlists")
    return existing_playlists


def identify_missing_folder_playlists(existing_playlists: Dict[str, Dict]) -> List[str]:
    """
    Identify which folder playlists are missing.
    
    Args:
        existing_playlists: Dictionary of existing playlist names -> data
        
    Returns:
        List of folder names that need playlists created
    """
    missing_folders = []
    
    for folder in GENRE_FOLDERS:
        folder_playlist_name = f"{FOLDER_PLAYLIST_PREFIX} {folder}"
        
        if folder_playlist_name not in existing_playlists:
            missing_folders.append(folder)
        else:
            playlist_data = existing_playlists[folder_playlist_name]
            print(f"✅ Found existing: '{folder_playlist_name}' (ID: {playlist_data['id']}, {playlist_data['tracks_total']} tracks)")
    
    return missing_folders


def create_folder_playlist(sp, folder_name: str, dry_run: bool = False) -> Optional[str]:
    """
    Create a single folder playlist.
    
    Args:
        sp: Spotify client
        folder_name: Name of the folder (e.g., "House")
        dry_run: If True, don't actually create, just simulate
        
    Returns:
        Playlist ID if created successfully, None otherwise
    """
    folder_playlist_name = f"{FOLDER_PLAYLIST_PREFIX} {folder_name}"
    description = FOLDER_PLAYLIST_DESCRIPTIONS.get(folder_name, 
                                                 f"{folder_name} tracks automatically classified from the staging playlist")
    
    if dry_run:
        print(f"🧪 DRY RUN: Would create playlist '{folder_playlist_name}'")
        print(f"    Description: {description}")
        return "dry-run-playlist-id"
    
    try:
        # Get current user
        user = spotify_api_call_with_retry(sp.current_user)
        user_id = user['id']
        
        # Create the playlist
        playlist_response = spotify_api_call_with_retry(
            sp.user_playlist_create,
            user_id,
            folder_playlist_name,
            public=False,  # Private by default
            description=description
        )
        
        playlist_id = playlist_response['id']
        print(f"✅ Created playlist: '{folder_playlist_name}' (ID: {playlist_id})")
        
        return playlist_id
        
    except Exception as e:
        print(f"❌ Failed to create playlist '{folder_playlist_name}': {e}")
        return None


def create_missing_folder_playlists(dry_run: bool = False) -> Dict[str, str]:
    """
    Main function to create all missing folder playlists.
    
    Args:
        dry_run: If True, don't actually create playlists, just simulate
        
    Returns:
        Dictionary mapping folder_name -> playlist_id for created playlists
    """
    print(f"🎯 Creating missing folder playlists (Environment: {CURRENT_ENV})")
    print(f"📁 Folder prefix: '{FOLDER_PLAYLIST_PREFIX}'")
    print(f"📂 Target folders: {', '.join(GENRE_FOLDERS)}")
    
    if dry_run:
        print("🧪 DRY RUN MODE - No actual changes will be made")
    
    print()
    
    # Initialize Spotify client
    scope = "playlist-modify-private playlist-modify-public playlist-read-private"
    sp = initialize_spotify_client(scope)
    
    # Get existing playlists
    existing_playlists = get_existing_playlists(sp)
    
    # Identify missing folder playlists
    missing_folders = identify_missing_folder_playlists(existing_playlists)
    
    if not missing_folders:
        print("🎉 All folder playlists already exist!")
        return {}
    
    print(f"\n📝 Need to create {len(missing_folders)} folder playlists:")
    for folder in missing_folders:
        folder_playlist_name = f"{FOLDER_PLAYLIST_PREFIX} {folder}"
        print(f"  • {folder_playlist_name}")
    
    print()
    
    # Create missing playlists
    created_playlists = {}
    
    for folder in missing_folders:
        playlist_id = create_folder_playlist(sp, folder, dry_run=dry_run)
        if playlist_id:
            created_playlists[folder] = playlist_id
    
    # Summary
    if created_playlists:
        print(f"\n🎉 Successfully created {len(created_playlists)} folder playlists:")
        for folder, playlist_id in created_playlists.items():
            folder_playlist_name = f"{FOLDER_PLAYLIST_PREFIX} {folder}"
            if dry_run:
                print(f"  • {folder_playlist_name} (dry run)")
            else:
                print(f"  • {folder_playlist_name} (ID: {playlist_id})")
    else:
        if missing_folders:
            print(f"\n❌ Failed to create any of the {len(missing_folders)} missing playlists")
        else:
            print(f"\n✅ No playlists needed to be created")
    
    return created_playlists


def main():
    """Entry point for command-line use."""
    parser = argparse.ArgumentParser(description="Create missing folder playlists for genre classification")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be created without actually creating playlists")
    
    args = parser.parse_args()
    
    try:
        created_playlists = create_missing_folder_playlists(dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\n🧪 Dry run complete - {len(created_playlists)} playlists would be created")
        else:
            print(f"\n✅ Operation complete - {len(created_playlists)} playlists created")
            
    except Exception as e:
        print(f"\n❌ Error during folder playlist creation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()