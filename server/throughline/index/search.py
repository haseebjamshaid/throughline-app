"""Explainable semantic search over the vector store.

Embeds a query, runs KNN against :class:`VecStore`, converts the raw distance
into a ``[0, 1]`` similarity score, and attaches a human-readable ``why``.

Score formula
-------------
sqlite-vec's default metric for a ``FLOAT`` vec0 column is Euclidean (L2)
distance. Fingerprints are L2-normalized, so for unit vectors the L2 distance
``d`` and cosine similarity relate as ``cos = 1 - d**2 / 2``. We therefore map

    score = clamp(1 - d**2 / 2, 0.0, 1.0)

which yields 1.0 for an identical vector, ~0.0 for orthogonal, and clamps the
negative-cosine tail to 0.0. The result is a stable, interpretable percentage.
"""

from __future__ import annotations

from throughline.models.embeddings import Embeddings
from throughline.schemas import SearchResult
from throughline.index.store import VecHit, VecStore

_SCORE_MIN = 0.0
_SCORE_MAX = 1.0


def distance_to_score(distance: float) -> float:
    """Convert an L2 distance between unit vectors to a cosine-based score."""
    cosine = 1.0 - (distance * distance) / 2.0
    return max(_SCORE_MIN, min(_SCORE_MAX, cosine))


def _build_why(store: VecStore, hit: VecHit, query: str) -> str:
    """Return a human-readable reason ``hit`` matched ``query``.

    Prefers overlapping query terms found in the item's title/body (via FTS5);
    falls back to the matched type/title when there is no lexical overlap so the
    explanation is never empty.
    """
    terms = store.fts_match_terms(hit.item_id, query)
    if terms:
        joined = ", ".join(terms)
        return f"shares the words: {joined}"
    return f"closest {hit.type} by overall vibe: “{hit.title}”"


async def search(
    store: VecStore,
    embeddings: Embeddings,
    query: str,
    *,
    types: list[str] | None = None,
    inward_only: bool = True,
    k: int = 10,
) -> list[SearchResult]:
    """Run an explainable semantic search and return ranked results.

    Raises ``ValueError`` for an empty query so callers fail fast.
    """
    if not query.strip():
        raise ValueError("search query must not be empty")

    query_vec = await embeddings.fingerprint_query(query)
    hits = store.search(query_vec, types=types, inward_only=inward_only, k=k)
    return [
        SearchResult(
            item_id=hit.item_id,
            title=hit.title,
            path=hit.path,
            score=distance_to_score(hit.distance),
            why=_build_why(store, hit, query),
        )
        for hit in hits
    ]
