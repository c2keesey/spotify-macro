"""
Automated sorting from the "New" playlist into folder aggregators.

Behavior:
- Build folder -> artist_id index from cached library using data/playlist_folders.json
- Discover or create aggregator playlists per folder (configurable prefixes)
- For each track in "New": if any artist is in any folder index, add to that folder's aggregator
- If at least one add succeeded and --keep is not set, remove that track from "New"

This job uses cached library data for all classification logic. Spotify API is used only for:
- Resolving/creating the "New" playlist and aggregators
- Adding tracks to aggregators
- Optionally removing from "New"
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from common.config import (
    PROJECT_ROOT,
    SPOTIFY_NEW_PLAYLIST_NAME,
)
from common.folder_sort_utils import (
    is_aggregator_for_folder,
    make_aggregator_name,
    normalize_name_key,
    strip_json_suffix,
)
from common.library_sync import (  # reuse helper
    _fetch_playlist_track_uris,
    load_library_manifest,
)
from common.playlist_data_utils import PlaylistDataLoader
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry
from common.utils.notifications import send_notification_via_file


@dataclass
class TrackRef:
    uri: str
    artist_ids: List[str]


def _load_playlist_folders_map() -> Dict[str, List[str]]:
    """Load folders -> playlist display filenames from data/playlist_folders.json.

    Returns a mapping of folder display name -> list of playlist display names (without .json).
    """
    folders_path = PROJECT_ROOT / "data" / "playlist_folders.json"
    if not folders_path.exists():
        raise FileNotFoundError(f"Missing folder definition file: {folders_path}")

    with open(folders_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    normalized: Dict[str, List[str]] = {}
    for folder_name, items in raw.items():
        clean_items = [strip_json_suffix(x) for x in items]
        normalized[folder_name] = clean_items
    return normalized


def _build_manifest_name_index(manifest: Dict) -> Dict[str, Tuple[str, Dict]]:
    """Build name-key -> (playlist_id, manifest_entry)."""
    index: Dict[str, Tuple[str, Dict]] = {}
    for pid, entry in manifest.get("playlists", {}).items():
        name = entry.get("name") or pid
        index[normalize_name_key(name)] = (pid, entry)
    return index


def _resolve_folder_playlist_ids(
    folders_map: Dict[str, List[str]],
    manifest_name_index: Dict[str, Tuple[str, Dict]],
) -> Tuple[Dict[str, List[str]], List[str]]:
    """Resolve listed folder playlist names to playlist IDs using the manifest index.

    Returns tuple of (folder_name -> list[playlist_id], missing_names_log)
    """
    folder_ids: Dict[str, List[str]] = {}
    missing: List[str] = []

    for folder, names in folders_map.items():
        ids: List[str] = []
        for display_name in names:
            key = normalize_name_key(display_name)
            if key in manifest_name_index:
                pid, _ = manifest_name_index[key]
                ids.append(pid)
            else:
                missing.append(f"{folder}:{display_name}")
        folder_ids[folder] = ids
    return folder_ids, missing


def _build_folder_artist_index(
    folders_to_playlist_ids: Dict[str, List[str]],
    playlist_loader_data: Dict[str, Dict],
) -> Dict[str, Set[str]]:
    """Build folder -> set[artist_id] from cached playlists referenced by the folder."""
    index: Dict[str, Set[str]] = {}
    for folder, pids in folders_to_playlist_ids.items():
        artist_ids: Set[str] = set()
        for pid in pids:
            pdata = playlist_loader_data.get(pid)
            if not pdata:
                continue
            for track in pdata.get("tracks", []):
                for artist in track.get("artists", []):
                    aid = artist.get("id")
                    if aid:
                        artist_ids.add(aid)
        index[folder] = artist_ids
    return index


def _discover_or_create_aggregators(
    sp,
    folders: List[str],
) -> Tuple[Dict[str, Dict], List[str]]:
    """Find or create aggregator playlists for each folder.

    Returns mapping folder -> playlist_obj, and list of created names.
    """
    me = spotify_api_call_with_retry(sp.current_user)
    my_id = me["id"]

    # Build authored-by-name index for current account
    from common.library_sync import (
        _build_authored_playlist_indexes,  # local import to avoid cycle
    )

    by_id, by_name = _build_authored_playlist_indexes(sp, my_id)

    created: List[str] = []
    result: Dict[str, Dict] = {}

    for folder in folders:
        # Try to find any existing aggregator matching any prefix
        found = None
        for key, candidates in by_name.items():
            # key is normalized lower-case; rebuild candidate name to check
            # but we can just scan candidates for a match
            for pl in candidates:
                name = pl.get("name") or ""
                if is_aggregator_for_folder(name, folder):
                    found = pl
                    break
            if found:
                break

        if not found:
            # Create standard bracket aggregator name
            display_name = make_aggregator_name(folder)
            created_pl = spotify_api_call_with_retry(
                sp.user_playlist_create,
                my_id,
                display_name,
                public=False,
                collaborative=False,
                description=f"Auto aggregator for {folder}",
            )
            # Update indexes for potential subsequent matches
            by_id[created_pl["id"]] = created_pl
            # Normalize name key similar to library_sync
            name_key = (created_pl.get("name") or "").strip().lower()
            by_name[name_key].append(created_pl)
            result[folder] = created_pl
            created.append(display_name)
        else:
            result[folder] = found

    return result, created


def _find_new_playlist(sp, new_name: str) -> Optional[Dict]:
    me = spotify_api_call_with_retry(sp.current_user)
    my_id = me["id"]
    from common.library_sync import _build_authored_playlist_indexes

    by_id, by_name = _build_authored_playlist_indexes(sp, my_id)
    key = (new_name or "").strip().lower()
    candidates = by_name.get(key)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Prefer most recent snapshot
    return max(candidates, key=lambda p: p.get("snapshot_id", ""))


def _fetch_new_tracks_with_artists(sp, playlist_id: str) -> List[TrackRef]:
    items: List[TrackRef] = []
    offset = 0
    limit = 100

    while True:
        response = spotify_api_call_with_retry(
            sp.playlist_items,
            playlist_id,
            limit=limit,
            offset=offset,
            additional_types=("track",),
        )
        page = response.get("items", [])
        if not page:
            break
        for item in page:
            track = item.get("track") or {}
            if not track or track.get("is_local") or not track.get("uri"):
                continue
            artist_ids = []
            for artist in track.get("artists", []) or []:
                aid = artist.get("id")
                if aid:
                    artist_ids.append(aid)
            if not artist_ids:
                continue
            items.append(TrackRef(uri=track["uri"], artist_ids=artist_ids))
        if len(page) < limit or not response.get("next"):
            break
        offset += limit

    return items


def _plan_additions(
    new_tracks: List[TrackRef],
    folder_to_artist_ids: Dict[str, Set[str]],
    folder_to_aggregator: Dict[str, Dict],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Plan which URIs to add per aggregator; also return tracks-to-folders mapping."""
    plan: Dict[str, List[str]] = defaultdict(list)  # aggregator_id -> uris
    track_to_folders: Dict[str, List[str]] = defaultdict(list)  # track_uri -> folders

    for t in new_tracks:
        matched_any = False
        for folder, artist_set in folder_to_artist_ids.items():
            if not artist_set:
                continue
            if any(aid in artist_set for aid in t.artist_ids):
                agg = folder_to_aggregator.get(folder)
                if not agg:
                    continue
                plan[agg["id"]].append(t.uri)
                track_to_folders[t.uri].append(folder)
                matched_any = True
        # If not matched_any, we leave it in New (no-op).
    return plan, track_to_folders


