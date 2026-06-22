"""Disk persistence for Thread turns and momentum.

Two rebuildable JSON files live in the cache dir:

* ``threads.json`` — a map of ``turn_id -> ThreadTurn`` so the "different /
  smaller / did-it" controls can recall the original stuck text and connection
  for a turn across requests.
* ``momentum.json`` — an append-only log of closed loops (one entry per "did
  it"), the small record that proves the engine moved someone forward.

Both files degrade gracefully: a missing or corrupt file reads as empty rather
than raising, so a damaged cache never blocks the Thread.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from throughline.schemas import ThreadTurn

THREADS_FILE_NAME = "threads.json"
MOMENTUM_FILE_NAME = "momentum.json"


def _threads_path(cache_dir: Path) -> Path:
    return Path(cache_dir) / THREADS_FILE_NAME


def _momentum_path(cache_dir: Path) -> Path:
    return Path(cache_dir) / MOMENTUM_FILE_NAME


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _load_threads_raw(cache_dir: Path) -> dict[str, object]:
    """Return the raw ``turn_id -> turn dict`` map (``{}`` on miss/corrupt)."""
    path = _threads_path(cache_dir)
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def save_turn(cache_dir: Path, turn: ThreadTurn) -> None:
    """Persist ``turn`` into ``threads.json`` keyed by its id (immutably).

    Reads the existing map, returns a NEW map with the turn added/replaced, and
    writes it back — the on-disk state is replaced wholesale, never mutated in
    place.
    """
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    existing = _load_threads_raw(cache)
    updated = {**existing, turn.id: turn.model_dump()}
    _threads_path(cache).write_text(
        json.dumps(updated, indent=2), encoding="utf-8"
    )


def load_turn(cache_dir: Path, turn_id: str) -> ThreadTurn | None:
    """Return the persisted :class:`ThreadTurn` for ``turn_id``, or ``None``.

    A turn whose stored shape no longer validates degrades to ``None`` rather
    than raising, so a stale cache never crashes a control action.
    """
    raw = _load_threads_raw(cache_dir).get(turn_id)
    if not isinstance(raw, dict):
        return None
    try:
        return ThreadTurn.model_validate(raw)
    except ValueError:
        return None


def log_momentum(cache_dir: Path, turn_id: str) -> None:
    """Append a closed-loop record for ``turn_id`` to ``momentum.json``.

    The log is a JSON array of ``{"turn_id", "at"}`` entries. A missing or
    corrupt file is treated as an empty log so the append always succeeds.
    """
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    path = _momentum_path(cache)

    entries: list[dict[str, str]] = []
    if path.exists():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, list):
                entries = [e for e in parsed if isinstance(e, dict)]
        except (OSError, ValueError):
            entries = []

    appended = [*entries, {"turn_id": turn_id, "at": _now_iso()}]
    path.write_text(json.dumps(appended, indent=2), encoding="utf-8")
