"""Live vision-read test: Qwen3-VL describes a real generated PNG.

A small dark-blue -> neon-magenta gradient PNG is synthesized with Pillow,
handed to the *real* vision model, and the resulting :class:`ImageRead` is
checked for a non-empty description, at least one ``#hex`` colour, and a
searchable 256-dim fingerprint of the description.

Skips cleanly when Ollama is unreachable so the suite stays green offline.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from throughline.config import get_settings
from throughline.intake.reader_image import read_image
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient

from .conftest import requires_ollama

_HEX_PREFIX = "#"
_FINGERPRINT_DIM = 256
_GRADIENT_SIZE = 256
# A cold vision generation can exceed the 120s client default; give it room.
_LIVE_TIMEOUT_SECONDS = 600.0


def _write_neon_gradient(path: Path) -> None:
    """Render a dark-blue (top) -> neon-magenta (bottom) vertical gradient PNG."""
    size = _GRADIENT_SIZE
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    assert pixels is not None
    # Dark blue (10, 10, 60) at the top, neon magenta (255, 43, 214) at the bottom.
    top = (10, 10, 60)
    bottom = (255, 43, 214)
    for y in range(size):
        ratio = y / (size - 1)
        row = tuple(
            int(round(top[c] + (bottom[c] - top[c]) * ratio)) for c in range(3)
        )
        for x in range(size):
            pixels[x, y] = row
    image.save(path, format="PNG")


@requires_ollama
async def test_read_image_describes_neon_gradient(tmp_path: Path) -> None:
    # Arrange
    settings = get_settings()
    image_path = tmp_path / "neon_gradient.png"
    _write_neon_gradient(image_path)
    client = OllamaClient(
        vision_model=settings.vision_model, timeout=_LIVE_TIMEOUT_SECONDS
    )
    embeddings = Embeddings(client, embed_dim=settings.embed_dim)

    try:
        # Act: real Qwen3-VL read
        read = await read_image(client, image_path, model=settings.vision_model)

        # Assert: a usable, honest read
        assert read.description.strip(), "vision model returned an empty description"
        assert len(read.colors) >= 1, "expected at least one dominant colour"
        assert any(
            color.hex.startswith(_HEX_PREFIX) for color in read.colors
        ), "expected at least one #hex colour code"
        assert read.confidence in {"medium", "high"}

        # Act: the description must fingerprint into a searchable vector
        vectors = await embeddings.fingerprint_documents([read.description])

        # Assert
        assert len(vectors) == 1
        assert len(vectors[0]) == _FINGERPRINT_DIM
    finally:
        await client.aclose()

    # Surface the real output for the proof-of-life report.
    print(f"\nIMAGE_DESCRIPTION: {read.description}")
    print(f"IMAGE_COLORS: {[(c.name, c.hex) for c in read.colors]}")
