"""Background intake worker: read each vault item once, fingerprint, index.

The worker iterates every item in the vault (notes via the text model, images
via the vision model), persists a structured read, fingerprints the relevant
text (note body or image description), and upserts both into the index.

Guarantees:
* **Read-once** — items whose bytes are unchanged are skipped.
* **Pausable** — a pause flag is honoured between items via an asyncio.Event.
* **Corrections win** — a locked read is never overwritten.
* **Honesty** — low-confidence reads are flagged, never invented.
* **Progress** — an :class:`IntakeProgress` snapshot is emitted per step.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from throughline.config import Settings, resolve_text_model
from throughline.index.store import VecStore
from throughline.models.embeddings import Embeddings
from throughline.models.model_manager import ModelManager
from throughline.models.ollama_client import OllamaClient
from throughline.schemas import (
    IMAGE_SUFFIXES,
    ImageRead,
    IntakeProgress,
    Item,
    NoteRead,
)
from throughline.intake.reader_image import read_image
from throughline.intake.reader_note import read_note

PHASE_IDLE = "idle"
PHASE_READING = "reading"
PHASE_PAUSED = "paused"
PHASE_DONE = "done"

KIND_IMAGE = "image"
KIND_NOTE = "note"


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (read timestamp)."""
    return datetime.now(timezone.utc).isoformat()


def is_image_item(item: Item) -> bool:
    """Return True when ``item`` should be read by the vision model.

    An item is an image when its declared type is ``image`` or its file suffix
    is a known image extension.
    """
    if item.type == KIND_IMAGE:
        return True
    return Path(item.path).suffix.lower() in IMAGE_SUFFIXES


class IntakeWorker:
    """Drives one full read-pass over the vault's items.

    Subscribers receive :class:`IntakeProgress` snapshots via :meth:`subscribe`
    (an ``asyncio.Queue``). Pause/resume is cooperative: the worker checks the
    pause gate between items, so an in-flight model read always completes.
    """

    def __init__(
        self,
        settings: Settings,
        client: OllamaClient,
        store: VecStore,
        embeddings: Embeddings,
        items: list[Item],
        *,
        manager: ModelManager | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._store = store
        self._embeddings = embeddings
        self._items = list(items)
        self._manager = manager or ModelManager(
            client,
            text_model=settings.text_model,
            vision_model=settings.vision_model,
            embed_model=settings.embed_model,
        )
        # Event is *set* when running; *cleared* when paused (so waiters block).
        self._resume_gate = asyncio.Event()
        self._resume_gate.set()
        self._subscribers: list[asyncio.Queue[IntakeProgress | None]] = []
        self._done = 0
        self._phase = PHASE_IDLE

    @property
    def total(self) -> int:
        return len(self._items)

    @property
    def done(self) -> int:
        return self._done

    @property
    def is_paused(self) -> bool:
        return not self._resume_gate.is_set()

    def pause(self) -> None:
        """Request a pause; takes effect before the next item is read."""
        self._resume_gate.clear()

    def resume(self) -> None:
        """Lift a pause so the worker continues with the next item."""
        self._resume_gate.set()

    def subscribe(self) -> asyncio.Queue[IntakeProgress | None]:
        """Register a progress subscriber and return its queue.

        A ``None`` sentinel is enqueued when the run finishes so consumers can
        terminate their stream.
        """
        queue: asyncio.Queue[IntakeProgress | None] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def _emit(self, current_title: str | None, phase: str) -> None:
        """Broadcast a progress snapshot to every subscriber."""
        snapshot = IntakeProgress(
            done=self._done,
            total=self.total,
            current_title=current_title,
            phase=phase,
            paused=self.is_paused,
        )
        for queue in self._subscribers:
            queue.put_nowait(snapshot)

    def _close_subscribers(self) -> None:
        """Send the end-of-stream sentinel to every subscriber."""
        for queue in self._subscribers:
            queue.put_nowait(None)

    async def run(self, *, force: bool = False) -> None:
        """Read every vault item once and index it.

        When ``force`` is True the read-once guard is bypassed (a full re-read),
        though locked reads are still preserved by the store.
        """
        self._phase = PHASE_READING
        text_model = await resolve_text_model(self._settings, self._client)
        for item in self._items:
            await self._await_resume()
            if not force and self._store.is_up_to_date(item.id, item.content_hash):
                self._done += 1
                self._emit(item.title, PHASE_READING)
                continue
            await self._process_item(item, text_model)
            self._done += 1
            self._emit(item.title, PHASE_READING)

        self._phase = PHASE_DONE
        self._emit(None, PHASE_DONE)
        self._close_subscribers()

    async def _await_resume(self) -> None:
        """Block while paused; emit a paused snapshot once when entering pause."""
        if self.is_paused:
            self._emit(None, PHASE_PAUSED)
            await self._resume_gate.wait()

    async def _process_item(self, item: Item, text_model: str) -> None:
        """Read, fingerprint and index a single item (image or note)."""
        if is_image_item(item):
            await self._process_image(item)
        else:
            await self._process_note(item, text_model)

    async def _process_image(self, item: Item) -> None:
        """Vision-read an image, fingerprint its description, and index it."""
        model = await self._manager.use("vision")
        read = await read_image(self._client, item.path, model=model)
        fingerprint_text = read.description or item.title
        await self._index(item, fingerprint_text)
        self._persist_read(item, KIND_IMAGE, read)

    async def _process_note(self, item: Item, text_model: str) -> None:
        """Text-read a note, fingerprint its body, and index it."""
        await self._manager.use("vision" if text_model == self._settings.vision_model else "text")
        read = await read_note(self._client, item, text_model)
        fingerprint_text = item.body or item.title
        await self._index(item, fingerprint_text)
        self._persist_read(item, KIND_NOTE, read)

    async def _index(self, item: Item, text: str) -> None:
        """Fingerprint ``text`` and upsert ``item`` into the vector store."""
        vectors = await self._embeddings.fingerprint_documents([text])
        self._store.upsert(item, vectors[0])

    def _persist_read(
        self, item: Item, kind: str, read: ImageRead | NoteRead
    ) -> None:
        """Persist a derived read, honouring the locked-overwrite refusal."""
        self._store.upsert_read(
            item.id,
            kind=kind,
            data=read.model_dump_json(),
            confidence=read.confidence,
            content_hash=item.content_hash,
            read_at=_now_iso(),
        )
