"""Fit Check engine — score one artifact against the user's profile.

Given a subject (an image's description, a caption, or a song) and the user's
:class:`~throughline.schemas.Profile`, produce a :class:`FitResult`: a 0–100
closeness score, one honest lowercase verdict, a checklist tying each relevant
profile claim to a pass/fail with a concrete fix, and the nearest matches from
the user's own vault.

Guardrails, in the same spirit as the Thread:

* checks only ever cite REAL profile claims — a paraphrased or invented "rule"
  is dropped rather than shown;
* rules the user has disagreed with are never returned as failures;
* a missing/unparseable score degrades to a grounded similarity score (from the
  nearest vault match), and a missing verdict degrades to an honest band line —
  never fabricated certainty.
"""

from __future__ import annotations

import json

from throughline.config import Settings
from throughline.fit.disagreements import load_disagreements
from throughline.fit.prompts import (
    IMAGE_SUBJECT_PROMPT,
    build_fit_prompt,
    select_claims,
)
from throughline.index.search import search
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import FitCheckItem, FitResult, Profile, ProfileClaim

# How many nearest vault items to surface as "closest to your taste".
_CLOSEST_K = 3
# Score bounds.
_SCORE_MIN = 0
_SCORE_MAX = 100
# Verdict bands (inclusive lower bound → honest lowercase line) for the fallback
# verdict when the model returns none.
_VERDICT_BANDS: tuple[tuple[int, str], ...] = (
    (75, "this is very you."),
    (50, "this is mostly you, with a little drift."),
    (25, "this drifts from your usual taste."),
    (0, "this is far from your usual taste."),
)


class FitCheckError(ValueError):
    """Raised when a fit check cannot run (e.g. no profile generated yet)."""


def _normalise(text: str) -> str:
    """Lowercase + collapse whitespace, for tolerant rule↔claim matching."""
    return " ".join(text.lower().split())


def _clamp_score(value: int) -> int:
    return max(_SCORE_MIN, min(_SCORE_MAX, value))


def _similarity_score(closest: list[dict]) -> int:
    """Grounded fallback score: the nearest vault match's similarity, 0–100."""
    if not closest:
        return 50  # nothing to compare against — an honest, neutral midpoint.
    best = max((c.get("score", 0) for c in closest), default=0)
    return _clamp_score(int(best))


def _parse_score(payload: dict[str, object], closest: list[dict]) -> int:
    """Read + clamp the model's score, falling back to a similarity score."""
    raw = payload.get("score")
    if isinstance(raw, bool):  # bool is an int subclass — reject it explicitly.
        return _similarity_score(closest)
    if isinstance(raw, (int, float)):
        return _clamp_score(int(raw))
    if isinstance(raw, str):
        digits = raw.strip().rstrip("%")
        try:
            return _clamp_score(int(float(digits)))
        except ValueError:
            pass
    return _similarity_score(closest)


def _band_verdict(score: int) -> str:
    """Return the honest fallback verdict line for ``score``."""
    for lower, line in _VERDICT_BANDS:
        if score >= lower:
            return line
    return _VERDICT_BANDS[-1][1]


def _parse_verdict(payload: dict[str, object], score: int) -> str:
    """Read the model's verdict (lowercased); fall back to a band line."""
    raw = payload.get("verdict")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return _band_verdict(score)


def _check_from_entry(
    entry: dict[str, object],
    claim_by_norm: dict[str, ProfileClaim],
    disagreed_norms: set[str],
) -> FitCheckItem | None:
    """Build one validated :class:`FitCheckItem`, or ``None`` when unusable.

    The entry's ``rule`` must map to a REAL profile claim (exact normalised match
    preferred, then a generous substring match) — an invented rule is dropped.
    Rules the user has disagreed with are dropped entirely so they never read as
    failures. ``fix`` degrades to ``None`` when blank.
    """
    rule_raw = entry.get("rule")
    if not isinstance(rule_raw, str) or not rule_raw.strip():
        return None
    norm = _normalise(rule_raw)
    if norm in disagreed_norms:
        return None

    claim = claim_by_norm.get(norm)
    if claim is None:
        # Generous fallback: the model lightly paraphrased a real claim.
        for claim_norm, candidate in claim_by_norm.items():
            if len(norm) > 10 and (norm in claim_norm or claim_norm in norm):
                claim = candidate
                break
    if claim is None:
        return None

    passed = bool(entry.get("passed"))
    fix_raw = entry.get("fix")
    fix = fix_raw.strip().lower() if isinstance(fix_raw, str) and fix_raw.strip() else None
    if passed:
        fix = None  # a passing check needs no fix.
    return FitCheckItem(rule=claim.text, passed=passed, fix=fix)


