"""
Telegram notification utilities for Spotify automations.

Provides a lightweight wrapper that other modules can import as
`SpotifyTelegramNotifier` with a consistent `send_success`, `send_info`,
and `send_error` API. If Telegram credentials are missing, calls will
degrade gracefully by printing to stdout instead of raising.
"""

import os
from typing import Optional

import requests


class SpotifyTelegramNotifier:
    """Simple Telegram notifier with context-aware titles.

    Usage:
        telegram = SpotifyTelegramNotifier("Save Current Track")
        telegram.send_success("Added 'Song' to library", "By Artist")
    """

    def __init__(self, context: str, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.context = context
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        # Allow disabling via env flag
        self.disabled = os.getenv("TELEGRAM_DISABLED", "false").lower() in {"1", "true", "yes"}

    def _is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id) and not self.disabled

    def _format_title(self, title: str, emoji: Optional[str] = None) -> str:
        prefix = f"{emoji} " if emoji else ""
        # Include context to make messages easier to trace
        return f"{prefix}{self.context}: {title}" if self.context else f"{prefix}{title}"

    def _send(self, title: str, message: str, emoji: Optional[str] = None, silent: bool = False) -> bool:
        formatted_title = self._format_title(title, emoji)

        if not self._is_configured():
            print(f"[telegram disabled] {formatted_title}\n{message}")
            return False

        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"*{formatted_title}*\n\n{message}",
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "disable_notification": silent,
        }

        try:
            response = requests.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"Telegram notification failed: {exc}\n{formatted_title}\n{message}")
            return False

    def send_success(self, title: str, message: str) -> bool:
        return self._send(title, message, emoji="✅")

    def send_error(self, title: str, message: str) -> bool:
        return self._send(title, message, emoji="🚨")

    def send_info(self, title: str, message: str) -> bool:
        return self._send(title, message, emoji="ℹ️", silent=True)
