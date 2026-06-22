# throughline — build spec

A second brain + taste engine that holds who you are and what you love, reflects your patterns, connects threads, and shows you a way through when you're stuck. Built on an Obsidian vault, powered by a local LLM.

---

> ## ⟢ BUILD DIRECTIVE — read first
> *(This block is the planning instruction. Delete it if you want the planner to infer freely from the spec below — but then it will treat all five features as equal weight and the heart will get buried.)*
>
> **Objective:** plan the v1 build of throughline as a local-first desktop/web app on top of an Obsidian vault.
>
> **v1 — build these:** vault & intake · unified profile · **the thread (the heart)** · fit check (images + captions) · vibe search (inward only).
>
> **v1 — explicitly DEFER (do not plan now):** outward web discovery, ambient nudges, boards, multi-profile, audio/song feel, polished export.
>
> **Required build sequence (the spine).** These are not equal-weight features; later ones depend on earlier ones:
> 1. **vault & intake** — nothing works without the corpus being read.
> 2. **profile** — the ruler everything else measures against.
> 3. **the thread** — THE HEART. Must become reachable as early as the spine allows; it is the reason the app exists. Do not schedule it last.
> 4. **fit check** and **inward vibe search** — ride on the profile + index; can parallelize once 1–3 exist.
>
> **Non-negotiable guardrails (treat as acceptance criteria on every relevant task):**
> - **Privacy wall:** "self" material (fears, ambitions, journal, experiences) is inward-only and must never enter any outward/web query. Inward features never touch the network.
> - **Action-bias:** the thread must always terminate on ONE concrete next step. "Pure insight, no next step" is a failure state, not an acceptable output.
> - **Vault is the source of truth; the app is disposable.** Never store canonical data anywhere but the vault files. The derived index/fingerprints are rebuildable cache, per-machine, never committed.
> - **Local-first / offline:** all v1 features run locally against a local model; no cloud dependency for inward work.
>
> **Stack:** deliberately deferred — do not hardcode. If you must assume to produce a plan, assume: React/Next/TS frontend; local LLM on an M4 MacBook Air 16GB via Ollama (MLX backend); Obsidian vault + private git as the store; a local vector index for fingerprints. Flag every such assumption explicitly as a decision still open.

---

## What it is (one paragraph)

The user keeps a vault of the things that make them *them* — films, music, books, quotes they live by, plus their own notes on what they're chasing and what they're scared of, plus images. throughline reads all of it with a local model and becomes the brain on top: it knows their taste, sees their patterns, and when they're stuck it pulls a thread — a sharp question, a connection from their own past, and one concrete next step. Everything is owned by the user, stored as plain files, synced by their own git repo. Sensitive material never leaves the machine.

## Architecture (decided — implement as given)

- **Source of truth = an Obsidian vault**, which is a **private git repo**. The app does not own data; it reads and writes the vault's files.
- **Every item is one note.** Frontmatter (`type:`, `title:`, `feeling:`, `tags:`) declares *what* it is; the note body is the human "why it matters," which is the primary signal the model learns from.
  - Taste types: `movie`, `song`, `book`, `quote`.
  - Self types: `ambition`, `fear`, `experience`, `journal`.
  - Images are vault attachments.
