"""Batch Fit — rank several candidates by how close they sit to the user's taste.

Where the single-item :mod:`~throughline.fit.check` runs a full reasoning pass,
batch ranking is the fast lane: each candidate is embedded and compared to the
user's own taste items via the same vector store, so a handful (or a hundred)
can be ranked in one breath without a slow per-item model call. The score is the
candidate's closeness to its nearest taste match, surfaced with that match so the
ranking is explainable ("closest to <title>").
"""

from __future__ import annotations

from pydantic import BaseModel

from throughline.index.search import search
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings

# Candidates are ranked against the user's outward-shareable taste only (the
# privacy wall keeps self-material out of an outward-style comparison).
_INWARD_ONLY = False
# Only the single nearest taste match is needed to score + explain each candidate.
_SEARCH_K = 1


class RankedCandidate(BaseModel):
    """One candidate scored against the user's taste, for the batch ranking.

    ``score`` is 0–100 (closeness to the nearest taste item). ``closest_title``
    is that nearest item's title (empty when the vault has nothing to compare
    against), making the rank explainable.
    """

    text: str
    score: int
    closest_title: str = ""
    closest_id: str = ""


async def rank_candidates(
    store: VecStore,
    embeddings: Embeddings,
    candidates: list[str],
) -> list[RankedCandidate]:
    """Rank ``candidates`` by closeness to the user's taste, highest first.

    Each non-blank candidate is embedded and matched against the user's taste
    items; its score is the nearest match's similarity scaled to 0–100. Blank
    candidates are skipped. Returns the ranked list (stable for equal scores).
    """
    ranked: list[RankedCandidate] = []
    for text in candidates:
        cleaned = text.strip()
        if not cleaned:
            continue
        hits = await search(
            store, embeddings, cleaned, inward_only=_INWARD_ONLY, k=_SEARCH_K
        )
        if hits:
            top = hits[0]
            ranked.append(
                RankedCandidate(
                    text=cleaned,
                    score=round(top.score * 100),
                    closest_title=top.title,
                    closest_id=top.item_id,
                )
            )
        else:
            ranked.append(RankedCandidate(text=cleaned, score=0))

    ranked.sort(key=lambda c: c.score, reverse=True)
    return ranked
