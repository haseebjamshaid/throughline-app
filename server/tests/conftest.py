"""Shared pytest fixtures and Ollama-availability helpers."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from throughline.config import DEFAULT_OLLAMA_BASE_URL

SAMPLE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def _ollama_up() -> bool:
    """Return True when the local Ollama server answers ``/api/tags``."""
    try:
        response = httpx.get(f"{DEFAULT_OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def sample_vault() -> Path:
    """Path to the fixture vault with three real notes."""
    return SAMPLE_VAULT


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """A throwaway cache dir for an isolated index per test."""
    target = tmp_path / ".throughline"
    target.mkdir(parents=True, exist_ok=True)
    return target


requires_ollama = pytest.mark.skipif(
    not _ollama_up(),
    reason="Ollama not reachable at 127.0.0.1:11434 — skipping live embedding test",
)
