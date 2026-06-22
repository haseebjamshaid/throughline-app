"""Persist a Profile two ways: a rebuildable JSON working copy and a vault note.

The structured ``profile.json`` in the cache dir is the machine-readable working
copy (rebuildable, git-ignored). The human-readable ``throughline-profile.md``
note is written into the vault itself via the frontmatter writer, so the profile
is git-versioned and portable — readable in plain Obsidian without throughline.
"""

from __future__ import annotations

from pathlib import Path

from throughline.config import Settings
from throughline.schemas import (
    CREATIVE_SECTIONS,
    DEEPER_SECTIONS,
    Profile,
    ProfileClaim,
)
from throughline.vault.frontmatter import write_item
from throughline.schemas import Item

PROFILE_JSON_NAME = "profile.json"
PROFILE_NOTE_NAME = "throughline-profile.md"
PROFILE_NOTE_TYPE = "profile"

# Human-readable headings for each section, in display order. Creative slice
# first, then the deeper slice — the same shape the build spec describes.
_SECTION_HEADINGS: tuple[tuple[str, str], ...] = (
    ("mood", "mood"),
    ("light", "light"),
    ("framing", "framing"),
    ("subjects", "recurring subjects"),
    ("dos", "do's"),
    ("donts", "don'ts"),
    ("themes", "recurring themes"),
    ("ambitions", "stated ambitions"),
    ("threads", "threads"),
)


def _require_cache_dir(settings: Settings) -> Path:
    """Return the configured cache dir or fail fast at the boundary."""
    if settings.cache_dir is None:
        raise ValueError("no cache dir configured: connect a vault first")
    return settings.cache_dir


def _require_vault(settings: Settings) -> Path:
    """Return the configured vault path or fail fast at the boundary."""
    if settings.vault_path is None:
        raise ValueError("no vault connected: cannot write the profile note")
    return settings.vault_path


def _profile_json_path(settings: Settings) -> Path:
    return _require_cache_dir(settings) / PROFILE_JSON_NAME


def load_profile(settings: Settings) -> Profile | None:
    """Return the persisted Profile, or ``None`` when none has been generated.

    A malformed/partial JSON file degrades to ``None`` rather than raising, so a
    corrupt cache never blocks regeneration.
    """
    path = _profile_json_path(settings)
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        return Profile.model_validate_json(raw)
    except (OSError, ValueError):
        return None


def save_profile(settings: Settings, profile: Profile) -> Path:
    """Persist ``profile`` as JSON and write the readable vault note.

    Returns the path to the vault note. The JSON working copy is written first
    (rebuildable cache), then the human-readable note into the vault root.
    """
    json_path = _profile_json_path(settings)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

    return _write_profile_note(settings, profile)


def _write_profile_note(settings: Settings, profile: Profile) -> Path:
    """Render ``profile`` as a markdown note and write it into the vault root."""
    vault = _require_vault(settings)
    note_path = vault / PROFILE_NOTE_NAME
    note = Item(
        id=PROFILE_NOTE_NAME,
        path=str(note_path.resolve()),
        type=PROFILE_NOTE_TYPE,
        title=profile.name,
        body=render_profile_markdown(profile),
        content_hash="",
        is_self=False,
    )
    write_item(note, note_path)
    return note_path


def _claims_in(profile: Profile, section: str) -> list[ProfileClaim]:
    """Return the profile's claims for ``section`` (preserving order)."""
    return [claim for claim in profile.claims if claim.section == section]


def _render_claim_line(claim: ProfileClaim) -> str:
    """Render one claim as a bullet: text, pin marker, confidence, examples."""
    pin = " (pinned)" if claim.pinned else ""
    examples = ""
    if claim.examples:
        examples = f" — from {', '.join(claim.examples)}"
    return f"- {claim.text}{pin} _[{claim.confidence}]_{examples}"


def _render_palette(profile: Profile) -> list[str]:
    """Render the palette as a lowercase markdown list of name + hex."""
    if not profile.palette:
        return []
    lines = ["## palette", ""]
    lines.extend(f"- {swatch.name.lower()} `{swatch.hex}`" for swatch in profile.palette)
    lines.append("")
    return lines


def _render_section(profile: Profile, section: str, heading: str) -> list[str]:
    """Render one section's claims under its heading (skipped when empty)."""
    claims = _claims_in(profile, section)
    if not claims:
        return []
    lines = [f"### {heading}", ""]
    lines.extend(_render_claim_line(claim) for claim in claims)
    lines.append("")
    return lines


def render_profile_markdown(profile: Profile) -> str:
    """Render a Profile to a readable, lowercase markdown body.

    The body is intentionally human-first: a palette block, the creative slice,
    the deeper slice, and an honest confidence note. Headings group the nine
    sections into the two slices.
    """
    lines: list[str] = [
        f"a picture drawn from {profile.source_count} "
        f"{'item' if profile.source_count == 1 else 'items'} in the vault.",
        "",
        f"_{profile.confidence_note}_",
        "",
    ]
    lines.extend(_render_palette(profile))

    creative = [
        (sec, head) for sec, head in _SECTION_HEADINGS if sec in CREATIVE_SECTIONS
    ]
    deeper = [
        (sec, head) for sec, head in _SECTION_HEADINGS if sec in DEEPER_SECTIONS
    ]

    creative_body = _render_slice(profile, creative)
    if creative_body:
        lines.append("## the creative slice")
        lines.append("")
        lines.extend(creative_body)

    deeper_body = _render_slice(profile, deeper)
    if deeper_body:
        lines.append("## the deeper slice")
        lines.append("")
        lines.extend(deeper_body)

    return "\n".join(lines).rstrip() + "\n"


def _render_slice(profile: Profile, sections: list[tuple[str, str]]) -> list[str]:
    """Render every non-empty section in ``sections`` for one slice."""
    body: list[str] = []
    for section, heading in sections:
        body.extend(_render_section(profile, section, heading))
    return body
