"""Pause is honoured between items: a paused worker makes no progress.

The model readers and manager are stubbed (no Ollama). The worker is paused
before its run starts; the test confirms it blocks at the pause gate without
completing, then resumes and finishes the full pass.
"""

from __future__ import annotations

import asyncio
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

_SETTLE_SECONDS = 0.05


class _StubEmbeddings(Embeddings):
    """Deterministic 256-dim fingerprints — no network."""

    def __init__(self, embed_dim: int = 256) -> None:  # noqa: D401 - test stub
        self._embed_dim = embed_dim

    async def fingerprint_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (self._embed_dim - 1) for _ in texts]


@pytest.fixture
def stub_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace model readers / manager / resolver with fast stubs."""

    async def fake_read_note(_client: object, _item: object, _model: str) -> NoteRead:
        return NoteRead(themes=["t"], feelings=["f"], confidence="high")

    async def fake_read_image(_client: object, _path: object, **_kw: object) -> ImageRead:
        return ImageRead(description="d", confidence="high")

    async def fake_use(_self: object, _role: str) -> str:
        return "stub-model"

    async def fake_resolve(_settings: object, _client: object) -> str:
        return "stub-text-model"

    monkeypatch.setattr(worker_module, "read_note", fake_read_note)
    monkeypatch.setattr(worker_module, "read_image", fake_read_image)
    monkeypatch.setattr(worker_module.ModelManager, "use", fake_use)
    monkeypatch.setattr(worker_module, "resolve_text_model", fake_resolve)


async def test_worker_blocks_while_paused_then_completes(
    sample_vault: Path, cache_dir: Path, stub_readers: None
) -> None:
    # Arrange
    settings = get_settings()
    client = OllamaClient()
    store = VecStore(cache_dir)
    embeddings = _StubEmbeddings(embed_dim=settings.embed_dim)
    items = read_vault(sample_vault)
    worker = IntakeWorker(settings, client, store, embeddings, items)

    try:
        # Act: pause before the run, then start it.
        worker.pause()
        assert worker.is_paused is True
        task = asyncio.create_task(worker.run())

        # Let the event loop run; the worker should block at the gate.
        await asyncio.sleep(_SETTLE_SECONDS)

        # Assert: no progress and the task is still alive (parked on the gate).
        assert worker.done == 0
        assert store.count_reads() == 0
        assert not task.done()

        # Act: resume; the worker should now finish the whole pass.
        worker.resume()
        assert worker.is_paused is False
        await asyncio.wait_for(task, timeout=5.0)

        # Assert: all items processed after resume.
        assert worker.done == len(items)
        assert store.count_reads() == len(items)
    finally:
        store.close()
        await client.aclose()
