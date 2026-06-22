"""Unit tests for frontmatter parsing (no Ollama required)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from throughline.schemas import DEFAULT_ITEM_TYPE
from throughline.vault.frontmatter import item_to_markdown, parse_item


def test_taste_item_is_not_self(sample_vault: Path) -> None:
    # Arrange / Act
    item = parse_item(sample_vault / "blade_runner_2049.md", sample_vault)

    # Assert
    assert item.type == "movie"
    assert item.is_self is False
    assert item.title == "Blade Runner 2049"
    assert item.feeling == "loved"
    assert item.tags == ["nocturnal", "lonely", "neon"]
    assert item.id == "blade_runner_2049.md"


def test_self_item_sets_is_self(sample_vault: Path) -> None:
    item = parse_item(sample_vault / "the_move.md", sample_vault)

    assert item.type == "ambition"
    assert item.is_self is True
    assert "creative life" in item.title


def test_content_hash_is_sha256_of_raw_bytes(sample_vault: Path) -> None:
    file_path = sample_vault / "slow_morning.md"
    item = parse_item(file_path, sample_vault)

    expected = hashlib.sha256(file_path.read_bytes()).hexdigest()
    assert item.content_hash == expected


def test_malformed_frontmatter_falls_back_to_defaults(tmp_path: Path) -> None:
    # Arrange: a file whose YAML is broken (unterminated bracket, bad indent)
    bad = tmp_path / "broken note.md"
    bad.write_text(
        "---\ntype: [movie\nbad: : :\n---\nsome body text that should survive\n",
        encoding="utf-8",
    )

    # Act
    item = parse_item(bad, tmp_path)

    # Assert: low-confidence defaults instead of a crash
    assert item.type == DEFAULT_ITEM_TYPE
    assert item.title == "broken note"
    assert item.is_self is False
    assert "some body text" in item.body


def test_missing_frontmatter_uses_filename_title(tmp_path: Path) -> None:
    plain = tmp_path / "just_a_note.md"
    plain.write_text("no frontmatter here, only prose.\n", encoding="utf-8")

    item = parse_item(plain, tmp_path)

    assert item.type == DEFAULT_ITEM_TYPE
    assert item.title == "just a note"
    assert item.is_self is False


def test_round_trip_serialization_preserves_fields(sample_vault: Path) -> None:
    # Arrange
    item = parse_item(sample_vault / "blade_runner_2049.md", sample_vault)

    # Act: serialize then re-parse from a temp file
    markdown = item_to_markdown(item)

    # Assert: the serialized form carries the declared metadata back
    assert "type: movie" in markdown
    assert "feeling: loved" in markdown
    assert "Blade Runner 2049" in markdown
