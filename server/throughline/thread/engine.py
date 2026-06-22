"""The Thread — the unstuck engine, the heart of throughline.

The user says what they're stuck on. The engine returns, IN ORDER: ONE sharp
question that unsticks their own head; ONE connection pulled from their OWN
vault (a thing they already said / loved / lived, quoted, with why it connects);
and ONE next step — small, specific, doable TODAY.

Hard rules enforced here:

* It ALWAYS ends on a concrete action. Pure analysis with no next step is a
  failure state — :func:`finalize` retries with a stricter prompt and, failing
  that, synthesizes a minimal concrete step from the connection.
* Every nudge is grounded in the user's own vault content, never a generic
  platitude — the connection cites a real vault item id.
"""

from __future__ import annotations

import uuid

from throughline.config import Settings
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.profile.store import load_profile
from throughline.schemas import (
    Item,
    NextStep,
    NextStepSize,
    ThreadConnection,
    ThreadTurn,
)
from throughline.thread.connection import extract_quote, find_connection
from throughline.thread.persistence import log_momentum, save_turn
from throughline.thread.prompts import build_thread_prompt

__all__ = [
    "find_connection",
    "pull_thread",
    "finalize",
    "log_momentum",
    "save_turn",
]

# Words/phrases that signal a non-actionable, analysis-only "step" we reject.
_NON_ACTIONABLE_MARKERS: frozenset[str] = frozenset(
    {
        "think about",
        "reflect on",
        "consider whether",
        "ponder",
        "contemplate",
        "analyze",
        "analyse",
    }
)
# A next step shorter than this many characters is treated as too vague to act on.
_MIN_STEP_CHARS = 8
# Fallback question when the model returns nothing usable for the question slot.
_FALLBACK_QUESTION = "what is the smallest piece of this you could start right now?"


def _state_pieces(
    state: object,
    text_model: str | None,
) -> tuple[Settings, VecStore, Embeddings, OllamaClient, list[Item], str]:
    """Pull the pieces the engine needs off an :class:`AppState`-like object.

    Fails fast with a clear error when no vault (and therefore no store) is
    connected, since the Thread has nothing of the user's own to ground in.
    ``text_model`` overrides the configured model (the route resolves it, with
    the vision-model fallback); ``None`` uses ``settings.text_model``.
    """
    store = getattr(state, "store", None)
    if store is None:
        raise ValueError("no vault connected")
    settings: Settings = state.settings  # type: ignore[attr-defined]
    if settings.cache_dir is None:
        raise ValueError("no cache dir configured: connect a vault first")
    resolved = text_model or settings.text_model
    return (
        settings,
        store,
        state.embeddings,  # type: ignore[attr-defined]
        state.client,  # type: ignore[attr-defined]
        state.items,  # type: ignore[attr-defined]
        resolved,
    )


def _is_actionable(text: str) -> bool:
    """Return True when ``text`` reads like a real, do-it-today action.

    Rejects empty/too-short text, bare questions, and analysis-only phrasings —
    the guardrail that keeps the Thread from ending on pure reflection.
    """
    cleaned = text.strip()
    if len(cleaned) < _MIN_STEP_CHARS:
        return False
    lowered = cleaned.lower()
    if lowered.endswith("?"):
        return False
    return not any(marker in lowered for marker in _NON_ACTIONABLE_MARKERS)


def _fallback_step(connection: ThreadConnection | None, stuck: str) -> str:
    """Synthesize a minimal concrete step when the model gives none.

    Anchors to the user's own connection when there is one (re-read it, write
    one sentence) so the fallback is still grounded; otherwise a generic-but-
    concrete first move. Never returns empty — the Thread must end on an action.
    """
    if connection is not None and connection.title:
        return (
            f'open a blank note and write one sentence reacting to "'
            f'{connection.title}" — just the first thing that comes out.'
        )
    return (
        "set a 10-minute timer and write the very first sentence of this, "
        "however rough."
    )


def _build_connection(
    pair: tuple[Item, str] | None, why: str
) -> ThreadConnection | None:
    """Build a :class:`ThreadConnection` from a found ``(item, quote)`` pair."""
    if pair is None:
        return None
    item, quote = pair
    return ThreadConnection(
        item_id=item.id,
        title=item.title,
        quote=quote,
        why=why.strip(),
    )


