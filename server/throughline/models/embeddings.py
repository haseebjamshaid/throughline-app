"""Fingerprinting: turn text into a normalized 256-dim vector.

EmbeddingGemma is a Matryoshka model, so the first ``embed_dim`` dimensions of
its 768-dim output are themselves a valid (smaller) embedding. We truncate to
256 dims and L2-normalize so that cosine similarity reduces to a dot product.
"""

from __future__ import annotations

import numpy as np

from throughline.config import DEFAULT_EMBED_DIM
from throughline.models.ollama_client import OllamaClient, OllamaError


def _truncate_and_normalize(vector: list[float], dim: int) -> list[float]:
    """Truncate ``vector`` to ``dim`` dims (Matryoshka) then L2-normalize.

    Raises :class:`OllamaError` if the source vector is shorter than ``dim``.
    A zero vector is returned unchanged (after truncation) to avoid division by
    zero; the result still has exactly ``dim`` elements.
    """
    if len(vector) < dim:
        raise OllamaError(
            f"embedding has {len(vector)} dims but {dim} are required "
            "(is the embed model correct?)"
        )
    truncated = np.asarray(vector[:dim], dtype=np.float32)
    norm = float(np.linalg.norm(truncated))
    if norm == 0.0:
        return truncated.tolist()
    return (truncated / norm).tolist()


class Embeddings:
    """Produce normalized, dimension-truncated fingerprints via Ollama."""

    def __init__(self, client: OllamaClient, embed_dim: int = DEFAULT_EMBED_DIM) -> None:
        self._client = client
        self._embed_dim = embed_dim

    @property
    def embed_dim(self) -> int:
        return self._embed_dim

    async def fingerprint_documents(self, texts: list[str]) -> list[list[float]]:
        """Return a normalized 256-dim fingerprint per document."""
        if not texts:
            return []
        raw = await self._client.embed_documents(texts)
        return [_truncate_and_normalize(vec, self._embed_dim) for vec in raw]

    async def fingerprint_query(self, text: str) -> list[float]:
        """Return a normalized 256-dim fingerprint for a search query."""
        raw = await self._client.embed_query(text)
        return _truncate_and_normalize(raw, self._embed_dim)
