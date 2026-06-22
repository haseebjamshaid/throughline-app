"""Build a :class:`Profile` from the connected vault.

The text model is given a digest of every vault item plus its structured read
(note themes/feelings, image colours/mood/light/framing) and asked for a single
JSON object holding the creative slice and the deeper slice. Every returned
claim is validated: its ``examples`` must reference item ids that actually exist,
its section must be one of the nine, and its confidence is graded honestly.

Honesty over invention is the rule throughout. A thin vault yields lower
confidences and a ``confidence_note`` that says so. An unparseable model
response degrades to an empty-but-valid profile rather than fabricated detail.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from throughline.config import Settings
from throughline.index.store import VecStore
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import (
    Confidence,
    Item,
    PaletteSwatch,
    Profile,
    ProfileClaim,
)

# The nine valid sections; used to drop any section the model invents.
_VALID_SECTIONS: frozenset[str] = frozenset(
    {
        "mood",
        "light",
        "framing",
        "subjects",
        "dos",
        "donts",
        "themes",
        "ambitions",
        "threads",
    }
)
_VALID_CONFIDENCES: frozenset[str] = frozenset({"low", "medium", "high"})

# Below this many source items the read is "thin": confidences are capped at
# medium and the confidence note acknowledges it.
_THIN_VAULT_THRESHOLD = 6
_THIN_CONFIDENCE_NOTE = (
    "thin first read — feed it more and it sharpens"
)
_RICH_CONFIDENCE_NOTE = (
    "drawn from a healthy spread of items — claims are well supported"
)
_EMPTY_CONFIDENCE_NOTE = (
    "no items to read yet — connect a vault with a few notes and images"
)

# A small fallback palette when no image colours are present and the model
# proposes none — kept neutral and honest rather than invented vibrancy.
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

_MAX_BODY_CHARS = 600
_MAX_PALETTE = 8


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# Default sampling knobs for the portrait (editable in the UI). Temperature 0 +
# a fixed seed makes the same vault yield the same portrait; raising temperature
# or changing the seed produces a different take, on purpose.
DEFAULT_PROFILE_TEMPERATURE = 0.0
DEFAULT_PROFILE_SEED = 7

# The profile note's own type, excluded from the source signature + inputs so the
# portrait is never drawn from (or invalidated by) a copy of itself.
_PROFILE_TYPE = "profile"


def source_signature(items: list[Item]) -> str:
    """Return a stable hash of the vault's content (excluding the profile note).

    Same items + same bytes → same signature, in any order, so a profile is only
    regenerated when the inputs actually change.
    """
    lines = sorted(
        f"{item.id}:{item.content_hash}"
        for item in items
        if item.type != _PROFILE_TYPE
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _normalise_hex(value: str) -> str | None:
    """Return a valid ``#rrggbb`` hex (lowercased), or ``None`` when invalid.

    Tolerates a missing leading ``#`` and three-digit shorthand; anything that
    is not a recognisable hex colour is rejected rather than guessed.
    """
    text = value.strip().lower()
    if not text:
        return None
    if not text.startswith("#"):
        text = f"#{text}"
    if _HEX_RE.match(text):
        return text
    # Expand #abc -> #aabbcc shorthand.
    if re.match(r"^#[0-9a-f]{3}$", text):
        return "#" + "".join(ch * 2 for ch in text[1:])
    return None


def _read_payload(store: VecStore, item_id: str) -> dict[str, object]:
    """Return the parsed structured-read payload for ``item_id`` (``{}`` if none)."""
    read = store.get_read(item_id)
    if read is None:
        return {}
    try:
        parsed = json.loads(read.data)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _item_digest(item: Item, payload: dict[str, object]) -> str:
    """Render one item + its read into a compact line for the prompt."""
    parts = [f"id: {item.id}", f"type: {item.type}", f"title: {item.title}"]
    if item.feeling:
        parts.append(f"feeling: {item.feeling}")
    if item.tags:
        parts.append(f"tags: {', '.join(item.tags)}")

    themes = payload.get("themes")
    if isinstance(themes, list) and themes:
        parts.append(f"themes: {', '.join(str(t) for t in themes)}")
    feelings = payload.get("feelings")
    if isinstance(feelings, list) and feelings:
        parts.append(f"feelings: {', '.join(str(f) for f in feelings)}")
    mood = payload.get("mood")
    if isinstance(mood, list) and mood:
        parts.append(f"mood: {', '.join(str(m) for m in mood)}")
    light = payload.get("light")
    if isinstance(light, str) and light:
        parts.append(f"light: {light}")
    framing = payload.get("framing")
    if isinstance(framing, str) and framing:
        parts.append(f"framing: {framing}")

    body = item.body.strip().replace("\n", " ")
    if body:
        parts.append(f"body: {body[:_MAX_BODY_CHARS]}")
    return " | ".join(parts)


def _collect_colors(store: VecStore, items: list[Item]) -> list[PaletteSwatch]:
    """Pull dominant colours from image reads into a deduped palette."""
    swatches: list[PaletteSwatch] = []
    seen_hex: set[str] = set()
    for item in items:
        payload = _read_payload(store, item.id)
        colors = payload.get("colors")
        if not isinstance(colors, list):
            continue
        for entry in colors:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip().lower()
            hex_code = _normalise_hex(str(entry.get("hex", "")))
            if name and hex_code and hex_code not in seen_hex:
                seen_hex.add(hex_code)
                swatches.append(PaletteSwatch(name=name, hex=hex_code))
            if len(swatches) >= _MAX_PALETTE:
                return swatches
    return swatches


def _build_prompt(digests: list[str], need_palette: bool) -> str:
    """Compose the profile-generation prompt for the text model."""
    palette_clause = (
        '  "palette": an array of {"name": <plain lowercase color name>, '
        '"hex": <"#rrggbb">} — 3 to 6 colors that match the overall vibe of '
        "these items (use real hex codes),\n"
        if need_palette
        else '  "palette": [] (leave empty),\n'
    )
    return (
        "You are building a personal profile from someone's vault of notes and "
        "images. Look across ALL the items below and respond with ONLY a JSON "
        "object, no prose, with exactly these keys:\n"
        + palette_clause
        + '  "claims": an array of claim objects. Each claim is '
        '{"section": <one of "mood","light","framing","subjects","dos","donts",'
        '"themes","ambitions","threads">, "text": <a short LOWERCASE sentence>, '
        '"examples": <array of item ids this claim is drawn from>, '
        '"confidence": <one of "low","medium","high">}.\n'
        "\nThe creative slice is mood / light / framing / subjects / dos / "
        "donts. The deeper slice is themes / ambitions / threads. You MUST "
        "include at least one creative-slice claim AND at least one deeper-slice "
        "claim (a theme, a stated ambition, or a recurring thread) — look for "
        "what the items are really about underneath. Each claim's text MUST be "
        "lowercase. Each claim MUST list real example ids it was drawn from "
        "(only ids from the list below). Only state what the items actually "
        "support — do NOT invent. With few items, prefer lower confidence.\n\n"
        "ITEMS:\n" + "\n".join(digests)
    )


def _grade_confidence(raw: object, source_count: int) -> Confidence:
    """Return a valid confidence, capped to medium when the vault is thin."""
    value = str(raw).strip().lower()
    confidence: Confidence = value if value in _VALID_CONFIDENCES else "low"  # type: ignore[assignment]
    if source_count < _THIN_VAULT_THRESHOLD and confidence == "high":
        return "medium"
    return confidence


def _claim_from_payload(
    entry: dict[str, object], valid_ids: set[str], source_count: int
) -> ProfileClaim | None:
    """Build a validated :class:`ProfileClaim`, or ``None`` when unusable.

    Drops claims with an unknown section, empty text, or no example that maps to
    a real item id — honesty over invention.
    """
    section = str(entry.get("section", "")).strip().lower()
    if section not in _VALID_SECTIONS:
        return None
    text = str(entry.get("text", "")).strip().lower()
    if not text:
        return None

    raw_examples = entry.get("examples")
    examples: list[str] = []
    if isinstance(raw_examples, list):
        for ex in raw_examples:
            ex_id = str(ex).strip()
            if ex_id in valid_ids and ex_id not in examples:
                examples.append(ex_id)
    if not examples:
        return None

    return ProfileClaim(
        id=str(uuid.uuid4()),
        section=section,  # type: ignore[arg-type]
        text=text,
        examples=examples,
        confidence=_grade_confidence(entry.get("confidence"), source_count),
    )


def _palette_from_payload(
    raw: object, existing_hex: set[str]
) -> list[PaletteSwatch]:
    """Build palette swatches from the model's proposed palette (validated)."""
    if not isinstance(raw, list):
        return []
    swatches: list[PaletteSwatch] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip().lower()
        hex_code = _normalise_hex(str(entry.get("hex", "")))
        if name and hex_code and hex_code not in existing_hex:
            existing_hex.add(hex_code)
            swatches.append(PaletteSwatch(name=name, hex=hex_code))
        if len(swatches) >= _MAX_PALETTE:
            break
    return swatches


