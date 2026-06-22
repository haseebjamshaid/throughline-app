"""Quick-capture: write real vault files from app input.

``capture_note`` turns a paste box of title/body into a clean ``.md`` note in
the vault (the same files Obsidian reads). ``capture_image`` saves a dropped
image into the vault's attachments folder. Neither side keeps a hidden copy.
"""

from __future__ import annotations

import re
from pathlib import Path

from throughline.config import Settings
from throughline.schemas import Item
from throughline.vault.frontmatter import parse_item, write_item

ATTACHMENTS_DIR_NAME = "attachments"
_MAX_SLUG_LENGTH = 80
_SLUG_FALLBACK = "untitled"


def slugify(title: str) -> str:
    """Return a filesystem-safe slug derived from ``title``.

    Lowercases, replaces runs of non-alphanumerics with single hyphens, and
    trims to a sane length. Falls back to ``untitled`` for empty results.
    """
    lowered = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = slug[:_MAX_SLUG_LENGTH].strip("-")
    return slug or _SLUG_FALLBACK


def _require_vault(settings: Settings) -> Path:
    """Return the configured vault path or fail fast at the boundary."""
    if settings.vault_path is None:
        raise ValueError("no vault connected: cannot capture without a vault path")
    return settings.vault_path


def _unique_path(directory: Path, slug: str, suffix: str) -> Path:
    """Return a non-colliding path ``<dir>/<slug><suffix>`` (de-duped with -N)."""
    candidate = directory / f"{slug}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{slug}-{counter}{suffix}"
        counter += 1
    return candidate


def capture_note(
    settings: Settings,
    *,
    type: str,
    title: str,
    body: str,
    feeling: str | None = None,
    tags: list[str] | None = None,
) -> Item:
    """Write a quick-capture note into the vault and return the parsed Item.

    The file is written via the frontmatter writer so it round-trips cleanly in
    plain Obsidian. ``is_self`` and ``locked`` are derived by re-parsing the
    written file, keeping the on-disk note the single source of truth.
    """
    vault = _require_vault(settings)
    vault.mkdir(parents=True, exist_ok=True)

    file_path = _unique_path(vault, slugify(title), ".md")
    draft = Item(
        id=file_path.name,
        path=str(file_path.resolve()),
        type=type,
        title=title,
        feeling=feeling,
        tags=list(tags or []),
        body=body,
        content_hash="",  # placeholder; the real hash comes from re-parsing
        is_self=False,  # placeholder; derived from type on re-parse
    )
    write_item(draft, file_path)
    return parse_item(file_path, vault)


def capture_image(settings: Settings, filename: str, data: bytes) -> Path:
    """Save an uploaded image into the vault's attachments folder.

    Returns the path to the written file. The filename is slugified (preserving
    its suffix) and de-duplicated so concurrent drops never clobber each other.
    """
    vault = _require_vault(settings)
    attachments = vault / ATTACHMENTS_DIR_NAME
    attachments.mkdir(parents=True, exist_ok=True)

    source = Path(filename)
    suffix = source.suffix or ".png"
    slug = slugify(source.stem)
    target = _unique_path(attachments, slug, suffix)
    target.write_bytes(data)
    return target
