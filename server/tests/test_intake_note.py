"""Live text-read test: read the Blade Runner note with the resolved model.

Uses :func:`resolve_text_model`, which falls back to the vision model
(``qwen3-vl:4b``) until the preferred reasoning model is downloaded, and reads
the real fixture note. Asserts the model surfaces non-empty themes and feelings.

Skips cleanly when Ollama is unreachable.
"""

from __future__ import annotations

from pathlib import Path


from throughline.config import get_settings, resolve_text_model
from throughline.intake.reader_note import read_note
from throughline.models.ollama_client import OllamaClient
from throughline.vault.reader import read_vault

from .conftest import requires_ollama

_BLADE_RUNNER_ID = "blade_runner_2049.md"
# complete_json may make two cold generations (json mode + free-form retry) on
# the fallback model; give it generous headroom over the 120s client default.
_LIVE_TIMEOUT_SECONDS = 600.0


@requires_ollama
async def test_read_note_extracts_themes_and_feelings(sample_vault: Path) -> None:
    # Arrange
    settings = get_settings()
    client = OllamaClient(
        embed_model=settings.embed_model,
        vision_model=settings.vision_model,
        timeout=_LIVE_TIMEOUT_SECONDS,
    )
    items = read_vault(sample_vault)
    blade_runner = next(it for it in items if it.id == _BLADE_RUNNER_ID)

    try:
        # Act: resolve the text model (falls back to vision) and read for real
        text_model = await resolve_text_model(settings, client)
        read = await read_note(client, blade_runner, text_model)

        # Assert: an honest, non-empty read
        assert read.themes, "text model returned no themes"
        assert read.feelings, "text model returned no feelings"
        assert read.confidence in {"medium", "high"}
    finally:
        await client.aclose()

    # Surface the real output for the proof-of-life report.
    print(f"\nNOTE_MODEL: {text_model}")
    print(f"NOTE_THEMES: {read.themes}")
    print(f"NOTE_FEELINGS: {read.feelings}")
    print(f"NOTE_CONNECTIONS: {read.connections}")
