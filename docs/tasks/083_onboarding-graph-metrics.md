---
id: 083
slug: onboarding-graph-metrics
title: Onboarding — deterministic graph-metrics foundation (M10)
phase: 3
milestone: M10
status: done
depends_on: [014, 031, 017]
---

## Goal
The deterministic, read-only graph-metrics substrate Phase-3 onboarding builds on: fan-in / fan-out,
the entry-point set, and a dependency-direction summary that layering (084), the tour (087) and
summaries (085) all consume. No new tool surface here.

## Scope / Deliverables
- New `code_atlas/onboarding/metrics.py` — pure functions; **no SQL** (calls new read-only `GROUP BY`
  aggregate method(s) added to `store.py`, per R1.4 / `test_sql_confinement`).
- **Module unit = file path**, per-symbol = qname (locked 2026-08-11).
- **Entry-point = zero-inbound roots** — pure, deterministic, no config knob (locked).
- **SCC / cycle membership is out of scope** — deferred to 087 with its own node budget (locked;
  keeps 083 R4.3-clean).
- No language branches; graph shape + generic strings only (R1.1).

## Acceptance criteria
- Metrics compute over the anchor PHP index and are **byte-stable across two runs** (R4.2); anchor-repo
  run is a recorded local manual check.
- No PHP-specific logic — proven by the existing CI grep-gate (`tests/test_core_is_language_agnostic.py`).
- Unit tests over a fixture graph (including one cycle → a `mixed`-direction node) assert exact
  fan-in/out, the entry-point set, and the direction summary.

## References
[`../phase3-onboarding/ROADMAP.md`](../phase3-onboarding/ROADMAP.md) §3–§4 (M10, locked);
PLAN §14, §15 (M10). Reuses `store.py` traversal (`reachable_from`, `impact_radius`, `find_orphans`).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 083

## Session status
- **Runner:** `/mango:autorun 083 --no-challenger` (unattended lifecycle, stops at the PR).
- **Handover authorisation:** the two outward actions (push branch, open PR) are covered by the
  maintainer's standing durable approval in `AGENTS.md` (*Maintainer workflow*). Recorded in
  `.mango/run-contract-083.txt`.
- **Envelope:** RUN CONTRACT written + validated at t0; RECONCILE t0 clean (2 BROKEN bound floor
  conditions, 1 UNBOUND TREE-COMPARISON, 0 holding → no strikes). Merge-strategy: squash-or-rebase.
  Call-ceiling: **unknown** (no token budget supplied — recorded, not invented).
- **Phase:** 4 review — **complete; Gate 4 clean (reviewer only — CHALLENGER: OFF)**. Reviewer LGTM,
  no findings. Branch Docker gate 1283 passed. `Reviewed at ade9dbf`. Proceeding to finalise once the
  `main` baseline gate (worktree) returns the exact delta.
- **work_doc_mode:** embed. **Branch:** `feat/083-onboarding-graph-metrics`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.

## Phase 0 — refine (skipped)

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 1 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

- **Premise (all resolve):** `code_atlas/store.py` (+ `reachable_from`/`impact_radius`/`find_orphans`),
  `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py`,
  `docs/phase3-onboarding/ROADMAP.md`, `docs/PLAN.md`. To-be-created (not missing):
  `code_atlas/onboarding/metrics.py`.
- **Skip rationale:** every product-decision is locked — module unit = file path, entry-point =
  zero-inbound roots, SCC out of scope (ticket, "locked 2026-08-11"); layering direction per
  PHASE3 §4. No acceptance-bar want survives (AC1's anchor-repo check is defined by the ticket as a
  *recorded local manual check*). Per the skip rule the 1-dispatch exposure-checker does not run.
