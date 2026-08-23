---
id: 145
slug: artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract
title: '`artifact.json` is a gitignored cache — the moment a second renderer reads it, it is a published contract nobody versioned'
phase: 3
milestone: Presentation
status: blocked
depends_on: [088, 112, 116, 118]
---

> **Two halves, and only the first is schedulable.** Phase A (the contract) can run now and is worth
> doing alone. Phase B (the web renderer) is **blocked on [118](118_module-summary-seam-gets-empty-facts.md)**
> — see "Why B waits".

## Why this exists

`generate_onboarding` writes two things: the committable artifact under `docs/onboarding/` (markdown,
`manifest.json`, the single-file `index.html`) and a regenerable cache at
`.code-atlas/onboarding/artifact.json`, which is
`json.dumps(artifact.as_dict(), sort_keys=True, ensure_ascii=False, indent=2)` — deterministic, and
described in the source as *"the gitignored regenerable cache"*.

That description is safe **only while the single consumer is in-tree**. `viewer.py` embeds
`dataset.as_dict()` verbatim, so today the shape can move freely and both sides move together. A second
renderer **outside** this repository — a Next/Nuxt app, or anything else — turns that file into a
**published interface**: it gains a consumer that cannot be updated in the same commit. R3 exists for
exactly that situation (contract frozen, versioned, conformance-tested), and nothing in it applies to
`artifact.json` today: no version, no conformance test, and docs that call it a cache.

**Phase A is therefore the real content of this ticket**, and it is worth shipping even if no web app is
ever written.

Provenance: the architecture review of 2026-08-23, in the discussion of moving onboarding onto a JS
stack.

## Scope — Phase A (the contract)

- A version on `artifact.json`, and a conformance test pinning the shape — the same discipline
  `tests/contract/` applies to the adapter seam.
- A made-to-fail guard: changing the shape without bumping the version fails.
- The docs that call it a free-form cache stop calling it that.

## Scope — Phase B (`onboarding_web/`, opt-in, outside the core)

Placement mirrors `onboarding_llm/` — outside `code_atlas/`, off by default — but **the mechanism is
different and the ticket must not blur it**: `onboarding_llm/` is Python injected through Protocol
seams; a JS app cannot be imported by the core at all. It is a downstream consumer, and **the contract
between them is a file on disk, not a Protocol**. That is why Phase A comes first.

Hard boundaries, which are most of the value of writing this down:

- **Never opens `graph.db`, never calls an MCP tool, never runs a second pipeline.** A number the app
  needs and the dataset lacks is added **to the dataset in the core** — not fetched around the side.
- **Node never reaches the core's build path.** `pytest` and `scripts/gate.sh` stay green with no npm
  installed. The repo has no Node today (the only `package.json` belongs to a cross-repo sample).
- **`index.html` stays the default committable artifact.** The app is a second renderer, not a
  replacement.
- **No network at runtime** — the offline property is a product claim (§1), not a viewer detail.

**The R4.2 conflict, stated rather than discovered later:** the single-file viewer is byte-identical
under `R4.2`/116 AC3. A Next/Nuxt static export is **not** reproducible by default (build id, hashed
chunks). This ticket must choose in writing: pin the build, or declare this artifact outside that gate
and say what replaces it.

## Why B waits

The map today prints `Summary: (none)` on **every** module page (118), counts test controllers as web
surface (130), and opens the tour with a lint config (131). A better renderer would render those in
nicer type, and a diagram is trusted **more** than a table — the same argument that keeps sequence
diagrams out of [143](143_the-system-map-has-no-diagram.md). **Unblock condition: 118 closed.**

## Acceptance criteria — Phase A

- **AC1** `artifact.json` carries a version; a conformance test pins the shape (R6.5, red first).
- **AC2** A shape change without a version bump fails the suite (made-to-fail, not assumed).
- **AC3** No doc still describes the file as a free-form cache.
- **AC4** Determinism unchanged: identical index → byte-identical file (R4.2).

Phase B's criteria are written when 118 closes; drafting them now would read as a commitment to a stack
that has not been chosen.

## Out of scope

- **Choosing Next vs Nuxt.** Both static-export; the maintainer picks the one they maintain comfortably.
  A ticket does not get to decide it.
- **Serving the app from a container.** Deployment, and it is separate — the read-only snapshot idea
  belongs with whatever ticket owns distribution.
- **Replacing the single-file viewer.**
