"""Read-only iteration over an Obsidian vault directory.

Yields one :class:`Item` per ``.md`` file, skipping the ``.throughline`` cache
directory and any hidden directories. Pure reads: no file is modified.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from throughline.config import CACHE_DIR_NAME
from throughline.schemas import Item
from throughline.vault.frontmatter import parse_item

MARKDOWN_SUFFIX = ".md"


def _is_skipped_dir(part: str) -> bool:
    """Return True for hidden dirs and the throughline cache dir."""
    return part == CACHE_DIR_NAME or (part.startswith(".") and part not in (".", ".."))


def _is_under_skipped_dir(file_path: Path, vault_root: Path) -> bool:
    """Return True when any directory between the vault and file is skipped."""
    try:
        relative = file_path.resolve().relative_to(vault_root.resolve())
    except ValueError:
        return False
    # Inspect directory parts only (exclude the file name itself).
    return any(_is_skipped_dir(part) for part in relative.parts[:-1])


def iter_items(vault_root: Path) -> Iterator[Item]:
    """Yield an :class:`Item` for each markdown note in the vault.

    Raises ``NotADirectoryError`` when ``vault_root`` is not a directory so
    callers fail fast at the system boundary.
    """
    root = Path(vault_root)
    if not root.is_dir():
        raise NotADirectoryError(f"vault path is not a directory: {root}")

    for file_path in sorted(root.rglob(f"*{MARKDOWN_SUFFIX}")):
        if not file_path.is_file():
            continue
        if _is_under_skipped_dir(file_path, root):
            continue
        yield parse_item(file_path, root)


def read_vault(vault_root: Path) -> list[Item]:
    """Return all markdown notes in the vault as a list of :class:`Item`."""
    return list(iter_items(vault_root))
