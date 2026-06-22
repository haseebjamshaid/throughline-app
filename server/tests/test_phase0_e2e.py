"""Phase 0 end-to-end: real note -> real Ollama embed -> sqlite-vec -> search.

This test hits the LIVE local Ollama embedding model. If Ollama is unreachable
it is skipped (never failed) so CI without a model server stays green.
"""

from __future__ import annotations

from pathlib import Path


from throughline.config import DEFAULT_EMBED_DIM, DEFAULT_OLLAMA_BASE_URL
from throughline.index.search import search
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import Item
from throughline.vault.reader import read_vault

from tests.conftest import requires_ollama

BLADE_RUNNER_ID = "blade_runner_2049.md"
SLOW_MORNING_ID = "slow_morning.md"
FEELING_QUERY = "rainy neon city, someone alone at night"


async def _index(store: VecStore, embeddings: Embeddings, items: list[Item]) -> None:
    """Fingerprint each item's body and upsert into the store."""
    vectors = await embeddings.fingerprint_documents([item.body for item in items])
    for item, vector in zip(items, vectors, strict=True):
        assert len(vector) == DEFAULT_EMBED_DIM  # exactly 256 dims
        store.upsert(item, vector)


@requires_ollama
async def test_note_becomes_searchable_fingerprint(
    sample_vault: Path, cache_dir: Path
) -> None:
    # Arrange
    client = OllamaClient(base_url=DEFAULT_OLLAMA_BASE_URL)
    embeddings = Embeddings(client, embed_dim=DEFAULT_EMBED_DIM)
    items = read_vault(sample_vault)
    assert len(items) == 3

    try:
        with VecStore(cache_dir) as store:
            await _index(store, embeddings, items)
            assert store.count() == 3

            # Act: query a feeling and rank the vault
            results = await search(
                store, embeddings, FEELING_QUERY, inward_only=True, k=3
            )

            # Assert: Blade Runner ranks #1, calm morning is not #1
            assert results, "search returned no results"
            assert results[0].item_id == BLADE_RUNNER_ID, [
                (r.item_id, round(r.score, 4)) for r in results
            ]
            assert results[0].item_id != SLOW_MORNING_ID

            # Every result is a valid, explainable hit
            for result in results:
                assert 0.0 <= result.score <= 1.0
                assert result.why.strip()

            # Idempotency: re-index the same files -> no duplicate rows
            await _index(store, embeddings, items)
            assert store.count() == 3

            # wipe() + rebuild proves the cache is disposable
            store.wipe()
            assert store.count() == 0
            await _index(store, embeddings, items)
            assert store.count() == 3
            rebuilt = await search(store, embeddings, FEELING_QUERY, k=3)
            assert rebuilt[0].item_id == BLADE_RUNNER_ID
    finally:
        await client.aclose()
