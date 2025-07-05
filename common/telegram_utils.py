#!/usr/bin/env python3
"""
Telegram notification utilities for Spotify automations.
"""
import sys
import os
from pathlib import Path
from typing import Optional

# Add telegram-cron to path
sys.path.insert(0, str(Path(__file__).parent.parent / "telegram-cron"))

from telegram_toolkit import TelegramNotifier


class SpotifyTelegramNotifier:
    """Telegram notifier specifically for Spotify automations."""
    
    def __init__(self, automation_name: str):
        """
        Initialize Spotify Telegram notifier.
        
        Args:
            automation_name: Name of the automation (e.g., "Save Current Track")
        """
        self.automation_name = automation_name
        
        try:
            # Load from project root .env file
            env_file = Path(__file__).parent.parent / ".env"
            self.notifier = TelegramNotifier(env_file=str(env_file) if env_file.exists() else None)
            self.enabled = True
        except (ValueError, Exception) as e:
            print(f"Telegram notifications disabled: {e}")
            self.enabled = False
    
    def send_success(self, message: str, details: Optional[str] = None) -> bool:
        """
        Send success notification for Spotify automation.
        
        Args:
            message: Success message
            details: Optional additional details
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        full_message = message
        if details:
            full_message += f"\n\n{details}"
            
        return self.notifier.send_success(
            f"Spotify: {self.automation_name}",
            full_message
        )
    
    def send_error(self, error_message: str, details: Optional[str] = None) -> bool:
        """
        Send error notification for Spotify automation.
        
        Args:
            error_message: Error message
            details: Optional error details
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        full_message = error_message
        if details:
            full_message += f"\n\n{details}"
            
        return self.notifier.send_error(
            f"Spotify: {self.automation_name}",
            full_message
        )
    
    def send_info(self, message: str, details: Optional[str] = None) -> bool:
        """
        Send info notification for Spotify automation.
        
        Args:
            message: Info message
            details: Optional additional details
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        full_message = message
        if details:
            full_message += f"\n\n{details}"
            
        return self.notifier.send(
            f"🎵 Spotify: {self.automation_name}",
            full_message
        )