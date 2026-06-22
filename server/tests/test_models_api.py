"""Model on/off control API (no real model loads).

Exercises ``GET /models`` and ``POST /models/{load,unload,unload-all}`` against
the FastAPI app with the Ollama client's network methods monkeypatched, so the
tests are fast and never touch a real Ollama server. Asserts the installed /
loaded / size reporting, name validation, and that load/unload call through.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from throughline.config import Settings
from throughline.main import create_app
from throughline.models.ollama_client import OllamaClient

EMBED = "embeddinggemma:300m"
TEXT = "qwen3.5:9b"
VISION = "qwen3-vl:4b"

# size_vram in bytes -> the route divides by 1e6 and rounds for size_mb.
_TEXT_VRAM_BYTES = 5_400_000_000  # ~5400 MB
_VISION_VRAM_BYTES = 3_200_000_000  # ~3200 MB


@pytest.fixture
def settings() -> Settings:
    """Settings with the three roles pinned to known names."""
    return Settings(embed_model=EMBED, text_model=TEXT, vision_model=VISION)


class _FakeOllama:
    """Records load/unload calls and serves canned installed/loaded data."""

    def __init__(self, installed: list[str], loaded: list[dict[str, Any]]) -> None:
        self.installed = installed
        self.loaded = loaded
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []

    async def list_models(self) -> list[str]:
        return list(self.installed)

    async def ps(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self.loaded]

    async def load_model(self, name: str) -> None:
        self.load_calls.append(name)
        # Reflect the load in the loaded set so a follow-up status reads "loaded".
        if not any(e.get("name") == name for e in self.loaded):
            self.loaded.append({"name": name, "size_vram": _TEXT_VRAM_BYTES})

    async def unload_model(self, name: str) -> None:
        self.unload_calls.append(name)
        self.loaded = [e for e in self.loaded if e.get("name") != name]


def _patch(monkeypatch: pytest.MonkeyPatch, fake: _FakeOllama) -> None:
    monkeypatch.setattr(OllamaClient, "list_models", fake.list_models)
    monkeypatch.setattr(OllamaClient, "ps", fake.ps)
    monkeypatch.setattr(OllamaClient, "load_model", fake.load_model)
    monkeypatch.setattr(OllamaClient, "unload_model", fake.unload_model)


def _client(settings: Settings, fake: _FakeOllama, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _patch(monkeypatch, fake)
    return TestClient(create_app(settings))


def test_get_models_reports_installed_loaded_and_size(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: embed+text installed; only text loaded with a known VRAM size.
    fake = _FakeOllama(
        installed=[EMBED, TEXT],
        loaded=[{"name": TEXT, "size_vram": _TEXT_VRAM_BYTES}],
    )
    with _client(settings, fake, monkeypatch) as client:
        # Act
        resp = client.get("/models")

    # Assert
    assert resp.status_code == 200
    by_name = {row["name"]: row for row in resp.json()}
    assert set(by_name) == {EMBED, TEXT, VISION}

    assert by_name[EMBED] == {
        "name": EMBED,
        "role": "embed",
        "installed": True,
        "loaded": False,
        "size_mb": None,
    }
    assert by_name[TEXT]["role"] == "text"
    assert by_name[TEXT]["installed"] is True
    assert by_name[TEXT]["loaded"] is True
    assert by_name[TEXT]["size_mb"] == 5400  # 5_400_000_000 / 1e6
    # Vision is neither installed nor loaded.
    assert by_name[VISION]["installed"] is False
    assert by_name[VISION]["loaded"] is False
    assert by_name[VISION]["size_mb"] is None


def test_get_models_when_ollama_offline_degrades(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: nothing installed, nothing loaded (as if Ollama returned empty).
    fake = _FakeOllama(installed=[], loaded=[])
    with _client(settings, fake, monkeypatch) as client:
        resp = client.get("/models")

    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 3
    assert all(row["installed"] is False and row["loaded"] is False for row in rows)


def test_load_calls_through_and_returns_status(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeOllama(installed=[EMBED, TEXT, VISION], loaded=[])
    with _client(settings, fake, monkeypatch) as client:
        # Act
        resp = client.post("/models/load", json={"name": VISION})

    # Assert: the client.load_model was invoked for VISION and status reflects it.
    assert resp.status_code == 200
    assert fake.load_calls == [VISION]
    body = resp.json()
    assert body["name"] == VISION
    assert body["role"] == "vision"
    assert body["loaded"] is True


def test_unload_calls_through_and_returns_status(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeOllama(
        installed=[EMBED, TEXT],
        loaded=[{"name": TEXT, "size_vram": _TEXT_VRAM_BYTES}],
    )
    with _client(settings, fake, monkeypatch) as client:
        resp = client.post("/models/unload", json={"name": TEXT})

    assert resp.status_code == 200
    assert fake.unload_calls == [TEXT]
    body = resp.json()
    assert body["name"] == TEXT
    assert body["loaded"] is False
    assert body["size_mb"] is None


def test_load_unknown_model_is_rejected(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeOllama(installed=[EMBED, TEXT, VISION], loaded=[])
    with _client(settings, fake, monkeypatch) as client:
        resp = client.post("/models/load", json={"name": "llama3:70b"})

    assert resp.status_code == 400
    assert fake.load_calls == []  # never called through for an unknown model


def test_unload_unknown_model_is_rejected(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeOllama(installed=[EMBED], loaded=[])
    with _client(settings, fake, monkeypatch) as client:
        resp = client.post("/models/unload", json={"name": "mistral:latest"})

    assert resp.status_code == 400
    assert fake.unload_calls == []


def test_unload_all_unloads_every_loaded_model(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: both heavy models loaded.
    fake = _FakeOllama(
        installed=[EMBED, TEXT, VISION],
        loaded=[
            {"name": TEXT, "size_vram": _TEXT_VRAM_BYTES},
            {"name": VISION, "size_vram": _VISION_VRAM_BYTES},
        ],
    )
    with _client(settings, fake, monkeypatch) as client:
        resp = client.post("/models/unload-all")

    # Assert: both loaded models were unloaded; final status shows none loaded.
    assert resp.status_code == 200
    assert sorted(fake.unload_calls) == sorted([TEXT, VISION])
    rows = resp.json()
    assert all(row["loaded"] is False for row in rows)
