"""Quick-capture writes real vault files that round-trip to Items.

``capture_note`` must produce a plain ``.md`` Obsidian note that re-parses to an
Item with the right type/title and a correct ``is_self`` privacy flag.
``capture_image`` must persist bytes into the vault's attachments folder.
No Ollama involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from throughline.config import Settings
from throughline.intake.capture import capture_image, capture_note
from throughline.schemas import SELF_TYPES, TASTE_TYPES


@pytest.fixture
def vault_settings(tmp_path: Path) -> Settings:
    """A Settings pointed at a throwaway tmp vault."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    return Settings().with_vault(vault)


def test_capture_taste_note_roundtrips_outward(vault_settings: Settings) -> None:
    # Act
    item = capture_note(
        vault_settings,
        type="movie",
        title="Blade Runner 2049",
        body="rain and neon and loneliness",
        feeling="loved",
        tags=["neon", "nocturnal"],
    )

    # Assert: a real file was written and re-parses correctly.
    written = Path(item.path)
    assert written.exists()
    assert written.suffix == ".md"
    assert "movie" in TASTE_TYPES
    assert item.type == "movie"
    assert item.title == "Blade Runner 2049"
    assert item.feeling == "loved"
    assert item.tags == ["neon", "nocturnal"]
    assert item.is_self is False  # taste type -> outward-shareable
    assert item.content_hash  # a real hash from re-parsing the bytes

    text = written.read_text(encoding="utf-8")
    assert "rain and neon and loneliness" in text


def test_capture_self_note_marks_is_self(vault_settings: Settings) -> None:
    # Act
    item = capture_note(
        vault_settings,
        type="journal",
        title="a quiet thought",
        body="something private",
    )

    # Assert: self type -> inward-only privacy flag set.
    assert "journal" in SELF_TYPES
    assert item.type == "journal"
    assert item.is_self is True


def test_capture_note_deduplicates_filenames(vault_settings: Settings) -> None:
    # Act: two notes with the same title must not clobber each other.
    first = capture_note(vault_settings, type="movie", title="Dune", body="a")
    second = capture_note(vault_settings, type="movie", title="Dune", body="b")

    # Assert
    assert first.path != second.path
    assert Path(first.path).exists()
    assert Path(second.path).exists()


def test_capture_image_saves_into_attachments(vault_settings: Settings) -> None:
    # Arrange: a tiny valid-ish PNG byte blob (header is enough for storage).
    data = b"\x89PNG\r\n\x1a\n" + b"throughline-test-bytes"

    # Act
    saved = capture_image(vault_settings, "My Screenshot.png", data)

    # Assert
    assert saved.exists()
    assert saved.parent.name == "attachments"
    assert saved.suffix == ".png"
    assert saved.read_bytes() == data
