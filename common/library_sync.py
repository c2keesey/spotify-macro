"""Unified Spotify library cache synchronization.

This module replaces the old scattered caching setup with a single entry point
that keeps a normalized cache of the prod account's authored playlists in
``data/library``. The cache is organized around a manifest file plus one JSON
file per playlist containing lightweight track data.

Typical usage::

    from common.library_sync import sync_prod_library_cache

    summary = sync_prod_library_cache()
    print(summary["updated"], "playlists refreshed")

On first run the sync function will automatically migrate any legacy playlist
dumps that exist in ``data/playlists`` so that older tooling keeps working.
"""

from __future__ import annotations

import json
import logging
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
) -> Dict[str, Any]:
    """Synchronize the prod account's playlists into ``data/library``.

    Args:
        force_full_refresh: If ``True`` every authored playlist is re-fetched
            even when the snapshot_id indicates no change.
        spotify_client: Optional Spotipy client to reuse an existing session.

    Args:
        force_full_refresh: If ``True`` every authored playlist is re-fetched
            even when the snapshot_id indicates no change.
        spotify_client: Optional Spotipy client to reuse an existing session.
        playlist_ids: Optional iterable of playlist IDs to restrict the sync to
            a specific subset (useful for testing).
        limit: Optional maximum number of playlists to sync. Applied after
            filtering by ``playlist_ids``.

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
            playlist_file_payload = _fetch_playlist_payload(sp, playlist_obj)
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


def _fetch_playlist_payload(sp, playlist_obj: Dict[str, Any]) -> Dict[str, Any]:
    playlist_id = playlist_obj["id"]
    tracks: List[Dict[str, Any]] = []
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
        "track_count": len(tracks),
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
