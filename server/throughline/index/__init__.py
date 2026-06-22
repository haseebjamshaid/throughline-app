"""Vector index: sqlite-vec store plus explainable semantic search."""

from throughline.index.search import search
from throughline.index.store import StoredRead, VecHit, VecStore

__all__ = ["StoredRead", "VecHit", "VecStore", "search"]
