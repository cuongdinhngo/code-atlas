---
id: 104
slug: onboarding-layer-signal
title: Onboarding — fix the layer collapse (F1): group beneath the dominant subtree (M10)
phase: 3
milestone: M10
status: done
depends_on: [103]
---

## Why this exists (the shipped defect, not a fresh guess)

Two iterations have now inferred "architectural layer" from the **shape of the file path**, and each
failed on real repos in the *opposite* direction:

- **084** grouped by the **deepest** parent dir → `app/Http/Controllers/Api/UserController.php` became a
  near-singleton layer `.../Api`. **Over-fragmentation.**
- **103** (PR #122, **merged 2026-08-18**) grouped by the **first segment past the longest common dir
  prefix**. Run against a real Laravel tree (8 classes under `app/**` **plus one** `routes/web.php`) it
  collapses the *entire application* into one layer `app`:

  ```
  layers: ('routes', 'app')
    app/Http/Controllers/Api/UserController.php -> 'app'
    app/Models/User.php                         -> 'app'
    app/Services/Billing.php                    -> 'app'   ← Http/Models/Services/Providers all == 'app'
    routes/web.php                              -> 'routes'
  ```
  A single top-level file outside `app/` (every real repo has `routes/`, `config/`, `public/`,
  `bootstrap/`, `database/`, `tests/`) empties the common prefix and flattens the architecture.
  **Under-fragmentation.** Drop the one outlier and it splits correctly — so the output is decided by an
  incidental file, not by architecture.

103 shipped this deliberately as **deterministic-but-limited scaffolding**: `assign_layers` has **no
consumer until 086** (`architecture_overview`, still `todo`), so the defect reaches nothing yet. This
ticket must land **before 086** (086 now depends on 104).

Full evidence + runnable reproduction: `today-i-learned/ai/how-to-create-mango-plugin/Retrospective/2026-08-18_mango-autorun-output-quality-1.md`
(finding F1).

## The signal is decided — this ticket implements it (not "decide again")

The earlier 104 draft asked *which signal a layer should come from at all*. That question has now been
answered empirically by a bake-off over 6 real-shape layouts (Laravel, deep-root `src/App/**`, a
`packages/*/src/**` monorepo, and the flat/2-deep cases 084/103 already covered). Do not re-open it
without new evidence — record the result as the design decision and implement it:

**Chosen — C1, "dominant-subtree".** Group modules **beneath the top-level directory that holds the most
modules** (the *dominant* subtree): strip the common prefix **within** that subtree and layer by its
first remaining segment; every **other** top-level directory becomes its **own** layer. This is the only
candidate that survived all 6 shapes — it splits `app/Http` · `app/Models` · `app/Services` while keeping
`routes/` as its own layer, and it does not collapse the deep `src/App/**` tree.

**Rejected (record in the design doc with these reasons):**
- **C0 — common-prefix + first segment (the shipped 103).** Collapses Laravel `app/**` the moment one
  top-level outlier file exists. This is the defect being fixed.
- **C2 — first-two-segments.** Collapses the deep `src/App/**` layout (everything becomes `src/App`).
- **Namespace declaration (PSR-4 `App\Http\…` from the qname).** Closer to the language's own structure,
  **but** qnames are language-specific, so the derivation would have to live in the adapter/contract,
  never a core branch (R1.1). Deferred: heavier, and C1 already produces the architectural grain from the
  path alone. Revisit only if C1 proves insufficient on the anchor repo (AC2).
- **Dependency topology (condensation / longest-path rank).** Most principled, heaviest; makes "layer"
  mean depends-on depth rather than lives-in dir. Deferred as a possible successor, not this ticket.

## Known residual to handle in this ticket
C1 leaves a **root-level file** (e.g. a top-level `config.php` whose directory prefix is empty) with an
empty-string layer name. Assign it an explicit `"(root)"` layer rather than emitting `""`. Add a fixture
for it.

## Acceptance criteria
- **AC1 (design gate)** — the signal decision above is recorded in the design phase (chosen C1 + the four
  rejected alternatives with why), consistent with R1.1 (no language branch in the core) and R4.2
  (determinism). No grouping code changes before the design gate closes.
- **AC2 (the real-input gate — this is the point)** — the C1 implementation is proven on a **real indexed
  repo** (the anchor PHP monorepo the plan already names), **not** a hand-built fixture. Record the actual
  layer assignment produced and a human judgement that it is architecturally sensible. A green unit suite
  over authored fixtures is **explicitly insufficient** — that is exactly what hid both 084's and 103's
  defects (retro F1). **If the anchor repo is unavailable this session, AC2 is a recorded manual-check
  exclusion and the ticket is `blocked`, not silently passed.**
- **AC3 (regression fixtures)** — add, as unit fixtures *in addition to* AC2, the bake-off shapes that
  broke C0/C2: (a) real Laravel `app/**` + `routes/web.php` does **not** collapse into one `app` layer;
  (b) the deep `src/App/**` tree still splits into Http/Domain/Infra; (c) a `packages/*/src/**` monorepo
  keeps each package distinct; (d) the root-level-file `"(root)"` rule. Fixture coverage alone never
  closes AC2.
- **AC4 (invariants preserved)** — determinism / byte-stability (R4.2), language-agnostic core
  (R1.1/R1.5/R2), the derived-not-listed `LAYER_METHODS` guard (R6.7), comments ≤3 lines, lines ≤100
  chars. The direction-fallback path (flat namespaces) is unchanged.

## Relationship to 103 / PR #122
PR #122 is **merged**. 103 is `done` with a documented known-limitation note pointing here. 104 **replaces
`assign_layers`'s grouping** (the dominant-subtree derivation) rather than extending the direction
fallback. There is no production urgency — nothing calls `assign_layers` until 086 — but 104 is a hard
dependency of 086 so the collapse is fixed before any consumer exists.

## Out of scope
- LLM layer-name refinement (091). 083 metrics substrate (unchanged). The Summarizer seam (085).
- Namespace-declaration and dependency-topology signals (recorded as deferred alternatives above).

## References
- Retro F1 (runnable repro): `.../Retrospective/2026-08-18_mango-autorun-output-quality-1.md`.
- `code_atlas/onboarding/layers.py` (`assign_layers`, `_common_dir_prefix`, `_group_key`, `_by_prefix`).
- 084 `docs/tasks/084_onboarding-layer-assignment.md`; 103 `docs/tasks/103_onboarding-layer-granularity.md`;
  086 `docs/tasks/086_architecture-overview-tool.md` (the gated consumer).
- PLAN §14, §15 (M10). R1.1/R1.5/R2 (language-agnostic core), R4.2 (determinism), R6.7 (derived-not-listed).

## Session status
- **Runner:** `/mango:autorun 104 --no-challenger` (unattended lifecycle, stops at the PR; challenger OFF).
- **Handover authorisation:** the two outward actions (push branch, open PR) are covered by the
  maintainer's standing durable approval in `AGENTS.md` (*Maintainer workflow*) plus the explicit
  `/mango:autorun 104 --no-challenger` invocation. Recorded verbatim in `.mango/run-contract-104.txt`.
- **Envelope:** RUN CONTRACT written + validated at t0 and bound at Gate 2; RECONCILE t0 clean (2 BROKEN
  bound floor conditions, 2 UNBOUND — TREE-COMPARISON + PROVING-TEST, 0 holding → no strikes).
  Merge-strategy: squash-or-rebase (27 first-parent commits since newest merge; narrows not removes).
  Call-ceiling: **unknown** (no token budget supplied — recorded, not invented). Windows note: floor
  POSIX checks wrapped in `bash -c`.
- **Outcome — `blocked` on AC2, by the ticket's own rule.** The C1 dominant-subtree implementation +
  **AC1** (design gate), **AC3** (four regression fixtures), **AC4** (invariants) have all landed and are
  delta-green. **AC2 — the real anchor-repo proof, "this is the point" — is unmet: the anchor PHP
  monorepo is unavailable this session.** Per the ticket AC2, that makes AC2 a **recorded manual-check
  exclusion** and the ticket **`blocked`, not silently passed**. It is not `done`.
- **Next action (maintainer):** (1) review & merge **PR [#123](https://github.com/cuongdinhngo/code-atlas/pull/123)** (squash — the F1 fix is correct and green); (2) run the
  AC2 anchor-repo check — index the anchor monorepo, capture the actual layer assignment, record a human
  judgement that it is architecturally sensible — then flip 104 → `done`. **086 must not start until AC2
  clears** (086 depends on 104).
- **Revert path:** unmerged → close the PR + `git push origin --delete feat/104-onboarding-layer-signal`.
  Merged → revert the single squash-merge commit on `main` (no schema/contract/tool change to undo).
- **work_doc_mode:** embed. **Branch:** `feat/104-onboarding-layer-signal`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: S` · `TIER: full`.

## Phase 0 — refine (self-skipped)
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved | 0 ASSUMED | skip: yes`

104 pre-decides the signal: the ticket names the chosen approach (**C1 dominant-subtree**) and records
the four rejected alternatives (C0, C2, namespace-declaration, dependency-topology) *with reasons*, plus
the residual `"(root)"` rule and the exact AC3 fixtures. There is no open product-decision, so refine
self-skips and `j` is untouched (Gate 0 clear). The one contingency — AC2 anchor-repo unavailability — is
**not** a want-decision: the ticket itself pre-resolves it ("recorded manual-check exclusion; ticket
`blocked`"), so it is a recorded exclusion, not an unresolved clarification, and does not stop the run.

## Phase 1 — analysis
`SECTIONS: 6 found (Why, Signal-decided, Residual, Acceptance criteria, Out of scope, References) | 6 decomposed | ROWS: C≈4 R=1 G=1 AC=4`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Status |
|---|---|---|---|---|
| G1 | Signal-decided | Replace `assign_layers`'s grouping with **C1 dominant-subtree** | Group beneath the top dir holding the most modules; others each own layer | ✅ done |
| R1 | Residual | A root-level file (empty dir prefix) → explicit `"(root)"`, never `""` | `_layer_of` returns `_ROOT_LAYER` when `not dirs` | ✅ done |
| AC1 | AC | Design gate: chosen C1 + 4 rejected recorded; R1.1 + R4.2 consistent; no grouping code before it | Phase-2 design below records the decision | ✅ done |
| AC2 | AC | **Real anchor-repo proof** (not a fixture); human judgement it is sensible. Anchor unavailable → recorded exclusion + `blocked` | Anchor monorepo not available this session | ⛔ **recorded exclusion** |
| AC3 | AC | Regression fixtures: (a) Laravel `app/**`+`routes/` no-collapse; (b) deep `src/App/**` splits; (c) `packages/*/src` distinct; (d) `"(root)"` | Four unit fixtures added | ✅ done |
| AC4 | AC | Invariants: determinism/byte-stability (R4.2), language-agnostic (R1.1/R1.5/R2), derived-not-listed (R6.7), comments ≤3, lines ≤100; fallback unchanged | All held; fallback (`_by_direction`) untouched | ✅ done |

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision` — `j = 0`. AC2's exclusion is
ticket-authored, not an open clarification. Gate 0 clear → autorun proceeds.

### Blast radius
- **Modified:** `code_atlas/onboarding/layers.py` (grouping helpers `_top_dir`/`_dominant_subtree`/
  `_layer_of`/`_by_group`, `_ROOT_LAYER`, `LAYER_METHODS`, `assign_layers`, header docstring);
  `tests/test_onboarding_layers.py` (method-label flips, boundary test rewrite, AC3 fixtures + tests,
  determinism-at-boundary test). `docs/BACKLOG.md` (status + token row + F1→104 note; **also fixed 103's
  unparseable status cell**, see below). `docs/tasks/104_...md` (this working doc + frontmatter).
- **Untouched:** `metrics.py`, `store.py`, `main.py`, `contract.py`, adapters, resolver. **No count-pin
  change** — module count stays 44; `test_sql_confinement.py` / `test_core_is_language_agnostic.py`
  untouched.
- **Scope-adjacent fix (disclosed):** commit `6f70590` on `main` set 103's BACKLOG status cell to
  `done (F1 known — see 104)`, which the `TASK_ROW` regex in `test_backlog_bookkeeping.py` cannot parse
  (`[a-z-]+`), so the full Docker gate was **already red on `main`** (2 failures). Since 104 edits
  `BACKLOG.md` anyway, the cell is cleaned to a bare `done` (the F1→104 pointer moved to prose); this
  turns those 2 pre-existing reds green. Not a code change; recorded in DISCLOSURE.

### Baseline
`BASELINE: red on main — 2 failed (bookkeeping) / 1305 passed` in Docker, both failures the unparseable
103 status cell above (not this ticket's subject). Scoped pure-Python baseline for the layer modules is
green. DoD = the delta is green, with those 2 pre-existing reds fixed by the BACKLOG cleanup.

### Declarations
`STRUCTURE: native` · `SCOPE: S` · `TIER: full` · `TRACK: backend` — one source file + its test file +
docs; no new module, no count-pin, no contract change. `TIER: full` (revises a merged/locked output
contract, 103), routed through the full flow (challenger waived by the operator flag).

## Phase 2 — design

### Approach (records AC1 — the signal decision)
**Chosen: C1 "dominant-subtree".** In `assign_layers`, find the top-level directory holding the most
modules (`_dominant_subtree`, ties broken by name for determinism). For a module **inside** that subtree,
strip the within-subtree common prefix (`_common_dir_prefix` over the subtree slice) and take the first
remaining segment; a module sitting directly in the dominant dir takes the top-dir name. Every **other**
top-level directory becomes its own layer (its top-dir name). A module with **no** directory prefix takes
the explicit `_ROOT_LAYER = "(root)"`. Groups are ordered by net dependency direction (`_by_group`,
unchanged from 103's `_by_prefix`). The pure **dependency-direction fallback** (`_by_direction`) fires
only when `dominant is None` (all root files) or < 2 named groups result — flat legacy is unchanged.
Method label `common-root-segment` → `dominant-subtree` (`LAYER_METHODS` + the emitted literal + the
derived-not-listed pin move together, R6.7).

### Rejected alternatives (recorded per AC1)
- **C0 — common-prefix + first segment (the shipped 103).** One top-level outlier file empties the
  common prefix, collapsing all of Laravel `app/**` into a single `app` layer. **This is the F1 defect
  being fixed.**
- **C2 — first-two-segments.** Collapses the deep `src/App/**` layout (everything becomes `src/App`).
- **Namespace declaration (PSR-4 from the qname).** Closer to the language's structure but qnames are
  language-specific, so the derivation would have to live in the adapter/contract, never a core branch
  (R1.1). Deferred: C1 already yields the architectural grain from the path alone. Revisit only if C1
  proves insufficient on the anchor repo (AC2).
- **Dependency topology (condensation / longest-path rank).** Most principled, heaviest; redefines
  "layer" as depends-on depth. Deferred as a possible successor, not this ticket.

### Determinism argument (R4.2)
`_dominant_subtree` tie-break is an explicit `sorted(key=(-count, name))`; `_common_dir_prefix` is an
order-independent segment-wise fold; `_by_group` orders by `sorted(key=(-net, name))`; `assign_layers`
receives `metrics.modules` already sorted by `_grain`. No set-iteration or wall-clock leak.

### Smallest change-list
| # | Change | File | Covers |
|---|---|---|---|
| 1 | `_top_dir`, `_dominant_subtree`, `_layer_of`, `_by_group` (rename of `_by_prefix`); remove `_group_key` | `layers.py` | G1, R1, AC4 |
| 2 | `assign_layers` uses dominant-subtree grouping; fallback trigger `dominant is None or <2 groups` | `layers.py` | G1, AC4 |
| 3 | `_ROOT_LAYER`; `LAYER_METHODS` + emitted method → `dominant-subtree`; header docstring | `layers.py` | R1, AC1, AC4 |
| 4 | Flip method assertions; rewrite the boundary test for C1; AC3 fixtures + 4 tests; determinism-at-boundary test | `tests/test_onboarding_layers.py` | AC1, AC3, AC4 |

### Verification plan (per-AC)
| AC | risk | proof | layer-match |
|---|---|---|---|
| AC1 | logic | design record above (chosen + 4 rejected) | ✅ |
| AC2 | integration (real repo) | **⛔ recorded manual-check exclusion — anchor repo unavailable** (`expiry:` below) | n/a this session |
| AC3 | logic | unit fixtures (a)/(b)/(c)/(d), each one assertion set | ✅ |
| AC4 | logic | determinism (pipeline + boundary tie-break), ruff/mypy/line-length, unchanged fallback tests | ✅ |

**AC2 exclusion (Gate-2, ticket-pre-approved):** `expiry:` the next anchor-repo indexing session — 086 is
hard-blocked on 104 and must not start until this clears. This is the ticket's own rule, not a waiver
invented here.

### Proving test (logic layer)
`test_dominant_subtree_does_not_collapse_laravel_app_into_one_layer` — 8 classes under `app/**` plus one
`routes/web.php`; asserts `"app" not in layers`, `{Http,Models,Services,Providers,Console} ⊆ layers`,
`routes` present. **Red pre-change** (C0 emits a single `app` layer — empirically reproduced against
`main:layers.py`), **green post-change**. Invocation:
`python -m pytest tests/test_onboarding_layers.py -k dominant_subtree_does_not_collapse -q`.

## Phase 3 — execute

### Implemented (approved change list only)
`layers.py`: replaced C0 grouping with C1 dominant-subtree (`_top_dir`/`_dominant_subtree`/`_layer_of`/
`_by_group`); `_ROOT_LAYER`; `LAYER_METHODS` + emitted method renamed; header docstring. `_by_direction`
fallback untouched. Tests: method-label flips (4), boundary test rewritten for C1, AC3 fixtures (a–d) +
tests, byte-stability over Laravel, and a determinism-at-boundary probe (added in review). Docs: BACKLOG
status/token/note + 103 status-cell fix; this working doc + frontmatter → `blocked`.

### Verification sweep — EMPIRICAL OUTPUT
- **Proving test:** pre-change (`git show main:…/layers.py`) → **FAIL**; post-change → **1 passed**.
- **Scoped (bare, Windows):** `pytest test_onboarding_layers.py test_sql_confinement.py
  test_core_is_language_agnostic.py` → **111 passed**; strengthened `test_onboarding_layers.py` alone →
  **19 passed**. `ruff` clean, `mypy` clean, 0 lines > 100.
- **Full Docker gate** (`scripts/docker-test.sh`, read directly): **1308 passed, 0 failed**, ruff clean,
  mypy 44 files. `main` was **red** (2 bookkeeping failures from 103's unparseable status cell); this
  branch fixes them and adds 6 onboarding tests, none removed. **Delta-green.**
- **Axis (file set):** `git diff` ⊆ approved change list; every hunk maps to a matrix row; 0 deviations.

## Phase 4 — review
`CHALLENGER: OFF` (waived by `--no-challenger`; first line of DISCLOSURE). One subagent, ref-based
read-only on `main...HEAD`.

- **`mango:reviewer`** (Sonnet — cost_tier standard; diff touches no auth/access/schema) → **LGTM**, no
  Critical/Important. Verified directly: `pytest` 18 passed (pre-strengthening), `mypy --strict` clean,
  `ruff` clean, grep for dir/framework literals in runtime code → none (data-derived), no line > 100 / no
  comment block > 3. Traced every edge shape (single/tie/deep/packages/root-file/boundary/all-root/single
  module) → no empty-string layer, no `KeyError`; confirmed the `dominant or ""` coercion is safe because
  `_dominant_subtree` returns `None` only when every module is a root file (then `_layer_of` short-circuits
  before comparing `dominant`).
- **Non-blocking observation acted on:** the byte-stability test shuffled `compute_metrics`'s **input**,
  but `_grain` sorts modules before `assign_layers`, so it could not observe order-dependence inside the
  new code (lesson-009 proof-strength gap, inherited from 103). **Fixed** in commit `bf1bea2`: added
  `test_dominant_subtree_tie_break_is_order_independent_at_the_assign_boundary`, which shuffles the
  `modules` tuple at the `assign_layers` boundary on a **count-tie** fixture whose output depends on the
  `(-count, name)` tie-break — so a buggy insertion-order tie-break would now be caught.

### Clean decision
Clean: reviewer LGTM, no Critical/Important; the one observation improved beyond a finding; `diff ⊆
approved list`; proving test green; every AC met **except AC2**, which is the ticket-pre-approved recorded
manual-check exclusion (→ status `blocked`, not `done`). `Reviewed at 3459ff5` + verify-only re-run after
`bf1bea2` (test-only, main-loop, no re-dispatch) → 19 passed, ruff/mypy clean.

## Phase 5 — finalise

### Cost ledger (subagent dispatch only — main-loop unmeasured on this host)
| Phase | Dispatch | Tokens | Tool-uses / s | Result |
|---|---|---|---|---|
| review | `mango:reviewer` (Sonnet) | 91.8k | 21 / 401s | **LGTM**, no Critical/Important; 1 non-blocking note (acted on) |

`LEDGER TOTAL: 91.8k dispatch · sole driver: review/reviewer`. Challenger **waived by `--no-challenger`**
(0). refine **self-skipped** (0 unresolved) → no exposure-checker dispatch. Analysis Explore fan-out done
in the main loop (session standing instruction) — disclosed, not silently skipped. Main-loop
**unmeasured** (host surfaces no usage block). Ledger complete: 1 dispatch, 1 row, token cell filled.

### Learning loop
`CLAIMS: 1 proposed | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0` — **[type 2, process · handle:
determinism-test-observability · seen: 104]** a byte-stability test that shuffles a *pre-sorted*
pipeline's input cannot observe order-dependence in the stage under test; shuffle at the stage boundary.
Recurs with 103's equivalent test (the reviewer flagged both). **Proposed, not written** — awaiting
maintainer ratification.

## AC2 resolved — 2026-08-23, and the verdict on C1 is negative

104 parked at `blocked` because AC2 needed a **real indexed repo** and the anchor PHP monorepo was
unavailable that session. It is still unavailable. AC2 is discharged anyway, by two things that did
not exist when this ticket was written:

**1. The real-repo run happened — in 105 — and it refuted this ticket's own C1.** 105 ran
dominant-subtree against `laravel/laravel` at the SHA already pinned in
[`scripts/cross_repo_samples.json`](../../scripts/cross_repo_samples.json) and found the dominant
subtree was **`config/` (10 modules)**, not `app/` (3) — collapsing the application into one `app`
layer, *the exact F1 shape 104 existed to fix*. So AC2's real-input gate ran, and **C1 as 104 shipped
it failed it.** 105 replaced the file-count tie-break with graph mass; 110 replaced path-segment names
with responsibility names. **This ticket closes because its deliverable landed and its gate now
exists — not because C1 was vindicated.** 104's own AC3 fixture (a) is what hid the defect (it
authored 8 classes under `app/**` so `app/` could not lose the count); the fixture in the tree today
is 105's replacement, and it is labelled `105 / AC3(a)`.

**2. The human eyeball AC2 asked for has been replaced by a committed assertion**, which is strictly
stronger: [`scripts/layer_report.py`](../../scripts/layer_report.py) clones, indexes and **asserts**
the invariant per pinned repo, because authored fixtures had by then hidden a path-shape layer defect
**five times** (084, 103, 104, 086, 105 — retro `fixture-shape-begs-the-question`).

### Recorded assignment at HEAD (`b277f1a`), `scripts/layer_report.py`, Linux host

```
### laravel_app @ ff031db
  method=responsibility  layers=5  uncategorised=6/26 (23%)
  Config / Migration(13) → HTTP / Entry(3) → Tests(3) → Uncategorised(6) → Domain / Data(1)

### symfony_demo @ 03fe256
  method=responsibility  layers=7  uncategorised=18/51 (35%)
  Uncategorised(18) → HTTP / Entry(8) → Tests(6) → Views(8) → Config / Migration(2)
  → Shared Library(2) → Domain / Data(7)

### brick_math @ b61d8e6
  method=responsibility  layers=2  uncategorised=24/32 (75%)
  Tests(8) → Uncategorised(24)

all repos pass the layer check
```

**Human judgement (AC2's second half).** Architecturally sensible on the two app-shaped repos: no
collapsed `app` layer anywhere, controllers land in *HTTP / Entry* and models/entities in
*Domain / Data*, and `config/` is now **one layer named for what it is** rather than the winner that
swallows the application — F1 and 105's defect are both absent. `brick_math` at 75 %
*Uncategorised* is **correct, not a miss**: a pure arbitrary-precision math library has no web or
domain roles to surface, and `layer_report.py`'s `_EXPECT` records that as the expected shape. The
honest limitation, stated rather than hidden: these are three small pins (26 / 51 / 32 modules), so
this is evidence the rule does not collapse on real trees — **not** evidence about a 112k-file
monorepo. That remains untested, and is the same gap 074 carries.

### AC status at close
| AC | State | Evidence |
|---|---|---|
| AC1 design gate | ✅ | C1 + four rejected alternatives recorded, PR [#123](https://github.com/cuongdinhngo/code-atlas/pull/123) |
| AC2 real-input gate | ✅ **with a negative verdict on C1** | 105's `laravel/laravel` run refuted C1; `layer_report.py` green at HEAD, readout above |
| AC3 regression fixtures | ✅ | `tests/test_onboarding_layers.py` — (a) at :431 *(105's replacement)*, (b) :447, (c) :458, (d) :469 |
| AC4 invariants | ✅ | R4.2 byte-stability :481 + shuffled-input :490; `LAYER_METHODS` derived-not-listed guard; 49 layer tests green |

### Two ticket assumptions overtaken by events
- *"086 must not start until AC2 clears"* — 086 shipped 2026-08-18 and so did 105/110/111–117. The
  ordering constraint was overtaken; what protected 086 in the end was 105 catching the defect on
  real input, not this gate holding the queue.
- *"the anchor PHP monorepo the plan already names"* — the project has since built a **pinned public
  sample tier** (042) which is the substitute AC2 lacked. It is smaller, and the paragraph above says
  so instead of letting the pass imply monorepo coverage.

**No code change in this ticket** — the implementation it verifies is already in `main` via 105/110.
