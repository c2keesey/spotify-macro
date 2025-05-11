import json
import logging
import re
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry

# Define the required scopes
SCOPE = "playlist-read-private playlist-read-collaborative"

# Data directory
DATA_DIR = Path("_data")

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def sanitize_filename(name):
    """Sanitize a string to be used as a valid filename."""
    name = re.sub(
        r'[<>:"/\\\\|?*]', "_", name
    )  # Replace forbidden characters with underscore
    name = name.strip()
    if not name:
        name = "untitled_playlist"
    return name


def fetch_all_playlist_items(sp, playlist_id):
    """Fetch all items (tracks/episodes) from a playlist, handling pagination and retries, requesting default full objects."""
    items = []

    # By omitting the `fields` parameter, we request Spotify's default full object representation.
    results = spotify_api_call_with_retry(
        sp.playlist_items,
        playlist_id,
        # fields=fields_string, # Removed to get default full objects
        limit=50,  # Keep limit reasonable per page
        additional_types=("track", "episode"),  # Ensure we get both types
    )
    while results:
        for item in results["items"]:
            # Start with playlist item specific details, prefixed to avoid collision
            item_data_to_store = {
                "item_added_at": item.get("added_at"),
                "item_added_by": item.get("added_by"),
                "item_is_local": item.get("is_local"),
                "item_primary_color": item.get("primary_color"),
                "item_video_thumbnail": item.get("video_thumbnail"),
            }

            # The item will have EITHER a 'track' or 'episode' field populated by the API
            media_object = item.get("track") or item.get("episode")

            if media_object:
                # Add all fields from the track/episode object to the dictionary
                item_data_to_store.update(media_object)
            else:
                # If no track/episode data (e.g., deleted item, local file not synced, rare error)
                item_data_to_store["id"] = None
                item_data_to_store["name"] = "Unavailable or Missing Track/Episode"
                item_data_to_store["type"] = "unknown_media_type"

            items.append(item_data_to_store)

        if results["next"]:
            # sp.next() will correctly use the 'next' URL from the default API response
            results = spotify_api_call_with_retry(sp.next, results)
        else:
            results = None
    return items


def _fetch_all_user_playlists(sp):
    """Fetches all playlists for the current user."""
    try:
        current_user_details = spotify_api_call_with_retry(sp.current_user)
        user_id = current_user_details["id"]
        logging.info(f"Successfully fetched user ID: {user_id}")
    except Exception as e:
        logging.error(f"Could not fetch user details: {e}. Aborting.")
        raise  # Re-raise to be caught by main or stop execution

    logging.info(f"Fetching playlists for user: {user_id}")
    all_playlists = []
    try:
        playlists_page = spotify_api_call_with_retry(
            sp.current_user_playlists, limit=50
        )
        if playlists_page and playlists_page["items"]:
            all_playlists.extend(playlists_page["items"])
            while playlists_page and playlists_page["next"]:
                logging.info("Fetching next page of playlists...")
                playlists_page = spotify_api_call_with_retry(sp.next, playlists_page)
                if playlists_page and playlists_page["items"]:
                    all_playlists.extend(playlists_page["items"])
    except Exception as e:
        logging.error(f"Could not fetch playlists: {e}. Aborting.")
        raise  # Re-raise

    if not all_playlists:
        logging.info("No playlists found for the current user.")
        return [], user_id  # Return empty list and user_id

    logging.info(
        f"Found {len(all_playlists)} playlists. Filtering for playlists owned by you..."
    )

    # Filter for playlists owned by the current user
    owned_playlists = [
        p for p in all_playlists if p.get("owner", {}).get("id") == user_id
    ]

    if not owned_playlists:
        logging.info(
            f"No playlists owned by user {user_id} were found among the {len(all_playlists)} accessible playlists."
        )
        return [], user_id

    logging.info(f"Found {len(owned_playlists)} playlists owned by you.")
    return owned_playlists, user_id


def _process_and_save_playlist_data(sp, playlists_to_process, output_dir):
    """Processes each playlist, fetches its items, and saves data to JSON files."""
    logging.info(f"Processing {len(playlists_to_process)} playlists...")
    processed_count = 0
    skipped_count = 0
    error_count = 0

    # Wrap playlists_to_process with tqdm for a progress bar
    for playlist in tqdm(
        playlists_to_process, desc="Processing Playlists", unit="playlist"
    ):
        playlist_id = playlist["id"]
        playlist_name = playlist.get(
            "name", "Unnamed Playlist"
        )  # Handle potentially missing names
        sanitized_playlist_name = sanitize_filename(playlist_name)

        file_path = output_dir / f"{sanitized_playlist_name}.json"
        error_file_path = output_dir / f"{sanitized_playlist_name}_error.json"

        if file_path.exists():
            logging.info(
                f"Playlist '{playlist_name}' (ID: {playlist_id}) already downloaded. Skipping."
            )
            skipped_count += 1
            continue
        if error_file_path.exists():
            logging.warning(
                f"Playlist '{playlist_name}' (ID: {playlist_id}) previously resulted in an error. "
                f"Skipping. Delete '{error_file_path.name}' from {output_dir} to retry."
            )
            skipped_count += 1
            continue

        logging.info(
            f"Fetching tracks for playlist: '{playlist_name}' (ID: {playlist_id})"
        )

        try:
            tracks = fetch_all_playlist_items(sp, playlist_id)

            playlist_info = {
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
                "playlist_url": playlist.get("external_urls", {}).get("spotify"),
                "owner": playlist.get("owner", {}).get("display_name", "Unknown Owner"),
                "total_tracks_api": playlist.get("tracks", {}).get(
                    "total"
                ),  # Total from playlist object
                "total_tracks_fetched": len(tracks),  # Total actually fetched
                "tracks": tracks,
                "download_timestamp": datetime.now().isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(playlist_info, f, indent=4, ensure_ascii=False)

            logging.info(f"Saved playlist '{playlist_name}' to {file_path.name}")
            processed_count += 1

        except Exception as e:
            logging.error(
                f"Error processing playlist '{playlist_name}' (ID: {playlist_id}): {e}"
            )
            error_info = {
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            with open(error_file_path, "w", encoding="utf-8") as f:
                json.dump(error_info, f, indent=4, ensure_ascii=False)
            logging.info(
                f"Saved error information for '{playlist_name}' to {error_file_path.name}"
            )
            error_count += 1
    return processed_count, skipped_count, error_count


def main():
    """Main function to download playlist information."""
    sp = initialize_spotify_client(scope=SCOPE, cache_name="playlist_download_cache")

    try:
        all_playlists, user_id = _fetch_all_user_playlists(sp)
    except Exception:
        return

    if not all_playlists:
        return

    base_output_dir_name = "playlists"
    output_dir = DATA_DIR / base_output_dir_name
    counter = 1
    while output_dir.exists():
        output_dir = DATA_DIR / f"{base_output_dir_name} ({counter})"
        counter += 1

    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count, skipped_count, error_count = _process_and_save_playlist_data(
        sp, all_playlists, output_dir
    )

    logging.info(
        f"\nAll processing complete. "
        f"Playlists successfully processed: {processed_count}. "
        f"Playlists skipped: {skipped_count}. "
        f"Playlists with errors: {error_count}."
    )
    logging.info(f"Playlist data saved in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
