"""Disk persistence for Fit Check disagreements.

When the user pushes back on a check ("this rule doesn't define me — i'm
off-profile on purpose"), that pushback is remembered in a rebuildable JSON file
in the cache dir so future fit checks soften that rule rather than dinging the
user for it again. The list is the small record that the tool listens back.

The file degrades gracefully: a missing or corrupt file reads as an empty set
rather than raising, so a damaged cache never blocks a fit check.
"""

from __future__ import annotations

import json
from pathlib import Path

DISAGREEMENTS_FILE_NAME = "fit_disagreements.json"


def _path(cache_dir: Path) -> Path:
    return Path(cache_dir) / DISAGREEMENTS_FILE_NAME


def load_disagreements(cache_dir: Path) -> list[str]:
    """Return the rule texts the user has disagreed with (``[]`` on miss/corrupt).

    Order is preserved (most-recently-added last) and duplicates are collapsed
    so the list reads as a stable set.
    """
    path = _path(cache_dir)
    if not path.exists():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    seen: set[str] = set()
    rules: list[str] = []
    for entry in parsed:
        rule = str(entry).strip()
        if rule and rule not in seen:
            seen.add(rule)
            rules.append(rule)
    return rules


def add_disagreement(cache_dir: Path, rule: str) -> list[str]:
    """Record a disagreement with ``rule`` and return the full updated list.

    Reads the existing list, returns a NEW list with the rule appended (deduped),
    and writes it back — the on-disk state is replaced wholesale, never mutated
    in place. A blank rule is a no-op that returns the current list unchanged.
    """
    cleaned = rule.strip()
    existing = load_disagreements(cache_dir)
    if not cleaned or cleaned in existing:
        return existing

    updated = [*existing, cleaned]
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    _path(cache).write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return updated
