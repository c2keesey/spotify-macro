# Spotify Save Current Track - Automator Workflow

This document explains how to set up an Automator workflow to save the currently playing Spotify track to your library with a keyboard shortcut.

## Setting Up the Workflow

1. Open Automator from your Applications folder
2. Select "Quick Action" when prompted for a document type
3. Configure the workflow settings at the top:
   - Workflow receives: "no input"
   - In: "any application"
4. Add a "Run Shell Script" action from the Actions library
   - Search for "shell" in the search box if you can't find it immediately
5. In the shell script box, enter the full path to the run script:
   ```
   /Users/yourusername/path/to/macos-automations/scripts/run_spotify_save.sh
   ```
   - Replace `/Users/yourusername/path/to/` with the actual path to where you've installed this project
6. Set "Pass input" to "as arguments"
7. Save the workflow with a name like "Add Current Spotify Song to Library"

## Assigning a Keyboard Shortcut

1. Open System Settings (or System Preferences)
2. Navigate to Keyboard > Keyboard Shortcuts
3. Select "Services" or "Quick Actions" from the left sidebar
4. Find your "Add Current Spotify Song to Library" workflow
5. Click to the right of the workflow name where it says "none" or "add shortcut"
6. Press your desired key combination (e.g., Command + Shift + A)
7. Close System Settings

## Testing the Workflow

1. Play a song in Spotify
2. Press your assigned keyboard shortcut
3. You should see a notification indicating whether the song was added to your library or was already there

## Troubleshooting

If the workflow doesn't work as expected:

1. Check that the path in the shell script action is correct
2. Ensure the shell script has execute permissions (`chmod +x scripts/run_spotify_save.sh`)
3. Try running the script directly from Terminal to see if there are any errors
4. Check the environment variables in the `.env` file are properly set
