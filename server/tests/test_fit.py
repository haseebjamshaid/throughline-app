"""Fit Check engine — guardrails, parsing, ranking, persistence. No live model.

The model call (``OllamaClient.complete_json``) and the vault search are
monkeypatched, so Ollama is never touched. The point is the HONESTY rules:

* a fit result is ALWAYS valid — a blank/garbage model response degrades to a
  grounded similarity score + an honest band verdict, never fabricated checks;
* checks only ever cite REAL profile claims (invented "rules" are dropped) and
  rules the user disagreed with never read as failures;
* batch ranking orders by closeness and scales similarity to 0–100;
* disagreements persist and de-duplicate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from throughline.config import Settings
from throughline.fit import batch as batch_module
from throughline.fit import check as check_module
from throughline.fit.batch import RankedCandidate, rank_candidates
from throughline.fit.check import (
    _band_verdict,
    _checks_from_payload,
    _parse_score,
    _parse_verdict,
    describe_image_subject,
    run_fit_check,
)
from throughline.fit.disagreements import add_disagreement, load_disagreements
from throughline.fit.prompts import MAX_CLAIMS, build_fit_prompt, select_claims
from throughline.index.store import VecStore
from throughline.main import create_app
from throughline.models.embeddings import Embeddings
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import Profile, ProfileClaim, SearchResult


def _claim(text: str, confidence: str = "medium") -> ProfileClaim:
    return ProfileClaim(
        id=text[:8],
        section="mood",
        text=text,
        examples=["blade_runner.md"],
        confidence=confidence,  # type: ignore[arg-type]
    )


def _profile() -> Profile:
    return Profile(
        name="your throughline",
        source_count=8,
        confidence_note="a healthy spread",
        palette=[],
        claims=[
            _claim("you lean nocturnal and rain-soaked", "high"),
            _claim("you love loneliness with neon", "medium"),
            _claim("you avoid bright busy noise", "low"),
        ],
    )


# --------------------------------------------------------------------------- #
# score + verdict parsing (the honest fallbacks)
# --------------------------------------------------------------------------- #


def test_parse_score_reads_and_clamps() -> None:
    assert _parse_score({"score": 82}, []) == 82
    assert _parse_score({"score": 140}, []) == 100
    assert _parse_score({"score": -5}, []) == 0
    assert _parse_score({"score": "73%"}, []) == 73


def test_parse_score_falls_back_to_similarity() -> None:
    # No usable score → grounded in the nearest vault match's similarity.
    closest = [{"item_id": "a.md", "title": "a", "score": 64}]
    assert _parse_score({}, closest) == 64
    # bool must not be read as an int score.
    assert _parse_score({"score": True}, closest) == 64


def test_parse_verdict_prefers_model_then_band() -> None:
    assert _parse_verdict({"verdict": "Very You"}, 90) == "very you"
    # Blank verdict → honest band line for the score.
    assert _parse_verdict({}, 90) == _band_verdict(90)
    assert _band_verdict(10) != _band_verdict(90)


# --------------------------------------------------------------------------- #
# checks: only real claims, drop invented + disagreed, dedupe
# --------------------------------------------------------------------------- #


def test_checks_only_cite_real_claims() -> None:
    payload = {
        "checks": [
            {"rule": "you lean nocturnal and rain-soaked", "passed": True, "fix": None},
            {"rule": "you love loneliness with neon", "passed": False, "fix": "dim it"},
            {"rule": "invented rule the model made up", "passed": False, "fix": "nope"},
        ]
    }
    checks = _checks_from_payload(payload, _profile().claims, disagreed=[])
    rules = {c.rule for c in checks}
    assert "invented rule the model made up" not in rules
    assert "you lean nocturnal and rain-soaked" in rules
    # A passing check carries no fix; a failing one keeps its fix.
    passed = next(c for c in checks if c.passed)
    failed = next(c for c in checks if not c.passed)
    assert passed.fix is None
    assert failed.fix == "dim it"


def test_disagreed_rules_never_fail() -> None:
    payload = {
        "checks": [
            {"rule": "you avoid bright busy noise", "passed": False, "fix": "tone down"},
        ]
    }
    checks = _checks_from_payload(
        payload, _profile().claims, disagreed=["you avoid bright busy noise"]
    )
    assert checks == []


def test_checks_dedupe_by_rule() -> None:
    payload = {
        "checks": [
            {"rule": "you love loneliness with neon", "passed": True},
            {"rule": "you love loneliness with neon", "passed": False},
        ]
    }
    checks = _checks_from_payload(payload, _profile().claims, disagreed=[])
    assert len(checks) == 1


# --------------------------------------------------------------------------- #
# claim selection + prompt + image subject
# --------------------------------------------------------------------------- #


def test_select_claims_orders_by_confidence_and_caps() -> None:
    claims = select_claims(_profile())
    assert claims[0].confidence == "high"
    assert len(claims) <= MAX_CLAIMS


def test_build_fit_prompt_lists_real_rules_verbatim() -> None:
    profile = _profile()
    prompt = build_fit_prompt(
        profile, "caption", "a lonely neon street at night", profile.claims
    )
    assert "you lean nocturnal and rain-soaked" in prompt
    assert "a lonely neon street at night" in prompt


def test_describe_image_subject_reads_description_or_falls_back() -> None:
    assert describe_image_subject('{"description": "a foggy ridge"}') == "a foggy ridge"
    assert describe_image_subject("just plain text") == "just plain text"
    assert describe_image_subject("") == ""


# --------------------------------------------------------------------------- #
# disagreements persistence
# --------------------------------------------------------------------------- #


def test_disagreements_persist_and_dedupe(tmp_path: Path) -> None:
    cache = tmp_path / ".throughline"
    assert load_disagreements(cache) == []
    add_disagreement(cache, "you avoid bright busy noise")
    add_disagreement(cache, "you avoid bright busy noise")  # dup
    add_disagreement(cache, "  ")  # blank no-op
    result = add_disagreement(cache, "you lean nocturnal and rain-soaked")
    assert result == [
        "you avoid bright busy noise",
        "you lean nocturnal and rain-soaked",
    ]
    assert load_disagreements(cache) == result


# --------------------------------------------------------------------------- #
# batch ranking (search stubbed — no embeddings traffic)
# --------------------------------------------------------------------------- #


async def test_rank_candidates_orders_by_closeness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_search(_store, _emb, query, **_kw):  # type: ignore[no-untyped-def]
        score = {"very me": 0.9, "kind of me": 0.4}.get(query, 0.1)
        return [SearchResult(item_id="x.md", title="x", path="x", score=score, why="")]

    monkeypatch.setattr(batch_module, "search", _fake_search)
    ranked = await rank_candidates(None, None, ["kind of me", "very me", "  "])  # type: ignore[arg-type]

    assert [r.text for r in ranked] == ["very me", "kind of me"]  # blank skipped, sorted
    assert ranked[0].score == 90
    assert isinstance(ranked[0], RankedCandidate)


# --------------------------------------------------------------------------- #
# the engine guardrail: a valid result even from a blank model response
# --------------------------------------------------------------------------- #


class _FakeState:
    """A minimal AppState stand-in carrying just what the engine reads."""

    def __init__(self, settings: Settings, store: VecStore, client: OllamaClient):
        self.settings = settings
        self.store = store
        self.client = client
        self.embeddings = Embeddings(client, embed_dim=settings.embed_dim)


@pytest.fixture
def fake_state(tmp_path: Path) -> _FakeState:
    cache = tmp_path / ".throughline"
    settings = Settings(vault_path=tmp_path / "vault", cache_dir=cache)
    store = VecStore(cache, embed_dim=settings.embed_dim)
    return _FakeState(settings, store, OllamaClient())


def _stub_closest(monkeypatch: pytest.MonkeyPatch, score: float) -> None:
    async def _fake_search(_store, _emb, _query, **_kw):  # type: ignore[no-untyped-def]
        return [
            SearchResult(
                item_id="blade_runner.md",
                title="blade runner 2049",
                path="b",
                score=score,
                why="",
            )
        ]

    monkeypatch.setattr(check_module, "search", _fake_search)


def _stub_model(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    async def _fake_complete(*_a, **_k):  # type: ignore[no-untyped-def]
        return payload

    monkeypatch.setattr(OllamaClient, "complete_json", _fake_complete)


async def test_blank_model_response_still_yields_valid_result(
    fake_state: _FakeState, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: the model returns nothing usable.
    _stub_closest(monkeypatch, 0.81)
    _stub_model(monkeypatch, {})

    # Act
    try:
        result = await run_fit_check(
            fake_state,
            _profile(),
            "caption",
            "a lonely neon street",
            text_model="qwen3.5:9b",
        )
    finally:
        fake_state.store.close()
        await fake_state.client.aclose()

    # Assert: a grounded similarity score, an honest verdict, and closest matches.
    assert result.score == 81  # fell back to the nearest match's similarity
    assert result.verdict.strip()
    assert result.kind == "caption"
    assert result.closest and result.closest[0]["item_id"] == "blade_runner.md"
    assert result.checks == []  # no fabricated checks from an empty response


async def test_engine_keeps_only_real_checks(
    fake_state: _FakeState, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_closest(monkeypatch, 0.5)
    _stub_model(
        monkeypatch,
        {
            "score": 70,
            "verdict": "mostly you",
            "checks": [
                {"rule": "you love loneliness with neon", "passed": True},
                {"rule": "totally invented", "passed": False, "fix": "x"},
            ],
        },
    )
    try:
        result = await run_fit_check(
            fake_state,
            _profile(),
            "song",
            "a quiet rainy synth track",
            text_model="qwen3.5:9b",
        )
    finally:
        fake_state.store.close()
        await fake_state.client.aclose()

    assert result.score == 70
    assert [c.rule for c in result.checks] == ["you love loneliness with neon"]


# --------------------------------------------------------------------------- #
# route guards (no Ollama needed — the 409s fire before any model call)
# --------------------------------------------------------------------------- #


def test_fit_409_without_vault(tmp_path: Path) -> None:
    settings = Settings(vault_path=tmp_path / "vault")
    with TestClient(create_app(settings)) as client:
        resp = client.post("/fit", data={"kind": "caption", "text": "hi"})
    assert resp.status_code == 409


def test_fit_409_without_profile(tmp_path: Path) -> None:
    # A connected store but no profile → 409. Avoid the TestClient context
    # manager here: its lifespan teardown would close the sqlite store from the
    # portal worker thread (sqlite forbids cross-thread close). The 409 fires
    # before any store/sqlite call, so we close the store in this thread instead.
    cache = tmp_path / ".throughline"
    settings = Settings(vault_path=tmp_path / "vault", cache_dir=cache)
    app = create_app(settings)
    store = VecStore(cache, embed_dim=settings.embed_dim)
    app.state.app_state.store = store
    try:
        resp = TestClient(app).post("/fit", data={"kind": "caption", "text": "hi"})
    finally:
        store.close()
    assert resp.status_code == 409
    assert "profile" in resp.json()["detail"]
