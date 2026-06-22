# throughline — build status

**Repo:** `github.com/haseebjamshaid/throughline-app` (private, proprietary) · **Status:** ✅ **v1 complete — ready to stress-test end to end.**

## TL;DR
All five rooms are built, wired to the live local models, and verified: **vault + intake**, **profile**, **the thread** (the heart), **fit check**, and **vibe search** — plus a guided **first-run onboarding**. Everything runs fully locally on the 16 GB M4 (one heavy model resident at a time). The UI is the warm "nature distilled" vintage skin, all lowercase. Committed and pushed under the personal account.

---

## What works (v1)

- **vault & intake** — connect any folder of Markdown + images; background worker reads each item once (notes → themes/feelings/connections via `qwen3.5:9b`; images → description/colors+hex/light/mood/framing via `qwen3-vl:4b`), fingerprints into sqlite-vec + FTS5, pausable + idempotent + SSE progress; quick-capture; corrections write back to frontmatter and are never overwritten (`locked`).
- **profile** — a living portrait: palette + backed claims across a creative slice (mood/light/framing/subjects/dos/donts) and a deeper slice (themes/ambitions/threads), each with confidence + source items; pin/edit/delete; written back to the vault as a readable note.
- **the thread (the heart)** — stuck text → one sharp question + one connection from your own shelf + one concrete next step; smaller/different/did-it controls; the guardrail guarantees it never ends on analysis without an action.
- **fit check** — hold up a caption/song/image → a 0–100 closeness score, one honest verdict, a checklist tied to your REAL profile claims (each with a fix), and the closest items from your shelf; "that's me on purpose" softens a rule and is remembered; fast embedding-only batch ranking too. Guardrails: checks only ever cite real claims; a blank model response degrades to a grounded similarity score.
- **vibe search** — explainable semantic + keyword search over your own vault.
- **first-run onboarding** — a focused full-bleed walk (connect → read → first portrait → first thread), honest on empty/thin shelves; a local flag + an existing-profile check route returning users straight to the heart.
- **model RAM control** — in-app Models panel + `/models` endpoints; Ollama is app-managed (started by `run.sh`, stopped on quit).

## API surface
`/health` · `/vault/connect` · `/vault/items` · `/vault/capture[/image]` · `PATCH /vault/items/{id}` · `/intake/start|pause|resume` · `/intake/progress` (SSE) · `/search` · `/profile` · `/profile/generate` · `PATCH /profile` · `/thread` + `/thread/{id}/different|smaller|did-it` · `/fit` · `/fit/disagree` · `/fit/batch` · `/models[/load|unload|unload-all]`

## Verification
- **Backend: full pytest suite green (63 tests)** — unit, route guards, and live-model paths. One live test (`test_generate_profile_from_sample_vault`) is **flaky on the 3-note sample vault** (the model occasionally returns only creative-slice claims); it passes on retry. Profile-generation code is unchanged.
- **Frontend:** `npm run build` passes clean (tsc + vite).
- **Live end-to-end (screenshot-verified):** onboarding walk connect → read → portrait → handoff → thread; fit check (a fitting caption → 100 "this is very you"; a drifting one → 42 "louder and brighter than you tend to go" with concrete fixes); the thread returns a grounded, actionable turn.

## Memory budget — validated on the 16 GB M4
Only one heavy model resident at a time (`keep_alive=0` swap + `OLLAMA_MAX_LOADED_MODELS=1`): peak ≈ heavy model (≤6.6 GB) + embedder (~0.6 GB) + app + macOS ≈ **~10–11 GB of 16 GB.**

## How to run
```
./setup.sh                 # one-time: installs ollama/uv/node, pulls 3 models, deps
./scripts/setup-vault.sh   # creates a private Obsidian vault + git sync (optional)
./run.sh                   # starts Ollama + backend (:8000) + frontend (:5173)
# tests:  uv --directory server run pytest -q
```

## Known follow-ups (non-blocking)
- De-flake the live profile test (relax the "must span both slices" assertion for a thin sample vault, or seed a richer fixture) — model nondeterminism, not a code bug.
- The thread can occasionally pick the indexed `throughline-profile.md` note as its connection; excluding `type=profile` from thread/fit connections is a small refinement.
- Deferred per spec (not v1): ambient thread nudges, outward vibe search, boards, multi-profile, audio feel.
