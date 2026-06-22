"""Apply user edits to a Profile's claims (edit text, toggle pin, delete).

The user owns the profile: they can rewrite a line, pin it so it survives
regeneration, or delete a claim that does not ring true. Edits are applied
immutably — a new :class:`Profile` is returned, the input is never mutated.
"""

from __future__ import annotations

from pydantic import BaseModel

from throughline.schemas import Profile, ProfileClaim


class ProfileEdit(BaseModel):
    """One edit targeting a claim by ``id``.

    Any field left ``None`` is unchanged. ``deleted=True`` removes the claim
    (and wins over any text/pin change in the same edit). ``text`` is stored
    lowercased to match generated claims.
    """

    id: str
    text: str | None = None
    pinned: bool | None = None
    deleted: bool | None = None


def _apply_one(claim: ProfileClaim, edit: ProfileEdit) -> ProfileClaim:
    """Return a copy of ``claim`` with ``edit`` applied (text / pin)."""
    update: dict[str, object] = {}
    if edit.text is not None:
        update["text"] = edit.text.strip().lower()
    if edit.pinned is not None:
        update["pinned"] = edit.pinned
    if not update:
        return claim
    return claim.model_copy(update=update)


def apply_edits(profile: Profile, edits: list[ProfileEdit]) -> Profile:
    """Return a new :class:`Profile` with ``edits`` applied to its claims.

    Edits are keyed by claim id. Unknown ids are ignored (a no-op, never an
    error) so a stale client edit cannot break the call. Deletions drop the
    claim entirely; other edits update text and/or the pin flag.
    """
    by_id: dict[str, ProfileEdit] = {edit.id: edit for edit in edits}
    updated: list[ProfileClaim] = []
    for claim in profile.claims:
        edit = by_id.get(claim.id)
        if edit is None:
            updated.append(claim)
            continue
        if edit.deleted:
            continue
        updated.append(_apply_one(claim, edit))
    return profile.model_copy(update={"claims": updated})
