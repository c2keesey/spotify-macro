"""
Utility functions for displaying desktop notifications.
"""

import os
import subprocess
import tempfile


def macos_notification(title, message):
    """
    Display a macOS notification with the specified title and message.

    Args:
        title (str): The notification title
        message (str): The notification message

    Returns:
        bool: True if notification was displayed, False otherwise
    """
    try:
        # Create AppleScript to display notification
        script = f'''
        display notification "{message}" with title "{title}"
        '''

        # Execute AppleScript
        subprocess.run(["osascript", "-e", script], check=True)
        return True
    except Exception as e:
        print(f"Error displaying notification: {e}")
        return False


def send_notification_via_file(title, message, file_path=None):
    """
    Write notification content to a file for later use by shell scripts.

    Args:
        title (str): The notification title
        message (str): The notification message
        file_path (str, optional): Path to output file. Defaults to /tmp/notification_result.txt.

    Returns:
        str: Path to the file containing the notification data
    """
    file_path = file_path or os.path.join(
        tempfile.gettempdir(), "notification_result.txt"
    )

    with open(file_path, "w") as f:
        f.write(f"{title}\n{message}")

    return file_path
