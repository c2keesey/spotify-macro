#!/usr/bin/env python3
"""
Configuration for music API clients.
"""

import os
from typing import Optional

def get_lastfm_api_key() -> Optional[str]:
    """Get Last.fm API key from environment."""
    return os.environ.get('LASTFM_API_KEY')

def get_getsongbpm_api_key() -> Optional[str]:
    """Get GetSongBPM API key from environment."""
    return os.environ.get('GETSONGBPM_API_KEY')

def has_api_keys() -> bool:
    """Check if we have any API keys configured."""
    return bool(get_lastfm_api_key() or get_getsongbpm_api_key())

def get_available_apis() -> list:
    """Get list of available APIs based on configured keys."""
    available = ['deezer']  # Always available
    
    if get_lastfm_api_key():
        available.append('lastfm')
        
    if get_getsongbpm_api_key():
        available.append('getsongbpm')
        
    return available