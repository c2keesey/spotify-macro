#!/usr/bin/env python3
"""
Test real-time genre fetching for unknown artists.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.playlist_data_utils import PlaylistDataLoader
from analysis.genre.composite_classifier import CompositeClassifier
import json

def test_realtime_genres():
    # Load data
    print('📁 Loading data...')
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()

    # Find New playlist and get a track with unknown artist
    new_playlist = None
    for pid, pdata in playlists_dict.items():
        if pdata.get('name') == 'New':
            new_playlist = pdata
            break

    if not new_playlist or not new_playlist.get('tracks'):
        print('❌ Could not find New playlist with tracks')
        return

    # Test multiple tracks with unknown artists
    test_tracks = [
        ('3yxE4Fhv4K1FoTPYoE9uDg', 'M4verick by Bravo Charlie'),
        ('1KY3su6yQ7pNiCqSGMZOOj', 'Silence by NVYKO'),  
        ('3KcDfeZ1UAMtun8TuvG1kT', 'Peak (Fed Up) by RAAHiiM')
    ]
    
    # Initialize classifier
    print('🧠 Initializing classifier...')
    classifier = CompositeClassifier()
    
    # Prepare training data
    with open('data/playlist_folders.json', 'r') as f:
        playlist_folders = json.load(f)
    
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    train_tracks = []
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data['name']
        if playlist_name in playlist_to_folder and playlist_name != 'New':
            folder_name = playlist_to_folder[playlist_name]
            for track in playlist_data['tracks']:
                train_tracks.append((track['id'], folder_name))
    
    train_data = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    print('🎓 Training classifier...')
    classifier.train(train_data)
    
    print('\n🆕 Testing real-time genre fetching on multiple unknown artists...')
    
    for test_track_id, description in test_tracks:
        print(f'\n📀 Testing: {description}')
        result = classifier.predict(test_track_id)
        print(f'   📁 Folders: {result.predicted_folders}')
        print(f'   📊 Confidence: {getattr(result, "confidence_scores", {})}')
        print(f'   💭 Reasoning: {result.reasoning}')
    
    # Check all fetched genre data
    print(f'\n📚 Summary of fetched genre data:')
    fetched_count = 0
    for artist_id, artist_data in classifier.artist_genres.items():
        if artist_data['genres']:  # Has non-empty genres
            fetched_count += 1
            print(f'   ✅ {artist_data["name"]}: {artist_data["genres"][:3]}{"..." if len(artist_data["genres"]) > 3 else ""}')
        elif 'name' in artist_data and artist_data['name'] not in ['Unknown']:
            print(f'   ❌ {artist_data["name"]}: (no genres)')
    
    print(f'\n📊 Artists with genres: {fetched_count} newly fetched + {len([a for a in classifier.artist_genres.values() if a.get("genres") and "name" in a])} total')

if __name__ == "__main__":
    test_realtime_genres()