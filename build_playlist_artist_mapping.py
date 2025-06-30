#!/usr/bin/env python3
"""
Build playlist → artists mapping from playlist data.

Creates a consolidated mapping similar to playlist_to_genres.json
but focused on artist frequency data for each playlist.
"""

import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any

def build_playlist_artist_mapping():
    """Build mapping from playlist IDs to their top artists."""
    print("🎵 Building Playlist → Artists Mapping")
    print("=" * 50)
    
    # Load existing playlist_to_genres to get playlist IDs
    genres_file = Path('./_data/playlist_to_genres.json')
    if not genres_file.exists():
        print("❌ No playlist_to_genres.json found")
        return
    
    with open(genres_file, 'r') as f:
        playlist_to_genres = json.load(f)
    
    # Load individual playlist files
    playlists_dir = Path('./_data/playlists')
    if not playlists_dir.exists():
        print("❌ No playlists directory found")
        return
    
    print(f"📊 Found {len(playlist_to_genres)} playlists to process")
    
    playlist_to_artists = {}
    
    for playlist_id, playlist_info in playlist_to_genres.items():
        playlist_name = playlist_info.get('playlist_name', '')
        if not playlist_name:
            continue
        
        # Find corresponding playlist data file
        playlist_file = playlists_dir / f"{playlist_name}.json"
        if not playlist_file.exists():
            print(f"   ⚠️  Playlist data not found: {playlist_name}")
            continue
        
        try:
            with open(playlist_file, 'r') as f:
                playlist_data = json.load(f)
            
            tracks = playlist_data.get('tracks', [])
            print(f"   📀 {playlist_name}: {len(tracks)} tracks")
            
            # Count artists in this playlist
            artist_counts = Counter()
            total_tracks = 0
            
            for track_data in tracks:
                artists = track_data.get('artists', [])
                if artists:
                    total_tracks += 1
                    for artist in artists:
                        artist_name = artist.get('name')
                        if artist_name:
                            artist_counts[artist_name] += 1
            
            # Get top artists (limit to top 50 to keep file size manageable)
            top_artists = dict(artist_counts.most_common(50))
            
            # Calculate artist frequencies as percentages
            artist_frequencies = {}
            if total_tracks > 0:
                for artist, count in top_artists.items():
                    artist_frequencies[artist] = {
                        'count': count,
                        'frequency': round(count / total_tracks, 3)
                    }
            
            playlist_to_artists[playlist_id] = {
                'playlist_name': playlist_name,
                'total_tracks': total_tracks,
                'unique_artists': len(artist_counts),
                'top_artists': artist_frequencies,
                'most_frequent_artist': artist_counts.most_common(1)[0] if artist_counts else None
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {playlist_name}: {e}")
            continue
    
    print(f"\n✅ Successfully processed {len(playlist_to_artists)} playlists")
    
    # Save the mapping
    output_file = Path('./_data/playlist_to_artists.json')
    with open(output_file, 'w') as f:
        json.dump(playlist_to_artists, f, indent=2)
    
    print(f"💾 Saved playlist → artists mapping to: {output_file}")
    
    # Show some stats
    print(f"\n📈 MAPPING STATISTICS")
    print("=" * 30)
    
    total_unique_artists = set()
    artist_playlist_counts = Counter()
    
    for playlist_data in playlist_to_artists.values():
        for artist in playlist_data['top_artists'].keys():
            total_unique_artists.add(artist)
            artist_playlist_counts[artist] += 1
    
    print(f"📊 Total unique artists: {len(total_unique_artists)}")
    print(f"📊 Average artists per playlist: {sum(len(p['top_artists']) for p in playlist_to_artists.values()) / len(playlist_to_artists):.1f}")
    
    # Show most frequent cross-playlist artists
    print(f"\n🔄 MOST CROSS-PLAYLIST ARTISTS:")
    for artist, playlist_count in artist_playlist_counts.most_common(10):
        print(f"   {artist:25} → {playlist_count:2} playlists")
    
    return playlist_to_artists

if __name__ == "__main__":
    build_playlist_artist_mapping()