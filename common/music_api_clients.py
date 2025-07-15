#!/usr/bin/env python3
"""
Music API clients for fetching additional song features.
Includes rate limiting and caching to respect API terms.
"""

import time
import requests
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

class RateLimiter:
    """Rate limiter to respect API limits."""
    
    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        
    def wait_if_needed(self):
        """Wait if we've exceeded rate limit."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            # Wait until oldest call is more than 1 minute old
            sleep_time = 60 - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                print(f"    ⏱️ Rate limit reached, waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        self.calls.append(now)

class MusicAPICache:
    """Simple file-based cache for API responses."""
    
    def __init__(self, cache_dir: str = "data/cache/music_apis"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_hours = 24 * 7  # 1 week cache
        
    def _get_cache_key(self, api_name: str, artist: str, track: str) -> str:
        """Generate cache key from track info."""
        content = f"{api_name}:{artist.lower()}:{track.lower()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, api_name: str, artist: str, track: str) -> Optional[Dict]:
        """Get cached response if available and not expired."""
        cache_key = self._get_cache_key(api_name, artist, track)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cached_time > timedelta(hours=self.cache_ttl_hours):
                cache_file.unlink()  # Delete expired cache
                return None
                
            return cached_data['data']
        except Exception:
            # Invalid cache file, delete it
            cache_file.unlink()
            return None
    
    def set(self, api_name: str, artist: str, track: str, data: Dict):
        """Cache API response."""
        cache_key = self._get_cache_key(api_name, artist, track)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cached_data = {
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f)
        except Exception as e:
            print(f"    ⚠️ Failed to cache data: {e}")

class LastFmClient:
    """Last.fm API client for genre tags and metadata."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.rate_limiter = RateLimiter(calls_per_minute=25)  # Conservative limit
        self.cache = MusicAPICache()
        
    def get_track_info(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Get track information including genre tags."""
        # Check cache first
        cached = self.cache.get('lastfm', artist, track)
        if cached is not None:
            return cached
            
        self.rate_limiter.wait_if_needed()
        
        params = {
            'method': 'track.getInfo',
            'api_key': self.api_key,
            'artist': artist,
            'track': track,
            'format': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'track' not in data:
                return None
                
            track_data = data['track']
            
            # Extract useful features
            features = {
                'duration_ms': int(track_data.get('duration', '0')) * 1000 if track_data.get('duration') else None,
                'playcount': int(track_data.get('playcount', 0)),
                'listeners': int(track_data.get('listeners', 0)),
                'tags': [],
                'similar_artists': []
            }
            
            # Extract genre tags
            if 'toptags' in track_data and 'tag' in track_data['toptags']:
                tags = track_data['toptags']['tag']
                if isinstance(tags, list):
                    features['tags'] = [tag['name'].lower() for tag in tags[:10]]
                elif isinstance(tags, dict):
                    features['tags'] = [tags['name'].lower()]
            
            # Cache the result
            self.cache.set('lastfm', artist, track, features)
            return features
            
        except Exception as e:
            print(f"    ⚠️ Last.fm API error for {artist} - {track}: {e}")
            return None

class GetSongBPMClient:
    """GetSongBPM API client for tempo data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.getsongbpm.com/search/"
        self.rate_limiter = RateLimiter(calls_per_minute=20)  # Conservative limit
        self.cache = MusicAPICache()
        
    def get_track_bpm(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Get BPM and key information for a track."""
        # Check cache first
        cached = self.cache.get('getsongbpm', artist, track)
        if cached is not None:
            return cached
            
        self.rate_limiter.wait_if_needed()
        
        params = {
            'api_key': self.api_key,
            'type': 'song',
            'lookup': f'song:{track} artist:{artist}'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'song' not in data:
                return None
                
            song_data = data['song']
            
            features = {
                'bpm': float(song_data.get('tempo', 0)) if song_data.get('tempo') else None,
                'key': song_data.get('song_key'),
                'time_signature': song_data.get('time_sig')
            }
            
            # Only cache if we got useful data
            if any(v is not None for v in features.values()):
                self.cache.set('getsongbpm', artist, track, features)
                return features
            else:
                return None
                
        except Exception as e:
            print(f"    ⚠️ GetSongBPM API error for {artist} - {track}: {e}")
            return None

class DeezerClient:
    """Deezer API client for basic metadata."""
    
    def __init__(self):
        self.base_url = "https://api.deezer.com"
        self.rate_limiter = RateLimiter(calls_per_minute=30)  # Conservative limit
        self.cache = MusicAPICache()
        
    def get_track_info(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Get track information from Deezer."""
        # Check cache first
        cached = self.cache.get('deezer', artist, track)
        if cached is not None:
            return cached
            
        self.rate_limiter.wait_if_needed()
        
        # Search for track
        search_query = f"artist:'{artist}' track:'{track}'"
        search_url = f"{self.base_url}/search"
        
        try:
            response = requests.get(search_url, params={'q': search_query}, timeout=10)
            response.raise_for_status()
            search_data = response.json()
            
            if not search_data.get('data'):
                return None
                
            # Get first result
            track_data = search_data['data'][0]
            
            features = {
                'duration_ms': int(track_data.get('duration', 0)) * 1000,
                'bpm': track_data.get('bpm'),  # May not always be available
                'rank': track_data.get('rank', 0),
                'explicit': track_data.get('explicit_lyrics', False),
                'preview_url': track_data.get('preview')
            }
            
            # Cache the result
            self.cache.set('deezer', artist, track, features)
            return features
            
        except Exception as e:
            print(f"    ⚠️ Deezer API error for {artist} - {track}: {e}")
            return None

class MusicFeatureFetcher:
    """Unified client for fetching music features from multiple APIs."""
    
    def __init__(self, lastfm_api_key: str = None, getsongbpm_api_key: str = None):
        self.clients = {}
        
        if lastfm_api_key:
            self.clients['lastfm'] = LastFmClient(lastfm_api_key)
            
        if getsongbpm_api_key:
            self.clients['getsongbpm'] = GetSongBPMClient(getsongbpm_api_key)
            
        self.clients['deezer'] = DeezerClient()  # No API key needed
        
    def get_all_features(self, artist: str, track: str, verbose: bool = False) -> Dict[str, Any]:
        """Fetch features from all available APIs."""
        if verbose:
            print(f"    🎵 Fetching features for: {artist} - {track}")
            
        all_features = {
            'artist': artist,
            'track': track,
            'features': {}
        }
        
        # Fetch from each API
        for api_name, client in self.clients.items():
            try:
                if api_name == 'lastfm':
                    features = client.get_track_info(artist, track)
                elif api_name == 'getsongbpm':
                    features = client.get_track_bpm(artist, track)
                elif api_name == 'deezer':
                    features = client.get_track_info(artist, track)
                else:
                    continue
                    
                if features:
                    all_features['features'][api_name] = features
                    if verbose:
                        print(f"      ✅ {api_name}: {len(features)} features")
                else:
                    if verbose:
                        print(f"      ❌ {api_name}: No data")
                        
            except Exception as e:
                if verbose:
                    print(f"      ⚠️ {api_name}: Error - {e}")
                continue
        
        return all_features
    
    def get_combined_features(self, artist: str, track: str) -> Dict[str, Any]:
        """Get combined features with conflict resolution."""
        all_features = self.get_all_features(artist, track)
        
        combined = {
            'bpm': None,
            'duration_ms': None,
            'key': None,
            'time_signature': None,
            'tags': [],
            'playcount': None,
            'rank': None,
            'explicit': None
        }
        
        # Merge features with priority: GetSongBPM > Last.fm > Deezer
        for api_name in ['deezer', 'lastfm', 'getsongbpm']:
            if api_name in all_features['features']:
                features = all_features['features'][api_name]
                
                for key in combined:
                    if key in features and features[key] is not None:
                        if key == 'tags':
                            # Extend tags instead of replace
                            if isinstance(features[key], list):
                                combined[key].extend(features[key])
                        else:
                            combined[key] = features[key]
        
        # Remove duplicates from tags
        if combined['tags']:
            combined['tags'] = list(set(combined['tags']))
            
        return combined