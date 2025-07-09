#!/usr/bin/env python3
"""
Quick search script to find which playlists contain specific tracks.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.playlist_data_utils import PlaylistDataLoader


def find_track_in_playlists(track_name: str, artist_name: str = None):
    """Find which playlists contain a specific track."""
    print(f"🔍 Searching for track: '{track_name}'" + (f" by {artist_name}" if artist_name else ""))
    
    # Load all playlist data
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory(
        include_empty=False,
        verbose=False
    )
    
    found_in_playlists = []
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data.get("name")
        tracks = playlist_data.get("tracks", [])
        
        for track in tracks:
            track_title = track.get("name", "").lower()
            track_artists = [artist.get("name", "") for artist in track.get("artists", [])]
            
            # Check if track name matches
            if track_name.lower() in track_title:
                # If artist specified, check if it matches
                if artist_name:
                    artist_match = any(artist_name.lower() in artist.lower() for artist in track_artists)
                    if not artist_match:
                        continue
                
                found_in_playlists.append({
                    "playlist": playlist_name,
                    "track": track.get("name"),
                    "artists": ", ".join(track_artists),
                    "track_count": len(tracks)
                })
    
    if found_in_playlists:
        print(f"✅ Found in {len(found_in_playlists)} playlist(s):")
        for result in found_in_playlists:
            print(f"   📋 '{result['playlist']}' ({result['track_count']} tracks)")
            print(f"      🎵 '{result['track']}' by {result['artists']}")
    else:
        print("❌ Track not found in any playlists")
    
    return found_in_playlists


def search_multiple_tracks():
    """Search for several tracks we saw in the automation output."""
    
    tracks_to_search = [
        ("M4verick", "Bravo Charlie"),
        ("OUTTA CONTROL", "COPYCATT"), 
        ("Dear Mr. Fantasy", "Traffic"),
        ("damn Right", "AUDREY NUNA"),
        ("The Girl From Ipanema", "João Gilberto"),
        ("Sunday Sketch", "Afternoon Bike Ride")
    ]
    
    print("🎵 Searching for tracks from single-playlist artists...\n")
    
    for track_name, artist_name in tracks_to_search:
        find_track_in_playlists(track_name, artist_name)
        print()  # Empty line between results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find tracks in playlists")
    parser.add_argument("--track", help="Track name to search for")
    parser.add_argument("--artist", help="Artist name (optional)")
    parser.add_argument("--multiple", action="store_true", help="Search for multiple example tracks")
    
    args = parser.parse_args()
    
    if args.multiple:
        search_multiple_tracks()
    elif args.track:
        find_track_in_playlists(args.track, args.artist)
    else:
        print("Usage:")
        print("  python find_track_in_playlists.py --track 'Track Name' --artist 'Artist Name'")
        print("  python find_track_in_playlists.py --multiple")