- **Recalled (advisory, blocks nothing):** `derived-not-listed-invariant` (by handle — if a guarded
  enumeration of direction labels is added, derive it, don't list it); store/impact-area type-5 claims
  100-C5 / 102-C3 (by area). **Scan constraint (high-value):** the 072 lesson — a new core module
  breaks the `len(core_modules()) == 41` pins in `test_sql_confinement.py:32` and
  `test_core_is_language_agnostic.py:42`; execute must bump the count.

## Phase 1 — analysis

Premise + recall carried forward from Phase 0 (not re-run):
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 1 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

### Decompose
`SECTIONS: 4 found (Goal, Scope/Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=3 (References = context)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | Deterministic read-only graph-metrics substrate (fan-in/out, entry-point set, direction summary) for 084/085/087; **no new tool surface** | A compute layer only; no MCP tool, no `main.py` change | `code_atlas/onboarding/` absent; PHASE3 §4 (locked) | ✅ |
| R1 | Scope | New `code_atlas/onboarding/metrics.py` — **pure functions** | Create `onboarding/` package + pure metric fns consuming store dicts | onboarding/ to-be-created | ✅ planned |
| R2 | Scope | New **read-only `GROUP BY` aggregate method(s)** added to `store.py` | fan-in (`GROUP BY target_qname`), fan-out (`GROUP BY source_qname`) over resolved edges | edges schema `store.py:85-91` | ✅ planned |
| R3 | Scope | **Entry-point = zero-inbound roots** — pure, deterministic, **no config knob** | qnames never appearing as a resolved `target_qname` | `idx_edges_tgt` | ✅ |
| C1 | Scope | metrics.py has **NO SQL** (R1.4 / `test_sql_confinement`) | SQL confined to store.py; metrics.py imports no sqlite | `test_sql_confinement.py:26` | ✅ |
| C2 | Scope | **Module unit = `file_path`; per-symbol = `qname`** (locked) | Two grains; module aggregates map qname→file_path via `nodes` | `nodes.file_path`/`qualified_name` `store.py:76-80` | ✅ |
| C3 | Scope | **SCC / cycle membership OUT of scope** (deferred to 087) | No SCC/Tarjan; a cycle still yields per-node degrees | ticket (locked) | ✅ exclusion |
| C4 | Scope | **No language branches**; graph shape + generic strings only (R1.1) | No `if language==`; edge kinds are contract vocabulary, not language names | `test_core_is_language_agnostic.py` | ✅ |
| AC1 | AC | Metrics **byte-stable across two runs** (R4.2); anchor-repo run = **recorded local manual check** | (a) determinism falsifiable on a fixture; (b) anchor-index run = manual-check exclusion | R4.2 | ⏳ split — see AC validation |
| AC2 | AC | **No PHP-specific logic** — proven by existing CI grep-gate | Existing gate + **count-pin bump 41→43** (072 collateral) | `test_core_is_language_agnostic.py:42` | ✅ planned |
| AC3 | AC | Unit tests over a **fixture graph** (incl. one cycle → a **`mixed`** node) assert **exact fan-in/out, entry-point set, direction summary** | The proving test; multi-clause → one proof row per clause at design | — | ⏳ proving test (design) |

### AC validation (falsifiability)
- **AC1(a) byte-stability** — falsifiable: compute metrics twice over the same fixture index, assert byte-identical serialisation (R4.2, deterministic `ORDER BY`). ✅ falsifiable.
- **AC1(b) "over the anchor PHP index"** — **not runnable here** (needs the private anchor repo). Recorded as an **explicit manual-check exclusion** (coverage-gap), same shape as 074/AC1 — a human runs it and records byte-stability on the anchor. Not a bare `✅`.
- **AC2** — falsifiable by the existing `test_core_is_language_agnostic.py` grep-gate. **Collateral (072 lesson):** the `len(core_modules()) == 41` pin in `test_sql_confinement.py:32` **and** `test_core_is_language_agnostic.py:42` becomes **43** (`core_modules()` = `sorted(code_atlas/**/*.py)`; +`__init__.py` +`metrics.py`).
- **AC3** — falsifiable (the unit tests). **Multi-clause, one proof row per clause (Gate 1 split):** (i) exact fan-in, (ii) exact fan-out, (iii) exact entry-point set, (iv) direction summary incl. the cycle→`mixed` node.

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`j = 0` — Gate 0 already cleared by the refine skip; every product-decision is locked (ticket + PHASE3 §4). No mismatch between a stated and a computed acceptance value.

### Universal inventory
R1.1 "no language branches" / AC2 "no PHP-specific logic" are universal but **covered by the existing CI grep-gate** (`test_core_is_language_agnostic.py`), not a per-item checklist. N (new core modules) = 2. No other "for each of N" requirement.

### Cause / gap (enhancement)
Gap: no graph-metrics layer exists (`code_atlas/onboarding/` absent). `store.py` has traversal (`reachable_from:1154`, `impact_radius:995`, `find_orphans:1349`) but **no fan-in/out `GROUP BY` aggregate and no zero-inbound query**. Target: `onboarding/metrics.py` (pure) + read-only aggregate(s) in `store.py`.

### Blast radius
- **New:** `code_atlas/onboarding/__init__.py`, `code_atlas/onboarding/metrics.py`, `tests/test_onboarding_metrics.py`.
- **Modified:** `code_atlas/store.py` (+read-only `GROUP BY` aggregate method(s)); `tests/test_sql_confinement.py:32` + `tests/test_core_is_language_agnostic.py:42` (count pin 41→43).
- **Untouched:** `main.py` (no tool surface — G1), `contract.py` (no vocab change — R3 N/A), adapters, resolver.
- Repos: `app` (single). No DB-map. No schema/migration.

### Baseline
`BASELINE: green (Docker full gate ~1268 on `main` at #117); bare Windows `pytest` is red by the documented platform exclusion (fcntl + PHP-adapter subprocess, AGENTS.md) — NOT a regression`
Definition of done = **prove delta-green via `scripts/docker-test.sh`** (new tests pass, +0 new failures, count pin updated). Delta measured in execute/finalise.

### Rule-compliance coverage
`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ · R4/R4.2 (change-type) ✅ · R1.2 (change-type) ✅ · R3 (change-type) N/A · R2 (change-type) N/A · R6.7 (recalled handle, PROVISIONAL) ✅`
- **R1.1** — new core module: metrics.py uses graph shape + generic edge-kind strings (contract vocabulary), no `if language==`; gated by `test_core_is_language_agnostic.py`. ✅
- **R1.4** — SQL only in store.py (new aggregates there); metrics.py imports no sqlite; gated by `test_sql_confinement.py`. ✅
- **R4 / R4.2** — pure functions + deterministic `ORDER BY` in the aggregates → identical input, byte-identical output (AC1). ✅
- **R1.2 (YAGNI)** — no registry/base-class/DI; just pure fns + store methods, one seam. ✅
- **R3** — **N/A**: no contract vocabulary/qname change, no new edge kind, `contract.py` untouched.
- **R2** — **N/A**: metrics encode graph-theory (fan-in/out, roots), not any repo's names/framework.
- **R6.7 (PROVISIONAL, recalled handle `derived-not-listed-invariant`)** — if the direction-label set is pinned by a test, the test must **derive** the labels from the source module, not hard-list them. Surfaced (provisional → does not gate-block); design will honour it if a label enumeration is introduced. ✅ answered.
- **Comments ≤3 lines** — honoured in new code. **P4 (AGENT_BRIEF, process):** re-run the R1.1 grep-gate after the *last* commit (100-C3 lesson) — an execute-time step.

### Declarations
`STRUCTURE: native` · `TRACK: backend — 0/6 touched files under UI paths` · `SCOPE: M` · `TIER: full`

## Phase 2 — design

### Approach
**metrics.py owns all graph logic as pure functions; store.py supplies read-only pulls via `GROUP BY`.**
- **store.py** (SQL boundary, R1.4) adds read-only aggregate methods:
  - `dependency_edges()` → distinct resolved dependency pairs: `SELECT source_qname, target_qname FROM
    edges WHERE target_qname IS NOT NULL AND source_qname <> target_qname GROUP BY source_qname,
    target_qname ORDER BY source_qname, target_qname` (deterministic; R4.2).
  - `node_universe()` → `(qualified_name, file_path)` for every node (the node set + qname→module map),
    `GROUP BY qualified_name, file_path ORDER BY …`.
- **metrics.py** (pure, **no SQL**, R1.4/C1) — `compute_metrics(nodes, edges)` takes plain Python data
  (a `(qname, file_path)` sequence + a `(src_qname, tgt_qname)` iterable) and returns a deterministic
  `GraphMetrics`:
  - **fan-out/fan-in** = distinct-neighbour degree per qname (symbol grain) and per file_path (module
    grain, endpoints mapped through the node→file map, same-module edges excluded).
  - **entry-point set** = qnames with **in-degree 0** over the node universe (R3, zero-inbound roots).
  - **direction summary** = a label per node/module from `(in, out)`; label set exported as
    `DIRECTION_LABELS = ("source", "sink", "mixed", "isolated")` — `source` (in=0, out>0), `sink`
    (in>0, out=0), `mixed` (in>0, out>0), `isolated` (in=0, out=0). The ticket names `mixed`.
- **Dependency edge = any resolved edge** (`target_qname IS NOT NULL`), self-loops excluded — **no kind
  allowlist** → pure graph shape, R1.1-clean. `ALIASES` bookkeeping carries `target_raw` not
  `target_qname` (`store.alias_targets`), so it drops out with **no kind branch**.

This split makes AC3's fixture-graph unit tests **DB-free** (feed `compute_metrics` a synthetic graph),
while the ticket's "`GROUP BY` aggregate method(s) in store.py" requirement is met by the two pulls.

### Rejected alternatives
1. **Count degrees in store via `GROUP BY source_qname` / `target_qname`** (store owns the counting) —
   rejected: it forces AC3's "fixture graph" tests to build a real index/DB (Docker-only, heavier
   fixtures) for what is pure arithmetic. Pulling distinct pairs + counting in pure metrics.py keeps the
   proving test at the logic layer where the requirement actually lives.
2. **Hardcode a dependency edge-kind allowlist** (e.g. `{CALLS, EXTENDS, …}`) — rejected: an arbitrary
   list in a core module reads as a language/heuristic seam and risks R1.1/R2 optics; the
   `target_qname IS NOT NULL` filter is the generic, defensible definition and excludes `ALIASES` for
   free.
3. **Compute SCC / cycle membership now** — rejected: explicitly out of scope (ticket, locked; deferred
   to 087 with its own node budget). A cycle still yields correct per-node degrees and a `mixed` label —
   which is exactly what AC3 tests.

### Assumptions
- **A1 (verified):** resolved dependency edges carry `target_qname`; `ALIASES` carry `target_raw`, not
  `target_qname` — so `WHERE target_qname IS NOT NULL` excludes bookkeeping with no kind branch. Source:
  `store.alias_targets` reads `source_qname, target_raw FROM edges WHERE kind='ALIASES'`.
- **A2 (verified):** a qname can map to >1 `file_path` (duplicate/ambiguous decls, 070/043 — `nodes`
  `UNIQUE(qualified_name, file_path)`). Module rollup maps each endpoint qname to its **set** of files
  and dedupes module pairs deterministically — no crash, no nondeterminism.
- **No novel-untested 3p/runtime assumption.** Determinism is proven directly by the AC1(a)
  byte-stability unit test (compute twice → identical); no spike needed.

### Smallest change-list
| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | New empty package marker | `code_atlas/onboarding/__init__.py` | +1 core module → count pin (#4) | R1, AC2 | — |
| 2 | Pure metrics: `GraphMetrics`, `compute_metrics`, `DIRECTION_LABELS`, entry/direction/module logic | `code_atlas/onboarding/metrics.py` | +1 core module → count pin (#4); future consumers 084/085/087 (**none exist yet** — traced) | R1, R3, C1, C2, C4, AC1(a), AC3 | — |
| 3 | Read-only `GROUP BY` pulls `dependency_edges()`, `node_universe()` | `code_atlas/store.py` | SQL boundary; **new methods only**, no schema change; sole caller = metrics.py | R2, C1 | — |
| 4 | **Proof collateral:** count pin `41 → 43` | `tests/test_sql_confinement.py:32`, `tests/test_core_is_language_agnostic.py:42` | pin invalidated by +2 core modules (072 lesson) | AC2 | 2/2 |
| 5 | Fixture-graph unit tests + a small DB-backed test for the store pulls | `tests/test_onboarding_metrics.py` (+ store-pull test) | new file — none | AC1(a), AC3 | — |

Every row traces to a matrix row. Blast-radius trace ran to real producers/consumers: the only
existing invalidations are the two count pins (#4); no code imports `onboarding` yet.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- **`derived-not-listed-invariant`** — **traced.** Command:
  `grep -rnE "DIRECTION_LABELS|direction_label|\"mixed\"|\"sink\"" code_atlas/ tests/` → **no match**
  (the one hit, `enrichment.py:370`, is an unrelated `label` error-context param). So the new label set
  is the first of its kind; design exports `DIRECTION_LABELS` as a tuple and its pin test **reads that
  tuple** (`assert set(m.direction_labels_used()) <= set(metrics.DIRECTION_LABELS)`), never a hardcoded
  copy. Honours R6.7 (PROVISIONAL) prospectively.

### Rule compliance
- **R1.1** ✅ no `if language==`; metrics operate on qnames/file-paths + generic degree counts.
  **P4 (process):** re-run the R1.1 grep-gate after the *last* commit (100-C3), incl. docstrings.
- **R1.4** ✅ all SQL in the two new store methods; metrics.py imports no `sqlite3`.
- **R4/R4.2** ✅ deterministic `ORDER BY` on both pulls; pure functions; byte-stable output (AC1a).
- **R1.2** ✅ no new abstraction/registry — pure fns + two store methods.
- **R3** N/A (no contract change). **R2** N/A (graph-theory, not repo names).
- **R6.7 (PROVISIONAL)** ✅ answered above (derive `DIRECTION_LABELS` from source).
- **Comments ≤3 lines** ✅ observed in new code.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1(a) byte-stability determinism | logic | unit — `compute_metrics` twice on the fixture, assert identical serialisation | ✅ |
| AC1(b) over the anchor PHP index | runtime (needs anchor repo) | **manual-recorded** — coverage-gap exclusion (see below) | ✅ recorded |
| AC2 no PHP logic + count pin | logic (static) | existing grep-gate unit + updated `==43` pins | ✅ |
| AC3 fan-in / fan-out / entry-set / direction incl. cycle→`mixed` | logic | unit over a fixture graph — one assertion per clause | ✅ |

No `❌`. **Coverage-gap exclusions:** AC1(b) *"byte-stable over the anchor PHP index"* — risk tier: low
(determinism already proven at the logic layer by AC1a); why deferred: needs the private anchor repo,
not available in this environment; follow-up: **maintainer runs it and records the result** (same shape
as 074/AC1). Human-approved by the ticket's own wording ("anchor-repo run is a recorded local manual
check").

### Proving test
`tests/test_onboarding_metrics.py` — fails pre-change (`ModuleNotFoundError: code_atlas.onboarding.metrics`)
and passes post-change. Named assertions, one per AC3 clause + AC1a:
`test_fan_out_is_exact_over_the_fixture`, `test_fan_in_is_exact_over_the_fixture`,
`test_entry_points_are_the_zero_inbound_roots`, `test_a_node_in_a_cycle_is_labelled_mixed`,
`test_metrics_are_byte_stable_across_two_runs`.
Invocation: `pytest -q tests/test_onboarding_metrics.py` (authoritative full gate via
`scripts/docker-test.sh`).

### Rollback + porting
Rollback: delete `code_atlas/onboarding/`, revert the two `store.py` methods and the two count pins;
`git revert` the PR. Single repo (`app`) — no cross-repo porting.

### SCOPE
`SCOPE: M` — unchanged; no tier crossing. Branch/PR type `feat`.

## Phase 3 — execute

Implemented the Gate-2 change list on `feat/083-onboarding-graph-metrics`, nothing more.
- **New** `code_atlas/onboarding/__init__.py`, `code_atlas/onboarding/metrics.py` (pure:
  `compute_metrics`, `GraphMetrics`/`NodeMetric`, `direction`, `DIRECTION_LABELS`).
- **`code_atlas/store.py`** +`dependency_edges()` +`node_universe()` (read-only `GROUP BY`, R4.2 order).
- **Count pin** `41 → 43` in `tests/test_sql_confinement.py` + `tests/test_core_is_language_agnostic.py`.
- **New** `tests/test_onboarding_metrics.py` (proving test + DB-backed store-pull test).

### Verification sweep — empirical output

**Axis 1 (file set):** diff ⊆ approved list.
```
$ git diff --stat main -- code_atlas tests
 code_atlas/store.py                     | 28 ++++++++++++++++++++++++++++
 tests/test_core_is_language_agnostic.py |  2 +-
 tests/test_sql_confinement.py           |  2 +-
```
plus new `code_atlas/onboarding/{__init__,metrics}.py` and `tests/test_onboarding_metrics.py`. Exactly
the five approved items; no file outside the list, no untouched-line reformat. `.mango/` run
artifacts are untracked and excluded from the PR.

**Axis 2 (design conformance):** every Gate-2 Approach bullet `implemented-as-approved` — store owns
the two SQL pulls; metrics.py is pure/no-SQL; dependency edge = resolved + self-loops excluded + no
kind allowlist; distinct-neighbour degrees; two grains; entry-point = in-degree 0; `DIRECTION_LABELS`
derived + guarded. **0 deviations.**

**Proving test + gates (Windows host; onboarding/store modules import no `fcntl`):**
```
$ python -m pytest -q tests/test_onboarding_metrics.py tests/test_sql_confinement.py tests/test_core_is_language_agnostic.py
102 passed
$ python -m ruff check code_atlas/onboarding/ code_atlas/store.py tests/test_onboarding_metrics.py
All checks passed!
$ python -m mypy code_atlas/onboarding/ code_atlas/store.py
Success: no issues found in 3 source files
```
The proving test fails pre-change (module absent → `ModuleNotFoundError`) and passes post-change.
`Ph3/4 proven by`: AC1(a) `test_metrics_are_byte_stable_across_two_runs`; AC2 count-pin `41→43` +
`test_core_is_language_agnostic`; AC3 `test_fan_out_is_exact_over_the_fixture` /
`test_fan_in_is_exact_over_the_fixture` / `test_entry_points_are_the_zero_inbound_roots` /
`test_a_node_in_a_cycle_is_labelled_mixed`. **Authoritative full gate via Docker — run at finalise.**
**P4 (100-C3):** R1.1 grep-gate re-run after the last edit (above) — clean.

## Phase 4 — review

`CHALLENGER: OFF (--no-challenger)` — recorded here and carried to DISCLOSURE line one. A clean verdict
below is **not** evidence that anything independent re-derived the requirements from the raw ticket.

**Reviewer** (`mango:reviewer`, Sonnet — `cost_tier: standard`, diff not security/auth/schema): **LGTM**,
no Critical or Important findings. Inspected read-only/ref-based (`main..feat/083-onboarding-graph-metrics`).
Independently confirmed:
- **R1.4** — SQL only in the two new `store.py:521-543` methods; `metrics.py` imports no `sqlite3`, no SQL string.
- **R1.1** — no language token in `code_atlas/onboarding/`; generic `(qname, file_path)` + set arithmetic.
- **R4/R4.2** — total `ORDER BY` on both pulls; `compute_metrics` emits via `sorted(...)`, argument order does not leak; byte-stability test proven.
- **R6.7** — `DIRECTION_LABELS` derived + the guard reads `direction()`'s range, not a hand-copied list (can fail).
- **Count pin 41→43** — recomputed `sorted(code_atlas/**/*.py)`: 41 on `main`, 43 on branch. Correct.
- **Logic** — fan-in/out, entry-points (zero-inbound), cycle→`mixed`, self-loop/unresolved/duplicate-qname handling all correct.
- **Scope** — diff is exactly the five approved items; no reformatting; single repo.
- **Non-finding flagged for visibility:** `dependency_edges()` does not filter `confidence_tier` — a product question for 084/085/087, and an explicit rejected-alternative in the design; not a defect in 083.

**Proving test / delta-green (both measured via Docker, exit 0):** `main` baseline **1268** → branch
**1283** (**+15**, 0 removed, 0 new failures). The +15 = **11 authored** tests in
`test_onboarding_metrics.py` + **4** from the two per-module R1.1 sweeps
(`test_core_is_language_agnostic.py:47,57`, parametrized over `core_modules()`) correctly picking up
the 2 new core modules. Delta-green confirmed.

**Layer-match re-confirmation:** no AC closed on a layer-mismatched proof. AC1(b) remains the recorded,
human-approved coverage-gap exclusion (anchor-repo manual check).

`Ph3/4 proven by`: **k = N** — AC1(a) `test_metrics_are_byte_stable_across_two_runs` ✅ · AC2 count-pin
+ `test_core_is_language_agnostic` ✅ · AC3 (i) `test_fan_out_is_exact_over_the_fixture` (ii)
`test_fan_in_is_exact_over_the_fixture` (iii) `test_entry_points_are_the_zero_inbound_roots` (iv)
`test_a_node_in_a_cycle_is_labelled_mixed` ✅. AC1(b) = recorded exclusion (not counted against k).

**Verdict: clean (reviewer only — CHALLENGER: OFF).**

**Reviewed at `ade9dbf`** — files: `code_atlas/onboarding/__init__.py`, `code_atlas/onboarding/metrics.py`,
`code_atlas/store.py`, `tests/test_onboarding_metrics.py`, `tests/test_sql_confinement.py`,
`tests/test_core_is_language_agnostic.py`. Working doc (embedded): `docs/tasks/083_onboarding-graph-metrics.md`
(exempt from the staleness comparison). `.mango/*` bookkeeping exempt.

## Phase 5 — finalise

**Stale-review guard:** not stale — `git diff --name-only ade9dbf..HEAD` empty; only the working doc
(exempt) and `.mango/*` (exempt) are uncommitted. Non-exempt delta beyond the reviewed set = ∅.

### Learning loop
`CLAIMS: 1 claim from 1 lesson entry | T1=0 T2=0 T3=1 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true | 0 falsified | 0 not cheaply checkable`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed | 0 cannot promote | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- **The code work produced no new engineering lesson** — it confirmed existing ones (072 core-module
  count pin; R6.7 derive-not-list), which the design already applied.
- **One type-3 skill-gap SIGNAL (proposed, awaiting human confirm — NOT written):** mango's
  `reconcile.py` / `run_contract.py` run each condition's `check` via `subprocess(shell=True)`, which is
  **cmd.exe on Windows**. A floor check needing shell features (`LOCAL-HEAD-PUSHED`) must be
  `bash -c`-wrapped **inside cmd double-quotes** — cmd ignores single quotes and splits on `&&`. Destination
  if ratified: `docs/SKILL_GAP_CANDIDATES.md` (a signal for mango's maintainer; edits no mango file).
  Type-3 does not promote into mango. Deferred to morning ratification (DISCLOSURE).

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| review | `mango:reviewer` (Sonnet) | r1 → LGTM | **65.4k** (30 tool-uses, 233 s) |

`LEDGER TOTAL: 65.4k dispatch · top cost driver: reviewer r1.` **Complete:** 1 dispatch this run
(reviewer), 1 row, real token value. Challenger **waived** (`--no-challenger`); refine
exposure-checker (refine skipped) and analysis Explore fan-out (done in main loop) **not dispatched** —
disclosed, not silently skipped. **Main-loop spend unmeasured** (host surfaces no usage block); for the
output-noise side see `rtk gain` (global, not attributable to one task).

### Outward actions
Covered by the maintainer's standing durable approval (AGENTS.md *Maintainer workflow* — the handover
authorisation named exactly these two):
1. **push** `feat/083-onboarding-graph-metrics` (carries code + working doc + BACKLOG bookkeeping).
2. **open PR** via `gh` from `.github/pull_request_template.md`.

Not taken (not authorised / not needed): merge, tracker transition, force-push. The type-3 SG claim is
**not written** pending morning ratification.

### RECONCILE (at close, harness-run)
```
RECONCILE
  conditions: 3 declared | 3 re-run | 3 holding | 0 BROKEN | 0 UNBOUND
  proven    : 0 shown BROKEN when forced | 3 shown HOLDING on a clean run
```
`q = 0` — all three floor conditions HOLDING (PR #120 OPEN, local tree == origin, local head == remote).
The force-broken direction is FORCE-UNPROVEN by design (safe no-op force cases — see DISCLOSURE).

### DISCLOSURE (read first)
1. **CHALLENGER: OFF** (`--no-challenger`). Nothing independent re-derived the requirements from the
   raw ticket. The reviewer LGTM is a single-lens verdict, not evidence of independence.
2. **refine exposure-checker NOT dispatched** — refine self-skipped (0 unresolved product-decisions),
   so the 1-dispatch completeness-of-exposure backstop did not run. On a heavily-locked ticket this is
   expected, but it means no agent asked "is any product-decision still un-exposed?"
3. **analysis Explore fan-out NOT dispatched** — `explore_fanout: true`, but the blast-radius
   investigation was done in the main loop. No independent fan-out corroborated the change list.
4. **`--prove` force-broken direction UNPROVEN** for all 3 floor conditions — I used safe **no-op**
   force cases, because forcing BROKEN would mutate the branch ref / add a commit and `--prove` leaves
   the last force applied (stranding the branch) in an unattended run. The force-**holding** direction
   IS proven (3 HOLDING on a clean run); the negative control is not. The conditions themselves ran
   real checks at t0 (2 BROKEN) and close (3 HOLDING), so they are not inert — only the in-run positive
   control for the broken direction is skipped.
5. **AC1(b) anchor-repo byte-stability is a recorded coverage-gap exclusion** — determinism is proven
   only at the logic layer (fixture). The maintainer must run metrics over the private anchor PHP index
   and record byte-stability (same shape as 074/AC1). Unverified here.
6. **Main-loop token spend UNMEASURED** — the host surfaces no usage block, so only the 65.4k reviewer
   dispatch is counted; the larger main-loop term (the implementation, the two Docker gate runs, the
   worktree baseline) is invisible to the ledger. Call-ceiling unknown (no token budget supplied).
7. **Full suite proven only via Docker** — bare `pytest` is red on the Windows host by the documented
   platform exclusion (fcntl + PHP adapter). Delta-green measured 1268 → 1283.
8. **Type-3 skill-gap SIGNAL — RATIFIED by the maintainer 2026-08-17 and written** as **SG-3** in
   `docs/SKILL_GAP_CANDIDATES.md` (reconcile.py / run_contract.py assume a POSIX shell; on Windows
   their checks run under cmd.exe). It is a signal for mango's maintainer — **no mango file was edited
   by the loop** (`mango files written: 0`).
9. **finalise edited `docs/BACKLOG.md` + the frontmatter beyond the reviewed set** — pure status/ledger
   bookkeeping the reviewer explicitly anticipated as finalise-time; the reviewed code set is unchanged
   since `ade9dbf`. Not a code change slipping past review.
10. **`.mango/` run artifacts (spec, contract) left untracked** — not committed to the PR.
11. **No merge.** autorun stops at the PR. **PR #120 awaits human review + merge.**

## Session status
- **Phase:** 5 finalise — **complete. Run stopped at the PR (no merge).**
- **PR:** [#120](https://github.com/cuongdinhngo/code-atlas/pull/120) — open, awaiting human review + merge.
- **Branch:** `feat/083-onboarding-graph-metrics` @ `a755382` (pushed; local head == origin).
- **Next action (human):** review + merge PR #120; ratify the type-3 SG claim (item 8) if agreed;
  run the AC1(b) anchor-repo byte-stability check (item 5) when next on the anchor repo.
- **Revert:** close PR #120 without merging and delete the branch; or after merge, `git revert` the
  squash commit (removes `code_atlas/onboarding/`, the two `store.py` methods, the count-pin bumps).
