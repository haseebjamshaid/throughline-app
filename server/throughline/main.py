"""FastAPI application for the throughline server (Phase 0 surface).

Exposes health, vault-connect, item listing, and semantic search. The store
and embeddings are held in app state and (re)built when a vault is connected.

# TODO: serve built SPA in later phase (mount the Vite `dist/` as static files).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from throughline.config import Settings, get_settings, resolve_text_model
from throughline.fit.batch import RankedCandidate, rank_candidates
from throughline.fit.check import FitCheckError, describe_image, run_fit_check
from throughline.fit.disagreements import add_disagreement, load_disagreements
from throughline.index.search import search as run_search
from throughline.index.store import VecStore
from throughline.intake.capture import capture_image, capture_note
from throughline.intake.worker import IntakeWorker
from throughline.models.embeddings import Embeddings
from throughline.models.model_manager import ModelManager
from throughline.models.ollama_client import OllamaClient, OllamaError
from throughline.profile.edits import ProfileEdit, apply_edits
from throughline.profile.generate import (
    DEFAULT_PROFILE_SEED,
    DEFAULT_PROFILE_TEMPERATURE,
    generate_profile,
    merge_preserving_pins,
    source_signature,
)
from throughline.profile.store import load_profile, save_profile
from throughline.schemas import (
    FitResult,
    Item,
    ModelStatus,
    Profile,
    SearchResult,
    ThreadTurn,
)
from throughline.thread.engine import pull_thread, regenerate_step
from throughline.thread.persistence import load_turn, log_momentum, save_turn
from throughline.vault.frontmatter import parse_item, write_item
from throughline.vault.reader import read_vault


class AppState:
    """Mutable-at-the-edges container for process-wide resources.

    Individual fields are replaced wholesale (never deep-mutated) when a vault
    is connected, keeping the update semantics object-replacing rather than
    in-place editing.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OllamaClient(
            base_url=settings.ollama_base_url,
            embed_model=settings.embed_model,
            vision_model=settings.vision_model,
        )
        self.embeddings = Embeddings(self.client, embed_dim=settings.embed_dim)
        self.store: VecStore | None = None
        self.items: list[Item] = []
        self.worker: IntakeWorker | None = None
        self.worker_task: asyncio.Task[None] | None = None


class ConnectRequest(BaseModel):
    path: str = Field(..., description="Absolute path to an Obsidian vault")


class ConnectResponse(BaseModel):
    vault_path: str
    cache_dir: str
    indexed: int


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    models_present: list[str]


class SearchRequest(BaseModel):
    query: str
    types: list[str] | None = None
    inward_only: bool = True
    k: int = Field(default=10, ge=1, le=100)


class CaptureRequest(BaseModel):
    type: str = Field(..., description="Item type (movie|song|journal|...)")
    title: str
    body: str = ""
    feeling: str | None = None
    tags: list[str] = Field(default_factory=list)


class CorrectionRequest(BaseModel):
    """Partial edit of a vault item; any field left None is unchanged.

    ``body`` edits the note's prose (the strongest signal), so changing it
    re-embeds the item and lets intake re-read it on the next run.
    """

    type: str | None = None
    title: str | None = None
    feeling: str | None = None
    tags: list[str] | None = None
    body: str | None = None


class IntakeControlResponse(BaseModel):
    phase: str
    done: int
    total: int
    paused: bool


class ModelActionRequest(BaseModel):
    name: str = Field(..., description="A configured model name (embed|text|vision)")


class ProfileEditRequest(BaseModel):
    """A batch of profile claim edits (edit text / toggle pin / delete)."""

    edits: list[ProfileEdit] = Field(default_factory=list)


class ThreadRequest(BaseModel):
    """What the user is stuck on, the input to the unstuck engine."""

    stuck: str = Field(..., min_length=1, description="What they're stuck on")


class FitDisagreeRequest(BaseModel):
    """A pushback on one fit-check rule — "this doesn't define me"."""

    rule: str = Field(..., min_length=1, description="The profile claim text to soften")


class FitBatchRequest(BaseModel):
    """A set of candidate texts to rank by closeness to the user's taste."""

    kind: str = Field(default="caption", description="image|caption|song (informational)")
    items: list[str] = Field(default_factory=list, description="Candidate texts to rank")


