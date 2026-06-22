"""Regression tests for Settings.with_vault cache-dir derivation.

The /vault/connect endpoint 500'd because `model_copy` does NOT re-run the
`_derive_cache_dir` validator, so `with_vault` must set `cache_dir` itself.
"""

from pathlib import Path

from throughline.config import CACHE_DIR_NAME, Settings


def test_with_vault_derives_cache_dir_when_none() -> None:
    # Server boots with no vault; connecting one must derive the cache dir.
    settings = Settings(vault_path=None, cache_dir=None)
    out = settings.with_vault(Path("/tmp/vault_a"))
    assert out.vault_path == Path("/tmp/vault_a")
    assert out.cache_dir == Path("/tmp/vault_a") / CACHE_DIR_NAME


def test_with_vault_rederives_for_a_new_vault() -> None:
    settings = Settings(vault_path=Path("/tmp/vault_a"))  # validator derives cache
    assert settings.cache_dir == Path("/tmp/vault_a") / CACHE_DIR_NAME
    out = settings.with_vault(Path("/tmp/vault_b"))
    assert out.cache_dir == Path("/tmp/vault_b") / CACHE_DIR_NAME


def test_with_vault_preserves_explicit_cache_dir() -> None:
    # An explicitly-configured cache dir (independent of the vault) is kept.
    settings = Settings(vault_path=None, cache_dir=Path("/custom/cache"))
    out = settings.with_vault(Path("/tmp/vault_a"))
    assert out.cache_dir == Path("/custom/cache")
