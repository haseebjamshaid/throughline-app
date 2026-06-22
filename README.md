# throughline

**A local-first second brain for your Obsidian vault — a taste engine that turns your notes and images into something you can actually search and explore. Fully local. No cloud. Your data stays yours.**

_Proprietary software — © 2026 Haseeb Jamshaid. All rights reserved. Not for redistribution._

throughline reads your Obsidian vault, understands what's in it (themes, feelings, connections in your notes; colors, mood, framing in your images), and builds an explainable, searchable map of your taste. Everything runs on your machine via [Ollama](https://ollama.com) and local models — there are no API keys, no accounts, and nothing leaves your laptop.

## What "throughline" means

The name comes from screenwriting. A story's **throughline** (Stanislavski's *through-line of action*, also called the *spine*) is the single connecting thread that runs beneath every scene — the core intention that ties otherwise-separate moments into one coherent whole. Without it, a script is just disconnected scenes; with it, everything pulls in the same direction.

That's the idea here. Your notes, films, songs, books, and half-formed thoughts are the scenes; throughline reads across them to find the thread running through it all — and when you're stuck, it pulls on that thread to hand you the next beat. The heart of the app — **the thread** — is named for exactly this.

## Fully local & private

- **No cloud, no API keys.** All inference runs on local models through Ollama.
- **Your vault is the source of truth.** throughline reads it and writes back to it (when you ask) — it never uploads it.
- **The search index is a rebuildable cache** stored under `.throughline/` and git-ignored. Delete it anytime; throughline regenerates it from your vault.
- **Models only use RAM while you want them to.** Ollama is app-managed: it starts when you run the app and stops when you quit, and an in-app Models panel lets you load/unload models on demand.

## Requirements