async def _ask_model(
    client: OllamaClient,
    text_model: str,
    store: VecStore,
    stuck: str,
    pair: tuple[Item, str] | None,
    profile: object,
    *,
    size: NextStepSize,
    avoid: str | None,
    strict: bool,
) -> tuple[str, str, str]:
    """Call the model once; return ``(question, connection_why, next_step)``.

    Each string is trimmed; missing keys degrade to empty so the guardrail in
    :func:`finalize` can decide what to do.
    """
    item = pair[0] if pair is not None else None
    quote = pair[1] if pair is not None else ""
    prompt = build_thread_prompt(
        store,
        stuck,
        item,
        quote,
        profile,  # type: ignore[arg-type]
        size=size,
        avoid=avoid,
        strict=strict,
    )
    payload = await client.complete_json(text_model, prompt)
    question = str(payload.get("question", "")).strip()
    why = str(payload.get("connection_why", "")).strip()
    step = str(payload.get("next_step", "")).strip()
    return question, why, step


async def finalize(
    client: OllamaClient,
    text_model: str,
    store: VecStore,
    stuck: str,
    pair: tuple[Item, str] | None,
    profile: object,
    *,
    size: NextStepSize = "normal",
    avoid: str | None = None,
) -> tuple[str, ThreadConnection | None, NextStep]:
    """Produce a guaranteed-actionable ``(question, connection, next_step)``.

    Calls the model once; if the next step is empty/vague/non-actionable, retries
    once with a stricter prompt; if it is STILL not actionable, synthesizes a
    minimal concrete step from the connection. The Thread never returns without
    an actionable step.
    """
    question, why, step = await _ask_model(
        client, text_model, store, stuck, pair, profile,
        size=size, avoid=avoid, strict=False,
    )

    if not _is_actionable(step):
        retry_q, retry_why, retry_step = await _ask_model(
            client, text_model, store, stuck, pair, profile,
            size=size, avoid=avoid, strict=True,
        )
        # Keep any non-empty improvements from the strict retry.
        question = retry_q or question
        why = retry_why or why
        step = retry_step or step

    connection = _build_connection(pair, why)

    if not _is_actionable(step):
        step = _fallback_step(connection, stuck)

    if not question:
        question = _FALLBACK_QUESTION

    return question, connection, NextStep(text=step, size=size)


async def pull_thread(
    state: object,
    stuck: str,
    *,
    size: NextStepSize = "normal",
    avoid: str | None = None,
    turn_id: str | None = None,
    text_model: str | None = None,
) -> ThreadTurn:
    """Build one :class:`ThreadTurn` for ``stuck`` and persist it.

    Finds the connection in the user's own vault, asks the model for the
    question / why / next step, enforces the actionable-step guardrail, and saves
    the turn to ``threads.json`` so the controls can recall it. ``turn_id`` reuses
    an id (controls regenerating a turn); a new uuid is minted otherwise.
    """
    settings, store, embeddings, client, items, resolved_model = _state_pieces(
        state, text_model
    )

    pair = await find_connection(store, embeddings, items, stuck)
    profile = load_profile(settings)

    question, connection, next_step = await finalize(
        client, resolved_model, store, stuck, pair, profile, size=size, avoid=avoid
    )

    turn = ThreadTurn(
        id=turn_id or str(uuid.uuid4()),
        stuck=stuck,
        question=question,
        connection=connection,
        next_step=next_step,
    )
    assert settings.cache_dir is not None  # guaranteed by _state_pieces
    save_turn(settings.cache_dir, turn)
    return turn


def _connection_pair(turn: ThreadTurn, items: list[Item]) -> tuple[Item, str] | None:
    """Rebuild the ``(item, quote)`` pair from a persisted turn's connection.

    Re-resolves the live :class:`Item` by id (so the latest body is used) and
    re-extracts the quote; falls back to the stored quote if the item is gone.
    """
    if turn.connection is None:
        return None
    item = next((it for it in items if it.id == turn.connection.item_id), None)
    if item is None:
        return None
    return item, extract_quote(item.body) or turn.connection.quote


async def regenerate_step(
    state: object,
    turn: ThreadTurn,
    *,
    size: NextStepSize,
    avoid: str | None,
    text_model: str | None = None,
) -> ThreadTurn:
    """Regenerate a turn's next step (for the different / smaller controls).

    Reuses the original stuck text and connection from ``turn`` so the new step
    stays grounded, keeps the same id, re-runs the guardrailed model call, and
    re-persists. ``avoid`` makes the step genuinely different; ``size`` makes it
    smaller.
    """
    settings, store, _embeddings, client, items, resolved_model = _state_pieces(
        state, text_model
    )
    pair = _connection_pair(turn, items)
    profile = load_profile(settings)

    question, connection, next_step = await finalize(
        client, resolved_model, store, turn.stuck, pair, profile,
        size=size, avoid=avoid,
    )

    updated = turn.model_copy(
        update={
            "question": question,
            "connection": connection,
            "next_step": next_step,
        }
    )
    assert settings.cache_dir is not None
    save_turn(settings.cache_dir, updated)
    return updated
