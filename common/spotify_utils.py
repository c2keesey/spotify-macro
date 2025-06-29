import logging
import os
import time
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from common.config import CLIENT_ID, CLIENT_SECRET, CURRENT_ENV

# Configure basic logging - assuming this might be useful for the utils too
# If not, this can be removed and logging can be handled by the calling modules
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MAX_RETRIES = 8  # Increased for high-volume scenarios
INITIAL_BACKOFF_SECONDS = 1  # Start lower for better throughput
MAX_BACKOFF_SECONDS = 300  # Increased to 5 minutes for severe rate limiting


def spotify_api_call_with_retry(api_call_func, *args, **kwargs):
    """
    Calls a Spotipy API function with retry logic for rate limiting and server errors.
    """
    retries = 0
    backoff_time = INITIAL_BACKOFF_SECONDS
    while retries < MAX_RETRIES:
        try:
            return api_call_func(*args, **kwargs)
        except spotipy.SpotifyException as e:
            logging.warning(
                f"Spotify API error: {e.http_status} - {e.msg}. "
                f"Retrying ({retries + 1}/{MAX_RETRIES}) for {api_call_func.__name__}..."
            )
            if e.http_status == 429:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                        logging.info(
                            f"Rate limited. Retrying after {wait_time} seconds (from Retry-After header)."
                        )
                    except ValueError:
                        logging.warning(
                            f"Invalid Retry-After header value: {retry_after}. Using exponential backoff."
                        )
                        wait_time = backoff_time
                        backoff_time = min(
                            backoff_time * 2 + (os.urandom(1)[0] / 255),
                            MAX_BACKOFF_SECONDS,
                        )
                else:
                    wait_time = backoff_time
                    logging.info(
                        f"Rate limited. Retrying after {wait_time:.2f} seconds (exponential backoff)."
                    )
                    backoff_time = min(
                        backoff_time * 2 + (os.urandom(1)[0] / 255), MAX_BACKOFF_SECONDS
                    )
            elif e.http_status >= 500:
                wait_time = backoff_time
                logging.info(
                    f"Server error ({e.http_status}). Retrying after {wait_time:.2f} seconds (exponential backoff)."
                )
                backoff_time = min(
                    backoff_time * 2 + (os.urandom(1)[0] / 255), MAX_BACKOFF_SECONDS
                )
            else:
                logging.error(
                    f"Unhandled Spotify API error: {e.http_status} - {e.msg}. Not retrying {api_call_func.__name__}."
                )
                raise e

            time.sleep(wait_time)
            retries += 1
        except Exception as e:
            logging.warning(
                f"Non-SpotifyException occurred: {type(e).__name__} - {str(e)}. "
                f"Retrying ({retries + 1}/{MAX_RETRIES}) for {api_call_func.__name__}..."
            )
            wait_time = backoff_time
            logging.info(
                f"Retrying after {wait_time:.2f} seconds (exponential backoff)."
            )
            backoff_time = min(
                backoff_time * 2 + (os.urandom(1)[0] / 255), MAX_BACKOFF_SECONDS
            )
            time.sleep(wait_time)
            retries += 1

    logging.error(
        f"API call {api_call_func.__name__} failed after {MAX_RETRIES} retries."
    )
    raise Exception(
        f"API call {api_call_func.__name__} failed after {MAX_RETRIES} retries."
    )


def initialize_spotify_client(scope: str, cache_name: str = "default_spotify_cache"):
    """Initialize and return a Spotipy client."""
    # Cache path will be in the same directory as this utils file (common/)
    # and named based on the cache_name parameter and current environment.
    cache_path = Path(__file__).parent / f".{cache_name}_{CURRENT_ENV}"

    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8889/callback" if CURRENT_ENV == "test" else "http://127.0.0.1:8888/callback",
        scope=scope,
        cache_path=str(cache_path),
    )

    # Ensure the cache file has secure permissions if it exists, or after creation.
    # This check needs to be done carefully, especially if spotipy creates the file.
    if cache_path.exists():
        try:
            # Attempt to set permissions if they are not already 0o600
            if not (os.stat(cache_path).st_mode & 0o600 == 0o600):
                os.chmod(cache_path, 0o600)
        except OSError as e:
            logging.warning(
                f"Could not set permissions on cache file {cache_path}: {e}"
            )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    # After Spotipy might have created the cache, ensure permissions are correct again.
    if cache_path.exists() and not (os.stat(cache_path).st_mode & 0o600 == 0o600):
        try:
            os.chmod(cache_path, 0o600)
            logging.info(f"Set permissions for cache file: {cache_path}")
        except OSError as e:
            logging.warning(
                f"Could not set permissions on newly created cache file {cache_path}: {e}. Please check manually."
            )

    return sp
