# Data Processing Scripts

This directory contains scripts for processing Spotify data:

- **`download_playlists.py`** - Downloads all user-owned playlists from Spotify API
- **`artist_genres.py`** - Extracts artist genre data from playlists and fetches from Spotify API
- **`playlist_genres_aggregator.py`** - Aggregates genre data per playlist with song counts
- **`clean_lib.py`** - Removes unnecessary `available_markets` fields from JSON files

## Workflow
1. Run `download_playlists.py` to get playlist data
2. Run `artist_genres.py` to fetch artist genre information
3. Run `playlist_genres_aggregator.py` to create genre summaries
4. Optionally run `clean_lib.py` to clean up JSON files