def _checks_from_payload(
    payload: dict[str, object],
    claims: list[ProfileClaim],
    disagreed: list[str],
) -> list[FitCheckItem]:
    """Validate the model's checks against the real claims (drops the rest).

    Deduplicates by rule so a claim is checked at most once, preserving the
    model's order.
    """
    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        return []
    claim_by_norm = {_normalise(c.text): c for c in claims}
    disagreed_norms = {_normalise(d) for d in disagreed}

    checks: list[FitCheckItem] = []
    seen: set[str] = set()
    for entry in raw_checks:
        if not isinstance(entry, dict):
            continue
        check = _check_from_entry(entry, claim_by_norm, disagreed_norms)
        if check is not None and check.rule not in seen:
            seen.add(check.rule)
            checks.append(check)
    return checks


async def find_closest(
    store: VecStore, embeddings: Embeddings, subject: str
) -> list[dict]:
    """Return the nearest taste items to ``subject`` as ``{item_id,title,score}``.

    Searches outward-shareable taste only (``inward_only=False``) so the privacy
    wall keeps self-material out of this comparison. Returns ``[]`` for a blank
    subject or an empty vault.
    """
    cleaned = subject.strip()
    if not cleaned:
        return []
    hits = await search(store, embeddings, cleaned, inward_only=False, k=_CLOSEST_K)
    return [
        {"item_id": hit.item_id, "title": hit.title, "score": round(hit.score * 100)}
        for hit in hits
    ]


def describe_image_subject(raw: str) -> str:
    """Turn the vision model's (JSON) image response into a plain subject string.

    Reads the ``description`` field when the response parses as a JSON object;
    otherwise falls back to the raw text. Never raises — a blank result degrades
    to an empty subject the scorer handles honestly.
    """
    text = raw.strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, dict):
        description = parsed.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()
    return text


async def describe_image(
    client: OllamaClient, vision_model: str, image_path: str
) -> str:
    """Describe an image for fit scoring via the vision model (one plain string)."""
    raw = await client.describe_image(
        image_path, IMAGE_SUBJECT_PROMPT, model=vision_model
    )
    return describe_image_subject(raw)


async def run_fit_check(
    state: object,
    profile: Profile,
    kind: str,
    subject: str,
    *,
    text_model: str,
) -> FitResult:
    """Score ``subject`` against ``profile`` and return a guardrailed FitResult.

    ``subject`` is the already-derived text to score (an image description for
    image kind, or the raw caption/song text). The route is responsible for
    making the text model resident before calling this. Pulls the closest vault
    matches, asks the model for score/verdict/checks, then enforces the
    grounding + honesty guardrails.
    """
    store = getattr(state, "store", None)
    if store is None:
        raise FitCheckError("no vault connected")
    settings: Settings = state.settings  # type: ignore[attr-defined]
    embeddings: Embeddings = state.embeddings  # type: ignore[attr-defined]
    client: OllamaClient = state.client  # type: ignore[attr-defined]

    closest = await find_closest(store, embeddings, subject)
    claims = select_claims(profile)
    disagreed = (
        load_disagreements(settings.cache_dir)
        if settings.cache_dir is not None
        else []
    )

    prompt = build_fit_prompt(profile, kind, subject, claims, disagreed=disagreed)
    payload = await client.complete_json(text_model, prompt)

    score = _parse_score(payload, closest)
    verdict = _parse_verdict(payload, score)
    checks = _checks_from_payload(payload, claims, disagreed)

    return FitResult(
        score=score,
        verdict=verdict,
        checks=checks,
        closest=closest,
        kind=kind,
    )
