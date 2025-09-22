"""Unified Spotify library cache synchronization.

This module keeps a manifest-driven cache of the prod account's authored
playlists in ``data/library``. Each sync can optionally persist track listings
per playlist or just the high-level metadata, depending on downstream needs.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from common.config import CURRENT_ENV, PROJECT_ROOT
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


LOGGER = logging.getLogger(__name__)

LIBRARY_DIR = PROJECT_ROOT / "data" / "library"
PLAYLISTS_DIR = LIBRARY_DIR / "playlists"
MANIFEST_PATH = LIBRARY_DIR / "manifest.json"
MANIFEST_VERSION = "1.0"
STAGING_STATE_PATH = LIBRARY_DIR / "staging_state.json"
STAGING_STATE_VERSION = "1.0"


@dataclass
class PlaylistManifestEntry:
    """Minimal information stored for each playlist in the manifest."""

    playlist_id: str
    name: str
    description: Optional[str]
    public: bool
    collaborative: bool
    snapshot_id: str
    track_count: int
    synced_at: str
    file: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "public": self.public,
            "collaborative": self.collaborative,
            "snapshot_id": self.snapshot_id,
            "track_count": self.track_count,
            "synced_at": self.synced_at,
            "file": self.file,
        }


def sync_prod_library_cache(
    *,
    force_full_refresh: bool = False,
    spotify_client=None,
    playlist_ids: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
    include_tracks: bool = True,
) -> Dict[str, Any]:
    """Synchronize the prod account's playlists into ``data/library``.

    Args:
        force_full_refresh: If ``True`` every authored playlist is re-fetched
            even when the snapshot_id indicates no change.
        spotify_client: Optional Spotipy client to reuse an existing session.
        playlist_ids: Optional iterable of playlist IDs to restrict the sync to
            a specific subset (useful for testing).
        limit: Optional maximum number of playlists to sync. Applied after
            filtering by ``playlist_ids``.
        include_tracks: When ``True`` (default) the sync fetches full track
            listings for each playlist. Set to ``False`` when only metadata is
            required, which reduces API usage considerably.

    Returns:
        Summary dictionary with counts of updated, skipped, and removed
        playlists plus the manifest path that was written.

    Raises:
        RuntimeError: When invoked in a non-prod environment.
    """

    if CURRENT_ENV != "prod":
        raise RuntimeError(
            "Library sync is restricted to the prod environment; "
            f"CURRENT_ENV={CURRENT_ENV!r}"
        )

    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()

    sp = spotify_client or _initialize_spotify_client()
    current_user = spotify_api_call_with_retry(sp.current_user)
    user_id = current_user["id"]

    remote_playlists = []
    target_ids = set(playlist_ids) if playlist_ids else None

    for playlist_obj in _iter_authored_playlists(sp, user_id):
        if target_ids and playlist_obj["id"] not in target_ids:
            continue
        remote_playlists.append(playlist_obj)
        if limit is not None and len(remote_playlists) >= limit:
            break

    updated = 0
    skipped = 0
    removed = 0

    new_manifest_entries: Dict[str, PlaylistManifestEntry] = {}

    for playlist_obj in remote_playlists:
        playlist_id = playlist_obj["id"]
        entry = manifest["playlists"].get(playlist_id)

        needs_refresh = force_full_refresh or _playlist_needs_refresh(
            entry,
            playlist_obj,
        )

        if needs_refresh:
            LOGGER.info("Refreshing playlist %s (%s)", playlist_obj["name"], playlist_id)
            playlist_file_payload = _fetch_playlist_payload(
                sp,
                playlist_obj,
                include_tracks=include_tracks,
            )
            _write_playlist_file(playlist_id, playlist_file_payload)
            updated += 1
            synced_at = playlist_file_payload["synced_at"]
        else:
            skipped += 1
            synced_at = entry["synced_at"] if entry else datetime.utcnow().isoformat()

        new_manifest_entries[playlist_id] = PlaylistManifestEntry(
            playlist_id=playlist_id,
            name=playlist_obj.get("name", playlist_id),
            description=playlist_obj.get("description"),
            public=bool(playlist_obj.get("public", False)),
            collaborative=bool(playlist_obj.get("collaborative", False)),
            snapshot_id=playlist_obj.get("snapshot_id", ""),
            track_count=int(playlist_obj.get("tracks", {}).get("total", 0)),
            synced_at=synced_at,
            file=f"playlists/{playlist_id}.json",
        )

    if target_ids is None and limit is None:
        removed_ids = set(manifest["playlists"]) - set(new_manifest_entries)
        for playlist_id in removed_ids:
            removed += 1
            playlist_path = PLAYLISTS_DIR / f"{playlist_id}.json"
            if playlist_path.exists():
                playlist_path.unlink()

    summary = {
        "updated": updated,
        "skipped": skipped,
        "removed": removed,
        "total": len(new_manifest_entries),
    }

    _save_manifest(
        manifest_template={
            "version": MANIFEST_VERSION,
            "generated_at": datetime.utcnow().isoformat(),
            "owner": {
                "id": current_user.get("id"),
                "display_name": current_user.get("display_name"),
                "uri": current_user.get("uri"),
            },
            "playlists": {pid: entry.to_dict() for pid, entry in new_manifest_entries.items()},
        }
    )

    LOGGER.info(
        "Library sync complete: %d updated, %d skipped, %d removed",
        summary["updated"],
        summary["skipped"],
        summary["removed"],
    )

    summary["manifest_path"] = str(MANIFEST_PATH)
    return summary


def _initialize_spotify_client():
    scope = "playlist-read-private playlist-read-collaborative"
    return initialize_spotify_client(scope)


def _initialize_write_spotify_client():
    scope = (
        "playlist-read-private playlist-read-collaborative "
        "playlist-modify-private playlist-modify-public"
    )
    return initialize_spotify_client(scope)


def _load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"version": MANIFEST_VERSION, "generated_at": None, "owner": None, "playlists": {}}

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        LOGGER.warning("Failed to parse manifest %s: %s", MANIFEST_PATH, exc)
        return {"version": MANIFEST_VERSION, "generated_at": None, "owner": None, "playlists": {}}


def _save_manifest(manifest_template: Dict[str, Any]) -> None:
    temp_path = MANIFEST_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(manifest_template, handle, indent=2, ensure_ascii=False)
    temp_path.replace(MANIFEST_PATH)


def _load_staging_state() -> Dict[str, Any]:
    if not STAGING_STATE_PATH.exists():
        return {"version": STAGING_STATE_VERSION, "generated_at": None, "playlists": {}}

    try:
        with open(STAGING_STATE_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        LOGGER.warning("Failed to parse staging state %s: %s", STAGING_STATE_PATH, exc)
        return {"version": STAGING_STATE_VERSION, "generated_at": None, "playlists": {}}


def _save_staging_state(state_template: Dict[str, Any]) -> None:
    temp_path = STAGING_STATE_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(state_template, handle, indent=2, ensure_ascii=False)
    temp_path.replace(STAGING_STATE_PATH)


def _iter_authored_playlists(sp, owner_id: str) -> Iterable[Dict[str, Any]]:
    offset = 0
    limit = 50

    while True:
        page = spotify_api_call_with_retry(sp.current_user_playlists, limit=limit, offset=offset)
        items = page.get("items", [])
        for playlist in items:
            playlist_owner = playlist.get("owner", {})
            if playlist_owner.get("id") == owner_id:
                yield playlist

        if len(items) < limit or not page.get("next"):
            break
        offset += limit


def _playlist_needs_refresh(
    manifest_entry: Optional[Dict[str, Any]],
    remote_playlist: Dict[str, Any],
) -> bool:
    if manifest_entry is None:
        return True

    if manifest_entry.get("snapshot_id") != remote_playlist.get("snapshot_id"):
        return True

    playlist_path = PLAYLISTS_DIR / f"{remote_playlist['id']}.json"
    if not playlist_path.exists():
        return True

    return False


def _fetch_playlist_payload(
    sp,
    playlist_obj: Dict[str, Any],
    *,
    include_tracks: bool,
) -> Dict[str, Any]:
    playlist_id = playlist_obj["id"]
    tracks: List[Dict[str, Any]] = []

    if include_tracks:
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

            for item in response.get("items", []):
                track_data = _serialize_playlist_item(item)
                if track_data is not None:
                    tracks.append(track_data)

            if len(response.get("items", [])) < limit or not response.get("next"):
                break
            offset += limit

    payload = {
        "playlist_id": playlist_id,
        "playlist_name": playlist_obj.get("name"),
        "snapshot_id": playlist_obj.get("snapshot_id"),
        "synced_at": datetime.utcnow().isoformat(),
        "metadata": {
            "description": playlist_obj.get("description"),
            "public": playlist_obj.get("public", False),
            "collaborative": playlist_obj.get("collaborative", False),
            "uri": playlist_obj.get("uri"),
            "href": playlist_obj.get("href"),
            "external_url": playlist_obj.get("external_urls", {}).get("spotify"),
            "image_url": _extract_cover_image(playlist_obj),
        },
        "tracks": tracks,
        "track_count": len(tracks) if include_tracks else int(playlist_obj.get("tracks", {}).get("total", 0)),
    }

    return payload


def _serialize_playlist_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    track = item.get("track")
    if not track or track.get("is_local") or not track.get("id"):
        return None

    simplified_track = {
        "id": track.get("id"),
        "name": track.get("name"),
        "uri": track.get("uri"),
        "duration_ms": track.get("duration_ms"),
        "popularity": track.get("popularity"),
        "explicit": track.get("explicit"),
        "preview_url": track.get("preview_url"),
        "external_urls": track.get("external_urls", {}),
        "album": _simplify_album(track.get("album")),
        "artists": _simplify_artists(track.get("artists", [])),
    }

    added_by = item.get("added_by") or {}

    return {
        "added_at": item.get("added_at"),
        "added_by": {
            "id": added_by.get("id"),
            "uri": added_by.get("uri"),
            "type": added_by.get("type"),
        },
        "track": simplified_track,
    }


def _simplify_artists(artists: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    simplified = []
    for artist in artists:
        if not isinstance(artist, dict):
            continue
        simplified.append(
            {
                "id": artist.get("id"),
                "name": artist.get("name"),
                "uri": artist.get("uri"),
            }
        )
    return simplified


def _simplify_album(album: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(album, dict):
        return None
    images = album.get("images") or []
    return {
        "id": album.get("id"),
        "name": album.get("name"),
        "uri": album.get("uri"),
        "release_date": album.get("release_date"),
        "images": images,
    }


def _extract_cover_image(playlist_obj: Dict[str, Any]) -> Optional[str]:
    images = playlist_obj.get("images") or []
    if not images:
        return None
    return images[0].get("url")


def _write_playlist_file(playlist_id: str, payload: Dict[str, Any]) -> None:
    playlist_path = PLAYLISTS_DIR / f"{playlist_id}.json"
    temp_path = playlist_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    temp_path.replace(playlist_path)


def load_library_manifest(*, strict: bool = True) -> Dict[str, Any]:
    """Load the cached library manifest.

    Args:
        strict: When ``True`` (default) raise if the manifest is missing or has
            no playlists.

    Returns:
        Parsed manifest dictionary.
    """

    manifest = _load_manifest()
    if strict and not manifest.get("playlists"):
        raise FileNotFoundError(
            "Library manifest missing or empty. Run sync_prod_library_cache() first."
        )
    return manifest


def sync_library_cache_to_current_account(
    *,
    spotify_client=None,
    playlist_ids: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Apply the cached prod library to the currently authenticated account.

    This helper is intended for staging/test environments to mirror prod
    playlists without falling back to legacy caches. It creates any missing
    playlists, updates metadata when required, and only rewrites tracklists
    when a diff is detected to keep API usage low.

    Args:
        spotify_client: Optional Spotipy client to reuse a preconfigured session.
        playlist_ids: Optional iterable of prod playlist IDs from the cache to
            restrict the sync scope.
        limit: Optional cap on the number of playlists processed after the
            ``playlist_ids`` filter is applied. Useful for smoke tests.

    Returns:
        Summary information about playlist creations, metadata updates, track
        rewrites, and removals applied to the target account.

    Raises:
        RuntimeError: When invoked from the prod environment.
        FileNotFoundError: When any referenced playlist payload is missing.
        ValueError: When cached playlists lack track data.
    """

    if CURRENT_ENV == "prod":
        raise RuntimeError("Refusing to push cache while CURRENT_ENV='prod'.")

    manifest = load_library_manifest(strict=True)
    playlist_items = list(manifest.get("playlists", {}).items())

    if playlist_ids is not None:
        ids = set(playlist_ids)
        playlist_items = [item for item in playlist_items if item[0] in ids]

    playlist_items.sort(key=lambda item: _name_key(item[1].get("name")))

    if limit is not None:
        playlist_items = playlist_items[:limit]

    if not playlist_items:
        return {
            "created": 0,
            "metadata_updates": 0,
            "track_updates": 0,
            "removed": 0,
            "processed": 0,
        }

    sp = spotify_client or _initialize_write_spotify_client()
    current_user = spotify_api_call_with_retry(sp.current_user)
    target_user_id = current_user["id"]

    authored_by_id, authored_by_name = _build_authored_playlist_indexes(sp, target_user_id)
    staging_state = _load_staging_state()
    state_playlists: Dict[str, Any] = staging_state.setdefault("playlists", {})

    summary = {
        "created": 0,
        "metadata_updates": 0,
        "track_updates": 0,
        "removed": 0,
        "processed": len(playlist_items),
    }

    for prod_playlist_id, entry in playlist_items:
        cached_payload = _read_cached_playlist_payload(entry)
        playlist_display_name = (
            cached_payload.get("playlist_name")
            or entry.get("name")
            or prod_playlist_id
        )
        cached_payload.setdefault("playlist_name", playlist_display_name)
        target_uris = _extract_track_uris_from_payload(cached_payload)
        if cached_payload.get("tracks") is None:
            raise ValueError(
                f"Cached playlist {prod_playlist_id} has no track data; run sync_prod_library_cache(include_tracks=True)."
            )

        state_entry = state_playlists.get(prod_playlist_id, {})
        staging_playlist_id = state_entry.get("staging_playlist_id")
        staging_playlist = None

        if staging_playlist_id and staging_playlist_id in authored_by_id:
            staging_playlist = authored_by_id[staging_playlist_id]
        else:
            if staging_playlist_id and staging_playlist_id not in authored_by_id:
                LOGGER.info(
                    "Recorded staging playlist %s missing; will rehydrate",
                    staging_playlist_id,
                )

            staging_playlist = _locate_playlist_by_name(
                authored_by_name,
                playlist_display_name,
            )

            if staging_playlist is None:
                metadata = cached_payload.get("metadata", {})
                staging_playlist = spotify_api_call_with_retry(
                    sp.user_playlist_create,
                    target_user_id,
                    playlist_display_name,
                    public=bool(metadata.get("public", False)),
                    collaborative=bool(metadata.get("collaborative", False)),
                    description=_safe_description(metadata.get("description")),
                )
                summary["created"] += 1
                authored_by_id[staging_playlist["id"]] = staging_playlist
                name_key = _name_key(staging_playlist.get("name"))
                authored_by_name[name_key].append(staging_playlist)

        staging_playlist_id = staging_playlist["id"]

        metadata_changed = _sync_playlist_metadata_if_needed(
            sp,
            staging_playlist,
            cached_payload,
        )
        if metadata_changed:
            summary["metadata_updates"] += 1

        remote_track_uris = _fetch_playlist_track_uris(sp, staging_playlist_id)
        if remote_track_uris != target_uris:
            snapshot_id = _overwrite_playlist_tracks(sp, staging_playlist_id, target_uris)
            if snapshot_id:
                staging_playlist["snapshot_id"] = snapshot_id
            summary["track_updates"] += 1

        state_playlists[prod_playlist_id] = {
            "staging_playlist_id": staging_playlist_id,
            "snapshot_id": staging_playlist.get("snapshot_id"),
            "playlist_name": staging_playlist.get("name"),
            "last_synced_at": datetime.utcnow().isoformat(),
        }

    if playlist_ids is None and limit is None:
        manifest_playlist_ids = set(manifest.get("playlists", {}))
        stale_entries = [pid for pid in list(state_playlists) if pid not in manifest_playlist_ids]

        for prod_playlist_id in stale_entries:
            staging_playlist_id = state_playlists[prod_playlist_id].get("staging_playlist_id")
            if staging_playlist_id and staging_playlist_id in authored_by_id:
                spotify_api_call_with_retry(sp.current_user_unfollow_playlist, staging_playlist_id)
                summary["removed"] += 1
            state_playlists.pop(prod_playlist_id, None)

    staging_state["version"] = STAGING_STATE_VERSION
    staging_state["generated_at"] = datetime.utcnow().isoformat()
    staging_state["owner"] = {
        "id": current_user.get("id"),
        "display_name": current_user.get("display_name"),
        "uri": current_user.get("uri"),
    }
    _save_staging_state(staging_state)

    return summary


