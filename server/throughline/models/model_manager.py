"""Heavy-model swap manager.

The 16GB memory budget allows only one heavy model resident at a time. Before
switching heavy roles, the previously-loaded model is unloaded via
``keep_alive=0`` so Ollama stops its runner process and Metal memory is
reclaimed cleanly. The small embedding model is kept warm and is never swapped.
"""

from __future__ import annotations

from typing import Any

from throughline.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VISION_MODEL,
)
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import ModelRole, ModelStatus

_UNLOAD_KEEP_ALIVE = 0

# Bytes-per-megabyte divisor for reporting VRAM size (decimal MB, per the spec).
_BYTES_PER_MB = 1e6


class ModelManager:
    """Guarantee that at most one heavy model is resident at a time."""

    def __init__(
        self,
        client: OllamaClient,
        *,
        text_model: str = DEFAULT_TEXT_MODEL,
        vision_model: str = DEFAULT_VISION_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
    ) -> None:
        self._client = client
        self.HEAVY: dict[str, str] = {"text": text_model, "vision": vision_model}
        self.EMBED = embed_model
        self._loaded_heavy: str | None = None

    @property
    def loaded_heavy(self) -> str | None:
        """The heavy model this manager believes is resident (or None)."""
        return self._loaded_heavy

    @property
    def client(self) -> OllamaClient:
        """The underlying Ollama client (for fetching installed/loaded lists)."""
        return self._client

    @property
    def configured(self) -> list[str]:
        """The three configured model names (embed, text, vision), in order.

        Order is deterministic so the control panel always lists models the
        same way. De-duplicates if the text/vision fallback collapses two
        roles onto one model.
        """
        ordered = [self.EMBED, self.HEAVY["text"], self.HEAVY["vision"]]
        seen: set[str] = set()
        unique: list[str] = []
        for name in ordered:
            if name not in seen:
                seen.add(name)
                unique.append(name)
        return unique

    def _role_for(self, name: str) -> ModelRole:
        """Classify a model name into its configured role (else ``"other"``)."""
        if name == self.EMBED:
            return "embed"
        if name == self.HEAVY["text"]:
            return "text"
        if name == self.HEAVY["vision"]:
            return "vision"
        return "other"

    async def use(self, role: str) -> str:
        """Make ``role``'s model the only resident heavy model; return its name.

        Unloads the previously-tracked heavy model first when switching to a
        different one. Raises ``KeyError`` for an unknown role.
        """
        if role not in self.HEAVY:
            raise KeyError(f"unknown heavy role: {role!r} (expected one of {sorted(self.HEAVY)})")
        target = self.HEAVY[role]
        if self._loaded_heavy is not None and self._loaded_heavy != target:
            await self._unload(self._loaded_heavy)
        self._loaded_heavy = target
        return target

    async def _unload(self, model: str) -> None:
        """Stop ``model``'s runner via ``keep_alive=0`` for clean reclaim."""
        await self._client.generate(model, prompt="", keep_alive=_UNLOAD_KEEP_ALIVE)

    async def loaded(self) -> list[str]:
        """Return the names of models Ollama currently reports as loaded."""
        running = await self._client.list_running()
        return [m["name"] for m in running if isinstance(m, dict) and "name" in m]

    async def status(
        self,
        installed: list[str],
        loaded: list[dict[str, Any]],
    ) -> list[ModelStatus]:
        """Build a :class:`ModelStatus` for each configured model.

        ``installed`` is the list of model names from ``/api/tags``; ``loaded``
        is the raw ``/api/ps`` entry list. Both are passed in (already fetched
        by the caller) so this stays pure and easy to test. The result is in
        configured order (embed, text, vision).
        """
        loaded_by_name = _loaded_by_name(loaded)
        statuses: list[ModelStatus] = []
        for name in self.configured:
            entry = loaded_by_name.get(name)
            statuses.append(
                ModelStatus(
                    name=name,
                    role=self._role_for(name),
                    installed=name in installed,
                    loaded=entry is not None,
                    size_mb=_size_mb(entry) if entry is not None else None,
                )
            )
        return statuses

    async def load(self, name: str) -> None:
        """Preload ``name`` into memory (no generation)."""
        await self._client.load_model(name)
        if name in self.HEAVY.values():
            self._loaded_heavy = name

    async def unload(self, name: str) -> None:
        """Unload ``name`` from memory via ``keep_alive=0``."""
        await self._client.unload_model(name)
        if self._loaded_heavy == name:
            self._loaded_heavy = None

    async def unload_all(self, loaded: list[dict[str, Any]]) -> None:
        """Unload every currently-loaded model named in ``loaded``."""
        for name in _loaded_by_name(loaded):
            await self.unload(name)


def _loaded_by_name(loaded: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index ``/api/ps`` entries by their model name.

    Ollama reports the identifier under ``name`` and/or ``model``; we accept
    either so a model loaded under its bare tag still matches.
    """
    indexed: dict[str, dict[str, Any]] = {}
    for entry in loaded:
        if not isinstance(entry, dict):
            continue
        key = entry.get("name") or entry.get("model")
        if isinstance(key, str):
            indexed[key] = entry
    return indexed


def _size_mb(entry: dict[str, Any]) -> float | None:
    """Return the resident VRAM size in megabytes (rounded), or ``None``."""
    raw = entry.get("size_vram")
    if not isinstance(raw, (int, float)):
        return None
    return round(raw / _BYTES_PER_MB)
