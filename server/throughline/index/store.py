"""sqlite-vec backed vector store with an FTS5 keyword side-table.

One git-ignored ``index.db`` holds fingerprints + filterable metadata
(``vec_items``) and a keyword index (``fts_items``) used to explain matches.
Brute-force exact KNN is correct at single-user scale; the whole file is
disposable and rebuildable.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec

from throughline.config import DEFAULT_EMBED_DIM
from throughline.schemas import Item

INDEX_FILE_NAME = "index.db"


@dataclass(frozen=True)
class VecHit:
    """A single KNN row: item metadata plus a raw vector distance."""

    item_id: str
    title: str
    path: str
    type: str
    distance: float


@dataclass(frozen=True)
class StoredRead:
    """A persisted derived read (image or note) for one vault item.

    ``data`` is the JSON-serialized read payload (an :class:`ImageRead` or
    :class:`NoteRead`). ``locked=True`` marks a user-corrected read that intake
    must never overwrite. ``content_hash`` ties the read to the exact file bytes
    it was produced from, enabling read-once idempotency.
    """

    item_id: str
    kind: str
    data: str
    confidence: str
    locked: bool
    content_hash: str
    read_at: str


def _placeholders(count: int) -> str:
    """Return ``?, ?, ...`` with ``count`` placeholders for an IN clause."""
    return ", ".join("?" for _ in range(count))


class VecStore:
    """A sqlite-vec vector store over a single ``index.db`` file."""

    def __init__(self, cache_dir: Path, embed_dim: int = DEFAULT_EMBED_DIM) -> None:
        self._cache_dir = Path(cache_dir)
        self._embed_dim = embed_dim
        self._db_path = self._cache_dir / INDEX_FILE_NAME
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._conn = self._connect()
        self._create_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        """Open the database with the sqlite-vec extension loaded."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def _create_schema(self) -> None:
        """Create the vec0 and fts5 tables if they do not already exist."""
        self._conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(
                item_id TEXT PRIMARY KEY,
                embedding FLOAT[{self._embed_dim}],
                type TEXT,
                is_self INTEGER,
                locked INTEGER,
                +path TEXT,
                +title TEXT,
                +content_hash TEXT
            )
            """
        )
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_items USING fts5(
                item_id, title, body
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reads(
                item_id TEXT PRIMARY KEY,
                kind TEXT,
                data TEXT,
                confidence TEXT,
                locked INTEGER DEFAULT 0,
                content_hash TEXT,
                read_at TEXT
            )
            """
        )
        self._conn.commit()

    def upsert(self, item: Item, vector: list[float]) -> None:
        """Insert or replace the rows for ``item`` in both tables.

        Implemented as delete-then-insert (vec0 has no UPDATE for the embedding
        column), which guarantees idempotency: re-upserting the same ``item.id``
        never creates duplicate rows.
        """
        if len(vector) != self._embed_dim:
            raise ValueError(
                f"vector has {len(vector)} dims, expected {self._embed_dim}"
            )
        serialized = sqlite_vec.serialize_float32(vector)
        self._conn.execute("DELETE FROM vec_items WHERE item_id = ?", (item.id,))
        self._conn.execute("DELETE FROM fts_items WHERE item_id = ?", (item.id,))
        self._conn.execute(
            """
            INSERT INTO vec_items(
                item_id, embedding, type, is_self, locked, path, title, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                serialized,
                item.type,
                1 if item.is_self else 0,
                1 if item.locked else 0,
                item.path,
                item.title,
                item.content_hash,
            ),
        )
        self._conn.execute(
            "INSERT INTO fts_items(item_id, title, body) VALUES (?, ?, ?)",
            (item.id, item.title, item.body),
        )
        self._conn.commit()

    def delete(self, item_id: str) -> None:
        """Remove ``item_id`` from every table (vectors, fts, derived read).

        Used when a vault item is deleted so the index never surfaces a stale
        entry. Idempotent: deleting an absent id is a no-op.
        """
        self._conn.execute("DELETE FROM vec_items WHERE item_id = ?", (item_id,))
        self._conn.execute("DELETE FROM fts_items WHERE item_id = ?", (item_id,))
        self._conn.execute("DELETE FROM reads WHERE item_id = ?", (item_id,))
        self._conn.commit()

    def search(
        self,
        query_vec: list[float],
        *,
        types: list[str] | None = None,
        inward_only: bool = True,
        k: int = 10,
    ) -> list[VecHit]:
        """Return up to ``k`` nearest items by vector distance.

        When ``inward_only`` is False, self-typed items are excluded (the
        privacy-wall filter). When ``types`` is given, only those types match.

        Note: sqlite-vec rejects combining an explicit ``k = ?`` with a
        ``LIMIT`` clause, so KNN bounding is expressed via ``LIMIT`` alone,
        which also lets metadata ``WHERE`` filters apply before truncation.
        """
        filters: list[str] = []
        params: list[object] = [sqlite_vec.serialize_float32(query_vec)]

        if not inward_only:
            filters.append("is_self = 0")
        if types:
            filters.append(f"type IN ({_placeholders(len(types))})")
            params.extend(types)

        where = "WHERE embedding MATCH ?"
        if filters:
            where += " AND " + " AND ".join(filters)

        rows = self._conn.execute(
            f"""
            SELECT item_id, title, path, type, distance
            FROM vec_items
            {where}
            ORDER BY distance
            LIMIT ?
            """,
            (*params, k),
        ).fetchall()
        return [
            VecHit(
                item_id=row["item_id"],
                title=row["title"],
                path=row["path"],
                type=row["type"],
                distance=float(row["distance"]),
            )
            for row in rows
        ]

    def fts_match_terms(self, item_id: str, query: str) -> list[str]:
        """Return query terms that appear in the item's indexed title/body.

        Used to build a human-readable "why it matched" string. An empty query
        or no overlap yields an empty list. FTS errors degrade to [].
        """
        terms = _query_terms(query)
        if not terms:
            return []
        row = self._conn.execute(
            "SELECT title, body FROM fts_items WHERE item_id = ?", (item_id,)
        ).fetchone()
        if row is None:
            return []
        haystack = f"{row['title']} {row['body']}".lower()
        seen: list[str] = []
        for term in terms:
            if term in haystack and term not in seen:
                seen.append(term)
        return seen

    def get_read(self, item_id: str) -> StoredRead | None:
        """Return the persisted read for ``item_id``, or ``None`` if absent."""
        row = self._conn.execute(
            """
            SELECT item_id, kind, data, confidence, locked, content_hash, read_at
            FROM reads WHERE item_id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return StoredRead(
            item_id=row["item_id"],
            kind=row["kind"],
            data=row["data"],
            confidence=row["confidence"],
            locked=bool(row["locked"]),
            content_hash=row["content_hash"],
            read_at=row["read_at"],
        )

    def upsert_read(
        self,
        item_id: str,
        *,
        kind: str,
        data: str,
        confidence: str,
        content_hash: str,
        read_at: str,
    ) -> bool:
        """Insert or replace the derived read for ``item_id``.

        Refuses to overwrite a read whose existing row has ``locked = 1`` (a
        user correction always wins). Returns ``True`` when the row was written
        and ``False`` when it was preserved because it is locked. The ``locked``
        flag itself is only changed via :meth:`set_read_locked`, never here.
        """
        existing = self.get_read(item_id)
        if existing is not None and existing.locked:
            return False
        self._conn.execute(
            """
            INSERT INTO reads(
                item_id, kind, data, confidence, locked, content_hash, read_at
            ) VALUES (?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                kind = excluded.kind,
                data = excluded.data,
                confidence = excluded.confidence,
                content_hash = excluded.content_hash,
                read_at = excluded.read_at
            """,
            (item_id, kind, data, confidence, content_hash, read_at),
        )
        self._conn.commit()
        return True

    def set_read_locked(self, item_id: str, locked: bool) -> None:
        """Set the ``locked`` flag on an existing read (no-op if absent)."""
        self._conn.execute(
            "UPDATE reads SET locked = ? WHERE item_id = ?",
            (1 if locked else 0, item_id),
        )
        self._conn.commit()

    def is_up_to_date(self, item_id: str, content_hash: str) -> bool:
        """Return True when ``item_id`` already has a read for ``content_hash``.

        This is the read-once guard: an item whose bytes are unchanged since its
        last read is skipped by intake.
        """
        existing = self.get_read(item_id)
        return existing is not None and existing.content_hash == content_hash

    def count_reads(self) -> int:
        """Return the number of persisted derived reads."""
        row = self._conn.execute("SELECT COUNT(*) AS n FROM reads").fetchone()
        return int(row["n"])

    def count(self) -> int:
        """Return the number of indexed items."""
        row = self._conn.execute("SELECT COUNT(*) AS n FROM vec_items").fetchone()
        return int(row["n"])

    def wipe(self) -> None:
        """Drop all rows from every table (rebuildable cache)."""
        self._conn.execute("DELETE FROM vec_items")
        self._conn.execute("DELETE FROM fts_items")
        self._conn.execute("DELETE FROM reads")
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> VecStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _query_terms(query: str) -> list[str]:
    """Split a query into lowercased alphanumeric terms of length >= 3."""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in query.lower())
    return [t for t in cleaned.split() if len(t) >= 3]
