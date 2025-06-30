#!/usr/bin/env python3
"""
Analyze over-classification in the genre system.
"""

from common.genre_classification_utils import (
    get_safe_spotify_client,
    get_default_genre_mapping,
    get_artist_genres,
    get_audio_features,
    classify_by_genres,
    classify_by_audio_features
)

def analyze_overclassification():
    """Analyze why tracks are getting classified to too many categories."""
    client = get_safe_spotify_client()
    if not client:
        print("❌ No client available")
        return
    
    # Get genre mapping
    mapping = get_default_genre_mapping()
    
    # Test one track from each major category
    test_cases = [
        ('Electronic', 'Expected to be clearly Electronic'),
        ('Base', 'Expected to be clearly Bass music'),
        ('House', 'Expected to be clearly House'),
        ('Rock', 'Expected to be clearly Rock'),
        ('Sierra', 'Expected to be clearly Acoustic/Country')
    ]
    
    for folder, description in test_cases:
        print(f"\n" + "="*60)
        print(f"📁 Testing {folder} - {description}")
        print("="*60)
        
        # Get a track from this folder
        playlists = client.get_folder_playlists(folder)
        if not playlists:
            print(f"No playlists found for {folder}")
            continue
            
        tracks = client.playlist_tracks(playlists[0]['id'], limit=1)
        if not tracks['items']:
            print(f"No tracks found in {playlists[0]['name']}")
            continue
            
        track = tracks['items'][0]
        track_id = track['id']
        track_name = track['name']
        
        print(f"🎵 Track: {track_name}")
        
        # Get artist genres and audio features
        artist_genres = get_artist_genres(client, track_id)
        audio_features = get_audio_features(client, track_id)
        
        print(f"🎤 Artist genres: {artist_genres}")
        if audio_features:
            relevant_features = {k: v for k, v in audio_features.items() 
                               if k in ['danceability', 'energy', 'valence', 'acousticness', 'instrumentalness']}
            print(f"🎶 Audio features: {relevant_features}")
        
        # Test genre-based classification
        genre_matches = classify_by_genres(artist_genres, mapping)
        print(f"🏷️  Genre matches: {genre_matches}")
        
        # Test audio feature classification  
        if audio_features:
            audio_matches = classify_by_audio_features(audio_features, mapping)
            print(f"🎵 Audio matches: {audio_matches}")
        
        # Show which folders this track's genres appear in
        print(f"\n🔍 Analyzing why each folder matches:")
        for match in set(genre_matches + (audio_matches if audio_features else [])):
            print(f"\n   📂 {match}:")
            
            # Check genre matches
            folder_genres = [g.lower() for g in mapping[match].get('genres', [])]
            for artist_genre in artist_genres:
                for folder_genre in folder_genres:
                    if folder_genre in artist_genre or artist_genre in folder_genre:
                        print(f"      🎤 Genre: '{artist_genre}' matches '{folder_genre}'")
            
            # Check audio feature matches
            if audio_features:
                folder_audio = mapping[match].get('audio_features', {})
                for feature, condition in folder_audio.items():
                    if feature in audio_features:
                        value = audio_features[feature]
                        from common.genre_classification_utils import evaluate_audio_feature_condition
                        meets_condition = evaluate_audio_feature_condition(value, condition)
                        status = "✅" if meets_condition else "❌"
                        print(f"      🎶 Audio: {feature} = {value:.2f} vs {condition} {status}")

if __name__ == "__main__":
    analyze_overclassification()