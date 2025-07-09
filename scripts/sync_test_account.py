#!/usr/bin/env python3
"""
Automation-friendly wrapper for test account playlist sync.
Provides functions that can be easily called from other scripts.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_playlist_sync(reset: bool = False, reset_only: bool = False, 
                     timeout: int = 1800, quiet: bool = True) -> Tuple[bool, str]:
    """
    Run playlist sync with monitoring.
    
    Args:
        reset: Whether to reset test account first
        reset_only: Only reset, don't sync playlists
        timeout: Timeout in seconds (default: 30 minutes)
        quiet: Minimize output
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    import tempfile
    import os
    
    # Create unique status file
    status_file = f"/tmp/playlist_sync_{int(time.time())}.txt"
    
    try:
        # Build command
        cmd = ["uv", "run", "scripts/upload_playlists_to_test_account.py"]
        if reset:
            cmd.append("--reset")
        if reset_only:
            cmd.append("--reset-only")
        if quiet:
            cmd.append("--quiet")
        cmd.extend(["--status-file", status_file])
        
        # Start the process
        print(f"🚀 Starting playlist sync...")
        if reset_only:
            print("   Mode: Reset only")
        elif reset:
            print("   Mode: Reset and sync")
        else:
            print("   Mode: Sync only")
            
        process = subprocess.Popen(
            cmd, 
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        start_time = time.time()
        last_status_check = 0
        
        while process.poll() is None:
            # Check timeout
            if time.time() - start_time > timeout:
                process.terminate()
                return False, f"Timeout reached ({timeout}s)"
            
            # Check status file every 10 seconds
            if time.time() - last_status_check > 10:
                status = _check_status_file(status_file)
                if status and status["status"] not in ["UNKNOWN", "STARTING"]:
                    if not quiet:
                        print(f"   📊 Status: {status['status']}")
                last_status_check = time.time()
            
            time.sleep(2)
        
        # Process finished, check final status
        final_status = _check_status_file(status_file)
        
        if process.returncode == 0 and final_status and final_status["status"] == "COMPLETED":
            return True, final_status.get("message", "Sync completed successfully")
        else:
            # Get any error output
            try:
                stdout, stderr = process.communicate(timeout=5)
                error_msg = stderr or stdout or "Unknown error"
            except:
                error_msg = f"Process failed with return code {process.returncode}"
                
            if final_status and final_status["status"] == "FAILED":
                error_msg = final_status.get("message", error_msg)
                
            return False, error_msg
            
    except Exception as e:
        return False, f"Failed to start sync: {str(e)}"
    
    finally:
        # Clean up status file
        try:
            if os.path.exists(status_file):
                os.remove(status_file)
        except:
            pass


def _check_status_file(status_file: str) -> Optional[Dict]:
    """Helper to check status file."""
    try:
        if not Path(status_file).exists():
            return None
            
        result = {}
        with open(status_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("STATUS: "):
                    result["status"] = line[8:]
                elif line.startswith("MESSAGE: "):
                    result["message"] = line[9:]
                elif line.startswith("TIMESTAMP: "):
                    result["timestamp"] = line[11:]
        
        return result
    except:
        return None


def reset_test_account(timeout: int = 600) -> Tuple[bool, str]:
    """
    Reset test account by deleting all playlists.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    return run_playlist_sync(reset_only=True, timeout=timeout)


def sync_playlists(reset_first: bool = False, timeout: int = 1800) -> Tuple[bool, str]:
    """
    Sync playlists to test account.
    
    Args:
        reset_first: Whether to reset account first
        timeout: Timeout in seconds (default: 30 minutes)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    return run_playlist_sync(reset=reset_first, timeout=timeout)


def main():
    """Command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automation-friendly playlist sync")
    parser.add_argument("action", choices=["reset", "sync", "reset-and-sync"],
                       help="Action to perform")
    parser.add_argument("--timeout", type=int, default=1800,
                       help="Timeout in seconds")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    
    args = parser.parse_args()
    
    if args.action == "reset":
        success, message = reset_test_account(args.timeout)
    elif args.action == "sync":
        success, message = sync_playlists(reset_first=False, timeout=args.timeout)
    else:  # reset-and-sync
        success, message = sync_playlists(reset_first=True, timeout=args.timeout)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()