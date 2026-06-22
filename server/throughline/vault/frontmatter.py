"""Parse and serialize Obsidian markdown notes with YAML frontmatter.

Parsing never crashes on bad input: a file with missing or malformed
frontmatter degrades to low-confidence defaults (type ``note``, title from the
filename) instead of raising.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import frontmatter

from throughline.schemas import DEFAULT_ITEM_TYPE, SELF_TYPES, Item


def _sha256_bytes(raw: bytes) -> str:
    """Return the hex sha256 of raw file bytes (read-once identity)."""
    return hashlib.sha256(raw).hexdigest()


def _relative_id(file_path: Path, vault_root: Path) -> str:
    """Return a stable id: POSIX path of ``file_path`` relative to the vault.

    Falls back to the file name when ``file_path`` lives outside the vault.
    """
    resolved = file_path.resolve()
    root = vault_root.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.name


def _coerce_tags(value: object) -> list[str]:
    """Normalize a frontmatter ``tags`` value into a list of strings.

    Accepts a list (any element types) or a single scalar; anything else
    yields an empty list. Never mutates the input.
    """
    if isinstance(value, list):
        return [str(tag) for tag in value]
    if value is None:
        return []
    return [str(value)]


def _coerce_optional_str(value: object) -> str | None:
    """Return ``value`` as a stripped string, or ``None`` when empty/absent."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title_from_filename(file_path: Path) -> str:
    """Derive a human title from a file name (stem, underscores to spaces)."""
    return file_path.stem.replace("_", " ").strip() or file_path.name


def parse_item(file_path: Path, vault_root: Path) -> Item:
    """Parse a markdown file into an :class:`Item`.

    The ``content_hash`` is computed over the *raw* file bytes so byte-identical
    files share an identity regardless of how frontmatter is serialized.
    Malformed frontmatter degrades gracefully to defaults.
    """
    raw = file_path.read_bytes()
    content_hash = _sha256_bytes(raw)
    item_id = _relative_id(file_path, vault_root)
    fallback_title = _title_from_filename(file_path)

    try:
        post = frontmatter.loads(raw.decode("utf-8", errors="replace"))
        metadata = dict(post.metadata)  # copy: never mutate the library's view
        body = post.content
    except Exception:
        # Any parse failure -> low-confidence defaults, never a crash.
        metadata = {}
        body = raw.decode("utf-8", errors="replace")

    item_type = str(metadata.get("type") or DEFAULT_ITEM_TYPE).strip() or DEFAULT_ITEM_TYPE
    title = _coerce_optional_str(metadata.get("title")) or fallback_title

    return Item(
        id=item_id,
        path=str(file_path.resolve()),
        type=item_type,
        title=title,
        feeling=_coerce_optional_str(metadata.get("feeling")),
        tags=_coerce_tags(metadata.get("tags")),
        body=body,
        content_hash=content_hash,
        is_self=item_type in SELF_TYPES,
        locked=bool(metadata.get("locked", False)),
    )


def item_to_markdown(item: Item) -> str:
    """Serialize an :class:`Item` back to frontmatter + body markdown.

    Only non-empty fields are emitted to keep the on-disk note minimal and
    close to what a human would hand-write.
    """
    metadata: dict[str, object] = {"type": item.type, "title": item.title}
    if item.feeling is not None:
        metadata["feeling"] = item.feeling
    if item.tags:
        metadata["tags"] = list(item.tags)
    if item.locked:
        metadata["locked"] = True

    post = frontmatter.Post(item.body, **metadata)
    return frontmatter.dumps(post)


def write_item(item: Item, file_path: Path) -> None:
    """Write an :class:`Item` to ``file_path`` as frontmatter + body."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(item_to_markdown(item), encoding="utf-8")
