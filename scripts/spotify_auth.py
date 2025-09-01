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
    # SSH-friendly: Use absolute path to avoid any path resolution issues
    cache_dir = PROJECT_ROOT / "common"
    cache_dir.mkdir(exist_ok=True)  # Ensure directory exists
    cache_path = cache_dir / f".spotify_master_cache_{CURRENT_ENV}"
    return cache_path


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


def ssh_friendly_auth(callback_url=None):
    """
    SSH-friendly authentication flow.
    Prints URLs clearly and accepts manual input or URL parameter.
    """
    cache_path = get_master_cache_path()
    scopes = get_all_scopes()
    
    print("🔐 Spotify Authentication for SSH Environment")
    print("=" * 50)
    print(f"Environment: {CURRENT_ENV}")
    print(f"Cache file: {cache_path}")
    print(f"Cache dir exists: {cache_path.parent.exists()}")
    print(f"Cache dir writable: {os.access(cache_path.parent, os.W_OK)}")
    print(f"Client ID: {CLIENT_ID[:8]}..." if CLIENT_ID else "❌ Missing CLIENT_ID")
    print(f"Client Secret: {'✅ Set' if CLIENT_SECRET else '❌ Missing CLIENT_SECRET'}")
    print(f"Scopes: {scopes}")
    print()
    
    # Check if we have valid cached credentials
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                token_info = json.load(f)
            
            # Create auth manager to test/refresh token
            redirect_uri = "http://127.0.0.1:8889/callback" if CURRENT_ENV == "test" else "http://127.0.0.1:8888/callback"
            auth_manager = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=redirect_uri,
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
    
    # Always use the configured redirect URI (matches your Spotify app settings)
    redirect_uri = "http://127.0.0.1:8889/callback" if CURRENT_ENV == "test" else "http://127.0.0.1:8888/callback"
    
    # Create auth manager
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=redirect_uri,
        scope=scopes,
        cache_path=str(cache_path)
    )
    
    # Get authorization URL
    auth_url = auth_manager.get_authorize_url()
    
    print("STEP 1: Open this URL in your browser (any device):")
    print()
    print("🔗 " + auth_url)
    print()
    print("STEP 2: After authorizing, you'll see a 'This site can't be reached' error.")
    print("        This is EXPECTED when using SSH! Don't worry.")
    print()
    print("STEP 3: Look at the URL in your browser's address bar. It will look like:")
    print(f"   {redirect_uri}?code=AQA...")
    print()
    print("STEP 4: Copy the 'code' parameter from that URL (the part after 'code=')")
    print("        Example: If URL is http://127.0.0.1:8889/callback?code=AQA123...")
    print("                 Copy: AQA123...")
    print()
    
    # If callback URL provided as parameter, use it directly
    if callback_url:
        print(f"📝 Using provided callback URL or code")
    else:
        print("STEP 5: Paste EITHER:")
        print("        - The full callback URL from your browser, OR")
        print("        - Just the authorization code (the part after 'code=')")
        print("(Or press Ctrl+C to exit and run with --url or --code parameter)")
        print()
    
    # Get callback URL from user or parameter
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            if not callback_url:
                try:
                    user_input = input("Paste callback URL or authorization code: ").strip()
                    callback_url = user_input
                except (EOFError, KeyboardInterrupt):
                    print("\n💡 TIP: You can also run this script with a callback URL or code:")
                    print(f"   SPOTIFY_ENV={CURRENT_ENV} uv run python scripts/spotify_auth.py auth --url '<callback_url>'")
                    print(f"   SPOTIFY_ENV={CURRENT_ENV} uv run python scripts/spotify_auth.py auth --code '<auth_code>'")
                    return False
            
            # Handle both full URLs and just authorization codes
            code = None
            if callback_url.startswith(("http://", "https://")):
                # Full URL provided
                expected_prefix = f"{redirect_uri}?code="
                if not callback_url.startswith(expected_prefix):
                    print(f"❌ Invalid URL format. Should start with '{expected_prefix}'")
                    if len(sys.argv) > 2:  # If URL was provided as parameter, don't retry
                        return False
                    callback_url = None
                    attempts += 1
                    continue
                
                # Extract code from URL
                parsed_url = urlparse(callback_url)
                code = parse_qs(parsed_url.query).get('code', [None])[0]
            else:
                # Assume it's just the authorization code
                code = callback_url.strip()
            
            if not code:
                print("❌ No authorization code found in URL")
                if callback_url:  # If URL was provided as parameter, don't retry
                    return False
                callback_url = None
                attempts += 1
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
                if callback_url:  # If URL was provided as parameter, don't retry
                    return False
                callback_url = None
                attempts += 1
                continue
                
        except KeyboardInterrupt:
            print("\n❌ Authentication cancelled")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            if callback_url:  # If URL was provided as parameter, don't retry
                return False
            print("Please try again with the correct callback URL")
            callback_url = None
            attempts += 1
    
    print(f"❌ Failed after {max_attempts} attempts")
    return False


