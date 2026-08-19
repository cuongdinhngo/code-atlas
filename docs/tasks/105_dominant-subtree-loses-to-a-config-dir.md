---
id: 105
slug: dominant-subtree-loses-to-a-config-dir
title: Onboarding — the dominant subtree is decided by file count, and a config dir can win it (M10)
phase: 3
milestone: M10
status: done
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

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

## Session status
- **Runner:** `/mango:solve 105 with skipped review & challenger` — standing maintainer approval to
  resolve decisions ("do the best option"), pass all gates, then commit + push + open PR.
- **`CHALLENGER: OFF` (`--no-challenger`).** **`REVIEW: skipped`** (operator-waived) — no reviewer
  dispatch; verification runs in the main loop and is recorded empirically below.
- **work_doc_mode:** embed. **Branch:** `fix/105-dominant-subtree-loses-to-a-config-dir`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: S` · `TIER: full`.
- **Outward-action authorisation:** push branch + open PR are covered by the maintainer's standing
  durable approval (`AGENTS.md`, *Maintainer workflow*) plus this explicit invocation. Merge /
  force-push / branch-delete remain out — they need a separate confirmation.
- **Outcome — `done`.** All four ACs met, including **AC2 on the three pinned real repos** (laravel no
  longer collapses `app/**`; symfony/brick byte-identical to 086). Full Docker gate 1453 passed / 0
  failed. Unlike 104 (AC2 was a recorded exclusion), 105's AC2 is **satisfied this session**.
- **Revert path:** unmerged → close PR + `git push origin --delete
  fix/105-dominant-subtree-loses-to-a-config-dir`. Merged → revert the single squash commit on `main`
  (no schema/contract/tool change to undo; the only core change is the election arithmetic).

## Phase 0 — refine (self-skipped)
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved | 0 ASSUMED | skip: yes`

105 carries no open **product/want** decision: the deliverable is single (fix the election signal),
the ACs are explicit, and the *signal choice* is a technical **how-decision** the ticket hands to the
design phase with a defined procedure (bake-off + the three pinned real repos, R2.2 stop-list
pre-rejected). Under the standing "do the best option" approval that how-decision is resolved in
Phase 2 against evidence, cited — not a clarification for the human. Premise check: every referenced
source resolves (`layers.py::_dominant_subtree`, `scripts/cross_repo_samples.json`, 086 evidence,
104). No `PREMISE FALSIFIED`. → straight to analysis.

## Phase 1 — analysis
`SECTIONS: 6 (Why, What-to-decide, Acceptance, Out-of-scope, References, +candidate signals) | 6 decomposed | ROWS: C≈1 R=1 G=1 AC=4`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why/What-to-decide | The dominant subtree must stop being decided by **file count**; a flat config dir must not out-vote a small source tree | Re-weight `_dominant_subtree` by a graph-shape signal | ▶ design |
| R1 | Explicitly rejected | **No** directory stop-list — no `config`/`vendor`/`tests` names in core (R2.2) | Signal from `GraphMetrics` degrees only; zero literals | ▶ design |
| AC1 | AC1 | Chosen signal recorded with alternatives + why; holds R1.1 (no lang branch), R2.2 (no stop-list), R4.2 (determinism) | Phase-2 design record | ▶ design |
| AC2 | AC2 | Proven on **laravel/laravel · symfony/demo · brick/math**: record each layer assignment + human judgement it is sensible; laravel no longer collapses `app/**`; symfony/brick do not regress from 086 | Real indexed runs via Docker (host has no php) | ▶ execute |
| AC3 | AC3 | Keep 104's AC3 fixtures; **rewrite fixture (a)** so it carries a non-source top dir with **more files** than the source tree (cannot beg the question) | New config-heavy Laravel fixture = the proving test | ▶ execute |
| AC4 | AC4 | `architecture_overview` (086) reflects the new grouping with **no payload-shape change**; its tests stay green | Same `LayerAssignment` shape; only which subtree is elected changes | ▶ execute |

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision` — `j = 0`, Gate 0 clear. The one
contingency (AC2 needs a real index; the host lacks php) is **not** a want-decision — it is an
execution route (Docker), resolved in the verification plan.

### Blast radius
- **Modified (core):** `code_atlas/onboarding/layers.py` — `_dominant_subtree` (count → graph mass)
  and the one header-docstring line describing it. No control-flow change; no new symbol.
- **Modified (tests):** `tests/test_onboarding_layers.py` — rewrite fixture (a) (config-heavy) + its
  proving test; adjust the tie-break determinism fixture to a genuine **mass**-tie; comment touch-ups.
- **New (verification tooling, non-core):** `scripts/layer_report.py` — opt-in; clones+indexes the
  three pinned repos (reuses `cross_repo_validate` helpers) and prints each repo's `assign_layers`.
  The durable, re-runnable answer to the recurring `fixture-shape-begs-the-question` lesson.
- **Docs:** `docs/tasks/105_*.md` (this doc + frontmatter), `docs/BACKLOG.md` (status + token row),
  `docs/PLAN.md:537` (drop the "one recorded limitation"), `docs/tasks/086_*.md` (forward-note the
  fix), `docs/LESSONS.md` (learning loop).
- **Untouched:** `metrics.py`, `store.py`, `main.py`, `contract.py`, adapters, resolver, the 091
  `LayerRefiner` seam. **No count-pin change** — nothing added under `code_atlas/`, so
  `core_modules() == 51` holds (`test_core_is_language_agnostic.py` / `test_sql_confinement.py`).

### Declarations
`STRUCTURE: native` · `SCOPE: S` · `TIER: full` · `TRACK: backend`. `TIER: full` because it revises a
merged/locked core output behaviour (104) and AC2 demands real-repo proof — routed through the full
flow (review + challenger operator-waived).

## Phase 2 — design

### Approach — records AC1 (the signal decision)
**Chosen — graph-mass election.** `_dominant_subtree` elects the top-level directory with the greatest
**dependency mass** = Σ over its modules of `fan_in + fan_out` (from 083's `GraphMetrics`), replacing
the module **count**. Ties broken by name (unchanged, R4.2). Nothing else moves: the within-subtree
prefix strip (`_layer_of`), the other-top-dirs-each-own-layer rule, `(root)`, and the
direction-fallback trigger are all untouched, so `LayerAssignment`'s shape and `method` values are
identical (AC4). The signal is pure graph shape — no directory name appears in the core (R2.2), no
language branch (R1.1), and it is an order-independent `sorted(key=(-mass, name))` fold (R4.2).

Why it fixes F1: on the laravel skeleton `app/**` carries the application's edges while `config/**` is
flat settings that reference almost nothing — so `app/` wins on mass even though `config/` wins on
count, and `app/` splits into Http/Models/Providers again. On symfony/demo and brick/math the source
tree (`src/`) is both the largest **and** by far the most-connected subtree, so the winner is unchanged
— verified in AC2, not assumed.

### Rejected alternatives (recorded per AC1)
- **Keep file count (status quo).** The defect: a scaffold's settings directory out-votes the source
  tree, and the split then depends on how many config files a framework happens to ship.
- **Directory stop-list (ignore `config`/`vendor`/`tests`).** Pre-rejected by the ticket and R2.2 —
  the core must encode no repo's or framework's directory habits.
- **Rank subtrees + keep every subtree above a threshold** (elect none). A larger change to the
  one-dominant model and a new threshold constant to defend; graph-mass fixes the measured defect
  without it. Deferred as a possible successor if a future repo defeats single-election.
- **Report the runner-up in the payload.** Useful transparency, but it is a **payload-shape change**,
  which AC4 forbids; `method` already lets a reader see which grouping produced the split. Rejected
  for this ticket.
- **fan_in only / fan_out only.** fan_in favours depended-upon cores (penalises tests too), fan_out
  favours callers (risks a test dir winning). The **sum** (total degree) is the ticket's named
  primary and is symmetric; chosen, and confirmed safe on all three repos in AC2.

### Determinism argument (R4.2)
`_dominant_subtree` returns `sorted(mass, key=(-mass[name], name))[0]`; `mass` is summed over
`metrics.modules`, which `_grain` already sorts. No set-iteration, wall-clock, or insertion-order
leak. Byte-stability is proven end-to-end by the existing shuffle tests plus the mass-tie boundary
probe.

### Smallest change-list
| # | Change | File | Covers |
|---|---|---|---|
| 1 | `_dominant_subtree`: count → Σ(fan_in+fan_out); docstring | `layers.py` | G1, R1, AC1, AC4 |
| 2 | Header-docstring line "holds the most modules" → "carries the most dependency mass" | `layers.py` | AC1 |
| 3 | Rewrite fixture (a) config-heavy (8 config files > 7 app files, config edge-less) + retarget its proving test (red on count, green on mass) | `tests/test_onboarding_layers.py` | AC3 |
| 4 | Tie fixture → genuine mass-tie so `(-mass, name)` is exercised; comment touch-ups on stale "count" wording | `tests/test_onboarding_layers.py` | AC4 |
| 5 | `scripts/layer_report.py` — clone+index the three pinned repos, print `assign_layers` | `scripts/` | AC2 |

### Verification plan (per-AC)
| AC | risk | proof | how |
|---|---|---|---|
| AC1 | logic | design record above (chosen + 5 rejected) | this doc |
| AC2 | integration (real repo) | `scripts/layer_report.py` in Docker → the three assignments recorded + human judgement | `scripts/docker-test.sh python scripts/layer_report.py` |
| AC3 | logic | rewritten config-heavy fixture (a): red on `main:layers.py`, green post-change | scoped pytest + `git show main` |
| AC4 | logic | `test_architecture_overview*` green; payload keys unchanged; full Docker gate delta-green | `scripts/docker-test.sh` |

### Proving test (logic layer)
`test_dominant_subtree_survives_a_config_dir_with_more_files` — `config/**` (8 files) out-counts
`app/**` (7 files) but carries no edges; asserts graph-mass keeps `app/` dominant so `{Http, Models,
Services, Providers, Console} ⊆ layers`, `"app" not in layers`, `config` is one layer. **Red** on the
count-based `main` (emits a single collapsed `app` layer), **green** post-change. Invocation:
`pytest tests/test_onboarding_layers.py -k survives_a_config_dir -q`.

## Phase 3 — execute

### Implemented (approved change list only)
`layers.py`: `_dominant_subtree` elects by `Σ (fan_in + fan_out)` instead of module count; docstring +
header line updated. No control-flow, symbol, or payload-shape change. `tests/test_onboarding_layers.py`:
fixture (a) rewritten config-heavy (8 config files vs 7 app files, config edge-less), proving test
retargeted, tie fixture made a genuine mass-tie, stale "count" comments fixed. New `scripts/layer_report.py`
(opt-in AC2 reporter). Docs: this working doc + frontmatter → `done`; BACKLOG, PLAN §M10, 086 forward-note,
LESSONS.

### Verification sweep — EMPIRICAL OUTPUT
- **Proving test:** against `git show main:…/layers.py` (count) → **FAIL** (`assert 'app' not in
  ('app','config')`); against branch (mass) → **1 passed**. Empirical red→green.
- **Scoped (bare, Windows):** `pytest tests/test_onboarding_layers.py` → **19 passed**. `ruff` clean on all
  three changed files; 0 lines > 100.
- **AC2 real-repo run** (`scripts/docker-test.sh python scripts/layer_report.py` — cloned + indexed live
  via the PHP adapter):
  - **`laravel/laravel` @ ff031db — 26 modules, 9 layers. Sensible; F1 fixed.**
    `bootstrap(2) → config(10) → Http(1) → database(5) → public(1) → routes(2) → tests(3) → Models(1) → Providers(1)`
    `app/**` no longer collapses — it splits into `Http`/`Models`/`Providers` (dominant subtree now
    elected by mass, not by `config/`'s 10 files). No `app` layer remains.
  - **`symfony/demo` @ 03fe256 — 51 modules, 17 layers. No regression — byte-identical to 086.**
    `tests(12) → Command(3) → Controller(4) → EventSubscriber(4) → DataFixtures(1) → Security(1) → public(1) → (root)(2) → config(2) → Pagination(1) → Twig(3) → Event(1) → Form(7) → Utils(1) → src(1) → Repository(3) → Entity(4)`
  - **`brick/math` @ b61d8e6 — 32 modules, 5 layers. No regression — byte-identical to 086.**
    `tests(8) → (root)(2) → src(5) → Exception(10) → Internal(7)`
  - **Human judgement (maintainer-delegated):** all three architecturally sensible. laravel now separates
    application code (`app/**`) from framework scaffolding (`config`/`database`/`routes`/`bootstrap`/
    `public`/`tests`); symfony/brick unchanged from the assignments 086 already judged sensible. **AC2 met
    — not a recorded exclusion.**
- **Full Docker gate** (`scripts/docker-test.sh`): **1453 passed, 0 failed**, ruff clean, mypy **51 source
  files** (count-pin intact). **Delta-green** (no tests removed; one proving test renamed/retargeted).
- **Axis (file set):** `git diff` ⊆ approved change list; every hunk maps to a matrix row; 0 deviations.

## Phase 4 — review
`CHALLENGER: OFF` · `REVIEW: skipped` — both operator-waived (`with skipped review & challenger`). No
subagent dispatched; verification ran in the main loop and is recorded above (empirical red→green proving
test, three real-repo assignments, full Docker gate delta-green). Self-check against the ENGINEERING_RULES
pre-PR gate: R1.1 (no language branch — the signal is graph degrees), R2.2 (no directory stop-list — no
`config`/`vendor`/`tests` literal in core), R4.2 (deterministic `sorted(key=(-mass, name))` fold over
pre-sorted modules), R6.7 (`LAYER_METHODS` unchanged, still derived-pinned), comments ≤3 lines, lines ≤100.

## Post-PR review round — `/code-review #131` (main-loop, 0 dispatch)
The maintainer asked for a direct `/code-review` after the PR opened (review phase was waived at solve
time, so still 0 mango-dispatch). 4 findings, none a hard bug; all reproduced and dispositioned:
- **F1 (heuristic trade-off) — a hub dir with one very high-fan-in file could out-mass the source
  tree.** True, but "fixing" it is the deferred *rank-subtrees-above-a-threshold* successor, out of
  scope here. **Accepted + documented** as a known limitation (the count secondary softens only the
  tie region); the threshold approach remains the recorded successor if a real repo defeats mass.
- **F2 (regression) — an edgeless index elected the alphabetically-first dir instead of the old
  most-populous one.** **Fixed:** the mass tie-break now falls back to `-count`, then name
  (`sorted(key=(-mass, -count, name))`), so an all-zero-mass index reverts to pre-105 behaviour. New
  fixture+test `test_edgeless_index_falls_back_to_module_count_not_alphabetical` (green with the
  fallback; the alphabetical bug would fail it).
- **F3 (weak check) — `layer_report.py` had no assertions and always exited 0.** **Fixed:** it now
  carries a per-repo `_EXPECT` (require/forbid layer subsets), prints then **checks**, and exits
  non-zero on any miss — so a future collapse fails the run instead of needing a human eyeball. Verified
  in Docker: `all repos pass the layer check`, exit 0.
- **F4 (doc inconsistency) — the reporter docstring said "three times" while LESSONS said 5th.**
  **Fixed:** docstring now reads "five times (084, 103, 104, 086, 105)".

Post-fix: full Docker gate **1454 passed, 0 failed** (+1 edgeless test), ruff clean, mypy 51 files.

## Phase 5 — finalise

### Cost ledger (subagent dispatch only)
| Phase | Dispatch | Tokens | Result |
|---|---|---|---|
| — | (none) | — | review + challenger operator-waived; refine self-skipped; Explore/analysis in main loop |

`LEDGER TOTAL: 0 dispatch` — a run that dispatched 0 subagents ends with 0 rows. Main-loop unmeasured
(host surfaces no usage block). Ledger complete.

### Learning loop
`CLAIMS: 2 proposed | T1=1 T2=1 T3=0 T4=0 T5=0 T6=0`
- **[type 2, process · handle: `fixture-shape-begs-the-question` · seen: 084, 103, 104, 086, 105]** an
  authored fixture that mirrors the code's own assumption hides the very path-shape defect it purports to
  guard. **Now recurred a 5th time.** 105's durable countermeasure: a **committed, re-runnable real-repo
  reporter** (`scripts/layer_report.py`) so the real-repo check is no longer an ad-hoc session action.
  **Promotion candidate** (seen crosses ≥2 ticket keys → `/mango:promote` is the cross-ticket pass; the
  maintainer runs it between tickets).
- **[type 1, technical · handle: `elect-by-graph-mass-not-file-count` · seen: 105]** when a heuristic
  elects "the main subtree/module/group," weight by graph connectivity (Σ fan_in+fan_out), not by count —
  a flat, populous, disconnected directory (config, fixtures, generated code) otherwise out-votes the small
  connected core. **Proposed, not written** — awaiting ratification.
