"""Prompt assembly for Fit Check's text-model call.

Fit Check asks the model one honest question: held up against this person's own
profile, how *them* is this artifact? The model is given the subject (an image
description, a caption, or a song) and the user's REAL profile claims, and asked
for a JSON object: a 0–100 score, one lowercase verdict, and a checklist that
ties each relevant claim to a pass/fail with a concrete fix.

The prompt is grounded in the user's actual claims — never generic "good"/"bad".
Off-profile-on-purpose is explicitly framed as valid so a fail reads as honest
drift, not a scolding.
"""

from __future__ import annotations

from throughline.schemas import FitKind, Profile, ProfileClaim

# How many profile claims to fold into the checklist. Capped so the prompt stays
# tight and the model can reason about each one; claims beyond this are dropped.
MAX_CLAIMS = 10

# Human phrasing for each input kind, used in the prompt's framing line.
_KIND_NOUN: dict[FitKind, str] = {
    "image": "image",
    "caption": "caption / piece of writing",
    "song": "song",
}


def select_claims(profile: Profile) -> list[ProfileClaim]:
    """Return the claims to check against, highest-confidence first, capped.

    Confidence ordering (high → medium → low) surfaces the claims the profile is
    most sure of; ties keep the profile's own order. Capped at :data:`MAX_CLAIMS`
    so the checklist stays focused.
    """
    rank = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(
        profile.claims, key=lambda c: rank.get(c.confidence, 3)
    )
    return ordered[:MAX_CLAIMS]


def _kind_noun(kind: str) -> str:
    return _KIND_NOUN.get(kind, "thing")  # type: ignore[arg-type]


def build_fit_prompt(
    profile: Profile,
    kind: str,
    subject: str,
    claims: list[ProfileClaim],
    *,
    disagreed: list[str] | None = None,
) -> str:
    """Compose the Fit Check prompt for ``complete_json``.

    Asks for a JSON object ``{score, verdict, checks:[{rule, passed, fix}]}``.
    ``claims`` are the (already selected) profile claims to check against, listed
    verbatim so the model cites real rules. ``disagreed`` rules are framed as
    things the user has said do NOT define them — the model must treat those as
    optional and never fail the artifact on them.
    """
    noun = _kind_noun(kind)
    lines: list[str] = [
        "You are a small, local tool that checks how well something fits a "
        "specific person's taste — their own profile, drawn from their own "
        "vault. You are honest, not flattering. Being off-profile ON PURPOSE is "
        "valid and interesting: a failed check means the thing DRIFTS from their "
        "usual taste, NOT that it is bad. Never scold.",
        "",
        "Respond with ONLY a JSON object, no prose, with exactly these keys:",
        '  "score": an integer 0-100 — how close this is to the centre of THEIR '
        "taste (100 = unmistakably them, 0 = nothing like them),",
        '  "verdict": ONE short honest lowercase line summarising the fit '
        "(e.g. \"this is very you — the loneliness and the neon are right there\" "
        'or "this drifts from your usual — brighter and busier than you tend to '
        'go"),',
        '  "checks": an array of objects, ONE per rule below that is relevant, '
        'each {"rule": <the rule text VERBATIM from the list>, "passed": '
        '<true|false>, "fix": <a short lowercase concrete suggestion to bring it '
        "closer, or null if it already fits or no honest fix applies>}.",
        "",
        f"WHAT THEY ARE HOLDING UP (a {noun}):",
        subject.strip() or "(nothing described)",
    ]

    if claims:
        lines.append("")
        lines.append(
            "THEIR PROFILE — check the artifact against these rules (use each "
            "rule's text VERBATIM in your checks; only include rules that are "
            "actually relevant to this artifact):"
        )
        lines.extend(f"  - {claim.text}" for claim in claims)
    else:
        lines.append("")
        lines.append(
            "Their profile has no firm claims yet, so checks can be an empty "
            "array — base the score and verdict on the overall vibe alone, and "
            "be honest that the read is thin."
        )

    cleaned_disagreed = [d.strip() for d in (disagreed or []) if d.strip()]
    if cleaned_disagreed:
        lines.append("")
        lines.append(
            "The user has said these rules do NOT define them — treat them as "
            "optional, never fail the artifact on them, and do not include them "
            "as failed checks:"
        )
        lines.extend(f"  - {rule}" for rule in cleaned_disagreed)

    lines.append("")
    lines.append(
        "Only state what the artifact and the rules actually support — do NOT "
        "invent rules that are not in the list. Keep every string lowercase."
    )
    return "\n".join(lines)


# The vision-model instruction used to turn an image into a describable subject
# before scoring. Kept terse — the vision model returns a plain description we
# then score against the profile (same one-embedding-space approach as intake).
IMAGE_SUBJECT_PROMPT = (
    "Describe this image plainly for a taste comparison. Respond with ONLY a "
    'JSON object: {"description": <2-3 lowercase sentences on subject, mood, '
    'light, colour, and framing>}. Be concrete and honest; do not invent detail '
    "you cannot see."
)