- **macOS on Apple Silicon** (M-series).
- **~16 GB RAM** (validated; only one heavy model is resident at a time).
- **~10 GB free disk** for the three local models.
- **[Homebrew](https://brew.sh)** (the setup script installs everything else).
- **Obsidian is optional** — throughline works on any folder of Markdown notes + images. You don't need Obsidian installed to use it.

## Quick start

```bash
git clone git@github.com:haseebjamshaid/throughline-app.git
cd throughline-app
./setup.sh      # installs prerequisites, pulls models, installs deps (one time)
./run.sh        # starts Ollama + backend + frontend
```

Then open the app at **http://localhost:5173**.

`setup.sh` is idempotent — re-running it is safe and skips anything already in place.

## What gets installed

`setup.sh` installs (via Homebrew, only if missing) and configures:

- **[Ollama](https://ollama.com)** — the local model runtime. It is *app-managed*: not registered as an always-on login service, so nothing runs in the background when throughline is closed.
- **Three local models** (~10 GB total): `embeddinggemma:300m` (~622 MB), `qwen3-vl:4b` (~3.3 GB), and `qwen3.5:9b` (~6.6 GB). The large one can take a while on a slow or flaky network; if a download fails, just re-run `setup.sh` — it resumes from cache.
- **Python toolchain** via [uv](https://docs.astral.sh/uv/) plus the backend dependencies.
- **Frontend dependencies** via npm.

## Using it

**First run.** The first time you open throughline it walks you through the first ten minutes: point it at a vault, watch it read your shelf, meet the first portrait it draws of you, then pull your first thread. (Returning visits drop you straight into the heart.)

Then you live in five rooms:

1. **vault** — connect a folder of Markdown + images, quick-capture new notes, and run intake. A background worker reads each note and image once (themes/feelings/connections for notes; description/colors+hex/light/mood/framing for images), fingerprints everything for search, and is pausable and idempotent with live progress. Corrections write back to frontmatter and are never overwritten.
2. **profile** — a living portrait drawn from your shelf: a palette and backed claims across a creative slice (mood/light/framing/subjects/do's/don'ts) and a deeper slice (themes/ambitions/threads), each with its confidence and the items it came from. Pin, edit, or delete any line; it's written back to the vault as a readable note.
3. **the thread** (the heart) — say what you're stuck on in plain words and get back exactly one sharp question, one connection pulled from your own shelf, and one concrete next step you can do today. Make it smaller, swap it, or mark it done. It never ends on analysis without an action.
4. **fit check** — hold something up (a caption, a song, an image) and hear, honestly, how *you* it is: a 0–100 closeness score, one verdict, a checklist tied to your own profile claims (each with a fix), and the closest things from your shelf. Off-profile on purpose? say so, and it remembers.
5. **vibe search** — ask in natural language (e.g. *"rainy neon city, someone alone at night"*) and get explainable semantic results ranked from your own vault.

Everything is local, lowercase, and warm — no cloud, no accounts.

### Managing model RAM

throughline keeps only one heavy model resident at a time, but you can control it directly:

- **In-app Models panel** — load or unload models to manage which ones use RAM.
- **API endpoints** for the same:
  - `GET /models` — list models and what's currently resident.
  - `POST /models/load` — load a model into RAM.
  - `POST /models/unload` — unload a specific model.
  - `POST /models/unload-all` — free all model RAM.

Because Ollama is app-managed, quitting the app (Ctrl+C in `run.sh`) unloads models and stops Ollama if throughline started it — nothing keeps running once you're done.

## Architecture

- **Vault = source of truth.** Your Markdown notes and images are the canonical data. throughline reads them and (on request) writes structured reads back as frontmatter.
- **sqlite-vec index = rebuildable cache.** Embeddings and full-text search live in an embedded [sqlite-vec](https://github.com/asg017/sqlite-vec) + FTS5 index under `.throughline/`. It's machine-specific, git-ignored, and can be rebuilt from the vault at any time — never commit it.
- **Models:**
  | role | model | purpose |
  |---|---|---|
  | text / reasoning | `qwen3.5:9b` | note reads (themes, feelings, connections) |
  | vision | `qwen3-vl:4b` | image reads (description, colors + hex, light, mood, framing) |
  | embeddings | `embeddinggemma:300m` | semantic search vectors |
- **Backend** (FastAPI, port 8000) serves the API and talks to Ollama. **Frontend** (React + Vite, port 5173) calls the backend.

## Manual / dev commands

```bash
# Backend dependencies
uv --directory server sync --extra dev

# Run the backend (API at http://127.0.0.1:8000, Swagger at /docs)
uv --directory server run uvicorn throughline.main:app --port 8000

# Run the backend tests
uv --directory server run pytest

# Frontend dependencies
npm --prefix app install

# Frontend dev server (http://localhost:5173)
npm --prefix app run dev

# Frontend production build
npm --prefix app run build
```

## Troubleshooting

- **A model download failed (TLS timeout / connection reset).** This is usually the large `qwen3.5:9b` on a flaky network. Just re-run `./setup.sh` — downloads resume from cache, so a patient retry gets there.
- **Port 8000 or 5173 already in use.** Something else is bound to that port (often a previous run that didn't exit cleanly). Stop the other process, or find it with `lsof -i :8000` / `lsof -i :5173` and kill it, then re-run `./run.sh`.
- **`ollama: command not found`.** Re-run `./setup.sh` to install it via Homebrew, or install it yourself with `brew install ollama`. Make sure Homebrew's bin directory is on your `PATH`.
- **App can't reach the backend.** Confirm the backend is up at http://127.0.0.1:8000/docs. If Ollama isn't responding, check http://127.0.0.1:11434/api/version.

## Tech stack

| Layer | Tech |
|---|---|
| Models / inference | Ollama (`qwen3.5:9b`, `qwen3-vl:4b`, `embeddinggemma:300m`) |
| Backend | Python 3.12, FastAPI, uvicorn, Pydantic |
| Vector + text search | sqlite-vec + FTS5 (embedded, rebuildable) |
| Package management | uv (Python), npm (JS) |
| Frontend | React 19, Vite, TypeScript, Tailwind v4, React Router |
| Vault parsing | python-frontmatter, watchdog |

## Project status

See [PROGRESS.md](./PROGRESS.md) for the current build status and what's implemented.
