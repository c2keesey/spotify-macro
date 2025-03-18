# Spotify Daily Liked Songs Workflow

This workflow automatically adds songs you've liked in the last 24 hours to a dedicated playlist.

## Setup

### Prerequisites

1. Make sure you have completed the general setup in the main README.md file, including:
   - Creating a Spotify App with appropriate credentials
   - Setting up your `.env` file with the CLIENT_ID and CLIENT_SECRET

### Running Manually

You can run the workflow manually using the provided shell script:

```bash
./scripts/run_spotify_daily_liked.sh
```

The first time you run it, the script will:

1. Authenticate with Spotify (a browser will open for you to login)
2. Look for an existing playlist named "Daily Liked Songs"
3. If it doesn't exist, create a new private playlist with that name
4. Add any songs you've liked in the past 24 hours to this playlist

### Setting Up Automatic Daily Runs

#### Using macOS LaunchAgent (recommended)

1. Create a LaunchAgent directory if it doesn't exist:

```bash
mkdir -p ~/Library/LaunchAgents
```

2. Copy the template plist file from this repository to your LaunchAgents directory:

```bash
cp workflows/launchagents/com.user.spotify.dailyliked.plist ~/Library/LaunchAgents/
```

3. Edit the file to update the path to your script location:

```bash
nano ~/Library/LaunchAgents/com.user.spotify.dailyliked.plist
```

Make sure the script path matches your actual installation path:

```xml
<string>/Users/YOUR_USERNAME/path/to/spotify-macro/scripts/run_spotify_daily_liked.sh</string>
```

You can also customize the interval if desired. The default is set to run every 24 hours (86400 seconds).

4. Load the LaunchAgent:

```bash
launchctl load ~/Library/LaunchAgents/com.user.spotify.dailyliked.plist
```

This will run the script every day at 11:30 PM.

#### Alternative: Using Crontab

1. Open your crontab configuration:

```bash
crontab -e
```

2. Add a line to run the script daily (this example runs at 11:30 PM):

```
30 23 * * * /Users/YOUR_USERNAME/path/to/spotify-macro/scripts/run_spotify_daily_liked.sh
```

**Make sure to replace `YOUR_USERNAME` with your actual username and update the path to point to your script location.**

## Customizing

### Changing the Playlist

By default, the script will create or use a playlist named "Daily Liked Songs". You can customize this in two ways:

#### Option 1: Using Environment Variables in .env file

Add these lines to your `.env` file:

```
# Optional: Specify an existing playlist ID (if you know it)
DAILY_LIKED_PLAYLIST_ID=your_playlist_id_here

# Optional: Change the default playlist name (used when creating a new playlist)
DAILY_LIKED_PLAYLIST_NAME=Your Custom Playlist Name
```

Each time the script runs, it will:

1. Check if a valid playlist ID is specified in `DAILY_LIKED_PLAYLIST_ID`
2. If not, it will look for a playlist with the name specified in `DAILY_LIKED_PLAYLIST_NAME`
3. If neither exists, it will create a new playlist with the specified name

#### Option 2: Creating a Playlist Manually

1. Create a playlist manually in Spotify with the name you want
2. Add this name to your `.env` file using the `DAILY_LIKED_PLAYLIST_NAME` variable

If you need to manually get a playlist ID from Spotify:

1. Open the playlist in Spotify
2. Click "Share" and then "Copy Spotify URI"
3. The URI will look like `spotify:playlist:PLAYLIST_ID` - the last part is your playlist ID

## Troubleshooting

- **Authentication Issues**: If you're having trouble with authentication, delete the `.spotify_cache` file in the `macros/spotify` directory and run the script again.
- **Missing Tracks**: The script only looks for tracks liked in the past 24 hours. If you don't see tracks you expected, make sure they were liked within this timeframe.
- **Playlist Creation Failures**: If you're having trouble with playlist creation, try creating the playlist manually in Spotify and adding the ID to your `.env` file as described above.
