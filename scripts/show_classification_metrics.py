#!/usr/bin/env python3
"""
Display metrics from the most recent classification run.
"""

import json
from pathlib import Path
from datetime import datetime

def show_latest_metrics():
    """Show metrics from the most recent classification run."""
    results_dir = Path("data/classification_results")
    
    if not results_dir.exists():
        print("❌ No classification results directory found")
        return
    
    # Find the most recent metrics file
    metrics_files = list(results_dir.glob("classification_metrics_*.json"))
    if not metrics_files:
        print("❌ No classification metrics files found")
        return
    
    latest_file = max(metrics_files, key=lambda f: f.stat().st_mtime)
    
    print(f"📊 Reading metrics from: {latest_file.name}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
        
        print("\n" + "="*60)
        print("🎯 CLASSIFICATION RUN METRICS")
        print("="*60)
        
        # Run info
        run_info = metrics.get('run_info', {})
        print(f"📅 Start Time: {run_info.get('start_time', 'Unknown')}")
        print(f"⏱️  Processing Time: {run_info.get('total_processing_time_seconds', 0):.1f} seconds")
        print(f"🔧 Environment: {run_info.get('environment', 'unknown')}")
        print(f"📝 Script Version: {run_info.get('script_version', 'unknown')}")
        
        # Input data
        input_data = metrics.get('input_data', {})
        print(f"\n📥 INPUT DATA:")
        print(f"  Total Playlists Loaded: {input_data.get('total_playlists_loaded', 0)}")
        print(f"  New Playlist Tracks: {input_data.get('new_playlist_track_count', 0)}")
        print(f"  Training Tracks: {input_data.get('training_tracks', 0)}")
        print(f"  Training Folders: {input_data.get('training_folders', 0)}")
        
        # Classification results
        results = metrics.get('classification_results', {})
        print(f"\n🎯 CLASSIFICATION RESULTS:")
        print(f"  Total Tracks Processed: {results.get('total_tracks_processed', 0)}")
        print(f"  Successfully Classified: {results.get('successfully_classified', 0)}")
        print(f"  Unclassified: {results.get('unclassified', 0)}")
        print(f"  Coverage: {results.get('coverage_percentage', 0):.1f}%")
        print(f"  Classification Errors: {results.get('classification_errors', 0)}")
        
        # Processing stats
        processing = metrics.get('processing_stats', {})
        print(f"\n📤 PROCESSING STATS:")
        print(f"  Tracks Moved to Playlists: {processing.get('tracks_moved_to_playlists', 0)}")
        print(f"  Total Errors: {processing.get('total_errors', 0)}")
        
        # Folder distribution
        folder_dist = metrics.get('folder_distributions', {})
        if folder_dist:
            print(f"\n📁 FOLDER DISTRIBUTION:")
            sorted_folders = sorted(folder_dist.items(), key=lambda x: x[1], reverse=True)
            for folder, count in sorted_folders:
                print(f"  {folder}: {count} tracks")
        
        # Confidence summary
        confidence = metrics.get('performance', {}).get('confidence_summary', {})
        if confidence:
            print(f"\n📈 CONFIDENCE SUMMARY:")
            for folder, stats in confidence.items():
                avg_conf = stats.get('avg_confidence', 0)
                count = stats.get('count', 0)
                print(f"  {folder}: {avg_conf:.3f} avg confidence ({count} tracks)")
        
        # Errors
        errors = metrics.get('errors', [])
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error reading metrics file: {e}")

if __name__ == "__main__":
    show_latest_metrics()