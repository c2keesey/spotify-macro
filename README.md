# macOS Automations

A collection of macOS automations and macros to enhance productivity and add useful features.

## Overview

This project provides a structured framework for creating and using various automations on macOS.
It currently includes:

- **Spotify Add to Library**: Save the currently playing Spotify track to your library with a keyboard shortcut
- **Spotify Daily Liked Songs**: Automatically add songs liked in the last 24 hours to a specified playlist

The modular design makes it easy to add new automations while maintaining a consistent structure.

## Features

- Modular, extensible framework for creating new automations
- Integration with macOS Automator for keyboard shortcuts
- Desktop notifications
- Modern Python package structure using UV package manager

## Prerequisites

- macOS
- Python 3.7 or later
- UV package manager (https://github.com/astral-sh/uv)
- Specific requirements for individual automations (e.g., Spotify Premium account)

## Setup

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/macos-automations.git
   cd macos-automations
   ```

2. Install UV if you don't have it already:

   ```
   curl -fsSL https://astral.sh/uv/install.sh | bash
   ```

3. Set up the virtual environment and install dependencies:

   ```
   uv venv
   uv pip install -r requirements.txt
   ```

4. Configure any specific requirements for automations you want to use (see below)

## Available Automations

### Spotify Add to Library

Save the currently playing Spotify track to your library with a keyboard shortcut.

#### Setup

1. Create a Spotify App:

   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Click "Create an App"
   - Set the Redirect URI to http://localhost:8888/callback

2. Create a `.env` file in the project root with your Spotify App credentials:

   ```
   CLIENT_ID=your_client_id_here
   CLIENT_SECRET=your_client_secret_here
   VENV_PATH=/path/to/your/project/.venv
   ```

3. Follow the instructions in `workflows/spotify_save_current.md` to set up the Automator workflow and keyboard shortcut

### Spotify Daily Liked Songs

Automatically add songs liked in the last 24 hours to a specified playlist.

#### Setup

1. Ensure you've created a Spotify App as described above.

2. Run the script manually to authenticate and create the playlist:

   ```
   ./scripts/run_spotify_daily_liked.sh
   ```

3. Follow the instructions in `workflows/spotify_daily_liked.md` to set up automatic daily execution

## Creating a New Automation

To create a new automation:

1. Copy the template directory structure:

   ```
   cp -r macros/template macros/your_new_automation
   ```

2. Copy the template shell script:

   ```
   cp scripts/template.sh scripts/run_your_new_automation.sh
   ```

3. Implement your automation logic in `macros/your_new_automation/action.py`

4. Update the shell script to use your new module path

5. Make the shell script executable:

   ```
   chmod +x scripts/run_your_new_automation.sh
   ```

6. Create documentation in the workflows directory

7. Update this README if needed

## Project Structure

```
macos-automations/
├── common/               # Shared utilities and helpers
│   ├── config.py         # Configuration management
│   └── utils/            # Utility functions
│       └── notifications.py  # Notification utilities
├── macros/               # Individual automation modules
│   ├── spotify/          # Spotify-related automations
│   │   └── save_current.py   # Save current track to library
│   └── template/         # Template for new automations
├── scripts/              # Shell scripts for running automations
│   ├── run_spotify_save.sh   # Run the Spotify save automation
│   └── template.sh       # Template shell script
├── workflows/            # Documentation for Automator workflows
│   ├── launchagents/     # Template plist files for LaunchAgents
│   ├── spotify_save_current.md  # Setup guide for Spotify workflow
│   └── spotify_daily_liked.md   # Setup guide for Daily Liked Songs
├── .env                  # Environment variables (create this)
├── pyproject.toml        # Project configuration
└── requirements.txt      # Python dependencies
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Required
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret

# Optional
VENV_PATH=/path/to/your/virtual/environment
PYTHON_PATH=/path/to/python/executable

# Spotify Daily Liked Songs (optional)
# Use either DAILY_LIKED_PLAYLIST_ID to specify a particular playlist by ID
DAILY_LIKED_PLAYLIST_ID=your_playlist_id
# Or specify a playlist name - the script will find it or create it if needed
DAILY_LIKED_PLAYLIST_NAME=Your Custom Playlist Name
```

## Running from Command Line

In addition to using Automator workflows with keyboard shortcuts, you can run any automation directly from the command line:

```
# Using the shell script
./scripts/run_spotify_save.sh

# Using Python directly
python -m macros.spotify.save_current

# Using the installed entry point (if available)
save-spotify-track
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