- **Two-way editing:** notes can be authored/edited in Obsidian *or* via the app's quick-capture; both write the same files. Neither side holds a hidden private copy.
- **Derived index:** on intake the app produces, per item, a structured read (description/colors/mood/themes/connections) and a **fingerprint** (an embedding) used for search and connection-finding. The index is big, machine-specific, rebuildable, and **git-ignored** — each machine rebuilds it from the vault.
- **Sync & history = git** (Obsidian Git plugin handles commit/pull). Git history *is* the versioning feature; don't build a separate one.
- **Gotchas to design around:** the app + local model install per machine (data syncs, the brain doesn't); use git-LFS for image attachments or keep large image folders out of the vault; never commit the index.

## v1 features

### 1. Vault & Intake
**What:** the corpus + the worker that reads it (text and images).
**Screen (layout):** persistent left nav rail (Vault, Profile, The Thread, Fit Check, Vibe Search, + Capture). Header shows an offline indicator and an intake progress counter ("reading N of M"). Below the header, a horizontal filter pill row (All · Movies · Songs · Books · Quotes · Self · Images). Main area: a vertical list of note cards interleaved with an image grid — each note card shows a type icon + title + a feeling/"private" marker + a short body preview. Right-hand quick-capture panel: a paste box, a type dropdown, and a hint that it writes a real note into the vault.
**Requirements:**
- Connect to an existing Obsidian vault or create one wired to a private git repo.
- Quick-capture inside the app: paste a title/lyric/thought, pick a type, it writes a clean note into the vault; drag-drop for images.
- Intake reads each note and image once, in the background, with a visible counter; pausable; never re-reads on every open.
- Per item, record: (images) description, dominant colors + hex, light, mood words, framing; (notes) themes, feelings, connections to other notes; (all) a fingerprint.
- User can correct any tag/read; corrections persist and are never silently overwritten.
- Low-confidence reads are flagged honestly, not invented.

### 2. Profile (unified)
**What:** one living picture of the user — taste *and* recurring themes — drawn from the vault. The ruler the thread and fit check both use.
**Screen (layout):** header with the profile's name, a version-history dropdown, and actions (Export slice, Regenerate). A toggle switches between "Creative slice" and "Deeper threads." Creative-slice view: a palette swatch row, mood pills (some marked pinned), and a "recurring threads" card carrying an example-count annotation ("solitude shows up across 14 films, 9 songs & your own notes"). Below: a "stated ambitions" card of editable pills with a confidence note. Pinned (📌) and local-only (🔒) markers are visible inline.
**Requirements:**
- A **creative slice** readable on its own: palette, mood, light signature, framing/shot grammar, recurring subjects, do's & don'ts.
- A **deeper slice:** recurring themes, stated ambitions, threads that recur across films/music/notes.
- Every claim is backed by linked examples ("because of these things") and carries a confidence level.
- Generate/regenerate from the current vault; the user can edit any line, **pin** lines (regeneration won't touch them), add/delete lines.
- Written back into the vault as a note (so it's versioned by git and portable).
- Deeper-slice material is marked local-only (never leaves the machine).

### 3. The Thread — THE HEART
**What:** the unstuck engine. The user says they're stuck; it returns a sharp question, a connection from their own vault, and one concrete next step.
**Screen (layout):** a conversation-style column with a nudge-frequency control in the header (default "rarely"). Flow renders as stacked bubbles: the user's stuck statement (right-aligned) → a "one question" reply → a "a thread I found" connection reply (visually distinct, gold-accented). It terminates in a highlighted card titled "your one next step · today" containing the single action, with three buttons beneath: "did it ✓", "smaller", "different step". The next-step card is the visual focal point — unmissable relative to everything above it.
**Requirements (core flow, on-demand):**
1. Free-text input of the stuck thing.
2. Respond with **one** sharp question first (not a list).
3. Surface **one** relevant connection pulled from the vault (something they already said/loved/lived).
4. Hand over **one** next step — small, specific, doable today, visually unmissable.
5. Controls: "different step," "smaller step," and "did it" (logs momentum, closes the loop).
**Requirements (ambient, low-frequency):**
- Occasionally surface a noticed thread ("you keep returning to X — want to pull on it?"); dismissible; frequency user-set, default rare.
- **No** streaks/badges/nagging/notification machinery.
**Hard rules:**
- Always ends on a concrete action (see guardrail). Pure analysis with no next step = failure.
- Every nudge is grounded in the user's own vault content, never generic platitudes.
- Presents as a tool, not a friend/therapist; for anything beyond a creative block it points to real people/help and is honest about being a small local model.

### 4. Fit Check
**What:** "how *me* is this?" for an image, a caption, or a song — scored against the profile, never against generic "good."
**Screen (layout):** header reads "checking against: [profile ▾]" beside an input-type toggle (Image · Caption · Song). Two-column body: left shows the submitted item (e.g. the image); right is a stack of cards — a score card (large % + a meter + a one-line verdict), a checklist card where each line is a pass/fail tied to a named profile rule with its fix, and a "closest from your vault" thumbnail grid. Footer surfaces the disagree affordance ("tap a line → 'I meant that'").
**Requirements:**
- Inputs: image, text (caption/title/line), song (by described feel in v1; audio feel deferred).
- Output: a 0–100 fit score (distance from the center of the user's taste); a one-line verdict; a checklist where each profile line becomes a named check; concrete fixes; side-by-side with closest vault matches.
- Batch mode: drop several, get them ranked by fit.
- Disagree loop: user marks "I meant that" on any flag → it stops flagging it and tunes the profile over time.
- Never edits the user's work; off-profile-on-purpose is treated as a valid choice, not an error.

### 5. Vibe Search — inward only (outward deferred)
**What:** find things already in the vault by feeling.
**Screen (layout):** top row pairs an Inward/Outward toggle (Inward active in v1, with a visible "searching your own vault — nothing leaves" note) with a feeling search box. Below: a results count + filter/weight pills (type filters, a "weight: mood↑" control), then a ranked grid where each result shows its match-% and, on inspection, *why* it matched. A small card illustrates what the same query would return in Outward mode (built but disabled in v1).
**Requirements:**
- Semantic ranking over the fingerprint index (not keyword matching); a plain-language feeling query returns the right items even when nothing is literally named that.
- Search-by-example: drop an image / point at a note → "more like this."
- Explainable: each result shows why it surfaced.
- Tunable: weight mood vs color etc.; filter by type.
- Fully local, private, instant.
- *(Outward web discovery is a later headliner; build the inward path so an outward mode can layer on without rework, but do not implement outward in v1.)*

## First run (v1)
The onboarding's only job: get the user from empty to their first profile *and* first thread.
**Screen (layout):** a three-step horizontal flow. Step 1 — "your vault": pick an existing Obsidian vault or create one wired to git, with an up-front privacy line. Step 2 — "it reads": a human-worded progress moment ("reading films, notes & feel — N of M") with a meter, not a blank spinner. Step 3 — the reveal: the first profile (palette swatches shown) immediately followed by a "want to pull a thread?" prompt so the heart is felt on day one, ending on a tiny first move. Thin vaults still work and the app says so honestly.

## Cross-cutting rules
- Vault is truth; app is disposable (data readable in plain Obsidian if the app vanished).
- Privacy wall is visible and default-on; the active mode (inward vs outward) is always shown.
- Everything the model asserts is editable and traceable; user corrections always win.
- Fingerprint = an embedding; never shown to the user, powers search + "more like this" + the thread's connections.
- The app is honest about being a small model (flags low confidence, thin profiles, empty results).
- Empty states are instructive invitations, not blank screens.

## v1 vs later

| capability | v1 | later |
|---|---|---|
| Vault + intake | connect Obsidian, read notes + images, fingerprints, two-way capture, corrections | git-LFS niceties, watch-folder, video frames |
| Profile | unified taste + threads, examples, confidence, edit/pin, written back to vault | brand-book export, multiple profiles |
| **The thread** | **on-demand: question + connection + one next step; "did it" loop** | ambient nudges, momentum tracking |
| Fit check | images + captions, score, profile checklist, fixes, batch rank, disagree loop | audio/song feel |
| Vibe search | inward: semantic, explainable, tunable, by-example | outward web discovery |
| Boards | — | project workspaces |
