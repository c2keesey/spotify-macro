- [x] Clean up the whole repo
- [x] rename, generalize this folder
- [x] add telegram and cron as subrepo

Playlist Flow:

- [ ] setup with prod

Saving by genre new songs

- [x] single playlist artists direct adding - PRIORITIZE (55.3% of artists are single playlist)
- [x] implement smart playlist prioritization: check if artist is single playlist artist first, then fall back to genre classification
- [ ] sync flow naming convention
- [x] centralize naming convention definitions
- [ ] instead of doing by playlist folders, make genre buckets dependent on the distribution of the songs in my lib. i.e. use bigger genre buckets for songs that are less common, more specific for more common like bass, etc.

Artist-Based Prioritization (HIGH PRIORITY):

- [x] implement single playlist artist lookup system
- [x] modify save_current_with_genre to check artist distribution first
- [ ] create artist-to-playlist mapping cache for fast lookups
- [ ] add fallback to genre classification when artist appears in multiple playlists
- [ ] add preference scoring: single playlist (100%) > genre classification (76% accuracy)

Performance & Testing:

- [ ] Make test account reset more efficient (currently too slow - takes multiple minutes)
- [ ] Investigate single-playlist artist sync issue - all tracks being skipped as staging playlists
- [ ] Test actual single-playlist artist movement by manually placing some tracks first
- [ ] make reset and sync more efficient -- update and compare instead of delete

- [ ] create version control for system
