"""The Thread — the unstuck engine, the heart of throughline.

The user types what they are stuck on; the engine returns ONE sharp question,
ONE connection from their OWN vault (quoted, with why it connects), and ONE
concrete next step they can do today. It ALWAYS ends on an action and is always
grounded in the user's own material — never a generic platitude.
"""

from __future__ import annotations

__all__ = [
    "find_connection",
    "finalize",
    "log_momentum",
    "pull_thread",
    "regenerate_step",
    "save_turn",
]

from throughline.thread.connection import find_connection
from throughline.thread.engine import (
    finalize,
    pull_thread,
    regenerate_step,
)
from throughline.thread.persistence import log_momentum, save_turn
