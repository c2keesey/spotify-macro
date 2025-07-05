- [ ] Clean up the whole repo
- [ ] rename, generalize this folder
- [ ] add telegram and cron as subrepo

Playlist Flow:

- [ ] setup with prod

Saving by genre new songs

- [x] single playlist artists direct adding - PRIORITIZE (55.3% of artists are single playlist)
- [ ] implement smart playlist prioritization: check if artist is single playlist artist first, then fall back to genre classification
- [ ] sync flow naming convention
- [ ] centralize naming convention definitions
- [ ] instead of doing by playlist folders, make genre buckets dependent on the distribution of the songs in my lib. i.e. use bigger genre buckets for songs that are less common, more specific for more common like bass, etc.

Artist-Based Prioritization (HIGH PRIORITY):

- [ ] implement single playlist artist lookup system
- [ ] modify save_current_with_genre to check artist distribution first
- [ ] create artist-to-playlist mapping cache for fast lookups
- [ ] add fallback to genre classification when artist appears in multiple playlists
- [ ] add preference scoring: single playlist (100%) > genre classification (76% accuracy)
