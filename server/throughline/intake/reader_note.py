"""Read a note body into a structured :class:`NoteRead`.

The text model is asked for a strict JSON object capturing the themes, feelings
and connections expressed in the note. Honesty over invention: a sparse or
unparseable response degrades to a low-confidence read with empty lists.
"""

from __future__ import annotations

from throughline.models.ollama_client import OllamaClient
from throughline.schemas import Confidence, Item, NoteRead

NOTE_PROMPT_TEMPLATE = (
    "Read this personal note and respond with ONLY a JSON object, no prose, "
    "with exactly these keys:\n"
    '  "themes": an array of short theme phrases the note is about,\n'
    '  "feelings": an array of one-word emotions the note expresses,\n'
    '  "connections": an array of short notes on what this might connect to '
    "(people, ideas, other interests).\n"
    "Only include what is actually present in the text. Do not invent.\n\n"
    "TITLE: {title}\n"
    "NOTE:\n{body}"
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


def _confidence_for(themes: list[str], feelings: list[str]) -> Confidence:
    """Grade the read: nothing extracted is low; both themes+feelings is high."""
    if not themes and not feelings:
        return "low"
    if themes and feelings:
        return "high"
    return "medium"


def _read_from_payload(payload: dict[str, object]) -> NoteRead:
    """Build a :class:`NoteRead` from a parsed JSON payload."""
    themes = _as_str_list(payload.get("themes"))
    feelings = _as_str_list(payload.get("feelings"))
    return NoteRead(
        themes=themes,
        feelings=feelings,
        connections=_as_str_list(payload.get("connections")),
        confidence=_confidence_for(themes, feelings),
    )


async def read_note(
    client: OllamaClient,
    item: Item,
    text_model: str,
) -> NoteRead:
    """Read ``item``'s body into a structured :class:`NoteRead`.

    ``text_model`` is the resolved model name (which may be the vision model
    when the preferred reasoning model is not yet downloaded). Returns a
    low-confidence empty read for an empty body or unusable model output.
    """
    if not item.body.strip():
        return NoteRead(confidence="low")
    prompt = NOTE_PROMPT_TEMPLATE.format(title=item.title, body=item.body)
    payload = await client.complete_json(text_model, prompt)
    if not payload:
        return NoteRead(confidence="low")
    return _read_from_payload(payload)
