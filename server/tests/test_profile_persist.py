"""Profile persistence + edit/pin/delete + pin-preserving regeneration.

No model is exercised here. ``save_profile`` must write both the rebuildable
``profile.json`` working copy AND a human-readable ``throughline-profile.md``
note into the vault (``type: profile``); ``load_profile`` must round-trip it.
The PATCH route (edit / pin / delete) and regeneration's pin-preservation are
driven through the FastAPI app with generation monkeypatched, so no Ollama is
touched.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
from fastapi.testclient import TestClient

from throughline.config import Settings
from throughline.main import create_app
from throughline.profile import generate as generate_module
from throughline.profile.store import (
    PROFILE_JSON_NAME,
    PROFILE_NOTE_NAME,
    load_profile,
    save_profile,
)
from throughline.schemas import PaletteSwatch, Profile, ProfileClaim


def _sample_profile() -> Profile:
    """A small but complete profile spanning both slices."""
    return Profile(
        name="your throughline",
        source_count=3,
        confidence_note="thin first read — feed it more and it sharpens (3 items so far).",
        palette=[
            PaletteSwatch(name="neon magenta", hex="#ff2bd6"),
            PaletteSwatch(name="cold blue", hex="#1b2a4a"),
        ],
        claims=[
            ProfileClaim(
                id="c-mood",
                section="mood",
                text="you chase a beautiful, lonely night-time glow",
                examples=["blade_runner_2049.md"],
                confidence="medium",
            ),
            ProfileClaim(
                id="c-amb",
                section="ambitions",
                text="you want a creative life on your own terms",
                examples=["the_move.md"],
                confidence="high",
            ),
        ],
        generated_at="2026-06-21T00:00:00+00:00",
    )


@pytest.fixture
def vault_settings(tmp_path: Path) -> Settings:
    """Settings pointed at a throwaway vault + derived cache dir."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    return Settings(vault_path=vault)


def test_save_profile_writes_json_and_vault_note(vault_settings: Settings) -> None:
    # Arrange
    profile = _sample_profile()

    # Act
    note_path = save_profile(vault_settings, profile)

    # Assert: the rebuildable JSON working copy exists in the cache dir.
    assert vault_settings.cache_dir is not None
    json_path = vault_settings.cache_dir / PROFILE_JSON_NAME
    assert json_path.exists()

    # Assert: a readable note exists in the vault with type: profile.
    assert note_path.name == PROFILE_NOTE_NAME
    assert note_path.exists()
    post = frontmatter.loads(note_path.read_text(encoding="utf-8"))
    assert post.metadata.get("type") == "profile"
    assert post.metadata.get("title") == profile.name
    body = post.content.lower()
    assert "#ff2bd6" in body  # palette hex rendered
    assert "creative life on your own terms" in body


def test_load_profile_round_trips(vault_settings: Settings) -> None:
    # Arrange
    profile = _sample_profile()
    save_profile(vault_settings, profile)

    # Act
    loaded = load_profile(vault_settings)

    # Assert
    assert loaded is not None
    assert loaded == profile


def test_load_profile_none_when_absent(vault_settings: Settings) -> None:
    assert load_profile(vault_settings) is None


class _StubStore:
    """A non-None store stand-in so ``_require_store`` passes a vault check.

    The profile routes never touch the store's DB: profile state is read from
    disk via ``load_profile`` and generation is monkeypatched. A real
    :class:`VecStore` cannot be used here because the TestClient closes it on a
    worker thread, which SQLite forbids. ``close`` is a thread-safe no-op.
    """

    def close(self) -> None:  # noqa: D401 - trivial no-op
        return None


def _app_with_store(settings: Settings) -> TestClient:
    """Build a TestClient whose app already has a connected (stub) store."""
    assert settings.cache_dir is not None
    app = create_app(settings)
    app.state.app_state.store = _StubStore()  # type: ignore[assignment]
    return TestClient(app)


def test_get_profile_404_before_generate(vault_settings: Settings) -> None:
    with _app_with_store(vault_settings) as client:
        resp = client.get("/profile")
    assert resp.status_code == 404


