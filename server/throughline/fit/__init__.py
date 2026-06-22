"""Fit Check — hold something up against the user's profile and answer, honestly,
how *them* it is.

The engine scores an artifact (an image, a caption, or a song) against the
living :class:`~throughline.schemas.Profile`: a 0–100 closeness to the centre of
their taste, one honest verdict, a checklist tying each relevant profile claim to
a pass/fail with a concrete fix, and the nearest matches from their own vault.

Honesty over invention is the rule, same as everywhere: off-profile-on-purpose
is valid (a fail is *drift*, not an error), checks only ever cite REAL profile
claims, and a sparse/unparseable model response degrades to a grounded
similarity-based read rather than fabricated certainty.
"""

from throughline.fit.check import run_fit_check
from throughline.fit.batch import rank_candidates
from throughline.fit.disagreements import (
    add_disagreement,
    load_disagreements,
)

__all__ = [
    "run_fit_check",
    "rank_candidates",
    "add_disagreement",
    "load_disagreements",
]
