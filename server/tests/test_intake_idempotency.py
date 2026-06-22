"""Read-once idempotency: a second intake pass skips every already-read item.

The note/image readers are monkeypatched with fast deterministic stubs so this
test never touches Ollama. It proves the worker's ``is_up_to_date`` guard skips
unchanged items, leaving the vec_items row count and read count stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from throughline.config import get_settings
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import ImageRead, NoteRead
from throughline.vault.reader import read_vault
from throughline.intake import worker as worker_module
from throughline.intake.worker import IntakeWorker


class _StubEmbeddings(Embeddings):
    """Deterministic 256-dim fingerprints — no network, no Ollama."""

    def __init__(self, embed_dim: int = 256) -> None:  # noqa: D401 - test stub
        self._embed_dim = embed_dim

    async def fingerprint_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def fingerprint_query(self, text: str) -> list[float]:
        return self._vec(text)

    def _vec(self, text: str) -> list[float]:
        seed = (len(text) % 7) + 1
        return [1.0 / seed] + [0.0] * (self._embed_dim - 1)


@pytest.fixture
def stub_readers(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Replace the model readers and model manager with fast counters."""
    calls = {"note": 0, "image": 0}

    async def fake_read_note(_client: object, item: object, _model: str) -> NoteRead:
        calls["note"] += 1
        return NoteRead(themes=["t"], feelings=["f"], confidence="high")

    async def fake_read_image(_client: object, _path: object, **_kw: object) -> ImageRead:
        calls["image"] += 1
        return ImageRead(description="d", confidence="high")

    async def fake_use(_self: object, _role: str) -> str:
        return "stub-model"

    async def fake_resolve(_settings: object, _client: object) -> str:
        return "stub-text-model"

    monkeypatch.setattr(worker_module, "read_note", fake_read_note)
    monkeypatch.setattr(worker_module, "read_image", fake_read_image)
    monkeypatch.setattr(worker_module.ModelManager, "use", fake_use)
    monkeypatch.setattr(worker_module, "resolve_text_model", fake_resolve)
    return calls


async def test_second_pass_skips_all(
    sample_vault: Path, cache_dir: Path, stub_readers: dict[str, int]
) -> None:
    # Arrange
    settings = get_settings()
    client = OllamaClient()
    store = VecStore(cache_dir)
    embeddings = _StubEmbeddings(embed_dim=settings.embed_dim)
    items = read_vault(sample_vault)
    assert len(items) == 3

    try:
        # Act: first pass reads everything
        worker_one = IntakeWorker(settings, client, store, embeddings, items)
        await worker_one.run()

        first_reads = store.count_reads()
        first_vecs = store.count()
        first_note_calls = stub_readers["note"]
        assert first_reads == 3
        assert first_vecs == 3
        assert first_note_calls == 3  # all three fixtures are notes

        # Act: second pass over the same bytes
        worker_two = IntakeWorker(settings, client, store, embeddings, items)
        await worker_two.run()

        # Assert: nothing was re-read, no duplicate rows
        assert stub_readers["note"] == first_note_calls  # no new reader calls
        assert store.count_reads() == first_reads
        assert store.count() == first_vecs
        assert worker_two.done == 3  # counted as done (skipped) but not re-read
    finally:
        store.close()
        await client.aclose()


async def test_force_rereads_all(
    sample_vault: Path, cache_dir: Path, stub_readers: dict[str, int]
) -> None:
    # Arrange
    settings = get_settings()
    client = OllamaClient()
    store = VecStore(cache_dir)
    embeddings = _StubEmbeddings(embed_dim=settings.embed_dim)
    items = read_vault(sample_vault)

    try:
        await IntakeWorker(settings, client, store, embeddings, items).run()
        assert stub_readers["note"] == 3

        # Act: force=True bypasses the read-once guard
        await IntakeWorker(settings, client, store, embeddings, items).run(force=True)

        # Assert: re-read, still no duplicate rows
        assert stub_readers["note"] == 6
        assert store.count() == 3
        assert store.count_reads() == 3
    finally:
        store.close()
        await client.aclose()