def _apply_additions_and_optionally_remove(
    sp,
    plan: Dict[str, List[str]],
    track_to_folders: Dict[str, List[str]],
    keep_in_new: bool,
    new_playlist_id: str,
) -> Tuple[int, int]:
    """Execute the plan: add to aggregators (dedup) and optionally remove from New.

    Returns (num_added, num_removed_from_new)
    """
    total_added = 0
    to_remove_from_new: List[str] = []

    for aggregator_id, uris in plan.items():
        if not uris:
            continue
        existing = set(_fetch_playlist_track_uris(sp, aggregator_id))
        missing = [u for u in uris if u not in existing]
        if not missing:
            continue
        # Batch add in 100s
        for i in range(0, len(missing), 100):
            chunk = missing[i : i + 100]
            spotify_api_call_with_retry(sp.playlist_add_items, aggregator_id, chunk)
            total_added += len(chunk)
        # Prepare removal list for any track that had at least one folder match
        if not keep_in_new:
            for u in set(uris):
                to_remove_from_new.append(u)

    removed = 0
    if not keep_in_new and to_remove_from_new:
        # Remove in chunks; Spotify requires positions or snapshot if duplicates exist.
        # Using URIs removal removes all occurrences; acceptable for "New" triage.
        for i in range(0, len(to_remove_from_new), 100):
            chunk = to_remove_from_new[i : i + 100]
            spotify_api_call_with_retry(
                sp.playlist_remove_all_occurrences_of_items, new_playlist_id, chunk
            )
            removed += len(chunk)

    return total_added, removed


