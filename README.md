# Spotify Add to Library Macro

This project provides a quick and easy way to add the currently playing Spotify track to your library using a keyboard shortcut on macOS.

## Features

- Add the currently playing Spotify track to your library with a single keyboard shortcut
- Displays a notification with the added song's details
- Maintains authentication between uses

## Prerequisites

- macOS
- Python 3.12 or later
- Spotify Premium account
- Spotify Developer account

## Setup

1. Clone this repository:
   git clone https://github.com/yourusername/spotify-macro.git
   cd spotify-macro

2. Install required Python packages:
   pip3 install spotipy python-dotenv

3. Create a Spotify App:

   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Click "Create an App"
   - Set the Redirect URI to http://localhost:8888/callback

4. Create a .env file in the project root with your Spotify App credentials and paths:
   CLIENT_ID=your_client_id_here
   CLIENT_SECRET=your_client_secret_here
   PYTHON_PATH=/path/to/your/python
   SCRIPT_PATH=/path/to/your/project/src/save_current.py

   Replace the PYTHON_PATH with the path to your Python 3.12 installation (e.g., /Library/Frameworks/Python.framework/Versions/3.12/bin/python3)
   The SCRIPT_PATH should be the full path to the save_current.py script in your src directory

5. Make the shell script executable:
   chmod +x src/run_spotify_macro.sh

6. Set up the Automator Quick Action:

   - Open Automator and create a new Quick Action
   - Add a "Run Shell Script" action
   - In the shell script box, add:
     /Users/yourusername/path/to/spotify-macro/src/run_spotify_macro.sh
   - Save the Quick Action with a name like "Add Spotify Song to Library"

7. Assign a keyboard shortcut:
   - Open System Settings > Keyboard > Keyboard Shortcuts
   - Select "Services" or "Quick Actions" from the left sidebar
   - Find your "Add Spotify Song to Library" action
   - Click on "add shortcut" and press your desired key combination (e.g., Command + Shift + A)

## Usage

1. Play a song on Spotify
2. Press your assigned keyboard shortcut
3. The song will be added to your library, and you'll see a notification confirming the action

## Troubleshooting

- If you encounter permission issues, ensure the Python script and shell script have the correct permissions
- Check that the paths in your .env file are correct
- Ensure your Spotify Developer App has the correct Redirect URI set

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
