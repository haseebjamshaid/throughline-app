"""Profile determinism — the source signature is stable, content-sensitive, and
ignores the profile note. No model involved.

This is the contract behind "the portrait stays the same unless the vault
changes": generation is skipped while the signature is unchanged.
"""

from __future__ import annotations

from throughline.profile.generate import source_signature
from throughline.schemas import Item


def _item(item_id: str, content_hash: str, item_type: str = "movie") -> Item:
    return Item(
        id=item_id,
        path=f"/vault/{item_id}",
        type=item_type,
        title=item_id,
        body="body",
        content_hash=content_hash,
        is_self=False,
    )


def test_signature_is_order_independent() -> None:
    a = [_item("a.md", "h1"), _item("b.md", "h2")]
    b = [_item("b.md", "h2"), _item("a.md", "h1")]
    assert source_signature(a) == source_signature(b)


def test_signature_changes_when_content_changes() -> None:
    base = [_item("a.md", "h1")]
    edited = [_item("a.md", "h2")]  # same id, new bytes
    added = [_item("a.md", "h1"), _item("b.md", "h3")]  # a new file
    assert source_signature(base) != source_signature(edited)
    assert source_signature(base) != source_signature(added)


def test_signature_ignores_the_profile_note() -> None:
    items = [_item("a.md", "h1")]
    with_profile = [*items, _item("throughline-profile.md", "hX", item_type="profile")]
    # Writing the profile note back must not invalidate the signature.
    assert source_signature(items) == source_signature(with_profile)
