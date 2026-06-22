"""Pydantic contracts for vault items and search results.

The vault is the source of truth: frontmatter declares *what* an item is and
the body is the *why*. These models are the parsed, validated representation
of that on-disk reality.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Taste types are outward-shareable; self types are inward-only (privacy wall).
TASTE_TYPES: frozenset[str] = frozenset({"movie", "song", "book", "quote"})
SELF_TYPES: frozenset[str] = frozenset({"ambition", "fear", "experience", "journal"})

# Fallback type for notes whose frontmatter is missing or unparseable.
DEFAULT_ITEM_TYPE = "note"

# Image attachment suffixes the intake worker treats as vision items.
IMAGE_SUFFIXES: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})

# Honesty-over-invention: a low-confidence read is the safe fallback.
Confidence = Literal["low", "medium", "high"]


class Item(BaseModel):
    """A single parsed vault note.

    ``id`` is the stable identifier (path relative to the vault root).
    ``content_hash`` is sha256 of the raw file bytes, enabling read-once
    idempotency. ``is_self`` marks inward-only material for the privacy wall.
    """

    id: str
    path: str
    type: str
    title: str
    feeling: str | None = None
    tags: list[str] = Field(default_factory=list)
    body: str = ""
    content_hash: str
    is_self: bool
    locked: bool = False


class SearchResult(BaseModel):
    """An explainable semantic-search hit.

    ``score`` is a similarity in ``[0, 1]`` (higher is closer). ``why`` is a
    human-readable reason the item matched (term overlap, tags, or title).
    """

    item_id: str
    title: str
    path: str
    score: float
    why: str


class ImageColor(BaseModel):
    """A named dominant colour with its hex code (e.g. ``neon magenta`` / ``#ff2bd6``)."""

    name: str
    hex: str


class ImageRead(BaseModel):
    """A structured read of an image attachment produced by the vision model.

    Honesty over invention: when the model returns sparse or unparseable output
    the read degrades to ``confidence="low"`` with empty fields rather than
    fabricated detail.
    """

    description: str = ""
    colors: list[ImageColor] = Field(default_factory=list)
    light: str = ""
    mood: list[str] = Field(default_factory=list)
    framing: str = ""
    confidence: Confidence = "low"


class NoteRead(BaseModel):
    """A structured read of a note body produced by the text model.

    Degrades to ``confidence="low"`` with empty lists when the model output is
    sparse or unparseable — never invents themes/feelings/connections.
    """

    themes: list[str] = Field(default_factory=list)
    feelings: list[str] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"


# The nine sections a profile claim can belong to: the creative slice
# (mood/light/framing/subjects + do's & don'ts) and the deeper slice
# (recurring themes, stated ambitions, threads that recur across items).
ProfileSection = Literal[
    "mood",
    "light",
    "framing",
    "subjects",
    "dos",
    "donts",
    "themes",
    "ambitions",
    "threads",
]

# Sections belonging to each slice, used to verify a generated profile spans
# both the creative and deeper halves of the picture.
CREATIVE_SECTIONS: frozenset[str] = frozenset(
    {"mood", "light", "framing", "subjects", "dos", "donts"}
)
DEEPER_SECTIONS: frozenset[str] = frozenset({"themes", "ambitions", "threads"})


class ProfileClaim(BaseModel):
    """One backed line in the profile.

    Every claim carries the example item ids it was drawn from and a confidence
    level — honesty over invention. ``pinned`` claims survive regeneration.
    """

    id: str
    section: ProfileSection
    text: str
    examples: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    pinned: bool = False


class PaletteSwatch(BaseModel):
    """A named colour in the profile's palette (e.g. ``neon magenta`` / ``#ff2bd6``)."""

    name: str
    hex: str


class Profile(BaseModel):
    """One living picture of the user drawn from their vault.

    ``source_count`` is how many vault items the picture was built from;
    ``confidence_note`` is an honest acknowledgement of how thin/rich the read
    is. The structured form is the rebuildable working copy; a readable note is
    written back into the vault alongside it.
    """

    name: str
    source_count: int
    confidence_note: str
    palette: list[PaletteSwatch] = Field(default_factory=list)
    claims: list[ProfileClaim] = Field(default_factory=list)
    generated_at: str | None = None
    # Stable hash of the vault items the portrait was drawn from. Regeneration is
    # skipped (the saved portrait is returned verbatim) while this is unchanged,
    # so colours/claims stay put until the vault actually changes.
    source_signature: str | None = None
    # The sampling knobs the portrait was drawn with (editable in the UI):
    # temperature 0 = identical every redraw; raise it or change the seed for a
    # different take. Changing either triggers a regeneration.
    temperature: float = 0.0
    seed: int = 7


class IntakeProgress(BaseModel):
    """A snapshot of the background intake worker's progress (for SSE)."""

    done: int
    total: int
    current_title: str | None = None
    phase: str
    paused: bool = False


# Roles a configured model can play; "other" is the catch-all for anything
# Ollama reports loaded that isn't one of the three configured roles.
ModelRole = Literal["embed", "text", "vision", "other"]


class ModelStatus(BaseModel):
    """On/off status of a configured model for the RAM-control panel.

    ``installed`` is true when Ollama has the model pulled locally (in
    ``/api/tags``); ``loaded`` is true when it is currently resident in memory
    (in ``/api/ps``). ``size_mb`` is the resident VRAM size in megabytes when
    loaded, else ``None``.
    """

    name: str
    role: ModelRole
    installed: bool
    loaded: bool
    size_mb: float | None = None


# The two sizes a next step can take: the default "normal" actionable nudge and
# the "smaller" variant the user can ask for when the normal step feels too big.
NextStepSize = Literal["normal", "smaller"]


class ThreadConnection(BaseModel):
    """One connection pulled from the user's OWN vault for the Thread.

    Grounds a nudge in something the user already said / loved / lived:
    ``item_id`` is the real vault item it was drawn from, ``quote`` is a short
    representative line lifted from that item's body, and ``why`` is the model's
    one-line reason it connects to what the user is stuck on.
    """

    item_id: str
    title: str
    quote: str
    why: str


class NextStep(BaseModel):
    """The Thread's ONE concrete, doable-today action.

    ``size`` records whether this is the default step or the deliberately
    smaller/easier variant the user asked for. The Thread NEVER ends without a
    non-empty, actionable ``text`` — pure analysis with no next step is a
    failure state.
    """

    text: str
    size: NextStepSize = "normal"


class ThreadTurn(BaseModel):
    """One turn of the unstuck engine, in order: question, connection, step.

    ``stuck`` is what the user typed they were stuck on. ``question`` is ONE
    sharp question to unstick their own head. ``connection`` is grounded in a
    real vault item (``None`` only when the vault is empty). ``next_step`` is
    always present and actionable. ``done`` flips true once the user logs
    momentum via "did it".
    """

    id: str
    stuck: str
    question: str
    connection: ThreadConnection | None = None
    next_step: NextStep
    done: bool = False


# The kinds of input Fit Check can score against the profile.
FitKind = Literal["image", "caption", "song"]


class FitCheckItem(BaseModel):
    """One named check, tied to a REAL profile claim.

    ``rule`` is the verbatim text of the profile claim this check is grounded
    in — never a generic "good"/"bad". ``passed`` is whether the input fits that
    rule (off-profile-on-purpose is valid, so a fail is drift, not an error).
    ``fix`` is a concrete, optional suggestion; ``None`` when the check passed or
    no honest fix applies.
    """

    rule: str
    passed: bool
    fix: str | None = None


class FitResult(BaseModel):
    """The answer to "how *me* is this?" — measured against the user's profile.

    ``score`` is 0–100, the closeness to the centre of the user's taste (higher
    is more "them"). ``verdict`` is one honest lowercase line. ``checks`` turns
    each relevant profile claim into a pass/fail with a fix. ``closest`` is the
    nearest matches from the user's own vault. ``kind`` echoes the input kind.
    """

    score: int
    verdict: str
    checks: list[FitCheckItem] = Field(default_factory=list)
    closest: list[dict] = Field(default_factory=list)
    kind: str
