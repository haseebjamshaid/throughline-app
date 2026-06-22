"""Live profile generation against the real reasoning model.

Connects the three-note sample vault and generates a profile for real with
``qwen3.5:9b`` (skips cleanly when Ollama is unreachable). Asserts an honest,
well-formed profile: a name, at least one #hex palette swatch, claims spanning
both the creative and deeper slices, every claim's examples referencing real
sample item ids, present confidences, and a confidence_note that acknowledges
the thin three-item vault.
"""

from __future__ import annotations

from pathlib import Path

from throughline.config import Settings, resolve_text_model
from throughline.index.store import VecStore
from throughline.models.ollama_client import OllamaClient
from throughline.profile.generate import generate_profile
from throughline.schemas import CREATIVE_SECTIONS, DEEPER_SECTIONS
from throughline.vault.reader import read_vault

from .conftest import requires_ollama

_HEX_LEN = 7  # "#rrggbb"
# Cold generations on the 9b model: give generous headroom over the 120s default.
_LIVE_TIMEOUT_SECONDS = 600.0


def _is_hex(value: str) -> bool:
    return (
        value.startswith("#")
        and len(value) == _HEX_LEN
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )


@requires_ollama
async def test_generate_profile_from_sample_vault(
    sample_vault: Path, tmp_path: Path
) -> None:
    # Arrange: connect the sample vault and a throwaway store.
    settings = Settings(vault_path=sample_vault, cache_dir=tmp_path / ".throughline")
    client = OllamaClient(
        embed_model=settings.embed_model,
        vision_model=settings.vision_model,
        timeout=_LIVE_TIMEOUT_SECONDS,
    )
    store = VecStore(tmp_path / ".throughline", embed_dim=settings.embed_dim)
    items = read_vault(sample_vault)
    sample_ids = {item.id for item in items}

    try:
        # Act: resolve the text model and generate for real.
        text_model = await resolve_text_model(settings, client)
        profile = await generate_profile(
            settings, store, client, items, text_model
        )
    finally:
        store.close()
        await client.aclose()

    # Assert: an honest, well-formed profile.
    assert profile.name, "profile has no name"
    assert profile.source_count == len(items) == 3

    # At least one valid #hex palette swatch.
    assert profile.palette, "no palette produced"
    assert all(_is_hex(s.hex) for s in profile.palette), "invalid hex in palette"

    # At least 3 claims spanning BOTH slices.
    assert len(profile.claims) >= 3, "too few claims"
    sections = {claim.section for claim in profile.claims}
    assert sections & CREATIVE_SECTIONS, "no creative-slice claim"
    assert sections & DEEPER_SECTIONS, "no deeper-slice claim"

    # Every claim references real sample item ids and carries a confidence.
    for claim in profile.claims:
        assert claim.examples, f"claim {claim.text!r} has no examples"
        assert all(ex in sample_ids for ex in claim.examples), (
            f"claim {claim.text!r} references unknown ids {claim.examples}"
        )
        assert claim.confidence in {"low", "medium", "high"}
        assert claim.text == claim.text.lower(), "claim text not lowercase"

    # Honest about the thin (3-item) vault.
    assert "3" in profile.confidence_note or "thin" in profile.confidence_note.lower()

    # Surface the real output for the proof-of-life report.
    print(f"\nPROFILE_NAME: {profile.name}")
    print(f"PROFILE_NOTE: {profile.confidence_note}")
    print(f"PROFILE_PALETTE: {[(s.name, s.hex) for s in profile.palette]}")
    for claim in profile.claims:
        print(
            f"CLAIM[{claim.section}/{claim.confidence}]: {claim.text} "
            f"<- {claim.examples}"
        )
