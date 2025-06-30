#!/usr/bin/env python3
"""
Debug script to test classification on specific tracks.
"""

from common.genre_classification_utils import (
    classify_track, 
    get_safe_spotify_client,
    get_artist_genres,
    get_audio_features,
    get_default_genre_mapping
)

def debug_classification():
    """Debug the classification process."""
    client = get_safe_spotify_client()
    if not client:
        print("❌ No client available")
        return
    
    # Test track from Electronic folder
    electronic_playlists = client.get_folder_playlists('Electronic')
    tracks = client.playlist_tracks(electronic_playlists[0]['id'], limit=1)
    track = tracks['items'][0]
    
    track_id = track['id']
    track_name = track['name']
    
    print(f"🎵 Testing: {track_name}")
    print(f"🆔 Track ID: {track_id}")
    print(f"📁 Expected: Electronic")
    
    # Check genre mapping
    mapping = get_default_genre_mapping()
    print(f"\n📊 Available folders: {list(mapping.keys())}")
    
    # Test step by step
    print(f"\n🔍 Step-by-step analysis:")
    
    # 1. Artist genres
    artist_genres = get_artist_genres(client, track_id)
    print(f"   🎤 Artist genres: {artist_genres}")
    
    # 2. Audio features
    audio_features = get_audio_features(client, track_id)
    if audio_features:
        relevant_features = {k: v for k, v in audio_features.items() 
                           if k in ['danceability', 'energy', 'valence', 'acousticness', 'instrumentalness']}
        print(f"   🎶 Audio features: {relevant_features}")
    else:
        print(f"   🎶 Audio features: None")
    
    # 3. Final classification
    print(f"\n🎯 Calling classify_track...")
    classification = classify_track(track_id=track_id)
    print(f"   Result: {classification}")
    
    # Test why Electronic/Rave/Vibes always match
    print(f"\n🔍 Analyzing Electronic folder mapping:")
    electronic_config = mapping.get('Electronic', {})
    electronic_genres = electronic_config.get('genres', [])
    print(f"   Electronic genres ({len(electronic_genres)}): {electronic_genres[:10]}...")
    
    # Check if any artist genres match Electronic
    if artist_genres:
        matches = []
        for artist_genre in artist_genres:
            for electronic_genre in electronic_genres:
                if electronic_genre in artist_genre or artist_genre in electronic_genre:
                    matches.append((artist_genre, electronic_genre))
        print(f"   Genre matches: {matches}")
    
    # Check audio features for Electronic
    electronic_audio = electronic_config.get('audio_features', {})
    print(f"   Electronic audio conditions: {electronic_audio}")
    
    if audio_features and electronic_audio:
        for feature, condition in electronic_audio.items():
            if feature in audio_features:
                value = audio_features[feature]
                print(f"   {feature}: {value} vs {condition}")

if __name__ == "__main__":
    debug_classification()