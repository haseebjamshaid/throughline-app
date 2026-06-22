"""Async HTTP client for a local Ollama server.

Wraps the embed / chat / generate endpoints with explicit, typed error
handling. EmbeddingGemma prompt conventions are applied here because they
materially improve retrieval quality:

* documents are prefixed ``"title: none | text: "``
* queries are prefixed ``"task: search result | query: "``
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from throughline.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_VISION_MODEL,
)

DOCUMENT_PREFIX = "title: none | text: "
QUERY_PREFIX = "task: search result | query: "

_DEFAULT_TIMEOUT_SECONDS = 120.0

# A roomy context window so a thinking model has space to emit the JSON answer
# rather than exhausting its budget mid-reasoning.
_DEFAULT_JSON_NUM_CTX = 8192
_DEFAULT_JSON_OPTIONS: dict[str, Any] = {"num_ctx": _DEFAULT_JSON_NUM_CTX}


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error.

    Carries a human-readable message suitable for surfacing to a user; the
    originating exception (when any) is chained for server-side logging.
    """


class OllamaClient:
    """Thin async wrapper over the Ollama REST API.

    A single ``httpx.AsyncClient`` is reused across calls and closed via
    :meth:`aclose` (or by using the instance as an async context manager).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        embed_model: str = DEFAULT_EMBED_MODEL,
        *,
        vision_model: str = DEFAULT_VISION_MODEL,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._embed_model = embed_model
        self._vision_model = vision_model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> OllamaClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def embed_model(self) -> str:
        return self._embed_model

    @property
    def vision_model(self) -> str:
        return self._vision_model

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to ``path`` and return the parsed response.

        Connection failures and non-2xx statuses are converted to
        :class:`OllamaError` with a clear, typed message.
        """
        url = f"{self._base_url}{path}"
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"cannot reach Ollama at {self._base_url} — is it running? "
                "(start it with `ollama serve`)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama returned {exc.response.status_code} for {path}: "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request to {path} failed: {exc}") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return raw embeddings for ``texts`` via ``POST /api/embed``.

        No prompt prefixing is applied here; callers that want EmbeddingGemma
        conventions should use :meth:`embed_documents` / :meth:`embed_query`.
        """
        if not texts:
            return []
        data = await self._post(
            "/api/embed", {"model": self._embed_model, "input": texts}
        )
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise OllamaError(
                "Ollama /api/embed returned an unexpected payload "
                f"(expected {len(texts)} embeddings)"
            )
        return embeddings

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents with the EmbeddingGemma document prefix."""
        return await self.embed([f"{DOCUMENT_PREFIX}{text}" for text in texts])

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query with the EmbeddingGemma query prefix."""
        result = await self.embed([f"{QUERY_PREFIX}{text}"])
        return result[0]

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        stream: bool = False,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call ``POST /api/chat`` (non-streaming by default).

        Provided for later phases (Thread/Profile); not exercised in Phase 0.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options
        return await self._post("/api/chat", payload)

    async def generate(
        self,
        model: str,
        prompt: str,
        *,
        stream: bool = False,
        keep_alive: int | str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call ``POST /api/generate``.

        ``keep_alive=0`` is the unload signal used by the model manager.
        """
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        if options:
            payload["options"] = options
        return await self._post("/api/generate", payload)

    async def describe_image(
        self,
        image_path: Path | str,
        prompt: str,
        *,
        model: str | None = None,
    ) -> str:
        """Describe an image and return the model's (JSON) text response.

        Uses ``POST /api/chat`` with the base64 image attached, ``think=False``
        and ``format="json"``. The thinking-off path matters for ``qwen3-vl``:
        via ``/api/generate`` it exhausts its token budget in a ``thinking``
        field and returns an empty ``response``; the chat path suppresses
        reasoning and returns the description JSON directly. A free-form
        ``/api/generate`` call (reading either ``response`` or ``thinking``) is
        the fallback.

        ``model`` defaults to the configured vision model. Raises
        :class:`OllamaError` when the file is missing/unreadable, or when no
        text could be obtained from either endpoint.
        """
        path = Path(image_path)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise OllamaError(f"cannot read image at {path}: {exc}") from exc

        encoded = base64.b64encode(raw).decode("ascii")
        target = model or self._vision_model

        chat = await self._post(
            "/api/chat",
            {
                "model": target,
                "messages": [
                    {"role": "user", "content": prompt, "images": [encoded]}
                ],
                "stream": False,
                "think": False,
                "format": "json",
                "options": _DEFAULT_JSON_OPTIONS,
            },
        )
        message = chat.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

        generated = await self._post(
            "/api/generate",
            {
                "model": target,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
                "options": _DEFAULT_JSON_OPTIONS,
            },
        )
        for field in ("response", "thinking"):
            value = generated.get(field)
            if isinstance(value, str) and value.strip():
                return value
        raise OllamaError(
            "Ollama returned no text response for the image (chat and generate)"
        )

    async def complete_json(
        self,
        model: str,
        prompt: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON object from a constrained chat completion.

        Uses ``POST /api/chat`` with ``think=False`` and ``format="json"``.
        This matters for *thinking* models (notably ``qwen3-vl``): via
        ``/api/generate`` they spend their whole token budget in a separate
        ``thinking`` field and emit an empty ``response``; ``/api/chat`` with
        ``think=False`` actually suppresses the reasoning phase and returns the
        JSON directly. A roomy default ``num_ctx`` leaves space for the answer.

        If the chat content is still blank or unparseable we fall back once to
        ``/api/generate`` and recover JSON from either the ``response`` or the
        ``thinking`` field with the tolerant parser.

        Honesty over invention: when nothing parses, this returns an empty
        ``{}`` rather than raising, so callers degrade to a low-confidence empty
        read instead of fabricating structure. Transport failures still raise
        :class:`OllamaError`.
        """
        merged = {**_DEFAULT_JSON_OPTIONS, **(options or {})}
        content = await self._chat_json(model, prompt, options=merged)
        parsed = _parse_json_object(content)
        if parsed:
            return parsed

        data = await self._post(
            "/api/generate",
            {"model": model, "prompt": prompt, "stream": False, "options": merged},
        )
        for field in ("response", "thinking"):
            value = data.get(field)
            if isinstance(value, str) and value.strip():
                recovered = _parse_json_object(value)
                if recovered:
                    return recovered
        return {}

    async def _chat_json(
        self,
        model: str,
        prompt: str,
        *,
        options: dict[str, Any],
    ) -> str:
        """POST a single-message chat with thinking off; return the content."""
        data = await self._post(
            "/api/chat",
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "think": False,
                "format": "json",
                "options": options,
            },
        )
        message = data.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        return content if isinstance(content, str) else ""

    async def ps(self) -> list[dict[str, Any]]:
        """Return currently-loaded models via ``GET /api/ps``.

        Each entry carries a ``name``/``model`` and a ``size_vram`` (bytes
        resident in VRAM/Metal memory). Raises :class:`OllamaError` when the
        server is unreachable.
        """
        url = f"{self._base_url}/api/ps"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"cannot reach Ollama at {self._base_url} — is it running?"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama /api/ps failed: {exc}") from exc
        models = response.json().get("models", [])
        return models if isinstance(models, list) else []

    async def list_running(self) -> list[dict[str, Any]]:
        """Return currently-loaded models via ``GET /api/ps`` (alias of :meth:`ps`)."""
        return await self.ps()

    async def load_model(self, name: str) -> None:
        """Preload ``name`` into memory without generating any tokens.

        Sends ``POST /api/generate`` with an empty prompt and a ``5m``
        keep-alive: Ollama loads the runner and holds it warm. Raises
        :class:`OllamaError` on transport failure.
        """
        await self._post(
            "/api/generate",
            {"model": name, "prompt": "", "keep_alive": "5m"},
        )

    async def unload_model(self, name: str) -> None:
        """Unload ``name`` from memory via ``keep_alive=0``.

        Sends ``POST /api/generate`` with an empty prompt and ``keep_alive=0``
        so Ollama stops the runner and reclaims memory immediately. Raises
        :class:`OllamaError` on transport failure.
        """
        await self._post(
            "/api/generate",
            {"model": name, "prompt": "", "keep_alive": 0},
        )

    async def is_reachable(self) -> bool:
        """Return True when the Ollama server responds to ``GET /api/tags``."""
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[str]:
        """Return the names of locally-available models, or [] if unreachable."""
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        models = response.json().get("models", [])
        return [m["name"] for m in models if isinstance(m, dict) and "name" in m]


def _parse_json_object(text: str) -> dict[str, Any]:
    """Best-effort parse of ``text`` into a JSON object.

    Tolerates models that wrap JSON in prose or code fences: tries a direct
    parse first, then falls back to extracting the outermost ``{...}`` span.
    Returns ``{}`` when no object can be recovered (never raises) so callers can
    degrade to a low-confidence empty read rather than inventing data.
    """
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
