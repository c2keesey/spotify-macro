#!/usr/bin/env python3
"""
Test cleanup hook for maintaining cache synchronization.

This script should be run after test executions to ensure the test
environment cache stays synchronized with production data.

Usage:
    python scripts/test_cleanup_hook.py
    
This can be added to CI/CD pipelines or test frameworks to automatically
clean up test artifacts.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.shared_cache import cleanup_test_cache
from common.config import get_config_value


def main():
    """Main cleanup function"""
    try:
        # Check current environment using the same logic as shared_cache
        from common.config import CURRENT_ENV
        environment = CURRENT_ENV
        
        if environment == "test":
            print("🧹 Running test cleanup hook...")
            cleanup_test_cache()
            print("✅ Test cache cleanup completed")
        else:
            print(f"ℹ️  Not in test environment (current: {environment}), skipping cleanup")
        
    except Exception as e:
        print(f"❌ Test cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()