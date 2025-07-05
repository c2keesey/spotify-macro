#!/usr/bin/env python3
"""
Setup script for Telegram bot integration with Spotify automations.
"""

import os
import sys
from pathlib import Path

# Add telegram-cron to path
sys.path.insert(0, str(Path(__file__).parent / "telegram-cron"))

from telegram_toolkit.telegram import setup_telegram_bot
from common.telegram_utils import SpotifyTelegramNotifier


def setup_and_test():
    """Set up Telegram bot and test the integration."""
    print("🎵 Spotify Automation - Telegram Bot Setup")
    print("=" * 50)
    print()
    
    # Check if .env already has telegram config
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if "TELEGRAM_BOT_TOKEN=" in content and "your_bot_token_here" not in content:
                print("✅ Telegram configuration already exists in .env")
                print("Testing existing configuration...")
                test_existing()
                return
    
    print("📝 Setting up new Telegram bot...")
    print()
    print("Instructions:")
    print("1. Message @BotFather on Telegram to create a new bot")
    print("2. Message @userinfobot on Telegram to get your chat ID")
    print("3. Enter the credentials below")
    print()
    
    # Get credentials from user
    bot_token = input("Enter your bot token: ").strip()
    chat_id = input("Enter your chat ID: ").strip()
    
    if not bot_token or not chat_id:
        print("❌ Both bot token and chat ID are required")
        return
    
    # Test the connection
    print("\n🔍 Testing connection...")
    try:
        # Test with SpotifyTelegramNotifier
        # First update .env file
        update_env_file(bot_token, chat_id)
        
        # Test the connection
        test_notifier = SpotifyTelegramNotifier("Setup Test")
        if test_notifier.enabled:
            success = test_notifier.send_success("Telegram Setup Complete", 
                                                 "Your Spotify automations can now send notifications!")
            if success:
                print("✅ Telegram setup successful!")
                print("🎵 Your Spotify automations will now send notifications via Telegram")
            else:
                print("❌ Failed to send test message")
        else:
            print("❌ Telegram notifications are not enabled")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")


def test_existing():
    """Test existing Telegram configuration."""
    try:
        test_notifier = SpotifyTelegramNotifier("Setup Test")
        if test_notifier.enabled:
            success = test_notifier.send_info("Telegram Test", 
                                             "Testing existing Telegram configuration for Spotify automations")
            if success:
                print("✅ Existing Telegram configuration works!")
            else:
                print("❌ Failed to send test message with existing configuration")
        else:
            print("❌ Telegram notifications are not enabled")
            print("Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    except Exception as e:
        print(f"❌ Test failed: {e}")


def update_env_file(bot_token: str, chat_id: str):
    """Update .env file with Telegram credentials."""
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace placeholder values
        content = content.replace("TELEGRAM_BOT_TOKEN=your_bot_token_here", f"TELEGRAM_BOT_TOKEN={bot_token}")
        content = content.replace("TELEGRAM_CHAT_ID=your_chat_id_here", f"TELEGRAM_CHAT_ID={chat_id}")
        
        with open(env_file, 'w') as f:
            f.write(content)
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")


if __name__ == "__main__":
    setup_and_test()