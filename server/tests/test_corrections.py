"""Corrections win: a locked read is never overwritten by intake.

Verifies the store-level guard directly: once a read is locked (a user
correction), :meth:`VecStore.upsert_read` refuses to overwrite it and returns
``False``, leaving the original payload intact.
"""

from __future__ import annotations

from pathlib import Path

from throughline.index.store import VecStore
from throughline.schemas import NoteRead

_ITEM_ID = "note.md"
_NOW = "2026-06-21T00:00:00+00:00"


def _read_payload(theme: str) -> str:
    return NoteRead(themes=[theme], feelings=["f"], confidence="high").model_dump_json()


def test_locked_read_is_preserved(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        # Arrange: an initial machine read, then a user correction that locks it.
        wrote = store.upsert_read(
            _ITEM_ID,
            kind="note",
            data=_read_payload("original"),
            confidence="high",
            content_hash="hash-1",
            read_at=_NOW,
        )
        assert wrote is True
        store.set_read_locked(_ITEM_ID, True)

        # Act: intake tries to overwrite with a fresh read for new bytes.
        overwrote = store.upsert_read(
            _ITEM_ID,
            kind="note",
            data=_read_payload("machine-rewrite"),
            confidence="low",
            content_hash="hash-2",
            read_at=_NOW,
        )

        # Assert: the write was refused and the locked read is untouched.
        assert overwrote is False
        preserved = store.get_read(_ITEM_ID)
        assert preserved is not None
        assert preserved.locked is True
        assert preserved.confidence == "high"
        assert preserved.content_hash == "hash-1"
        assert "original" in preserved.data
        assert "machine-rewrite" not in preserved.data


def test_unlocking_allows_overwrite(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        store.upsert_read(
            _ITEM_ID,
            kind="note",
            data=_read_payload("original"),
            confidence="high",
            content_hash="hash-1",
            read_at=_NOW,
        )
        store.set_read_locked(_ITEM_ID, True)
        assert store.upsert_read(
            _ITEM_ID,
            kind="note",
            data=_read_payload("blocked"),
            confidence="low",
            content_hash="hash-2",
            read_at=_NOW,
        ) is False

        # Act: unlock, then overwrite is allowed again.
        store.set_read_locked(_ITEM_ID, False)
        assert store.upsert_read(
            _ITEM_ID,
            kind="note",
            data=_read_payload("updated"),
            confidence="medium",
            content_hash="hash-3",
            read_at=_NOW,
        ) is True

        updated = store.get_read(_ITEM_ID)
        assert updated is not None
        assert "updated" in updated.data
        assert updated.content_hash == "hash-3"
