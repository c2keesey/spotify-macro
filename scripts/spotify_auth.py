#!/usr/bin/env python3
"""
Unified Spotify authentication for SSH environments.
Creates a master auth cache that all automations can share.
"""

import os
import sys
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from common.config import CURRENT_ENV, CLIENT_ID, CLIENT_SECRET
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def get_master_cache_path():
    """Get path to master auth cache that all automations will share."""
    return PROJECT_ROOT / "common" / f".spotify_master_cache_{CURRENT_ENV}"


def get_all_scopes():
    """Get superset of all scopes needed by any automation."""
    return " ".join([
        # Core user access
        "user-read-private",
        
        # Library management (save_current, daily_liked)
        "user-library-read",
        "user-library-modify", 
        "user-read-currently-playing",
        
        # Playlist management (playlist_flow, genre_classification)
        "playlist-read-private",
        "playlist-read-collaborative", 
        "playlist-modify-private",
        "playlist-modify-public",
        
        # Future-proofing for potential features
        "user-top-read",
        "user-read-recently-played"
    ])


def ssh_friendly_auth():
    """
    SSH-friendly authentication flow.
    Prints URLs clearly and accepts manual input.
    """
    cache_path = get_master_cache_path()
    scopes = get_all_scopes()
    
    print("🔐 Spotify Authentication for SSH Environment")
    print("=" * 50)
    print(f"Environment: {CURRENT_ENV}")
    print(f"Cache file: {cache_path}")
    print(f"Scopes: {scopes}")
    print()
    
    # Check if we have valid cached credentials
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                token_info = json.load(f)
            
            # Create auth manager to test/refresh token
            auth_manager = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri="http://127.0.0.1:8889/callback",
                scope=scopes,
                cache_path=str(cache_path)
            )
            
            # Try to get valid token (will refresh if needed)
            token = auth_manager.get_access_token(as_dict=False)
            if token:
                print("✅ Found valid cached credentials!")
                
                # Test the token
                sp = spotipy.Spotify(auth=token)
                user = sp.current_user()
                print(f"✅ Authenticated as: {user['display_name']} ({user['id']})")
                print("✅ No re-authentication needed!")
                return True
                
        except Exception as e:
            print(f"⚠️  Cached credentials invalid: {e}")
            print("Need to re-authenticate...")
    
    print()
    print("🌐 Manual OAuth Flow for SSH")
    print("-" * 30)
    
    # Create auth manager
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8889/callback",
        scope=scopes,
        cache_path=str(cache_path)
    )
    
    # Get authorization URL
    auth_url = auth_manager.get_authorize_url()
    
    print("STEP 1: Open this URL in your LOCAL browser:")
    print()
    print("🔗 " + auth_url)
    print()
    print("STEP 2: After authorizing, you'll be redirected to a URL like:")
    print("   http://127.0.0.1:8889/callback?code=AQ...")
    print()
    print("STEP 3: Copy and paste that ENTIRE redirect URL below:")
    print()
    
    # Get callback URL from user
    while True:
        try:
            callback_url = input("Paste the callback URL here: ").strip()
            
            if not callback_url.startswith("http://127.0.0.1:8889/callback?code="):
                print("❌ Invalid URL format. Should start with 'http://127.0.0.1:8889/callback?code='")
                continue
            
            # Extract code from URL
            parsed_url = urlparse(callback_url)
            code = parse_qs(parsed_url.query).get('code', [None])[0]
            
            if not code:
                print("❌ No authorization code found in URL")
                continue
            
            print(f"📝 Found authorization code: {code[:20]}...")
            
            # Exchange code for token
            print("🔄 Exchanging code for access token...")
            token_info = auth_manager.get_access_token(code)
            
            if token_info:
                print("✅ Successfully obtained access token!")
                
                # Test the token
                sp = spotipy.Spotify(auth=token_info['access_token'])
                user = sp.current_user()
                print(f"✅ Authenticated as: {user['display_name']} ({user['id']})")
                
                # Ensure cache file has correct permissions
                cache_path.chmod(0o600)
                print(f"✅ Saved credentials to: {cache_path}")
                print("✅ All automations can now use these credentials!")
                
                return True
            else:
                print("❌ Failed to get access token")
                return False
                
        except KeyboardInterrupt:
            print("\n❌ Authentication cancelled")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again with the correct callback URL")


def test_authentication():
    """Test that authentication works with the master cache."""
    cache_path = get_master_cache_path()
    
    if not cache_path.exists():
        print("❌ No master cache found. Run authentication first.")
        return False
    
    try:
        # Test with the master cache
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:8889/callback",
            scope=get_all_scopes(),
            cache_path=str(cache_path)
        )
        
        token = auth_manager.get_access_token(as_dict=False)
        if token:
            sp = spotipy.Spotify(auth=token)
            user = sp.current_user()
            playlists = sp.current_user_playlists(limit=5)
            
            print("✅ Authentication test successful!")
            print(f"   User: {user['display_name']} ({user['id']})")
            print(f"   Playlists: {playlists['total']} total")
            return True
        else:
            print("❌ Could not get valid token")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "auth":
            success = ssh_friendly_auth()
            sys.exit(0 if success else 1)
            
        elif command == "test":
            success = test_authentication()
            sys.exit(0 if success else 1)
            
        elif command == "status":
            cache_path = get_master_cache_path()
            print(f"Environment: {CURRENT_ENV}")
            print(f"Cache path: {cache_path}")
            print(f"Cache exists: {cache_path.exists()}")
            if cache_path.exists():
                import time
                mtime = cache_path.stat().st_mtime
                print(f"Cache modified: {time.ctime(mtime)}")
                success = test_authentication()
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: auth, test, status")
    else:
        print("Unified Spotify Authentication")
        print("Usage: python scripts/spotify_auth.py <command>")
        print()
        print("Commands:")
        print("  auth    - Run SSH-friendly authentication flow")
        print("  test    - Test existing authentication")  
        print("  status  - Show authentication status")
        print()
        print("Examples:")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py test")