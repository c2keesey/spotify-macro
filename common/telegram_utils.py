#!/usr/bin/env python3
"""
Telegram notification utilities for Spotify automations.

Removes path hacks and treats Telegram as an optional dependency.
If `telegram_toolkit` is not installed, notifications are disabled gracefully.
"""
from pathlib import Path
from typing import Optional

try:
    # Prefer a proper installed package if available
    from telegram_toolkit import TelegramNotifier  # type: ignore
    _TELEGRAM_AVAILABLE = True
except Exception:
    TelegramNotifier = None  # type: ignore
    _TELEGRAM_AVAILABLE = False


class SpotifyTelegramNotifier:
    """Telegram notifier specifically for Spotify automations."""
    
    def __init__(self, automation_name: str):
        """
        Initialize Spotify Telegram notifier.
        
        Args:
            automation_name: Name of the automation (e.g., "Save Current Track")
        """
        self.automation_name = automation_name
        
        # Load from project root .env file if package is present
        env_file = Path(__file__).parent.parent / ".env"
        if _TELEGRAM_AVAILABLE:
            try:
                self.notifier = TelegramNotifier(env_file=str(env_file) if env_file.exists() else None)  # type: ignore
                self.enabled = True
            except Exception as e:
                print(f"Telegram notifications disabled: {e}")
                self.enabled = False
        else:
            print("Telegram notifications disabled: telegram_toolkit not installed")
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
