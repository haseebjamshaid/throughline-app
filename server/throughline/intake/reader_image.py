"""Read an image attachment into a structured :class:`ImageRead`.

The vision model (Qwen3-VL) is asked for a strict JSON object describing the
image. Honesty over invention: a sparse or unparseable response degrades to a
low-confidence read with empty fields rather than fabricated detail.
"""

from __future__ import annotations

from pathlib import Path

from throughline.models.ollama_client import OllamaClient
from throughline.schemas import Confidence, ImageColor, ImageRead

IMAGE_PROMPT = (
    "You are an art-director's eye. Look at this image and respond with ONLY a "
    "JSON object, no prose, with exactly these keys:\n"
    '  "description": a vivid one-to-two sentence description of what is shown,\n'
    '  "colors": an array of objects each {"name": <plain color name>, '
    '"hex": <"#rrggbb">} for the dominant colors,\n'
    '  "light": a short phrase describing the lighting,\n'
    '  "mood": an array of one-word mood tags,\n'
    '  "framing": a short phrase describing the composition/framing.\n'
    "Use real hex codes. Do not invent detail you cannot see."
)


def _as_str(value: object) -> str:
    """Coerce a JSON value to a stripped string ('' for None/containers)."""
    if value is None or isinstance(value, (list, dict)):
        return ""
    return str(value).strip()


def _as_str_list(value: object) -> list[str]:
    """Coerce a JSON value to a list of non-empty strings."""
    if isinstance(value, list):
        return [s for s in (_as_str(v) for v in value) if s]
    single = _as_str(value)
    return [single] if single else []


def _coerce_colors(value: object) -> list[ImageColor]:
    """Coerce the ``colors`` field into validated :class:`ImageColor` entries.

    Accepts a list of ``{name, hex}`` objects. Entries missing a usable name or
    hex are dropped — never guessed.
    """
    if not isinstance(value, list):
        return []
    colors: list[ImageColor] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        name = _as_str(entry.get("name"))
        hex_code = _as_str(entry.get("hex"))
        if name and hex_code:
            colors.append(ImageColor(name=name, hex=hex_code))
    return colors


def _confidence_for(description: str, colors: list[ImageColor]) -> Confidence:
    """Grade the read: empty description is low; description + colors is high."""
    if not description:
        return "low"
    if colors:
        return "high"
    return "medium"


def _read_from_payload(payload: dict[str, object]) -> ImageRead:
    """Build an :class:`ImageRead` from a parsed JSON payload."""
    description = _as_str(payload.get("description"))
    colors = _coerce_colors(payload.get("colors"))
    return ImageRead(
        description=description,
        colors=colors,
        light=_as_str(payload.get("light")),
        mood=_as_str_list(payload.get("mood")),
        framing=_as_str(payload.get("framing")),
        confidence=_confidence_for(description, colors),
    )


async def read_image(
    client: OllamaClient,
    image_path: Path | str,
    *,
    model: str | None = None,
) -> ImageRead:
    """Read ``image_path`` into a structured :class:`ImageRead`.

    ``model`` overrides the client's configured vision model when supplied.
    Returns a low-confidence empty read when the model output is unusable.
    """
    description = await client.describe_image(image_path, IMAGE_PROMPT, model=model)
    payload = _extract_json(description)
    if payload is None:
        return ImageRead(confidence="low")
    return _read_from_payload(payload)


def _extract_json(text: str) -> dict[str, object] | None:
    """Reuse the client's tolerant JSON-object extraction over a text blob."""
    from throughline.models.ollama_client import _parse_json_object

    parsed = _parse_json_object(text)
    return parsed or None
