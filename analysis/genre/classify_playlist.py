#!/usr/bin/env python3
"""
Script to classify all tracks in a specific playlist and save results to JSON.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

from common.spotify_utils import initialize_spotify_client
from common.genre_classification_utils import classify_track, get_genre_mapping


def classify_playlist_tracks(playlist_name: str, output_file: str = None, sample_size: int = None) -> Dict[str, Any]:
    """
    Classify all tracks in a playlist using existing JSON data for testing.
    
    Args:
        playlist_name: Name of the playlist to classify
        output_file: Optional output file path for JSON results
        sample_size: Optional limit on number of tracks to classify (for testing)
        
    Returns:
        Dictionary with classification results
    """
    # Load playlist data from JSON file
    data_dir = Path("_data/playlists")
    playlist_file = data_dir / f"{playlist_name}.json"
    
    if not playlist_file.exists():
        raise ValueError(f"Playlist data file not found: {playlist_file}")
    
    print(f"📁 Loading playlist data from: {playlist_file}")
    
    with open(playlist_file, 'r') as f:
        playlist_data = json.load(f)
    
    playlist_id = playlist_data.get('playlist_id')
    total_tracks = playlist_data.get('total_tracks_fetched', 0)
    
    print(f"✅ Found playlist: {playlist_name} (ID: {playlist_id})")
    
    # Extract tracks from JSON data
    tracks = []
    for item in playlist_data.get('tracks', []):
        # The track data is directly in the item, not nested under 'track_info'
        if item.get('id'):
            tracks.append({
                'id': item['id'],
                'name': item['name'],
                'artist': item['artists'][0]['name'] if item.get('artists') else 'Unknown',
                'uri': item['uri']
            })
    
    # Limit tracks if sample_size is specified
    if sample_size and len(tracks) > sample_size:
        tracks = tracks[:sample_size]
        print(f"📊 Using sample of {len(tracks)} tracks (limited from {total_tracks})")
    else:
        print(f"📊 Found {len(tracks)} tracks to classify")
    
    # Set up Spotify client for classification
    scope = "playlist-read-private playlist-read-collaborative"
    sp = initialize_spotify_client(scope, "playlist_classifier_cache")
    
    # Get genre mapping
    genre_mapping = get_genre_mapping(sp, use_dynamic=True)
    
    # Classify each track
    classification_results = {
        'playlist_name': playlist_name,
        'playlist_id': playlist_id,
        'total_tracks': len(tracks),
        'genre_mapping': genre_mapping,
        'tracks': [],
        'genre_summary': {}
    }
    
    for i, track in enumerate(tracks, 1):
        print(f"🎵 Classifying {i}/{len(tracks)}: {track['name']} by {track['artist']}")
        
        try:
            classifications = classify_track(sp, track['id'], genre_mapping)
            
            track_result = {
                'track_info': track,
                'classifications': classifications,
                'classification_count': len(classifications)
            }
            
            classification_results['tracks'].append(track_result)
            
            # Update genre summary
            for genre in classifications:
                if genre not in classification_results['genre_summary']:
                    classification_results['genre_summary'][genre] = 0
                classification_results['genre_summary'][genre] += 1
            
            if not classifications:
                if 'Unclassified' not in classification_results['genre_summary']:
                    classification_results['genre_summary']['Unclassified'] = 0
                classification_results['genre_summary']['Unclassified'] += 1
                
        except Exception as e:
            print(f"❌ Error classifying {track['name']}: {e}")
            track_result = {
                'track_info': track,
                'classifications': [],
                'classification_count': 0,
                'error': str(e)
            }
            classification_results['tracks'].append(track_result)
    
    # Sort genre summary by count
    classification_results['genre_summary'] = dict(
        sorted(classification_results['genre_summary'].items(), 
               key=lambda x: x[1], reverse=True)
    )
    
    # Save to file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(classification_results, f, indent=2)
        
        print(f"💾 Results saved to: {output_path}")
    
    return classification_results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python classify_playlist.py <playlist_name> [output_file] [sample_size]")
        sys.exit(1)
    
    playlist_name = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    sample_size = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    # Default output file if not specified
    if not output_file:
        safe_name = playlist_name.replace(' ', '_').replace('/', '_')
        sample_suffix = f"_sample{sample_size}" if sample_size else ""
        output_file = f"_data/classified_{safe_name}{sample_suffix}.json"
    
    try:
        results = classify_playlist_tracks(playlist_name, output_file, sample_size)
        
        print("\n📈 Classification Summary:")
        print(f"Total tracks: {results['total_tracks']}")
        print(f"Genres found: {len(results['genre_summary'])}")
        print("\nGenre breakdown:")
        for genre, count in results['genre_summary'].items():
            percentage = (count / results['total_tracks']) * 100
            print(f"  {genre}: {count} tracks ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()