#!/usr/bin/env python3
"""
Test script for music API clients.
Tests Last.fm, GetSongBPM, and Deezer APIs with sample tracks.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from common.music_api_clients import MusicFeatureFetcher
from common.music_api_config import get_lastfm_api_key, get_getsongbpm_api_key, get_available_apis
import json

def test_apis():
    """Test the music API clients with sample tracks."""
    
    # Get API keys from environment
    lastfm_key = get_lastfm_api_key()
    getsongbpm_key = get_getsongbpm_api_key()
    available_apis = get_available_apis()
    
    print(f"🔑 Available APIs: {', '.join(available_apis)}")
    if lastfm_key:
        print("   ✅ Last.fm API key found")
    else:
        print("   ❌ Last.fm API key not found (set LASTFM_API_KEY env var)")
        
    if getsongbpm_key:
        print("   ✅ GetSongBPM API key found") 
    else:
        print("   ❌ GetSongBPM API key not found (set GETSONGBPM_API_KEY env var)")
    
    print("   ✅ Deezer API available (no key required)")
    
    # Initialize fetcher with available keys
    fetcher = MusicFeatureFetcher(lastfm_api_key=lastfm_key, getsongbpm_api_key=getsongbpm_key)
    
    # Test tracks from different genres
    test_tracks = [
        ("Skrillex", "Bangarang"),
        ("Deadmau5", "Ghosts 'n' Stuff"), 
        ("Porter Robinson", "Language"),
        ("Seven Lions", "Worlds Apart"),
        ("ODESZA", "Say My Name")
    ]
    
    print("🧪 TESTING MUSIC APIS")
    print("=" * 50)
    
    for artist, track in test_tracks:
        print(f"\n🎵 Testing: {artist} - {track}")
        print("-" * 40)
        
        # Test individual API results
        all_features = fetcher.get_all_features(artist, track, verbose=True)
        
        # Test combined features
        combined = fetcher.get_combined_features(artist, track)
        
        print(f"\n📊 Combined Features:")
        for key, value in combined.items():
            if value is not None and value != []:
                if key == 'tags':
                    print(f"  {key}: {value[:5]}{'...' if len(value) > 5 else ''}")
                else:
                    print(f"  {key}: {value}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    test_apis()