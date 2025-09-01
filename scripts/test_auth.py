#!/usr/bin/env python3
"""Test Spotify authentication."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.spotify_utils import initialize_spotify_client

def test_auth():
    try:
        print("Testing Spotify authentication...")
        sp = initialize_spotify_client('playlist-read-private', 'test_auth')
        print("✅ Auth successful")
        
        user = sp.current_user()
        print(f"✅ User: {user['display_name']}")
        
        return True
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return False

if __name__ == "__main__":
    test_auth()