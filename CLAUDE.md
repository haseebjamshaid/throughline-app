# throughline — project guide for Claude

throughline is a **local-first second brain + taste engine** on top of an Obsidian
vault, powered entirely by **local models via Ollama** (no cloud, no API keys).
The vault (markdown notes) is the source of truth; the app is a disposable brain
on top. Target machine: Apple M4 MacBook Air, 16 GB.

The heart is **the thread** — say what you're stuck on, get back one sharp
question, one connection from your own vault, and one concrete next step.

## Cardinal rules (do not violate)
- **Everything in the UI is lowercase.** Every label, heading, button, placeholder.
  No `text-transform: uppercase`, no all-caps strings. (Hard requirement.)
- **Design = warm vintage "nature distilled."** Tokens in `app/src/index.css`
  `@theme`: paper `#efe6d0`, card `#f7f0df`, ink `#43372a`, ink-soft `#8c7b64`,
  terracotta `#c67b5c`, clay `#b5651d`, olive `#6f7444`, sand `#d4c4a8`, gold
  `#cba35f`, border `#e0d3b6`. Fonts: **Fraunces** (display), **EB Garamond**
  (body / the thread's voice), **Nunito Sans** (ui labels) — all offline via
  @fontsource. Rounded soft cards (~20px), soft warm shadows (no hard borders),
  low contrast, Phosphor icons, bespoke SVG illustrations in `app/src/illustrations/`.
- **Git identity is PERSONAL, never the work account.** Commits authored
  `Haseeb Jamshaid <88651579+haseebjamshaid@users.noreply.github.com>` (repo-local
  config, already set). Push uses `core.sshCommand "ssh -i ~/.ssh/id_personal -o
  IdentitiesOnly=yes"`. The `gh` CLI is logged in as the WORK account — do NOT use
  `gh` for these repos. Conventional-commit style; no Claude co-author trailer.
- **Vault privacy.** The vault holds private self-material. `.throughline/` (the
  derived index — rebuildable) is git-ignored and must NEVER be committed/synced.
  Self-typed items (ambition/fear/experience/journal) are inward-only (privacy wall).
- **Screenshot-verify UI** before claiming it's done (chrome-devtools MCP).
- **Never reconnect the user's running backend to a different vault while they're
  using the app** — it writes their captures to the wrong vault. Spin up a separate
  backend instance/port if you need to verify something.

## Repos
- Code: `github.com/haseebjamshaid/throughline-app` (PRIVATE, proprietary — all
  rights reserved), default branch `main`.
- Vault: `~/Desktop/throughline-vault` → its own PRIVATE repo `throughline-vault`,
  synced by the Obsidian Git plugin (auto commit-and-sync on).

## Run
- One-time: `./setup.sh` (installs ollama/uv/node, pulls 3 models, deps), then
  `./scripts/setup-vault.sh` (creates the private Obsidian vault + git sync).
- Run everything: `./run.sh` (app-manages Ollama, `OLLAMA_MAX_LOADED_MODELS=1`;
  backend :8000 + frontend :5173; Ctrl-C frees model RAM).
- Manual: `uv --directory server run uvicorn throughline.main:app --port 8000`;
  `npm --prefix app run dev` (→ http://localhost:5173; backend has CORS for it).
- Checks: `uv --directory server run pytest -q`; `npm --prefix app run build` (tsc+vite).

## Models (Ollama)
text `qwen3.5:9b`, vision `qwen3-vl:4b`, embeddings `embeddinggemma:300m`. These are
THINKING models → always call via `/api/chat` with `think:false` + `format:json`
(the `OllamaClient.complete_json` / `describe_image` helpers). One heavy model
resident at a time (~10–11 GB peak). Cold-loading qwen3.5 takes ~60–260s; warm
calls ~20–40s — budget curl/test timeouts accordingly.

## Architecture
**Backend** `server/throughline/`: `config.py` (Settings, `resolve_text_model`),
`vault/` (reader, frontmatter +writer), `models/` (ollama_client, model_manager =
single-heavy-slot swap, embeddings), `index/` (`store.py` = sqlite-vec
`vec_items`+`fts_items`+`reads`; `search.py`), `intake/` (worker = read-once /
pausable / SSE, capture), `profile/` (`generate.py` = deterministic w/
temperature+seed + source-signature skip; store; edits), `thread/` (engine,
connection, prompts, persistence), `fit/` (check, prompts, batch, disagreements),
`main.py` (FastAPI app, `AppState`, CORS, all routes), `schemas.py`.

**Frontend** `app/src/`: `shell/` (`AppShell` wraps content in `<AppProviders>`),
`lib/` (`api.ts` + raw hooks `useVault/useProfile/useThread/useFit/useIntake/
useSearch` + **`appState.tsx`** = the shared, context-backed versions), `screens/`
(vault/, ProfileScreen + profile/, ThreadScreen + thread/, FitCheckScreen + fit/,
search/), `onboarding/` (`Landing` gate + `OnboardingFlow` + steps), `illustrations/`,
`index.css` (@theme tokens), `App.tsx` (routes; `/` → Landing, `/welcome` →
onboarding, the rest under AppShell).

**Key frontend pattern (state persistence):** every screen hook is instantiated
ONCE in `<AppProviders>` (mounted in AppShell, above the router outlet) and shared
via context, so in-flight state — busy flags, results, the profile's editable
temperature/seed knobs — **survives tab switches**. Screens import the shared hooks
from `lib/appState`, NOT the raw `lib/useX`. Onboarding lives outside the shell and
uses raw hooks on purpose.

## Conventions worth knowing
- Immutability everywhere (new objects, never mutate). Many small files (<400 lines).
  Errors handled explicitly; honesty over invention (sparse model output degrades to
  low-confidence/empty, never fabricated).
- **Profile is deterministic + idempotent**: a source-signature (hash of vault
  items, excluding the profile note) skips regeneration when the vault is unchanged;
  generation samples at temperature 0 + a fixed seed (both editable in the UI;
  changing either, or the vault, redraws). Pins survive regeneration.
- **Intake is read-once** per file (content-hash) — adding a file only reads the new
  one; editing a file re-reads just that one.
- Vault items are **editable + deletable**: PATCH re-embeds/re-indexes; DELETE
  removes the `.md` and prunes the index.

## Gotchas (harness)
- GateGuard denies the FIRST touch of each new/edited file → just retry the identical
  Write/Edit (it passes). A stricter variant asks you to grep importers first.
- The auto-mode classifier blocks self-granting permissions (don't try to widen your
  own perms in `.claude/settings.local.json`).
- Avoid `rm -rf` and `git reset --hard` (denied).

## Status
v1 is complete and stress-tested. `handoff.md` (local, git-ignored) has the current
running state, full commit log, and open follow-ups. `PROGRESS.md` (committed) is the
v1 status report.