def run_action(argv: Optional[List[str]] = None):
    """CLI entrypoint for folder sorter."""
    # TODO: Consider adding --folders filter later if needed
    parser = argparse.ArgumentParser(description="Sort 'New' into folder aggregators")
    parser.add_argument(
        "--keep", action="store_true", help="Do not remove matched tracks from 'New'"
    )
    args = parser.parse_args(argv)

    # Build classification data from cache
    manifest = load_library_manifest(strict=True)
    name_index = _build_manifest_name_index(manifest)

    playlists_loader = PlaylistDataLoader.load_playlists_from_directory(
        normalize_tracks=True,
        include_empty=False,
        verbose=False,
    )

    folders_map = _load_playlist_folders_map()
    folders_to_ids, unresolved = _resolve_folder_playlist_ids(folders_map, name_index)
    folder_artist_index = _build_folder_artist_index(folders_to_ids, playlists_loader)

    # Initialize Spotify client
    scope = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"
    sp = initialize_spotify_client(scope)

    # Find or create aggregators
    folder_names = list(folders_map.keys())
    aggregators, created_names = _discover_or_create_aggregators(sp, folder_names)

    # Find New playlist
    new_name = SPOTIFY_NEW_PLAYLIST_NAME
    new_pl = _find_new_playlist(sp, new_name)
    if not new_pl:
        title = "❌ New playlist not found"
        message = f"No playlist named '{new_name}' in current account"
        send_notification_via_file(
            title, message, "/tmp/spotify_folder_sort_result.txt"
        )
        print(f"{title}\n{message}")
        return title, message

    new_tracks = _fetch_new_tracks_with_artists(sp, new_pl["id"])

    # Plan additions
    folder_to_agg = {folder: aggregators.get(folder) for folder in folder_names}
    plan, track_to_folders = _plan_additions(
        new_tracks, folder_artist_index, folder_to_agg
    )

    # Apply
    added, removed = _apply_additions_and_optionally_remove(
        sp,
        plan,
        track_to_folders,
        keep_in_new=args.keep,
        new_playlist_id=new_pl["id"],
    )

    # Summary
    matched_tracks = len({u for u, folders in track_to_folders.items() if folders})
    folders_hit = sum(1 for uris in plan.values() if uris)

    title = f"✅ Folder sort: +{added}"
    message = (
        f"Tracks scanned: {len(new_tracks)} | matched: {matched_tracks} | "
        f"folders affected: {folders_hit} | removed from New: {removed}"
    )
    if created_names:
        message += f" | created: {len(created_names)} aggregators"
    if unresolved:
        message += f" | unresolved refs: {len(unresolved)}"

    send_notification_via_file(title, message, "/tmp/spotify_folder_sort_result.txt")
    print(f"{title}\n{message}")
    return title, message


def main():
    return run_action()


if __name__ == "__main__":
    main()