def _build_authored_playlist_indexes(sp, owner_id: str):
    by_id: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for playlist in _iter_authored_playlists(sp, owner_id):
        by_id[playlist["id"]] = playlist
        by_name[_name_key(playlist.get("name"))].append(playlist)
    return by_id, by_name


def _read_cached_playlist_payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    relative_file = entry.get("file")
    if not relative_file:
        raise FileNotFoundError("Manifest entry missing playlist file reference")

    playlist_path = LIBRARY_DIR / relative_file
    if not playlist_path.exists():
        raise FileNotFoundError(f"Cached playlist payload missing: {playlist_path}")

    with open(playlist_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_track_uris_from_payload(payload: Dict[str, Any]) -> List[str]:
    uris: List[str] = []
    for item in payload.get("tracks", []) or []:
        track = item.get("track") if isinstance(item, dict) else None
        uri = track.get("uri") if isinstance(track, dict) else None
        if uri:
            uris.append(uri)
    return uris


def _fetch_playlist_track_uris(sp, playlist_id: str) -> List[str]:
    uris: List[str] = []
    offset = 0
    limit = 100

    while True:
        response = spotify_api_call_with_retry(
            sp.playlist_items,
            playlist_id,
            limit=limit,
            offset=offset,
            fields="items(track(uri,is_local)),next",
            additional_types=("track",),
        )

        items = response.get("items", [])
        for item in items:
            track = item.get("track") or {}
            if track.get("is_local"):
                continue
            uri = track.get("uri")
            if uri:
                uris.append(uri)

        if len(items) < limit or not response.get("next"):
            break
        offset += limit

    return uris


def _overwrite_playlist_tracks(sp, playlist_id: str, target_uris: List[str]) -> Optional[str]:
    if not target_uris:
        response = spotify_api_call_with_retry(sp.playlist_replace_items, playlist_id, [])
        return _extract_snapshot_id(response)

    head = target_uris[:100]
    response = spotify_api_call_with_retry(sp.playlist_replace_items, playlist_id, head)
    snapshot_id = _extract_snapshot_id(response)

    for index in range(100, len(target_uris), 100):
        chunk = target_uris[index : index + 100]
        response = spotify_api_call_with_retry(sp.playlist_add_items, playlist_id, chunk)
        latest_snapshot = _extract_snapshot_id(response)
        if latest_snapshot:
            snapshot_id = latest_snapshot

    return snapshot_id


def _sync_playlist_metadata_if_needed(sp, staging_playlist: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    desired_name = payload.get("playlist_name")
    metadata = payload.get("metadata", {})
    desired_description = _safe_description(metadata.get("description"))
    desired_public = bool(metadata.get("public", False))
    desired_collaborative = bool(metadata.get("collaborative", False))

    current_name = staging_playlist.get("name")
    current_description = _safe_description(staging_playlist.get("description"))
    current_public = bool(staging_playlist.get("public", False))
    current_collaborative = bool(staging_playlist.get("collaborative", False))

    changes: Dict[str, Any] = {}
    if desired_name and desired_name != current_name:
        changes["name"] = desired_name
    if desired_description != current_description:
        changes["description"] = desired_description
    if desired_public != current_public:
        changes["public"] = desired_public
    if desired_collaborative != current_collaborative:
        changes["collaborative"] = desired_collaborative

    if not changes:
        return False

    spotify_api_call_with_retry(sp.playlist_change_details, staging_playlist["id"], **changes)
    staging_playlist.update(changes)
    return True


def _locate_playlist_by_name(index: Dict[str, List[Dict[str, Any]]], name: Optional[str]):
    if not name:
        return None
    candidates = index.get(_name_key(name))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Prefer the most recently modified playlist when duplicates exist.
    return max(candidates, key=lambda playlist: playlist.get("snapshot_id", ""))


def _safe_description(description: Optional[str]) -> str:
    return (description or "").strip()


def _name_key(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def _extract_snapshot_id(response: Any) -> Optional[str]:
    if isinstance(response, dict):
        snapshot_id = response.get("snapshot_id")
        if isinstance(snapshot_id, str):
            return snapshot_id
    return None