# The valid Fit Check input kinds, mirrored from schemas.FitKind for validation.
_FIT_KINDS: frozenset[str] = frozenset({"image", "caption", "song"})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the FastAPI app with a fresh :class:`AppState`."""
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            state = _app.state.app_state
            if state.worker_task is not None and not state.worker_task.done():
                state.worker_task.cancel()
            if state.store is not None:
                state.store.close()
            await state.client.aclose()

    app = FastAPI(title="throughline", version="0.0.0", lifespan=lifespan)
    # Allow the local Vite dev SPA (a different origin) to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.app_state = AppState(resolved)

    def get_state() -> AppState:
        return app.state.app_state

    @app.get("/health", response_model=HealthResponse)
    async def health(state: AppState = Depends(get_state)) -> HealthResponse:
        reachable = await state.client.is_reachable()
        available = await state.client.list_models() if reachable else []
        present = [
            m
            for m in (
                state.settings.embed_model,
                state.settings.text_model,
                state.settings.vision_model,
            )
            if m in available
        ]
        return HealthResponse(
            status="ok",
            ollama_reachable=reachable,
            models_present=present,
        )

    def _model_manager(state: AppState) -> ModelManager:
        return ModelManager(
            state.client,
            text_model=state.settings.text_model,
            vision_model=state.settings.vision_model,
            embed_model=state.settings.embed_model,
        )

    async def _model_statuses(manager: ModelManager) -> list[ModelStatus]:
        """Fetch installed + loaded model lists and build their statuses.

        Ollama being offline is an expected local-first state: installed/loaded
        both degrade to empty so every configured model reads as not-installed,
        not-loaded rather than raising.
        """
        try:
            installed = await manager.client.list_models()
            loaded = await manager.client.ps()
        except OllamaError:
            installed, loaded = [], []
        return await manager.status(installed, loaded)

    def _require_configured(manager: ModelManager, name: str) -> None:
        if name not in manager.configured:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unknown model: {name!r} "
                    f"(expected one of {manager.configured})"
                ),
            )

    async def _status_for(manager: ModelManager, name: str) -> ModelStatus:
        statuses = await _model_statuses(manager)
        return next(s for s in statuses if s.name == name)

    @app.get("/models", response_model=list[ModelStatus])
    async def models_list(state: AppState = Depends(get_state)) -> list[ModelStatus]:
        return await _model_statuses(_model_manager(state))

    @app.post("/models/load", response_model=ModelStatus)
    async def models_load(
        body: ModelActionRequest, state: AppState = Depends(get_state)
    ) -> ModelStatus:
        manager = _model_manager(state)
        _require_configured(manager, body.name)
        try:
            await manager.load(body.name)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return await _status_for(manager, body.name)

    @app.post("/models/unload", response_model=ModelStatus)
    async def models_unload(
        body: ModelActionRequest, state: AppState = Depends(get_state)
    ) -> ModelStatus:
        manager = _model_manager(state)
        _require_configured(manager, body.name)
        try:
            await manager.unload(body.name)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        # Report the intended post-unload state: Ollama drops the model
        # asynchronously, so re-querying /api/ps can still list it for a beat.
        status = await _status_for(manager, body.name)
        return status.model_copy(update={"loaded": False, "size_mb": None})

    @app.post("/models/unload-all", response_model=list[ModelStatus])
    async def models_unload_all(
        state: AppState = Depends(get_state),
    ) -> list[ModelStatus]:
        manager = _model_manager(state)
        try:
            loaded = await manager.client.ps()
            await manager.unload_all(loaded)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        # Optimistically report all-unloaded (Ollama drops models asynchronously).
        statuses = await _model_statuses(manager)
        return [
            s.model_copy(update={"loaded": False, "size_mb": None}) for s in statuses
        ]

    @app.post("/vault/connect", response_model=ConnectResponse)
    async def vault_connect(
        body: ConnectRequest, state: AppState = Depends(get_state)
    ) -> ConnectResponse:
        vault_path = Path(body.path).expanduser()
        if not vault_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"vault path is not a directory: {vault_path}"
            )

        new_settings = state.settings.with_vault(vault_path)
        cache_dir = new_settings.cache_dir
        assert cache_dir is not None  # derived by with_vault

        if state.store is not None:
            state.store.close()
        store = VecStore(cache_dir, embed_dim=new_settings.embed_dim)

        try:
            items = read_vault(vault_path)
            await _index_items(store, state.embeddings, items)
        except OllamaError as exc:
            store.close()
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        state.settings = new_settings
        state.store = store
        state.items = items
        return ConnectResponse(
            vault_path=str(vault_path),
            cache_dir=str(cache_dir),
            indexed=len(items),
        )

    @app.get("/vault/items", response_model=list[Item])
    async def vault_items(state: AppState = Depends(get_state)) -> list[Item]:
        return state.items

    @app.post("/search", response_model=list[SearchResult])
    async def search_endpoint(
        body: SearchRequest, state: AppState = Depends(get_state)
    ) -> list[SearchResult]:
        if state.store is None:
            raise HTTPException(status_code=409, detail="no vault connected")
        try:
            return await run_search(
                state.store,
                state.embeddings,
                body.query,
                types=body.types,
                inward_only=body.inward_only,
                k=body.k,
            )
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _require_store(state: AppState) -> VecStore:
        if state.store is None:
            raise HTTPException(status_code=409, detail="no vault connected")
        return state.store

    @app.post("/intake/start", response_model=IntakeControlResponse)
    async def intake_start(
        force: bool = False, state: AppState = Depends(get_state)
    ) -> IntakeControlResponse:
        store = _require_store(state)
        if state.worker_task is not None and not state.worker_task.done():
            raise HTTPException(status_code=409, detail="intake already running")
        worker = IntakeWorker(
            state.settings, state.client, store, state.embeddings, state.items
        )
        state.worker = worker
        state.worker_task = asyncio.create_task(worker.run(force=force))
        return IntakeControlResponse(
            phase="reading", done=worker.done, total=worker.total, paused=False
        )

    @app.post("/intake/pause", response_model=IntakeControlResponse)
    async def intake_pause(state: AppState = Depends(get_state)) -> IntakeControlResponse:
        worker = state.worker
        if worker is None:
            raise HTTPException(status_code=409, detail="no intake run to pause")
        worker.pause()
        return IntakeControlResponse(
            phase="paused", done=worker.done, total=worker.total, paused=True
        )

    @app.post("/intake/resume", response_model=IntakeControlResponse)
    async def intake_resume(state: AppState = Depends(get_state)) -> IntakeControlResponse:
        worker = state.worker
        if worker is None:
            raise HTTPException(status_code=409, detail="no intake run to resume")
        worker.resume()
        return IntakeControlResponse(
            phase="reading", done=worker.done, total=worker.total, paused=False
        )

    @app.get("/intake/progress")
    async def intake_progress(state: AppState = Depends(get_state)) -> StreamingResponse:
        worker = state.worker
        if worker is None:
            raise HTTPException(status_code=409, detail="no intake run")
        queue = worker.subscribe()

        async def event_stream() -> AsyncIterator[str]:
            while True:
                snapshot = await queue.get()
                if snapshot is None:
                    break
                yield f"data: {snapshot.model_dump_json()}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/vault/capture", response_model=Item)
    async def vault_capture(
        body: CaptureRequest, state: AppState = Depends(get_state)
    ) -> Item:
        try:
            item = capture_note(
                state.settings,
                type=body.type,
                title=body.title,
                body=body.body,
                feeling=body.feeling,
                tags=body.tags,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        state.items = [*state.items, item]
        return item

    @app.post("/vault/capture/image")
    async def vault_capture_image(
        file: UploadFile = File(...),
        state: AppState = Depends(get_state),
    ) -> dict[str, str]:
        data = await file.read()
        try:
            path = capture_image(state.settings, file.filename or "image.png", data)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"path": str(path)}

    @app.patch("/vault/items/{item_id:path}", response_model=Item)
    async def correct_item(
        item_id: str, patch: CorrectionRequest, state: AppState = Depends(get_state)
    ) -> Item:
        store = _require_store(state)
        existing = next((it for it in state.items if it.id == item_id), None)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"unknown item: {item_id}")

        updated = existing.model_copy(
            update={
                k: v
                for k, v in {
                    "type": patch.type,
                    "title": patch.title,
                    "feeling": patch.feeling,
                    "tags": patch.tags,
                    "body": patch.body,
                }.items()
                if v is not None
            }
        )
        file_path = Path(existing.path)
        write_item(updated, file_path)
        reparsed = parse_item(file_path, state.settings.vault_path or file_path.parent)
        state.items = [reparsed if it.id == item_id else it for it in state.items]

        # Refresh the index so search / profile / thread reflect the edit (title,
        # body text, embedding, content-hash). Best-effort: if the embedder is
        # unavailable the file edit still stands and the index catches up on the
        # next intake/connect. A changed body alters content_hash, so intake will
        # re-derive that item's read on its next run (the old read is not locked).
        try:
            vectors = await state.embeddings.fingerprint_documents([reparsed.body])
            store.upsert(reparsed, vectors[0])
        except OllamaError:
            pass
        return reparsed

    @app.delete("/vault/items/{item_id:path}")
    async def delete_item(
        item_id: str, state: AppState = Depends(get_state)
    ) -> dict[str, str]:
        store = _require_store(state)
        existing = next((it for it in state.items if it.id == item_id), None)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"unknown item: {item_id}")
        # The vault file is the source of truth: remove it, then prune the index
        # so search / profile / thread never surface the deleted entry.
        Path(existing.path).unlink(missing_ok=True)
        store.delete(item_id)
        state.items = [it for it in state.items if it.id != item_id]
        return {"deleted": item_id}

    @app.post("/profile/generate", response_model=Profile)
    async def profile_generate(
        force: bool = False,
        temperature: float = DEFAULT_PROFILE_TEMPERATURE,
        seed: int = DEFAULT_PROFILE_SEED,
        state: AppState = Depends(get_state),
    ) -> Profile:
        store = _require_store(state)
        existing = load_profile(state.settings)
        signature = source_signature(state.items)
        # Determinism: while the vault AND the sampling knobs are unchanged,
        # return the saved portrait verbatim — no model call. A changed vault,
        # a changed temperature/seed, or an explicit force=true redraws it.
        if (
            not force
            and existing is not None
            and existing.source_signature == signature
            and existing.temperature == temperature
            and existing.seed == seed
        ):
            return existing
        manager = _model_manager(state)
        try:
            await manager.use("text")
            text_model = await resolve_text_model(state.settings, state.client)
            fresh = await generate_profile(
                state.settings,
                store,
                state.client,
                state.items,
                text_model,
                temperature=temperature,
                seed=seed,
            )
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        merged = merge_preserving_pins(existing, fresh)
        save_profile(state.settings, merged)
        return merged

    @app.get("/profile", response_model=Profile)
    async def profile_get(state: AppState = Depends(get_state)) -> Profile:
        profile = load_profile(state.settings)
        if profile is None:
            raise HTTPException(status_code=404, detail="no profile generated yet")
        return profile

    @app.patch("/profile", response_model=Profile)
    async def profile_patch(
        body: ProfileEditRequest, state: AppState = Depends(get_state)
    ) -> Profile:
        profile = load_profile(state.settings)
        if profile is None:
            raise HTTPException(status_code=404, detail="no profile generated yet")
        updated = apply_edits(profile, body.edits)
        save_profile(state.settings, updated)
        return updated

    async def _resolved_text_model(state: AppState) -> str:
        """Load the text model and return the name to use (with fallback).

        Mirrors the profile route: make the text role the resident heavy model,
        then resolve the actual model name (falling back to the vision model
        when the preferred reasoning model is not pulled).
        """
        manager = _model_manager(state)
        await manager.use("text")
        return await resolve_text_model(state.settings, state.client)

    def _load_turn_or_404(state: AppState, turn_id: str) -> ThreadTurn:
        _require_store(state)  # 409 when no vault is connected
        assert state.settings.cache_dir is not None  # a store implies a cache dir
        turn = load_turn(state.settings.cache_dir, turn_id)
        if turn is None:
            raise HTTPException(status_code=404, detail=f"unknown thread: {turn_id}")
        return turn

    @app.post("/thread", response_model=ThreadTurn)
    async def thread_start(
        body: ThreadRequest, state: AppState = Depends(get_state)
    ) -> ThreadTurn:
        _require_store(state)
        try:
            text_model = await _resolved_text_model(state)
            return await pull_thread(state, body.stuck, text_model=text_model)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/thread/{turn_id}/different", response_model=ThreadTurn)
    async def thread_different(
        turn_id: str, state: AppState = Depends(get_state)
    ) -> ThreadTurn:
        turn = _load_turn_or_404(state, turn_id)
        try:
            text_model = await _resolved_text_model(state)
            return await regenerate_step(
                state,
                turn,
                size=turn.next_step.size,
                avoid=turn.next_step.text,
                text_model=text_model,
            )
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/thread/{turn_id}/smaller", response_model=ThreadTurn)
    async def thread_smaller(
        turn_id: str, state: AppState = Depends(get_state)
    ) -> ThreadTurn:
        turn = _load_turn_or_404(state, turn_id)
        try:
            text_model = await _resolved_text_model(state)
            return await regenerate_step(
                state, turn, size="smaller", avoid=None, text_model=text_model
            )
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/thread/{turn_id}/did-it", response_model=ThreadTurn)
    async def thread_did_it(
        turn_id: str, state: AppState = Depends(get_state)
    ) -> ThreadTurn:
        turn = _load_turn_or_404(state, turn_id)
        assert state.settings.cache_dir is not None
        log_momentum(state.settings.cache_dir, turn_id)
        done_turn = turn.model_copy(update={"done": True})
        save_turn(state.settings.cache_dir, done_turn)
        return done_turn

    def _require_profile(state: AppState) -> Profile:
        """Return the generated profile or fail with 409 (nothing to measure against)."""
        profile = load_profile(state.settings)
        if profile is None:
            raise HTTPException(
                status_code=409,
                detail="no profile yet — generate your profile first",
            )
        return profile

    @app.post("/fit", response_model=FitResult)
    async def fit_check(
        kind: str = Form(...),
        text: str = Form(""),
        image: UploadFile | None = File(None),
        state: AppState = Depends(get_state),
    ) -> FitResult:
        _require_store(state)
        if kind not in _FIT_KINDS:
            raise HTTPException(
                status_code=400,
                detail=f"unknown fit kind: {kind!r} (expected {sorted(_FIT_KINDS)})",
            )
        profile = _require_profile(state)

        # One manager for the whole request so a vision→text swap actually
        # unloads vision before the text model loads (single-heavy-model budget).
        manager = _model_manager(state)
        tmp_path: Path | None = None
        try:
            if kind == "image":
                if image is None:
                    raise HTTPException(
                        status_code=400, detail="image kind requires an image file"
                    )
                data = await image.read()
                tmp_path = _write_fit_temp_image(state.settings, image.filename, data)
                await manager.use("vision")
                subject = await describe_image(
                    state.client, state.settings.vision_model, str(tmp_path)
                )
            else:
                subject = text.strip()
                if not subject:
                    raise HTTPException(
                        status_code=400, detail=f"{kind} kind requires text"
                    )
            await manager.use("text")
            text_model = await resolve_text_model(state.settings, state.client)
            return await run_fit_check(
                state, profile, kind, subject, text_model=text_model
            )
        except FitCheckError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    @app.post("/fit/disagree")
    async def fit_disagree(
        body: FitDisagreeRequest, state: AppState = Depends(get_state)
    ) -> dict[str, list[str]]:
        _require_store(state)
        assert state.settings.cache_dir is not None  # a store implies a cache dir
        disagreed = add_disagreement(state.settings.cache_dir, body.rule)
        return {"disagreed": disagreed}

    @app.post("/fit/batch", response_model=list[RankedCandidate])
    async def fit_batch(
        body: FitBatchRequest, state: AppState = Depends(get_state)
    ) -> list[RankedCandidate]:
        store = _require_store(state)
        try:
            return await rank_candidates(store, state.embeddings, body.items)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app


def _write_fit_temp_image(
    settings: Settings, filename: str | None, data: bytes
) -> Path:
    """Write uploaded image bytes to a temp file in the cache dir to be described.

    The file lives in the git-ignored cache dir and is deleted by the caller once
    the description is produced. Falls back to a ``.png`` suffix when the upload
    carries none.
    """
    assert settings.cache_dir is not None  # a connected store implies a cache dir
    suffix = Path(filename).suffix if filename else ".png"
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = settings.cache_dir / f"fit_subject{suffix or '.png'}"
    tmp.write_bytes(data)
    return tmp


async def _index_items(
    store: VecStore, embeddings: Embeddings, items: list[Item]
) -> None:
    """Fingerprint each item's body and upsert it into the store."""
    if not items:
        return
    vectors = await embeddings.fingerprint_documents([item.body for item in items])
    for item, vector in zip(items, vectors, strict=True):
        store.upsert(item, vector)


app = create_app()
