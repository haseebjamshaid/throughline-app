"""Find the one connection in the user's OWN vault for a stuck moment.

Every nudge the Thread gives must be grounded in the user's own material — not
a generic platitude. ``find_connection`` semantically searches the vault for
what the user is stuck on and picks the single most relevant item, PREFERRING
self types (journal / experience / ambition / fear — their own words and past)
over taste types, and pulls a short representative quote from that item's body.
"""

from __future__ import annotations

from throughline.index.search import search
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.schemas import SELF_TYPES, Item, SearchResult

# How many candidates to retrieve before re-ranking toward self types.
_SEARCH_K = 8
# A quote longer than this is trimmed to its first sentence(s) under the cap.
_MAX_QUOTE_CHARS = 240


def _item_by_id(items: list[Item], item_id: str) -> Item | None:
    """Return the loaded :class:`Item` for ``item_id`` (or ``None``)."""
    return next((it for it in items if it.id == item_id), None)


def _pick_hit(hits: list[SearchResult], items: list[Item]) -> SearchResult | None:
    """Choose the most relevant hit, preferring the user's own (self) material.

    Hits arrive already ranked by relevance. We keep that order but float the
    first self-typed hit to the front so the connection is grounded in the
    user's own words/past when one is relevant; otherwise the top hit wins.
    """
    if not hits:
        return None
    for hit in hits:
        item = _item_by_id(items, hit.item_id)
        if item is not None and item.type in SELF_TYPES:
            return hit
    return hits[0]


def extract_quote(body: str) -> str:
    """Pull a short, representative quote from an item body.

    Picks the first non-empty line (collapsing internal whitespace) and trims it
    to a sentence boundary under the length cap so the quote reads cleanly. An
    empty body yields an empty string.
    """
    normalized = " ".join(body.split())
    if not normalized:
        return ""
    if len(normalized) <= _MAX_QUOTE_CHARS:
        return normalized

    truncated = normalized[:_MAX_QUOTE_CHARS]
    # Prefer cutting at the last sentence end within the window; else last space.
    cut = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))
    if cut == -1:
        cut = truncated.rfind(" ")
    if cut == -1:
        return truncated.rstrip()
    return truncated[: cut + 1].rstrip()


async def find_connection(
    store: VecStore,
    embeddings: Embeddings,
    items: list[Item],
    stuck: str,
) -> tuple[Item, str] | None:
    """Return the best ``(item, quote)`` for ``stuck``, or ``None`` if empty.

    Searches the whole vault (``inward_only=True`` so the user's own self-typed
    material is eligible), re-ranks toward self types, and lifts a representative
    quote. Returns ``None`` only when the vault has no items to connect to.
    """
    if not items:
        return None

    query = stuck.strip()
    if not query:
        return None

    hits = await search(store, embeddings, query, inward_only=True, k=_SEARCH_K)
    chosen = _pick_hit(hits, items)
    if chosen is None:
        return None

    item = _item_by_id(items, chosen.item_id)
    if item is None:
        return None

    return item, extract_quote(item.body)
