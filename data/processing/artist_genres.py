import json
import logging
from pathlib import Path

from tqdm import tqdm

from common.spotify_utils import (
    initialize_spotify_client,
    spotify_api_call_with_retry,
)

# --- Configuration ---
DATA_DIR = Path("_data")
PLAYLISTS_INPUT_DIR_NAME = "playlists"  # As specified by user
OUTPUT_FILE_NAME = "artist_genres.json"
SPOTIFY_API_ARTISTS_BATCH_SIZE = 50  # Max artists per API call
SCOPE = ""  # Define an empty scope, as no specific user permissions are needed for public artist data

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def extract_artist_ids_from_playlist_data(playlist_data):
    """
    Extracts unique artist IDs from the tracks in a single loaded playlist JSON data.
    """
    artist_ids = set()
    if not isinstance(playlist_data, dict) or "tracks" not in playlist_data:
        logging.warning("Playlist data is not in expected format or has no tracks.")
        return artist_ids

    for track_item in playlist_data.get("tracks", []):
        if not isinstance(track_item, dict):
            continue

        # Tracks have an 'artists' list, episodes might not or have a different structure
        # We are interested in music artists primarily.
        # The 'type' field in track_item can be 'track' or 'episode'.
        # An 'artist' object in Spotify has an 'id'.
        if track_item.get("type") == "track" and "artists" in track_item:
            for artist in track_item.get("artists", []):
                if isinstance(artist, dict) and artist.get("id"):
                    artist_ids.add(artist["id"])
                elif isinstance(artist, dict) and not artist.get("id"):
                    logging.debug(
                        f"Artist entry found without ID: {artist.get('name', 'N/A')}"
                    )
    return artist_ids


def fetch_artists_details_in_batches(sp, artist_ids_list):
    """
    Fetches artist details (name, genres, URI, etc.) from Spotify API in batches.
    Filters out None or empty IDs before making API calls.
    """
    valid_artist_ids = [
        aid for aid in artist_ids_list if aid
    ]  # Filter out None/empty IDs
    if not valid_artist_ids:
        logging.info("No valid artist IDs to fetch details for.")
        return {}

    artists_details_map = {}
    num_batches = (
        len(valid_artist_ids) + SPOTIFY_API_ARTISTS_BATCH_SIZE - 1
    ) // SPOTIFY_API_ARTISTS_BATCH_SIZE

    logging.info(
        f"Fetching details for {len(valid_artist_ids)} artists in {num_batches} batches."
    )

    for i in tqdm(
        range(0, len(valid_artist_ids), SPOTIFY_API_ARTISTS_BATCH_SIZE),
        desc="Fetching Artist Details",
    ):
        batch_ids = valid_artist_ids[i : i + SPOTIFY_API_ARTISTS_BATCH_SIZE]
        try:
            results = spotify_api_call_with_retry(sp.artists, artists=batch_ids)
            if results and "artists" in results:
                for artist_data in results["artists"]:
                    if artist_data and artist_data.get(
                        "id"
                    ):  # Ensure artist_data is not None
                        artists_details_map[artist_data["id"]] = {
                            "name": artist_data.get("name"),
                            "genres": artist_data.get("genres", []),
                            "uri": artist_data.get("uri"),
                            "external_urls": artist_data.get("external_urls", {}),
                            "popularity": artist_data.get("popularity"),
                            "images": artist_data.get(
                                "images", []
                            ),  # Storing images might be useful
                        }
                    elif artist_data:
                        logging.warning(
                            f"Received artist data without an ID in batch: {artist_data.get('name')}"
                        )
                    # If artist_data is None, it means Spotify couldn't find an artist for one of the IDs.
                    # This is handled by sp.artists() returning None for that specific artist in the list.
            else:
                logging.warning(f"No 'artists' key in results for batch: {batch_ids}")
        except Exception as e:
            logging.error(f"Error fetching batch of artists {batch_ids}: {e}")
            # Optionally, store these IDs to retry later or mark as failed
    return artists_details_map


def main():
    """
    Main function to read playlists, extract artist IDs, fetch genres, and save.
    """
    logging.info("Starting artist genre extraction process...")
    try:
        # No specific scope is generally needed for public artist data
        # Using a distinct cache name for this script's token
        sp = initialize_spotify_client(scope=SCOPE, cache_name="artist_genres_cache")
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}. Exiting.")
        return

    playlists_input_dir = DATA_DIR / PLAYLISTS_INPUT_DIR_NAME
    output_file_path = DATA_DIR / OUTPUT_FILE_NAME

    if not playlists_input_dir.is_dir():
        logging.error(
            f"Playlists input directory not found: {playlists_input_dir}. "
            f"Please ensure playlists are downloaded to '{PLAYLISTS_INPUT_DIR_NAME}' within '{DATA_DIR}'."
        )
        return

    all_artist_ids = set()
    playlist_files = list(playlists_input_dir.glob("*.json"))

    if not playlist_files:
        logging.info(f"No JSON files found in {playlists_input_dir}. Exiting.")
        return

    logging.info(f"Found {len(playlist_files)} JSON files in {playlists_input_dir}.")

    for playlist_file_path in tqdm(playlist_files, desc="Scanning Playlists"):
        try:
            with open(playlist_file_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)
            artist_ids_from_file = extract_artist_ids_from_playlist_data(playlist_data)
            all_artist_ids.update(artist_ids_from_file)
        except json.JSONDecodeError:
            logging.warning(
                f"Could not decode JSON from {playlist_file_path}. Skipping."
            )
        except Exception as e:
            logging.warning(
                f"Error processing file {playlist_file_path}: {e}. Skipping."
            )

    if not all_artist_ids:
        logging.info("No unique artist IDs found across all playlists. Exiting.")
        return

    logging.info(f"Found {len(all_artist_ids)} unique artist IDs to process.")

    # Convert set to list for batching
    artist_details_map = fetch_artists_details_in_batches(sp, list(all_artist_ids))

    if not artist_details_map:
        logging.info("No artist details were fetched. Output file will not be created.")
        return

    # Ensure data directory exists for output
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(artist_details_map, f, indent=4, ensure_ascii=False)
        logging.info(
            f"Successfully saved artist genres to: {output_file_path.resolve()}"
        )
    except IOError as e:
        logging.error(f"Could not write output file to {output_file_path}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during file writing: {e}")

    logging.info("Artist genre extraction process finished.")


if __name__ == "__main__":
    main()
