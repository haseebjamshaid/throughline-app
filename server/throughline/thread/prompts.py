"""Prompt assembly for the Thread's text-model call.

The unstuck engine asks the model for exactly three things, in order: ONE sharp
question, ONE reason the user's own vault connection is relevant, and ONE
concrete next step they can do TODAY. The prompt is grounded in a real vault
item (title + quote + its themes/feelings) and, when available, the user's
profile tone — never generic.
"""

from __future__ import annotations

import json

from throughline.index.store import VecStore
from throughline.schemas import Item, NextStepSize, Profile

# How many profile claim lines to fold in as tone (kept short to stay grounded).
_MAX_TONE_CLAIMS = 4


def _read_themes_feelings(store: VecStore, item_id: str) -> str:
    """Return a short ``themes/feelings`` line from the item's stored read.

    The note read (when present) holds themes + feelings the deeper picture was
    built from; surfacing them helps the model connect the dots. Returns an
    empty string when there is no read or it carries nothing useful.
    """
    read = store.get_read(item_id)
    if read is None:
        return ""
    try:
        payload = json.loads(read.data)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(payload, dict):
        return ""

    parts: list[str] = []
    themes = payload.get("themes")
    if isinstance(themes, list) and themes:
        parts.append("themes: " + ", ".join(str(t) for t in themes))
    feelings = payload.get("feelings")
    if isinstance(feelings, list) and feelings:
        parts.append("feelings: " + ", ".join(str(f) for f in feelings))
    return " | ".join(parts)


def _tone_line(profile: Profile | None) -> str:
    """Render a brief tone hint from the profile (empty when there is none)."""
    if profile is None or not profile.claims:
        return ""
    lines = [claim.text for claim in profile.claims[:_MAX_TONE_CLAIMS]]
    return "; ".join(lines)


def _size_clause(size: NextStepSize, avoid: str | None) -> str:
    """Return the step-shaping clause for size + a step to avoid repeating."""
    clauses: list[str] = []
    if size == "smaller":
        clauses.append(
            "Make the next step MUCH smaller and easier than usual — a tiny, "
            "almost-trivial first move that takes only a few minutes, so it is "
            "impossible to feel too big to start."
        )
    if avoid:
        clauses.append(
            "The user did NOT want this previous step: "
            f'"{avoid}". Give a GENUINELY DIFFERENT next step — a different '
            "kind of action, not a reworded version of that one."
        )
    return " ".join(clauses)


def build_thread_prompt(
    store: VecStore,
    stuck: str,
    connection_item: Item | None,
    quote: str,
    profile: Profile | None,
    *,
    size: NextStepSize = "normal",
    avoid: str | None = None,
    strict: bool = False,
) -> str:
    """Compose the Thread prompt for ``complete_json``.

    Asks for a JSON object ``{question, connection_why, next_step}``. ``strict``
    is the guardrail retry: it hammers home that the next step must be concrete
    and doable today. ``size`` / ``avoid`` shape the requested step.
    """
    lines: list[str] = [
        "You are a small, local tool that helps someone get UNSTUCK on a "
        "creative block. You are honest about being a small model — you are a "
        "tool, not a therapist. If what they describe is clearly beyond a "
        "creative block (a crisis, or needing real help), gently point them to "
        "real people. Otherwise: unstick their own head.",
        "",
        "Respond with ONLY a JSON object, no prose, with exactly these keys:",
        '  "question": ONE sharp question (a single question, lowercase, not a '
        "list) that helps them unstick their OWN thinking,",
        '  "connection_why": ONE short lowercase line saying why the quoted '
        "thing from their own vault connects to what they are stuck on,",
        '  "next_step": ONE concrete action they can actually DO TODAY '
        "(lowercase, specific, small, and doable — a real verb-first action, "
        "NOT analysis, NOT a question, NOT 'think about it').",
        "",
        f"WHAT THEY ARE STUCK ON:\n{stuck.strip()}",
    ]

    if connection_item is not None:
        lines.append("")
        lines.append("SOMETHING FROM THEIR OWN VAULT (use this, do not invent):")
        lines.append(f"  title: {connection_item.title}")
        if quote:
            lines.append(f'  quote: "{quote}"')
        if connection_item.feeling:
            lines.append(f"  feeling: {connection_item.feeling}")
        read_line = _read_themes_feelings(store, connection_item.id)
        if read_line:
            lines.append(f"  {read_line}")
    else:
        lines.append("")
        lines.append(
            "Their vault is empty, so connection_why can be an empty string."
        )

    tone = _tone_line(profile)
    if tone:
        lines.append("")
        lines.append(
            "THEIR VOICE (match this tone, do not quote it back): " + tone
        )

    size_clause = _size_clause(size, avoid)
    if size_clause:
        lines.append("")
        lines.append(size_clause)

    if strict:
        lines.append("")
        lines.append(
            "CRITICAL: next_step MUST be a non-empty, concrete, do-it-today "
            "action that starts with a verb (e.g. 'open a blank file and write "
            "the first sentence', 'set a 15-minute timer and...'). It must NOT "
            "be empty, vague, abstract, or pure analysis. Always end on a real "
            "action."
        )

    return "\n".join(lines)
