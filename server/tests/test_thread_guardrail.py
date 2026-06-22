"""The Thread's actionable-step guardrail + the no-vault guard. No model.

The model call (``OllamaClient.complete_json``) and the vault search
(``find_connection``) are monkeypatched, so Ollama is never touched. The point
is the HARD RULE: the Thread ALWAYS ends on a concrete, non-empty next step —
even when the model returns a blank or analysis-only step it must never degrade
to pure analysis. We also assert grounding (a real vault item id) and the 409
when no vault is connected.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from throughline.config import Settings
from throughline.index.store import VecStore
from throughline.main import create_app
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import Item
from throughline.thread import engine as engine_module
from throughline.thread.engine import finalize, pull_thread


def _sample_item() -> Item:
    """A real-looking self-typed vault item to ground the connection in."""
    return Item(
        id="the_move.md",
        path="/vault/the_move.md",
        type="ambition",
        title="build a creative life i'm proud of",
        body=(
            "i keep planning the move and not starting it — drafting the same "
            "notes about quitting, about a studio of my own."
        ),
        content_hash="abc123",
        is_self=True,
    )


class _FakeState:
    """A minimal AppState stand-in carrying just what the engine reads."""

    def __init__(self, settings: Settings, store: VecStore, client: OllamaClient):
        self.settings = settings
        self.store = store
        self.client = client
        self.embeddings = Embeddings(client, embed_dim=settings.embed_dim)
        self.items = [_sample_item()]


@pytest.fixture
def fake_state(tmp_path: Path) -> _FakeState:
    """A connected (real store, no Ollama traffic) state for engine tests."""
    cache = tmp_path / ".throughline"
    settings = Settings(vault_path=tmp_path / "vault", cache_dir=cache)
    store = VecStore(cache, embed_dim=settings.embed_dim)
    client = OllamaClient()
    return _FakeState(settings, store, client)


def _stub_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``find_connection`` return a fixed (item, quote) — no embeddings."""

    async def _fake_find(*_args: object, **_kwargs: object) -> tuple[Item, str]:
        item = _sample_item()
        return item, "i keep planning the move and not starting it"

    monkeypatch.setattr(engine_module, "find_connection", _fake_find)


def _stub_model(monkeypatch: pytest.MonkeyPatch, payload: dict[str, str]) -> None:
    """Make every ``complete_json`` call return ``payload`` — no Ollama."""

    async def _fake_complete(*_args: object, **_kwargs: object) -> dict[str, str]:
        return payload

    monkeypatch.setattr(OllamaClient, "complete_json", _fake_complete)


async def test_blank_step_yields_actionable_fallback(
    fake_state: _FakeState, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: the model returns a question but a BLANK next step.
    _stub_connection(monkeypatch)
    _stub_model(
        monkeypatch,
        {"question": "what's the smallest first move?", "connection_why": "", "next_step": ""},
    )

    # Act
    try:
        turn = await pull_thread(fake_state, "i keep planning and never starting.")
    finally:
        fake_state.store.close()
        await fake_state.client.aclose()

    # Assert: NEVER pure analysis — the step is non-empty and actionable.
    assert turn.next_step.text.strip(), "guardrail returned an empty step"
    assert not turn.next_step.text.strip().endswith("?")
    # Grounded in a REAL vault item id.
    assert turn.connection is not None
    assert turn.connection.item_id == "the_move.md"
    assert turn.question, "question must not be empty"


async def test_analysis_only_step_is_rejected(
    fake_state: _FakeState, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: the model keeps returning a non-actionable "think about it" step.
    _stub_connection(monkeypatch)
    _stub_model(
        monkeypatch,
        {
            "question": "why does starting feel hard?",
            "connection_why": "you already wrote about this",
            "next_step": "think about what's really stopping you",
        },
    )

    # Act
    try:
        turn = await pull_thread(fake_state, "stuck on starting.")
    finally:
        fake_state.store.close()
        await fake_state.client.aclose()

    # Assert: the analysis-only step was rejected and replaced with a real action.
    assert "think about" not in turn.next_step.text.lower()
    assert turn.next_step.text.strip()


async def test_finalize_always_returns_a_step(
    fake_state: _FakeState, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: model returns literally nothing usable.
    _stub_model(monkeypatch, {})
    item = _sample_item()

    # Act: finalize directly with a known connection pair.
    try:
        question, connection, next_step = await finalize(
            fake_state.client,
            "qwen3.5:9b",
            fake_state.store,
            "i can't start.",
            (item, "i keep planning the move"),
            None,
        )
    finally:
        fake_state.store.close()
        await fake_state.client.aclose()

    # Assert: an actionable step + a grounded connection, even from empty output.
    assert next_step.text.strip()
    assert next_step.size == "normal"
    assert connection is not None and connection.item_id == "the_move.md"
    assert question.strip()


def test_thread_409_without_vault(tmp_path: Path) -> None:
    # No store attached -> no vault connected -> 409.
    settings = Settings(vault_path=tmp_path / "vault")
    with TestClient(create_app(settings)) as client:
        resp = client.post("/thread", json={"stuck": "i'm stuck"})
    assert resp.status_code == 409
