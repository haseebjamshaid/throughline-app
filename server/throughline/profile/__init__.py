"""Profile — one living picture of the user drawn from their vault.

A creative slice (palette, mood, light, framing, subjects, do's & don'ts) and a
deeper slice (themes, ambitions, threads). Every claim is backed by linked
example items and carries a confidence. Generated from the vault, editable by
the user (pinned lines survive regeneration), and written back into the vault
as a git-versioned note.
"""

from __future__ import annotations

__all__ = [
    "PROFILE_NOTE_NAME",
    "ProfileEdit",
    "apply_edits",
    "generate_profile",
    "load_profile",
    "merge_preserving_pins",
    "save_profile",
]

from throughline.profile.edits import ProfileEdit, apply_edits
from throughline.profile.generate import generate_profile, merge_preserving_pins
from throughline.profile.store import (
    PROFILE_NOTE_NAME,
    load_profile,
    save_profile,
)