def test_authentication():
    """Test that authentication works with the master cache."""
    cache_path = get_master_cache_path()
    
    if not cache_path.exists():
        print("❌ No master cache found. Run authentication first.")
        return False
    
    try:
        # Test with the master cache
        redirect_uri = "http://127.0.0.1:8889/callback" if CURRENT_ENV == "test" else "http://127.0.0.1:8888/callback"
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=redirect_uri,
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
            # Check for --url or --code parameter
            callback_url = None
            if len(sys.argv) > 3 and sys.argv[2] == "--url":
                callback_url = sys.argv[3]
            elif len(sys.argv) > 3 and sys.argv[2] == "--code":
                callback_url = sys.argv[3]  # Will be treated as auth code
            elif len(sys.argv) > 2 and sys.argv[2].startswith("--url="):
                callback_url = sys.argv[2][6:]  # Remove --url= prefix
            elif len(sys.argv) > 2 and sys.argv[2].startswith("--code="):
                callback_url = sys.argv[2][7:]  # Remove --code= prefix
            
            success = ssh_friendly_auth(callback_url)
            sys.exit(0 if success else 1)
            
        elif command == "test":
            success = test_authentication()
            sys.exit(0 if success else 1)
            
        elif command == "url":
            # Just print the auth URL without interactive flow
            cache_path = get_master_cache_path()
            scopes = get_all_scopes()
            redirect_uri = "http://127.0.0.1:8889/callback" if CURRENT_ENV == "test" else "http://127.0.0.1:8888/callback"
            
            auth_manager = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=redirect_uri,
                scope=scopes,
                cache_path=str(cache_path)
            )
            
            auth_url = auth_manager.get_authorize_url()
            print(f"🔗 Auth URL for {CURRENT_ENV} environment:")
            print(auth_url)
            print()
            print("📱 SSH/Remote Instructions:")
            print("1. Open the URL above in any browser")
            print("2. After authorization, you'll see 'This site can't be reached' - this is normal!")
            print("3. Copy the authorization code from the URL in your browser")
            print("4. Run one of these commands:")
            print(f"   SPOTIFY_ENV={CURRENT_ENV} uv run python scripts/spotify_auth.py auth --code '<auth_code>'")
            print(f"   SPOTIFY_ENV={CURRENT_ENV} uv run python scripts/spotify_auth.py auth --url '<full_callback_url>'")
            
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
            print("Available commands: auth, test, status, url")
    else:
        print("Unified Spotify Authentication")
        print("Usage: python scripts/spotify_auth.py <command> [options]")
        print()
        print("Commands:")
        print("  auth [--url <callback_url>|--code <auth_code>]  - Run SSH-friendly authentication flow")
        print("  url                                             - Print auth URL only (no interactive input)")
        print("  test                                            - Test existing authentication")  
        print("  status                                          - Show authentication status")
        print()
        print("Examples:")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py url")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth --url 'http://127.0.0.1:8889/callback?code=...'")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py auth --code 'AQA123...'")
        print("  SPOTIFY_ENV=test uv run python scripts/spotify_auth.py test")