def _confidence_note(source_count: int) -> str:
    """Return an honest note about how thin or rich the read is."""
    if source_count == 0:
        return _EMPTY_CONFIDENCE_NOTE
    if source_count < _THIN_VAULT_THRESHOLD:
        return f"{_THIN_CONFIDENCE_NOTE} ({source_count} items so far)."
    return f"{_RICH_CONFIDENCE_NOTE} ({source_count} items)."


def _profile_name(items: list[Item]) -> str:
    """Derive a profile name; falls back to a neutral default when empty."""
    if not items:
        return "your profile"
    return "your throughline"


async def generate_profile(
    settings: Settings,
    store: VecStore,
    client: OllamaClient,
    items: list[Item],
    text_model: str,
    *,
    temperature: float = DEFAULT_PROFILE_TEMPERATURE,
    seed: int = DEFAULT_PROFILE_SEED,
) -> Profile:
    """Generate a fresh :class:`Profile` from the connected vault.

    ``text_model`` is the resolved model name. The structured reads come from
    ``store``; ``items`` is the connected vault's parsed notes. Returns an
    honest, validated profile even when the model output is sparse. ``temperature``
    and ``seed`` are the editable sampling knobs: at temperature 0 the same vault
    redraws the same portrait; raising it (or changing the seed) yields a
    different take. The profile note itself is excluded from the inputs so the
    portrait is never drawn from a copy of itself.
    """
    signature = source_signature(items)
    items = [item for item in items if item.type != _PROFILE_TYPE]
    temperature = max(0.0, min(2.0, temperature))
    options = {"temperature": temperature, "seed": seed}
    source_count = len(items)
    valid_ids = {item.id for item in items}
    image_palette = _collect_colors(store, items)
    seen_hex = {swatch.hex for swatch in image_palette}

    if source_count == 0:
        return Profile(
            name=_profile_name(items),
            source_count=0,
            confidence_note=_confidence_note(0),
            palette=[],
            claims=[],
            generated_at=_now_iso(),
            source_signature=signature,
            temperature=temperature,
            seed=seed,
        )

    digests = [_item_digest(item, _read_payload(store, item.id)) for item in items]
    prompt = _build_prompt(digests, need_palette=not image_palette)
    payload = await client.complete_json(text_model, prompt, options=options)

    claims: list[ProfileClaim] = []
    raw_claims = payload.get("claims")
    if isinstance(raw_claims, list):
        for entry in raw_claims:
            if isinstance(entry, dict):
                claim = _claim_from_payload(entry, valid_ids, source_count)
                if claim is not None:
                    claims.append(claim)

    palette = image_palette + _palette_from_payload(payload.get("palette"), seen_hex)

    return Profile(
        name=_profile_name(items),
        source_count=source_count,
        confidence_note=_confidence_note(source_count),
        palette=palette[:_MAX_PALETTE],
        claims=claims,
        generated_at=_now_iso(),
        source_signature=signature,
        temperature=temperature,
        seed=seed,
    )


def merge_preserving_pins(existing: Profile | None, fresh: Profile) -> Profile:
    """Merge a freshly generated profile, preserving pinned claims.

    Pinned claims from ``existing`` are kept verbatim (their text, pin, examples,
    confidence and id survive). Fresh non-pinned claims are appended after them.
    The fresh palette / name / source_count / confidence_note win — those are
    redrawn from the vault every time. With no existing profile, ``fresh`` is
    returned unchanged.
    """
    if existing is None:
        return fresh
    pinned = [claim for claim in existing.claims if claim.pinned]
    if not pinned:
        return fresh
    merged_claims = [*pinned, *fresh.claims]
    return fresh.model_copy(update={"claims": merged_claims})
