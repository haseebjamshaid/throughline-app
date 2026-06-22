"""Live Thread run against the real reasoning model — the heart, end to end.

Connects the sample vault and drives the unstuck engine through the FastAPI app
with ``qwen3.5:9b`` (skips cleanly when Ollama is unreachable OR the model is not
pulled). Proves the HARD RULES:

* ``POST /thread`` returns a non-empty sharp question, a connection citing a
  REAL sample item id with a quote, and a NON-EMPTY concrete next step.
* ``/smaller`` and ``/different`` return a changed/different next step.
* ``/did-it`` flips ``done`` true and writes ``momentum.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from throughline.config import DEFAULT_OLLAMA_BASE_URL, DEFAULT_TEXT_MODEL, Settings
from throughline.main import create_app
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.thread.persistence import MOMENTUM_FILE_NAME

# Cold runs on the 9b model (index + two generations): generous headroom.
_LIVE_TIMEOUT_SECONDS = 600.0


def _text_model_present() -> bool:
    """Return True when the real reasoning model is pulled in Ollama."""
    try:
        resp = httpx.get(f"{DEFAULT_OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        return False
    names = [m.get("name") for m in resp.json().get("models", [])]
    return DEFAULT_TEXT_MODEL in names


requires_text_model = pytest.mark.skipif(
    not _text_model_present(),
    reason=f"{DEFAULT_TEXT_MODEL} not pulled in Ollama — skipping live Thread test",
)


def _client_with_long_timeout(settings: Settings) -> TestClient:
    """Build the app and swap in a long-timeout Ollama client + embeddings."""
    app = create_app(settings)
    state = app.state.app_state
    state.client = OllamaClient(
        embed_model=settings.embed_model,
        vision_model=settings.vision_model,
        timeout=_LIVE_TIMEOUT_SECONDS,
    )
    state.embeddings = Embeddings(state.client, embed_dim=settings.embed_dim)
    return TestClient(app)


@requires_text_model
def test_thread_unsticks_from_sample_vault(
    sample_vault: Path, tmp_path: Path
) -> None:
    # Arrange: a throwaway cache so we don't touch the fixture's index.
    cache = tmp_path / ".throughline"
    settings = Settings(vault_path=sample_vault, cache_dir=cache)
    sample_ids = {p.name for p in sample_vault.glob("*.md")}

    with _client_with_long_timeout(settings) as client:
        connected = client.post(
            "/vault/connect", json={"path": str(sample_vault)}
        )
        assert connected.status_code == 200, connected.text

        # Act: pull the thread on a real stuck moment.
        stuck = (
            "i keep planning the next thing and never starting. flat about it."
        )
        resp = client.post("/thread", json={"stuck": stuck})
        assert resp.status_code == 200, resp.text
        turn = resp.json()

        # Assert: ONE sharp question.
        assert turn["question"].strip(), "no question returned"

        # Assert: a connection grounded in a REAL sample item, with a quote.
        conn = turn["connection"]
        assert conn is not None, "no connection from the user's own vault"
        assert conn["item_id"] in sample_ids, (
            f"connection cites unknown id {conn['item_id']!r}"
        )
        assert conn["quote"].strip(), "connection has no quote"

        # Assert: ALWAYS ends on a concrete, non-empty next step.
        step = turn["next_step"]
        assert step["text"].strip(), "FAILURE: no actionable next step"
        assert step["size"] == "normal"

        turn_id = turn["id"]
        original_step = step["text"]

        # Act: ask for a SMALLER step — still actionable, marked smaller.
        smaller = client.post(f"/thread/{turn_id}/smaller")
        assert smaller.status_code == 200, smaller.text
        smaller_step = smaller.json()["next_step"]
        assert smaller_step["text"].strip()
        assert smaller_step["size"] == "smaller"

        # Act: ask for a DIFFERENT step — changed from the previous one.
        different = client.post(f"/thread/{turn_id}/different")
        assert different.status_code == 200, different.text
        different_step = different.json()["next_step"]["text"]
        assert different_step.strip()
        assert different_step != original_step, "different step was identical"

        # Act: "did it" closes the loop.
        did = client.post(f"/thread/{turn_id}/did-it")
        assert did.status_code == 200, did.text
        assert did.json()["done"] is True

    # Assert: momentum was logged for the closed loop.
    momentum_path = cache / MOMENTUM_FILE_NAME
    assert momentum_path.exists(), "momentum.json was not written"
    entries = json.loads(momentum_path.read_text(encoding="utf-8"))
    assert any(e.get("turn_id") == turn_id for e in entries)

    # Surface the real output for the proof-of-life report.
    print(f"\nSTUCK: {stuck}")
    print(f"QUESTION: {turn['question']}")
    print(f"CONNECTION[{conn['item_id']}]: \"{conn['quote']}\" — {conn['why']}")
    print(f"NEXT STEP: {original_step}")
    print(f"SMALLER: {smaller_step['text']}")
    print(f"DIFFERENT: {different_step}")
