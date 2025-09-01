#!/usr/bin/env python3
"""
Classify tracks from the 'New' playlist using the optimized multi-class composite classifier.

This script uses the champion optimization results (66.2% F1 score with multi-class support) 
to classify tracks from the 'New' playlist and distribute them to appropriate folder playlists.
Tracks can be assigned to multiple folders when they meet the optimized threshold (0.05).
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import get_config_value, CURRENT_ENV
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.playlist_data_utils import PlaylistDataLoader
from common.shared_cache import get_cached_artist_data
from common.constants import FOLDER_PLAYLIST_PREFIX
from analysis.optimization.run_full_optimization import OptimizedCompositeClassifier


def load_optimal_parameters():
    """Load the optimal parameters from the best optimization results."""
    return {
        # NEW: Corrected parameters optimized for proper 14-class problem
        "statistical_correlation_weight": 2.612,
        "keyword_matching_weight": 0.677,
        "top_folder_selection_ratio": 0.991,
        "max_confidence_cap": 0.849,
        "multi_class_threshold": 0.05,  # Optimized: Best F1 score (0.662) at threshold 0.05
        "folder_strategies": {
            # Optimized parameters from corrected 14-class optimization
            "House": {"strategy": "balanced", "threshold": 0.272},
            "Electronic": {"strategy": "simple_artist", "threshold": 0.263},
            "Base": {"strategy": "balanced", "threshold": 0.181},
            "Alive": {"strategy": "conservative", "threshold": 0.176},
            "Rave": {"strategy": "conservative", "threshold": 0.207},
            "Rock": {"strategy": "enhanced_genre", "threshold": 0.050},
            # Use default strategies/thresholds for folders not in optimization
            "Vibes": {"strategy": "simple_artist", "threshold": 0.080},
            "Sierra": {"strategy": "balanced", "threshold": 0.120},
            "Ride": {"strategy": "conservative", "threshold": 0.080},
            "Funk Soul": {"strategy": "balanced", "threshold": 0.150},
            "Reggae": {"strategy": "enhanced_genre", "threshold": 0.300},
            "Spiritual": {"strategy": "conservative", "threshold": 0.100},
            "Soft": {"strategy": "conservative", "threshold": 0.250},
            "Chill": {"strategy": "conservative", "threshold": 0.050}
        }
    }


def find_new_playlist(playlists_dict):
    """Find the 'New' playlist in the loaded playlists."""
    for playlist_id, playlist_data in playlists_dict.items():
        if playlist_data["name"].lower() == "new":
            return playlist_id, playlist_data
    return None, None


def classify_and_distribute_tracks():
    """Main function to classify tracks from New playlist."""
    start_time = datetime.now()
    print("🎯 Starting classification of 'New' playlist with optimized classifier...")
    
    # Initialize metrics tracking
    metrics = {
        'run_info': {
            'start_time': start_time.isoformat(),
            'script_version': 'v4.2_enhanced_fallback_cached_data',
            'environment': CURRENT_ENV
        },
        'input_data': {},
        'classification_results': {},
        'folder_distributions': defaultdict(int),
        'confidence_stats': defaultdict(list),
        'processing_stats': {},
        'errors': [],
        'performance': {}
    }
    
    # Initialize Spotify client with existing cache
    scope = "playlist-read-private playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope, "playlist_flow_cache")
    
    # Load playlist data
    print("📚 Loading playlist data...")
    playlists_dict = PlaylistDataLoader.load_playlists_from_directory()
    print(f"Loaded {len(playlists_dict)} playlists")
    metrics['input_data']['total_playlists_loaded'] = len(playlists_dict)
    
    # Find the 'New' playlist
    new_playlist_id, new_playlist_data = find_new_playlist(playlists_dict)
    if not new_playlist_id:
        error_msg = "❌ Could not find playlist named 'New'"
        print(error_msg)
        metrics['errors'].append(error_msg)
        _save_metrics(metrics, start_time)
        return
    
    tracks = new_playlist_data["tracks"]
    print(f"📀 Found 'New' playlist with {len(tracks)} tracks")
    metrics['input_data']['new_playlist_track_count'] = len(tracks)
    
    if len(tracks) == 0:
        print("ℹ️ No tracks to classify")
        metrics['processing_stats']['no_tracks_to_process'] = True
        _save_metrics(metrics, start_time)
        return
    
    # Use cached artist mappings for performance
    print("🚀 Loading cached artist mappings...")
    try:
        artist_to_playlists, single_playlist_artists = get_cached_artist_data(verbose=True)
        print(f"✅ Loaded cached data: {len(artist_to_playlists)} artists, {len(single_playlist_artists)} single-playlist artists")
        metrics['input_data']['used_cached_data'] = True
        metrics['input_data']['cached_artists_count'] = len(artist_to_playlists)
        metrics['input_data']['cached_single_artists_count'] = len(single_playlist_artists)
    except Exception as e:
        print(f"⚠️ Failed to load cached data, falling back to building mappings: {e}")
        artist_to_playlists = PlaylistDataLoader.build_artist_to_playlists_mapping(
            playlists_dict, exclude_parent_playlists=True
        )
        metrics['input_data']['used_cached_data'] = False
    
    # Initialize base classifier and apply optimal parameters manually
    print("🧠 Initializing optimized classifier with champion parameters...")
    optimal_params = load_optimal_parameters()
    
    # Import the composite classifier directly
    from analysis.genre.composite_classifier import CompositeClassifier
    classifier = CompositeClassifier()
    
    # Apply optimal parameters manually
    classifier.statistical_correlation_weight = optimal_params["statistical_correlation_weight"]
    classifier.keyword_matching_weight = optimal_params["keyword_matching_weight"]
    classifier.top_folder_selection_ratio = optimal_params["top_folder_selection_ratio"]
    classifier.max_confidence_cap = optimal_params["max_confidence_cap"]
    
    # Apply folder-specific strategies
    classifier.folder_strategies = optimal_params["folder_strategies"]
    
    # Load playlist folder mapping first for training
    print("📁 Loading folder mapping for training...")
    import json
    with open('data/playlist_folders.json', 'r') as f:
        playlist_folders = json.load(f)
    
    # Create reverse mapping: playlist name -> folder name
    playlist_to_folder = {}
    for folder_name, playlist_files in playlist_folders.items():
        for playlist_file in playlist_files:
            # Remove .json extension to get playlist name
            playlist_name = playlist_file.replace('.json', '')
            playlist_to_folder[playlist_name] = folder_name
    
    print(f"   Loaded mapping for {len(playlist_to_folder)} playlists to {len(playlist_folders)} folders")
    
    # Prepare training data using FOLDER NAMES instead of playlist names
    train_tracks = []
    folder_track_counts = {}
    
    for playlist_id, playlist_data in playlists_dict.items():
        playlist_name = playlist_data["name"]
        
        # Map playlist name to folder name
        if playlist_name in playlist_to_folder:
            folder_name = playlist_to_folder[playlist_name]
            
            # Count tracks per folder for stats
            if folder_name not in folder_track_counts:
                folder_track_counts[folder_name] = 0
            
            for track in playlist_data["tracks"]:
                train_tracks.append((track["id"], folder_name))  # ← Train on FOLDER names!
                folder_track_counts[folder_name] += 1
        else:
            # Skip playlists not in folder mapping (like "New" playlist)
            continue
    
    print(f"   Training on {len(train_tracks)} tracks across {len(folder_track_counts)} folders:")
    metrics['input_data']['training_tracks'] = len(train_tracks)
    metrics['input_data']['training_folders'] = len(folder_track_counts)
    metrics['input_data']['folder_track_counts'] = dict(folder_track_counts)
    
    for folder, count in sorted(folder_track_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"     {folder}: {count} tracks")
    
    train_data = {
        'playlists_dict': playlists_dict,
        'train_tracks': train_tracks
    }
    
    # Train the classifier
    classifier.train(train_data)
    
    # Track results
    classifications = {}
    unclassified = []
    errors = []
    
    print("🎵 Classifying tracks...")
    for i, track in enumerate(tracks):
        track_id = track["id"]
        track_name = track["name"]
        artist_names = [artist["name"] for artist in track["artists"]]
        
        print(f"  {i+1}/{len(tracks)}: {track_name} by {', '.join(artist_names)}")
        
        try:
            # Use the optimized classifier to predict folders
            result = classifier.predict(track_id)
            
            if hasattr(result, 'predicted_folders'):
                predicted_folders = result.predicted_folders
                confidence_scores = result.confidence_scores
            else:
                predicted_folders = result.get('folders', [])
                confidence_scores = result.get('confidence_scores', {})
            
            if predicted_folders:
                # Dynamic threshold adjustment based on folder characteristics and prediction strength
                base_threshold = optimal_params.get("multi_class_threshold", 0.05)
                
                # Calculate adaptive thresholds for each folder
                valid_folders = {}
                for folder in predicted_folders:
                    confidence = confidence_scores.get(folder, 0)
                    
                    # Get folder-specific threshold from strategy config
                    folder_threshold = optimal_params["folder_strategies"].get(folder, {}).get("threshold", 0.15)
                    
                    # Adaptive threshold: lower for high-confidence predictions, higher for weak ones
                    if confidence >= 0.8:  # High confidence
                        adaptive_threshold = base_threshold
                    elif confidence >= 0.5:  # Medium confidence
                        adaptive_threshold = max(base_threshold, folder_threshold * 0.7)
                    else:  # Low confidence
                        adaptive_threshold = max(base_threshold, folder_threshold * 0.5)
                    
                    if confidence >= adaptive_threshold:
                        valid_folders[folder] = confidence
                
                if valid_folders:
                    # Sort by confidence for display
                    sorted_folders = sorted(valid_folders.items(), key=lambda x: x[1], reverse=True)
                    
                    classifications[track_id] = {
                        'track_name': track_name,
                        'artists': artist_names,
                        'folders': valid_folders,  # Changed from single 'folder' to multiple 'folders'
                        'all_predicted_folders': predicted_folders
                    }
                    
                    # Update metrics for ALL valid folders
                    for folder, confidence in valid_folders.items():
                        metrics['folder_distributions'][folder] += 1
                        metrics['confidence_stats'][folder].append(confidence)
                    
                    # Display all valid folders
                    folder_strs = [f"{folder} ({conf:.3f})" for folder, conf in sorted_folders]
                    print(f"    → {', '.join(folder_strs)}")
                else:
                    # No folders meet adaptive thresholds
                    unclassified.append({
                        'track_id': track_id,
                        'track_name': track_name,
                        'artists': artist_names,
                        'reason': f"No folders above adaptive thresholds (base: {base_threshold})"
                    })
                    print(f"    → Unclassified (no folders above adaptive thresholds)")
            else:
                unclassified.append({
                    'track_id': track_id,
                    'track_name': track_name,
                    'artists': artist_names
                })
                print(f"    → Unclassified")
                
        except Exception as e:
            error_msg = f"Error classifying {track_name}: {str(e)}"
            errors.append(error_msg)
            metrics['errors'].append(error_msg)
            print(f"    → Error: {e}")
    
    # Group tracks by target folder (supporting multi-class output)
    print("\n📁 Grouping classified tracks by folder...")
    folder_to_tracks = {}
    for track_id, classification in classifications.items():
        folders_dict = classification['folders']  # Now a dict of folder -> confidence
        
        # Add track to ALL valid folders
        for folder_name in folders_dict.keys():
            if folder_name not in folder_to_tracks:
                folder_to_tracks[folder_name] = []
            folder_to_tracks[folder_name].append(track_id)
    
    print(f"   Classified tracks into {len(folder_to_tracks)} folders:")
    for folder, track_ids in sorted(folder_to_tracks.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"     {folder}: {len(track_ids)} tracks")
    
    # Find target playlists for each folder using Spotify API (folder playlists may not be in playlists_dict)
    print("\n🎯 Finding target folder playlists...")
    
    # Get current user playlists from Spotify API to find folder playlists
    user_playlists = sp.current_user_playlists(limit=50)
    api_playlists = {}
    for playlist in user_playlists['items']:
        api_playlists[playlist['id']] = playlist
    
    folder_to_playlist = {}
    for folder_name in folder_to_tracks.keys():
        # Look for folder playlist with prefix in API results
        target_folder_name = f"{FOLDER_PLAYLIST_PREFIX} {folder_name}"
        
        for playlist_id, playlist_data in api_playlists.items():
            if playlist_data["name"] == target_folder_name:
                folder_to_playlist[folder_name] = {
                    'id': playlist_id,
                    'name': playlist_data["name"]
                }
                print(f"  {folder_name} → {playlist_data['name']}")
                break
        
        # If no folder playlist found, warn about it
        if folder_name not in folder_to_playlist:
            print(f"  ⚠️ No folder playlist found for '{folder_name}' (expected '📁 {folder_name}')")
    
    print(f"   Found {len(folder_to_playlist)} folder playlists for {len(folder_to_tracks)} classified folders")
    
    # Execute the moves
    print(f"\n🚀 Adding tracks to target playlists...")
    total_moved = 0
    
    for folder_name, track_ids in folder_to_tracks.items():
        if folder_name in folder_to_playlist:
            target_playlist = folder_to_playlist[folder_name]
            target_id = target_playlist['id']
            target_name = target_playlist['name']
            
            # Remove duplicates by fetching current playlist contents from Spotify API
            try:
                current_playlist = spotify_api_call_with_retry(sp.playlist_tracks, target_id, limit=50)
                existing_track_ids = set()
                
                # Get all tracks from current playlist
                while current_playlist:
                    for item in current_playlist['items']:
                        if item['track'] and item['track']['id']:
                            existing_track_ids.add(item['track']['id'])
                    
                    # Get next page if available
                    if current_playlist['next']:
                        current_playlist = spotify_api_call_with_retry(sp.next, current_playlist)
                    else:
                        break
                        
            except Exception as e:
                error_msg = f"❌ Failed to fetch existing tracks from '{target_name}': {e}"
                print(error_msg)
                errors.append(error_msg)
                metrics['errors'].append(error_msg)
                print(f"❌ Stopping execution due to API error. Cannot ensure duplicate prevention.")
                _save_metrics(metrics, start_time)
                return
            
            new_track_ids = [tid for tid in track_ids if tid not in existing_track_ids]
            
            if new_track_ids:
                try:
                    # Add tracks in chunks of 100
                    chunk_size = 100
                    for i in range(0, len(new_track_ids), chunk_size):
                        chunk = new_track_ids[i:i + chunk_size]
                        spotify_api_call_with_retry(
                            sp.playlist_add_items, target_id, chunk
                        )
                    
                    total_moved += len(new_track_ids)
                    print(f"  ✅ Added {len(new_track_ids)} tracks to '{target_name}'")
                    
                    # Show track details with confidence for this specific folder
                    for track_id in new_track_ids:
                        if track_id in classifications:
                            track_info = classifications[track_id]
                            conf = track_info['folders'].get(folder_name, 0)  # Get confidence for this folder
                            print(f"    • {track_info['track_name']} (confidence: {conf:.3f})")
                
                except Exception as e:
                    error_msg = f"Failed to add tracks to '{target_name}': {e}"
                    errors.append(error_msg)
                    metrics['errors'].append(error_msg)
                    print(f"  ❌ {error_msg}")
            else:
                print(f"  ℹ️ All {len(track_ids)} tracks already in '{target_name}'")
        else:
            print(f"  ⚠️ No target playlist found for folder '{folder_name}'")
            for track_id in track_ids:
                if track_id in classifications:
                    track_info = classifications[track_id]
                    unclassified.append({
                        'track_id': track_id,
                        'track_name': track_info['track_name'],
                        'artists': track_info.get('artists', []),
                        'reason': f"No playlist found for folder '{folder_name}'"
                    })
    
    # Print summary
    print(f"\n📊 Classification Summary:")
    print(f"  Total tracks processed: {len(tracks)}")
    print(f"  Successfully classified: {len(classifications)}")
    
    # Calculate multi-class statistics
    total_folder_assignments = sum(len(folder_to_tracks[folder]) for folder in folder_to_tracks)
    multi_class_tracks = sum(1 for classification in classifications.values() if len(classification['folders']) > 1)
    
    print(f"  Total folder assignments: {total_folder_assignments}")
    print(f"  Multi-class tracks: {multi_class_tracks}")
    print(f"  Successfully moved: {total_moved}")
    print(f"  Unclassified: {len(unclassified)}")
    print(f"  Errors: {len(errors)}")
    
    if unclassified:
        print(f"\n❓ Unclassified tracks:")
        for track in unclassified:
            reason = track.get('reason', 'No classification found')
            print(f"  • {track['track_name']} by {', '.join(track['artists'])} - {reason}")
    
    if errors:
        print(f"\n❌ Errors:")
        for error in errors:
            print(f"  • {error}")
    
    # Calculate final metrics
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    metrics['run_info']['end_time'] = end_time.isoformat()
    metrics['run_info']['total_processing_time_seconds'] = processing_time
    
    metrics['classification_results']['total_tracks_processed'] = len(tracks)
    metrics['classification_results']['successfully_classified'] = len(classifications)
    metrics['classification_results']['total_folder_assignments'] = total_folder_assignments
    metrics['classification_results']['multi_class_tracks'] = multi_class_tracks
    metrics['classification_results']['unclassified'] = len(unclassified)
    metrics['classification_results']['classification_errors'] = len([e for e in errors if 'Error classifying' in e])
    metrics['classification_results']['coverage_percentage'] = (len(classifications) / len(tracks)) * 100 if tracks else 0
    metrics['classification_results']['avg_folders_per_track'] = total_folder_assignments / len(classifications) if classifications else 0
    
    metrics['processing_stats']['tracks_moved_to_playlists'] = total_moved
    metrics['processing_stats']['total_errors'] = len(errors)
    
    # Calculate confidence statistics per folder
    confidence_summary = {}
    for folder, confidences in metrics['confidence_stats'].items():
        if confidences:
            confidence_summary[folder] = {
                'count': len(confidences),
                'avg_confidence': sum(confidences) / len(confidences),
                'min_confidence': min(confidences),
                'max_confidence': max(confidences)
            }
    metrics['performance']['confidence_summary'] = confidence_summary
    
    # Convert defaultdicts to regular dicts for JSON serialization
    metrics['folder_distributions'] = dict(metrics['folder_distributions'])
    metrics['confidence_stats'] = {k: v for k, v in metrics['confidence_stats'].items()}
    
    # Save metrics to file
    _save_metrics(metrics, start_time)
    
    print(f"\n🎉 Classification complete! Moved {total_moved} tracks using the optimized classifier.")
    print(f"📊 Metrics saved to file (see data/classification_results/)")


def _save_metrics(metrics, start_time):
    """Save metrics to a timestamped JSON file."""
    # Create results directory
    results_dir = Path("data/classification_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped filename
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    filename = f"classification_metrics_{timestamp}.json"
    filepath = results_dir / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, default=str)
        print(f"📊 Metrics saved to: {filepath}")
    except Exception as e:
        print(f"⚠️ Failed to save metrics: {e}")


if __name__ == "__main__":
    classify_and_distribute_tracks()