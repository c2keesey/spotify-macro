import json
import logging
from pathlib import Path

from tqdm import tqdm

# --- Configuration ---
DATA_DIR = Path("_data")
PLAYLISTS_INPUT_DIR_NAME = "playlists"
ARTIST_GENRES_INPUT_FILE_NAME = "artist_genres.json"
OUTPUT_FILE_NAME = "playlist_to_genres.json"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """
    Main function to load artist genres, process playlists, and map playlists to aggregated genres.
    """
    logging.info("Starting playlist to genres aggregation process...")

    # Construct paths
    playlists_input_dir = DATA_DIR / PLAYLISTS_INPUT_DIR_NAME
    artist_genres_file_path = DATA_DIR / ARTIST_GENRES_INPUT_FILE_NAME
    output_file_path = DATA_DIR / OUTPUT_FILE_NAME

    # --- 1. Load Artist Genres Data ---
    if not artist_genres_file_path.is_file():
        logging.error(
            f"Artist genres file not found: {artist_genres_file_path}. "
            f"Please run the artist_genres.py script first. Exiting."
        )
        return

    try:
        with open(artist_genres_file_path, "r", encoding="utf-8") as f:
            artist_id_to_details_map = json.load(f)
        logging.info(
            f"Successfully loaded artist genres data from {artist_genres_file_path}."
        )
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from {artist_genres_file_path}. Exiting.")
        return
    except Exception as e:
        logging.error(
            f"Error loading artist genres file {artist_genres_file_path}: {e}. Exiting."
        )
        return

    # --- 2. Process Playlists ---
    if not playlists_input_dir.is_dir():
        logging.error(
            f"Playlists input directory not found: {playlists_input_dir}. Exiting."
        )
        return

    playlist_files = list(playlists_input_dir.glob("*.json"))
    if not playlist_files:
        logging.info(f"No JSON playlist files found in {playlists_input_dir}. Exiting.")
        return

    logging.info(
        f"Found {len(playlist_files)} JSON playlist files to process in {playlists_input_dir}."
    )

    aggregated_playlist_genres_map = {}

    for playlist_file_path in tqdm(playlist_files, desc="Aggregating Playlist Genres"):
        try:
            with open(playlist_file_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)

            playlist_id = playlist_data.get("playlist_id")
            playlist_name = playlist_data.get("playlist_name", "Unnamed Playlist")

            if not playlist_id:
                logging.warning(
                    f"Playlist file {playlist_file_path.name} is missing 'playlist_id'. Skipping."
                )
                continue

            # Changed from set to dict to store genre -> song_count
            current_playlist_genre_song_counts = {}

            for track_item in playlist_data.get("tracks", []):
                if not isinstance(track_item, dict):
                    continue

                if track_item.get("type") == "track":
                    # Genres unique to the current track
                    track_unique_genres = set()
                    artists_in_track = track_item.get("artists", [])
                    if not isinstance(artists_in_track, list):
                        logging.debug(
                            f"Artists field in track {track_item.get('name')} is not a list. Skipping artists."
                        )
                        continue

                    for artist in artists_in_track:
                        if isinstance(artist, dict) and "id" in artist:
                            artist_id = artist["id"]
                            if artist_id in artist_id_to_details_map:
                                artist_genres_list = artist_id_to_details_map[
                                    artist_id
                                ].get("genres", [])
                                track_unique_genres.update(artist_genres_list)
                            else:
                                logging.debug(
                                    f"Artist ID {artist_id} (Name: {artist.get('name', 'N/A')}) not found in artist_genres.json. "
                                    f"This might be an artist with no genres or not fetched."
                                )
                        elif isinstance(artist, dict):
                            logging.debug(
                                f"Artist entry in track {track_item.get('name')} missing ID: {artist.get('name', 'N/A')}"
                            )

                    # After processing all artists for the track, update playlist genre counts
                    for genre in track_unique_genres:
                        current_playlist_genre_song_counts[genre] = (
                            current_playlist_genre_song_counts.get(genre, 0) + 1
                        )

            aggregated_playlist_genres_map[playlist_id] = {
                "playlist_name": playlist_name,
                "genre_song_counts": current_playlist_genre_song_counts,  # New structure
                "distinct_genre_count": len(
                    current_playlist_genre_song_counts
                ),  # Renamed and reflects new structure
            }

        except json.JSONDecodeError:
            logging.warning(
                f"Could not decode JSON from {playlist_file_path.name}. Skipping."
            )
        except Exception as e:
            logging.warning(
                f"Error processing playlist file {playlist_file_path.name}: {e}. Skipping."
            )

    if not aggregated_playlist_genres_map:
        logging.info(
            "No playlist genre data was aggregated. Output file will not be created."
        )
        return

    # --- 3. Save Aggregated Data ---
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # Ensure _data directory exists
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(aggregated_playlist_genres_map, f, indent=4, ensure_ascii=False)
        logging.info(
            f"Successfully saved aggregated playlist genres to: {output_file_path.resolve()}"
        )
    except IOError as e:
        logging.error(f"Could not write output file to {output_file_path}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during file writing: {e}")

    logging.info("Playlist to genres aggregation process finished.")


if __name__ == "__main__":
    main()
