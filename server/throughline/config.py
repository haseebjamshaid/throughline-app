"""Application configuration via pydantic-settings.

All paths and model identifiers live here so nothing is hardcoded deeper in
the stack. Settings can be overridden via environment variables prefixed with
``THROUGHLINE_`` (e.g. ``THROUGHLINE_VAULT_PATH``).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_MODEL = "embeddinggemma:300m"
DEFAULT_TEXT_MODEL = "qwen3.5:9b"
DEFAULT_VISION_MODEL = "qwen3-vl:4b"
DEFAULT_EMBED_DIM = 256
CACHE_DIR_NAME = ".throughline"


class Settings(BaseSettings):
    """Runtime settings for the throughline server.

    ``vault_path`` is optional at construction time so the server can boot
    before a vault is connected. ``cache_dir`` defaults to
    ``<vault>/.throughline`` once a vault is known.
    """

    model_config = SettingsConfigDict(
        env_prefix="THROUGHLINE_",
        env_file=".env",
        extra="ignore",
    )

    vault_path: Path | None = None
    cache_dir: Path | None = None
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    embed_model: str = DEFAULT_EMBED_MODEL
    text_model: str = DEFAULT_TEXT_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    embed_dim: int = DEFAULT_EMBED_DIM

    @model_validator(mode="after")
    def _derive_cache_dir(self) -> Settings:
        """Default the cache dir to ``<vault>/.throughline`` when unset.

        Sets the field in place and returns ``self``: pydantic v2 ignores a
        non-``self`` return from an after-validator during ``__init__`` (this
        is construction-time validation, not user-facing mutation).
        """
        if self.cache_dir is None and self.vault_path is not None:
            self.cache_dir = self.vault_path / CACHE_DIR_NAME
        return self

    def with_vault(self, vault_path: Path) -> Settings:
        """Return a new ``Settings`` pointed at ``vault_path``.

        The cache dir is re-derived from the new vault unless one was set
        explicitly (independently of the previous vault) via environment
        configuration. ``model_copy`` does NOT re-run the ``_derive_cache_dir``
        validator, so the cache dir must be set here directly.
        """
        derived_for_current_vault = (
            self.vault_path is not None
            and self.cache_dir == self.vault_path / CACHE_DIR_NAME
        )
        keep_explicit_cache = (
            self.cache_dir is not None and not derived_for_current_vault
        )
        update: dict[str, object] = {"vault_path": vault_path}
        if not keep_explicit_cache:
            update["cache_dir"] = vault_path / CACHE_DIR_NAME
        return self.model_copy(update=update)


def default_cache_dir(vault_path: Path) -> Path:
    """Return the conventional cache dir for a vault."""
    return vault_path / CACHE_DIR_NAME


async def resolve_text_model(settings: Settings, client: object) -> str:
    """Return the text model to use, falling back to the vision model.

    The preferred reasoning model (``settings.text_model``, e.g.
    ``qwen3.5:9b``) may not be downloaded yet. When it is absent from Ollama's
    ``/api/tags`` we fall back to ``settings.vision_model`` (``qwen3-vl:4b``),
    which handles text fine. When the fallback is active, the "text" and
    "vision" roles map to the same model so the :class:`ModelManager` performs
    no swap during a mixed intake run.

    ``client`` must expose an async ``list_models() -> list[str]`` method (the
    :class:`OllamaClient` does). The parameter is typed loosely to avoid a
    circular import between config and the models package.
    """
    available = await client.list_models()  # type: ignore[attr-defined]
    if settings.text_model in available:
        return settings.text_model
    return settings.vision_model


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a process-wide ``Settings`` singleton (lazily constructed)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
