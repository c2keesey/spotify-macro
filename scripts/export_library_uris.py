#!/usr/bin/env python3
"""Export authored playlists to a minimal playlist->URIs JSON snapshot.

Usage:
    uv run python scripts/export_library_uris.py [--out /absolute/path.json] [--limit N]

By default, writes to PROJECT_ROOT/data/playlist_uris.json.
Requires prod credentials (SPOTIFY_ENV=prod) to reflect the canonical library.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.config import PROJECT_ROOT
from common.spotify_utils import initialize_spotify_client, spotify_api_call_with_retry


DEFAULT_SCOPE = "playlist-read-private playlist-read-collaborative"


def _initialize_spotify_client():
    return initialize_spotify_client(DEFAULT_SCOPE)


def _iter_authored_playlists(sp, owner_id: str):
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


def _build_snapshot(sp, *, limit: Optional[int] = None) -> Dict[str, Any]:
    current_user = spotify_api_call_with_retry(sp.current_user)
    user_id = current_user["id"]

    playlists: Dict[str, Any] = {}
    count = 0
    for playlist in _iter_authored_playlists(sp, user_id):
        playlist_id = playlist.get("id")
        if not playlist_id:
            continue
        uris = _fetch_playlist_track_uris(sp, playlist_id)
        playlists[playlist_id] = {
            "name": playlist.get("name", playlist_id),
            "description": playlist.get("description"),
            "public": bool(playlist.get("public", False)),
            "collaborative": bool(playlist.get("collaborative", False)),
            "snapshot_id": playlist.get("snapshot_id", ""),
            "uris": uris,
        }
        count += 1
        if limit is not None and count >= limit:
            break

    return {
        "version": "uris-1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "owner": {
            "id": current_user.get("id"),
            "display_name": current_user.get("display_name"),
            "uri": current_user.get("uri"),
        },
        "playlists": playlists,
    }


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Export authored Spotify playlists to a minimal URIs snapshot")
    parser.add_argument("--out", dest="out_path", default=str(PROJECT_ROOT / "data" / "playlist_uris.json"), help="Output JSON file path")
    parser.add_argument("--limit", dest="limit", type=int, default=None, help="Optional maximum number of playlists to export (for smoke tests)")
    args = parser.parse_args(argv)

    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sp = _initialize_spotify_client()
    snapshot = _build_snapshot(sp, limit=args.limit)

    tmp_path = out_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
    tmp_path.replace(out_path)

    print(f"Wrote {out_path} with {len(snapshot['playlists'])} playlists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
