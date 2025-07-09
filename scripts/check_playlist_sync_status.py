#!/usr/bin/env python3
"""
Helper script to check the status of playlist sync operations.
Used by automation to monitor completion.
"""

import os
import sys
from pathlib import Path

def check_sync_status(status_file: str = "/tmp/playlist_sync_result.txt") -> dict:
    """
    Check the status of a playlist sync operation.
    
    Returns:
        dict with keys: status, timestamp, message, exists
    """
    result = {
        "exists": False,
        "status": "UNKNOWN",
        "timestamp": None,
        "message": None
    }
    
    if not os.path.exists(status_file):
        return result
    
    result["exists"] = True
    
    try:
        with open(status_file, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith("STATUS: "):
                result["status"] = line[8:]
            elif line.startswith("TIMESTAMP: "):
                result["timestamp"] = line[11:]
            elif line.startswith("MESSAGE: "):
                result["message"] = line[9:]
                
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = f"Failed to read status file: {e}"
    
    return result


def main():
    """Command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check playlist sync status")
    parser.add_argument("--status-file", default="/tmp/playlist_sync_result.txt", 
                       help="Status file to check")
    parser.add_argument("--wait", action="store_true", 
                       help="Wait for completion (check every 5 seconds)")
    parser.add_argument("--timeout", type=int, default=600,
                       help="Timeout in seconds when waiting (default: 600)")
    
    args = parser.parse_args()
    
    if args.wait:
        import time
        start_time = time.time()
        
        print(f"⏳ Waiting for playlist sync to complete...")
        print(f"   Status file: {args.status_file}")
        print(f"   Timeout: {args.timeout} seconds")
        
        while True:
            status = check_sync_status(args.status_file)
            
            if not status["exists"]:
                print("   📄 No status file found yet...")
            elif status["status"] in ["COMPLETED", "FAILED"]:
                print(f"   ✅ Sync {status['status'].lower()}")
                if status["message"]:
                    print(f"   📝 {status['message']}")
                break
            elif status["status"] == "STARTING":
                print("   🚀 Sync is starting...")
            else:
                print(f"   ⏳ Status: {status['status']}")
            
            # Check timeout
            if time.time() - start_time > args.timeout:
                print(f"   ⏰ Timeout reached ({args.timeout}s)")
                sys.exit(1)
            
            time.sleep(5)
        
        # Final status check
        final_status = check_sync_status(args.status_file)
        if final_status["status"] == "FAILED":
            sys.exit(1)
    else:
        # Single check
        status = check_sync_status(args.status_file)
        
        print(f"Status: {status['status']}")
        if status["timestamp"]:
            print(f"Time: {status['timestamp']}")
        if status["message"]:
            print(f"Message: {status['message']}")
        
        if not status["exists"]:
            print("Note: Status file does not exist")
            sys.exit(1)
        elif status["status"] == "FAILED":
            sys.exit(1)


if __name__ == "__main__":
    main()