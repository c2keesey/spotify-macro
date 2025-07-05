import json
import logging
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Data directory (relative to the script location or an absolute path)
# Assuming this script might be run from the project root or its own directory.
# If run from project root, _data is correct. If run from download/, ../_data is needed.
# For simplicity, using a path relative to a common project structure.
DATA_DIR = Path("_data")  # This assumes the script is run from the workspace root.
# Or, you might want to define it based on this script's location:
# DATA_DIR = Path(__file__).parent.parent / "_data"


def remove_key_recursive(obj, key_to_remove):
    """
    Recursively removes a specified key from a Python object (dict or list).
    Modifies the object in place.
    """
    if isinstance(obj, dict):
        # Use list(obj.keys()) because we might modify the dictionary during iteration
        for key in list(obj.keys()):
            if key == key_to_remove:
                del obj[key]
            else:
                remove_key_recursive(obj[key], key_to_remove)
    elif isinstance(obj, list):
        for item in obj:
            remove_key_recursive(item, key_to_remove)
    return obj


def clean_json_files(data_directory: Path, key_to_remove: str):
    """
    Finds all JSON files in the given directory and its subdirectories,
    then removes the specified key from their content.
    """
    json_files_found = 0
    json_files_processed = 0
    json_files_failed = 0

    logging.info(f"Scanning for JSON files in: {data_directory.resolve()}")

    for file_path in data_directory.rglob("*.json"):
        json_files_found += 1
        logging.info(f"Processing file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Create a deep copy if you want to compare or be safer,
            # but for this task, modifying in place is fine.
            # import copy
            # original_data_hash = hash(json.dumps(data, sort_keys=True)) # For checking if changes occurred

            remove_key_recursive(data, key_to_remove)

            # modified_data_hash = hash(json.dumps(data, sort_keys=True))
            # if original_data_hash == modified_data_hash:
            #     logging.info(f"No '{key_to_remove}' keys found in {file_path}. Skipping write.")
            #     # Increment a different counter if needed, e.g., files_unmodified
            #     continue

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            logging.info(f"Successfully cleaned and saved {file_path}")
            json_files_processed += 1

        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from file: {file_path}. Skipping.")
            json_files_failed += 1
        except Exception as e:
            logging.error(
                f"An unexpected error occurred with file {file_path}: {e}. Skipping."
            )
            json_files_failed += 1

    logging.info(
        f"\nCleaning process summary:\n"
        f"Total JSON files found: {json_files_found}\n"
        f"JSON files successfully processed: {json_files_processed}\n"
        f"JSON files failed/skipped: {json_files_failed}"
    )


def main():
    """
    Main function to start the cleaning process.
    """
    # Adjust DATA_DIR if the script is not in the root of your project
    # For example, if clean_lib.py is in a 'scripts' or 'download' folder:
    # current_script_path = Path(__file__).resolve()
    # project_root = current_script_path.parent.parent # Adjust based on your structure
    # data_dir = project_root / "_data"

    # Using the globally defined DATA_DIR assuming it's set correctly
    # relative to where the script is executed.

    # Check if the _data directory exists
    if not DATA_DIR.exists() or not DATA_DIR.is_dir():
        logging.error(
            f"The data directory '{DATA_DIR.resolve()}' does not exist or is not a directory."
        )
        logging.error(
            "Please ensure the DATA_DIR variable is set correctly and the directory exists."
        )
        return

    key_to_remove = "available_markets"
    logging.info(f"Starting the process to remove '{key_to_remove}' from JSON files...")
    clean_json_files(DATA_DIR, key_to_remove)
    logging.info("Processing complete.")


if __name__ == "__main__":
    main()
