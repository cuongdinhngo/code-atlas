---
id: 105
slug: dominant-subtree-loses-to-a-config-dir
title: Onboarding — the dominant subtree is decided by file count, and a config dir can win it (M10)
phase: 3
milestone: M10
status: todo
depends_on: [104, 086]
---

## Why this exists (measured on a real repo, not guessed)

104 replaced 103's common-prefix grouping with **dominant-subtree**: group beneath the top-level
directory holding the **most modules**. Run against the real `laravel/laravel` skeleton at the SHA
this repo already pins in [`scripts/cross_repo_samples.json`](../../scripts/cross_repo_samples.json)
(`ff031db`, 26 indexed files), the dominant subtree is **`config/` (10 modules)**, not `app/`
(3 modules) — so the whole application collapses into a single `app` layer, exactly the F1 shape 104
existed to fix:

```
method=dominant-subtree  layers=('bootstrap','config','database','public','routes','tests','app')
  [config] 10 modules   config/app.php, config/auth.php, config/cache.php, …
  [app]     3 modules   app/Http/Controllers/Controller.php
                        app/Models/User.php
                        app/Providers/AppServiceProvider.php
```

**The count is the wrong tie-break for "which subtree is the architecture."** A directory of flat
settings files out-votes a small source tree, and the split then depends on how many config files a
scaffold happens to ship. 104's own AC3 fixture (a) hid this: it authored *8* classes under `app/**`
against one `routes/web.php`, so `app/` dominated by construction. This is the second time an
authored fixture has hidden a path-shape defect (retro F1; `LESSONS.md`, handle
`fixture-shape-begs-the-question`).

**It is not universal.** The same code is architecturally sensible on the other two pinned repos —
`symfony/demo` (dominant `src/` → Command · Controller · EventSubscriber · Form · Repository ·
Entity, ordered by real dependency direction) and `brick/math` (dominant `src/` → src · Exception ·
Internal). Both are recorded in 086's working doc. So the defect is **narrow**: it fires when a
non-source top-level directory holds more indexed files than the source tree.

## What this ticket must decide (do NOT pre-empt it here)

Candidate signals, to be judged against the same 6-shape bake-off 104 used **plus** the three pinned
real repos — a fixture-only verdict does not close this:

- **Weight the subtree by graph mass, not file count** (fan-in + fan-out, or symbol count). On the
  laravel skeleton `app/` carries the edges and `config/` carries almost none, so this inverts the
  wrong winner without naming a directory.
- **Rank candidate subtrees and keep every subtree above a threshold**, rather than electing exactly
  one dominant tree.
- **Report the runner-up.** Whatever the rule, the payload could name which subtree was elected and
  what it beat, so a reader can see the choice rather than inherit it.

**Explicitly rejected in advance (R2.2):** naming `config`, `vendor`, `tests` or any other directory
in the core. The core encodes no repo's or framework's directory habits — the signal must come from
graph shape, not from a stop-list.

## Acceptance criteria
- **AC1** — the chosen signal is recorded in the design phase with the alternatives and why, and
  holds R1.1 (no language branch), R2.2 (no directory stop-list) and R4.2 (determinism).
- **AC2** — proven on the **three pinned real repos** (`laravel/laravel`, `symfony/demo`,
  `brick/math`), with the actual layer assignment recorded for each and a human judgement that it is
  architecturally sensible. `laravel/laravel` must no longer collapse `app/**`, and `symfony/demo` /
  `brick/math` must not regress from the assignments recorded in 086's working doc.
- **AC3** — the AC3 fixtures 104 added are kept, and fixture (a) is **rewritten so it cannot beg the
  question**: it must carry a non-source top-level directory with more files than the source tree.
- **AC4** — `architecture_overview` (086) reflects the new grouping with no payload-shape change, and
  its own tests stay green.

## Out of scope
- The anchor-monorepo check 104's AC2 names — that remains the maintainer's, and this ticket does not
  substitute for it.
- LLM layer-name refinement (091); the summarizer seam (085); the metrics substrate (083).

## References
- Evidence + the three real-repo runs: `docs/tasks/086_architecture-overview-tool.md`
  (*Real-repo evidence*).
- `code_atlas/onboarding/layers.py` (`_dominant_subtree`, `_layer_of`, `assign_layers`).
- 104 `docs/tasks/104_onboarding-layer-signal.md`; 103; 084. PLAN §14, §15 (M10).
