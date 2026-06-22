"""Unit tests for the sqlite-vec store (synthetic vectors, no Ollama)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from throughline.config import DEFAULT_EMBED_DIM
from throughline.index.search import distance_to_score
from throughline.index.store import VecStore
from throughline.schemas import Item


def _unit_vector(seed: int, dim: int = DEFAULT_EMBED_DIM) -> list[float]:
    """Return a deterministic L2-normalized random vector."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    return (vec / np.linalg.norm(vec)).tolist()


def _item(item_id: str, *, is_self: bool = False, item_type: str = "movie") -> Item:
    return Item(
        id=item_id,
        path=f"/vault/{item_id}",
        type=item_type,
        title=item_id,
        body=f"body for {item_id}",
        content_hash="hash",
        is_self=is_self,
    )


def test_upsert_is_idempotent(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        vec = _unit_vector(1)
        item = _item("a.md")

        store.upsert(item, vec)
        store.upsert(item, vec)  # re-upsert same id
        store.upsert(item, vec)

        assert store.count() == 1


def test_wipe_then_rebuild(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        store.upsert(_item("a.md"), _unit_vector(1))
        store.upsert(_item("b.md"), _unit_vector(2))
        assert store.count() == 2

        store.wipe()
        assert store.count() == 0

        store.upsert(_item("a.md"), _unit_vector(1))
        assert store.count() == 1


def test_inward_only_filter_excludes_self(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        target = _unit_vector(5)
        store.upsert(_item("self.md", is_self=True, item_type="journal"), target)
        store.upsert(_item("public.md", is_self=False, item_type="movie"), _unit_vector(6))

        outward = store.search(target, inward_only=False, k=10)
        ids = {hit.item_id for hit in outward}
        assert "self.md" not in ids
        assert "public.md" in ids


def test_type_filter(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        store.upsert(_item("m.md", item_type="movie"), _unit_vector(7))
        store.upsert(_item("s.md", item_type="song"), _unit_vector(8))

        hits = store.search(_unit_vector(7), types=["movie"], k=10)
        assert {h.item_id for h in hits} == {"m.md"}


def test_wrong_dim_vector_rejected(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        with pytest.raises(ValueError):
            store.upsert(_item("a.md"), [0.1, 0.2, 0.3])


def test_delete_removes_item_from_index_and_reads(cache_dir: Path) -> None:
    with VecStore(cache_dir) as store:
        store.upsert(_item("a.md"), _unit_vector(1))
        store.upsert(_item("b.md"), _unit_vector(2))
        store.upsert_read(
            "a.md",
            kind="note",
            data="{}",
            confidence="low",
            content_hash="h",
            read_at="2026-06-21T00:00:00+00:00",
        )
        assert store.count() == 2
        assert store.count_reads() == 1

        store.delete("a.md")

        # The item is gone from vectors, fts, and reads — but its neighbour stays.
        assert store.count() == 1
        assert store.count_reads() == 0
        assert store.get_read("a.md") is None
        ids = {hit.item_id for hit in store.search(_unit_vector(2), k=10)}
        assert ids == {"b.md"}

        # Deleting an absent id is a harmless no-op.
        store.delete("missing.md")
        assert store.count() == 1


def test_distance_to_score_bounds() -> None:
    # identical (d=0) -> 1.0 ; orthogonal (d=sqrt2) -> ~0 ; opposite (d=2) -> 0
    assert distance_to_score(0.0) == pytest.approx(1.0)
    assert distance_to_score(2.0**0.5) == pytest.approx(0.0, abs=1e-6)
    assert distance_to_score(2.0) == 0.0
    assert 0.0 <= distance_to_score(1.0) <= 1.0