def test_patch_edits_pin_and_delete_persist(vault_settings: Settings) -> None:
    # Arrange: a saved profile is on disk.
    save_profile(vault_settings, _sample_profile())

    with _app_with_store(vault_settings) as client:
        # Act: edit one claim's text, pin it, and delete the other.
        resp = client.patch(
            "/profile",
            json={
                "edits": [
                    {"id": "c-mood", "text": "REWRITTEN night glow", "pinned": True},
                    {"id": "c-amb", "deleted": True},
                ]
            },
        )

    # Assert: response reflects the edits.
    assert resp.status_code == 200
    body = resp.json()
    claims = {c["id"]: c for c in body["claims"]}
    assert set(claims) == {"c-mood"}  # c-amb deleted
    assert claims["c-mood"]["pinned"] is True
    assert claims["c-mood"]["text"] == "rewritten night glow"  # lowercased

    # Assert: persisted to disk (json + note) too.
    persisted = load_profile(vault_settings)
    assert persisted is not None
    assert [c.id for c in persisted.claims] == ["c-mood"]
    assert persisted.claims[0].pinned is True


def test_patch_profile_404_before_generate(vault_settings: Settings) -> None:
    with _app_with_store(vault_settings) as client:
        resp = client.patch("/profile", json={"edits": []})
    assert resp.status_code == 404


def test_generate_409_without_vault(vault_settings: Settings) -> None:
    # No store attached -> no vault connected -> 409.
    with TestClient(create_app(vault_settings)) as client:
        resp = client.post("/profile/generate")
    assert resp.status_code == 409


def test_regenerate_preserves_pinned_claim(
    vault_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: an existing profile with one PINNED claim already saved.
    existing = _sample_profile()
    pinned_claim = existing.claims[0].model_copy(update={"pinned": True})
    existing = existing.model_copy(update={"claims": [pinned_claim]})
    save_profile(vault_settings, existing)

    # The model "regenerates" a wholly different set of fresh, unpinned claims.
    fresh = Profile(
        name="your throughline",
        source_count=3,
        confidence_note="thin first read.",
        palette=[PaletteSwatch(name="fresh teal", hex="#0a7d7d")],
        claims=[
            ProfileClaim(
                id="fresh-1",
                section="themes",
                text="a fresh theme the model just found",
                examples=["slow_morning.md"],
                confidence="low",
            )
        ],
        generated_at="2026-06-21T01:00:00+00:00",
    )

    async def _fake_generate(*_args: object, **_kwargs: object) -> Profile:
        return fresh

    monkeypatch.setattr(generate_module, "generate_profile", _fake_generate)
    # The route imports the symbol into main; patch there too.
    import throughline.main as main_module

    monkeypatch.setattr(main_module, "generate_profile", _fake_generate)

    # Avoid touching Ollama for model selection / loading.
    async def _fake_resolve(*_args: object, **_kwargs: object) -> str:
        return "qwen3.5:9b"

    monkeypatch.setattr(main_module, "resolve_text_model", _fake_resolve)

    async def _noop_use(self: object, role: str) -> str:  # noqa: ANN001
        return "qwen3.5:9b"

    from throughline.models.model_manager import ModelManager

    monkeypatch.setattr(ModelManager, "use", _noop_use)

    with _app_with_store(vault_settings) as client:
        resp = client.post("/profile/generate")

    # Assert: the pinned claim survived AND the fresh claim was merged in.
    assert resp.status_code == 200
    body = resp.json()
    ids = [c["id"] for c in body["claims"]]
    assert pinned_claim.id in ids  # pinned survived regeneration
    assert "fresh-1" in ids  # fresh claim merged
    # The pinned claim keeps its pin + text.
    pinned_out = next(c for c in body["claims"] if c["id"] == pinned_claim.id)
    assert pinned_out["pinned"] is True
    assert pinned_out["text"] == pinned_claim.text
    # Fresh palette/name won.
    assert body["palette"][0]["hex"] == "#0a7d7d"
