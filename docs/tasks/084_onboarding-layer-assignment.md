---
id: 084
slug: onboarding-layer-assignment
title: Onboarding — architectural layer assignment (M10)
phase: 3
milestone: M10
status: done
depends_on: [083]
---

## Goal
Assign modules (files) to architectural layers, deterministically and language-agnostically, as the
input to `architecture_overview` (086) and the tour (087).

## Scope / Deliverables
- New `code_atlas/onboarding/layers.py` consuming 083's metrics; no LLM, no SQL of its own.
- **Heuristic = namespace/dir prefix refined by dependency direction**, with a **pure
  dependency-direction fallback** when namespaces are uninformative (flat PSR-0/global legacy) — locked
  2026-08-11.
- Deterministic ordering; no per-language handling (R1.1).

## Acceptance criteria
- Layers are sensible on the anchor PHP repo (recorded manual check) and byte-stable for identical input.
- No PHP-specific logic (CI grep-gate).
- Fixture tests assert layer assignment on a namespaced graph **and** the fallback path on a
  flat-namespace fixture.

## References
[`../phase3-onboarding/ROADMAP.md`](../phase3-onboarding/ROADMAP.md) §4 (M10);
PLAN §14, §15 (M10).

# Working doc — 084

## Session status
- **Runner:** `/mango:autorun 084` (unattended lifecycle, stops at the PR; challenger ON).
- **Handover authorisation:** the two outward actions (push branch, open PR) are covered by the
  maintainer's standing durable approval in `AGENTS.md` (*Maintainer workflow*). Recorded in
  `.mango/run-contract-084.txt`.
- **Envelope:** RUN CONTRACT written + validated at t0; RECONCILE t0 clean (2 BROKEN bound floor
  conditions, 2 UNBOUND — TREE-COMPARISON + PROVING-TEST, 0 holding → no strikes). Merge-strategy:
  squash-or-rebase. Call-ceiling: **unknown** (no token budget supplied — recorded, not invented).
- **Phase:** 5 finalise — **complete; stops at the PR (no auto-merge).** Branch pushed, PR
  [#121](https://github.com/cuongdinhngo/code-atlas/pull/121) open. Full Docker gate green (1291
  passed, mypy 44, ruff clean). RECONCILE at close: 2 holding + 2 BROKEN (both accounted — tree
  pre-merge, head-pushed a Windows-shell false-red verified HOLDING in bash). DISCLOSURE recorded.
- **Next action (maintainer):** review & **merge PR #121** (squash); then run + record the AC1(b)
  anchor-repo sensibility check; ratify proposed lesson 084-C1.
- **Revert path:** unmerged → close PR #121 + `git push origin --delete feat/084-onboarding-layer-assignment`.
  Merged → revert the squash-merge commit on `main` (single commit; no schema/contract/tool change to undo).
- **work_doc_mode:** embed. **Branch:** `feat/084-onboarding-layer-assignment`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.

## Phase 0 — refine (skipped)

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

- **Premise (all resolve):** `code_atlas/onboarding/metrics.py` (083's `GraphMetrics`/`compute_metrics`,
  `NodeMetric`, `direction`/`DIRECTION_LABELS`), `docs/phase3-onboarding/ROADMAP.md` §4,
  `docs/PLAN.md`, `ENGINEERING_RULES.md` R1.1. To-be-created (not missing): `code_atlas/onboarding/layers.py`,
  `architecture_overview` (086), the tour (087).
- **Skip rationale:** every product-decision is locked (ticket + PHASE3 §4, "LOCKED 2026-08-11"):
  heuristic = namespace/dir prefix refined by dependency direction, with a **pure dependency-direction
  fallback** when namespaces are uninformative; module unit = file path; deterministic ordering; no
  per-language handling (R1.1). Layer *labels* are **derived from the repo's own namespace/dir prefixes**,
  not a canonical taxonomy — a canonical taxonomy would need per-language/framework knowledge, forbidden
  by R1.1/R2, so this is a how-decision the locked heuristic already settles, not an open want. AC1's
  "sensible on the anchor repo" is defined by the ticket/PHASE3 as a *recorded manual check* (coherence
  not falsifiable — task-023 note), so no acceptance-bar want survives. Per the skip rule the 1-dispatch
  exposure-checker does not run.
- **Recalled (advisory, blocks nothing):** `derived-not-listed-invariant` (by handle — 097-C1/095-C1/093-C2:
  if `layers.py` names a set of layer labels/reason codes, **derive it from the surface, don't list it**,
  and pin the derivation) and `pin-the-table-a-purity-claim-rests-on` (by handle — AC "byte-stable" is a
  purity claim; pin the table it rests on). **Scan constraint (high-value):** the **072 lesson** — a new
  core module breaks the `len(core_modules()) == 43` pin in `tests/test_sql_confinement.py:32` **and**
  `tests/test_core_is_language_agnostic.py:42`; execute must bump **43 → 44** (`core_modules()` =
  `sorted(code_atlas/**/*.py)`; +`layers.py`).

## Phase 1 — analysis

Premise + recall carried forward from Phase 0 (not re-run):
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

### Decompose
`SECTIONS: 4 found (Goal, Scope/Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=3 (References = context)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | Assign modules(files) to architectural layers, deterministically & language-agnostically, as input to `architecture_overview` (086) + tour (087) | A **pure compute layer** producing per-module layer assignment; **no MCP tool surface**, no `main.py` change | `onboarding/` exists, `layers.py` absent; PHASE3 §4 (locked) | ✅ planned |
| R1 | Scope | New `code_atlas/onboarding/layers.py` consuming 083's metrics; **no LLM, no SQL of its own** | Pure module: input = `GraphMetrics` (083) + `node_universe` `(qname, file_path)`; output = deterministic per-module layer assignment | `metrics.py:89` `compute_metrics`; `store.py:537` `node_universe` | ✅ planned |
| R2 | Scope | Heuristic = **namespace/dir prefix refined by dependency direction** (locked 2026-08-11) | Group modules by leading namespace/dir prefix (from qname namespace / `file_path` dir); order/refine layers by module `direction` (source→sink) | `metrics` module `direction`; `node_universe` qname/path | ✅ planned |
| R3 | Scope | **Pure dependency-direction fallback** when namespaces uninformative (flat PSR-0/global legacy) | When prefixes don't partition (all-same / flat), assign layers purely from dependency direction | `direction()` labels `metrics.py:16-27` | ✅ planned |
| C1 | Scope | Deterministic ordering; **no per-language handling** (R1.1) | Sorted, byte-stable output; no `if language==`; generic strings only | R1.1; `test_core_is_language_agnostic.py` | ✅ planned |
| C2 | Scope | **no SQL of its own** (R1.4) | `layers.py` imports no sqlite; SQL stays in `store.py` | R1.4; `test_sql_confinement.py:26` | ✅ planned |
| AC1 | AC | Layers **sensible on anchor PHP repo (recorded manual check)** AND **byte-stable for identical input** | (a) byte-stability falsifiable on a fixture; (b) anchor-repo sensibility = recorded manual-check exclusion | R4.2; task-023 note | ⏳ split — see AC validation |
| AC2 | AC | **No PHP-specific logic** (CI grep-gate) | Existing grep-gate + count-pin bump **43→44** (072 collateral) | `test_core_is_language_agnostic.py:42` | ✅ planned |
| AC3 | AC | Fixture tests assert layer assignment on a **namespaced graph** AND the **fallback path on a flat-namespace fixture** | Two proof clauses: (i) namespaced graph → prefix-refined layers; (ii) flat-namespace graph → dependency-direction fallback | — | ⏳ proving test (design) |

### AC validation (falsifiability)
- **AC1(a) byte-stability** — falsifiable: compute layers twice over the same fixture (shuffled input order), assert byte-identical serialisation (R4.2). ✅ falsifiable.
- **AC1(b) "sensible on the anchor PHP repo"** — **not runnable here** (needs the private anchor repo) **and** "sensible" is a coherence judgment, **not falsifiable** (task-023 note; PHASE3 §4 "coherence = a recorded manual check, not a gate"). Recorded as an **explicit manual-check exclusion** (coverage-gap), same shape as 083/AC1(b) and 074/AC1 — a human runs it and records the assessment. Not a bare `✅`.
- **AC2** — falsifiable by the existing `test_core_is_language_agnostic.py` grep-gate. **Collateral (072 lesson):** the `len(core_modules()) == 43` pin in `test_sql_confinement.py:32` **and** `test_core_is_language_agnostic.py:42` becomes **44** (`core_modules()` = `sorted(code_atlas/**/*.py)`; +`layers.py`).
- **AC3** — falsifiable (the unit tests). **Multi-clause, one proof row per clause (Gate 1 split):** (i) a **namespaced** fixture graph → exact per-module layer assignment via prefix-refined-by-direction; (ii) a **flat-namespace** fixture graph → exact assignment via the pure dependency-direction **fallback**.

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`j = 0` — Gate 0 already cleared by the refine skip; every product-decision is locked (ticket + PHASE3 §4, "LOCKED 2026-08-11"). No mismatch between a stated and a computed acceptance value.

### Universal inventory
R1.1 "no language branches" / AC2 "no PHP-specific logic" are universal but **covered by the existing CI grep-gate** (`test_core_is_language_agnostic.py`), not a per-item checklist. N (new core modules) = **1** (`layers.py`). No other "for each of N" requirement. AC3 is multi-clause (2 clauses) → 2 proof rows (above), not one aggregate.

### Cause / gap (enhancement)
Gap: no layer-assignment stage exists. `code_atlas/onboarding/` holds `metrics.py` (083 — fan-in/out, entry points, direction at symbol + module grain) but **nothing consumes it to assign layers**. Target: `onboarding/layers.py` (pure), consuming `GraphMetrics` + `node_universe` — **no new store pull** (083 already added `dependency_edges`/`node_universe`).

### Blast radius
- **New:** `code_atlas/onboarding/layers.py`, `tests/test_onboarding_layers.py`.
- **Modified:** `tests/test_sql_confinement.py:32` + `tests/test_core_is_language_agnostic.py:42` (count pin **43→44**).
- **Untouched:** `main.py` (no tool surface — G1), `store.py` (consumes existing `node_universe`/`dependency_edges` — R2 already shipped in 083), `contract.py` (no vocab change — R3 N/A), `metrics.py`, adapters, resolver.

### Baseline
`BASELINE: green — 103 passed | 1180 deselected | 0 failed` (Docker gate `ruff·mypy·pytest`, scoped `-k "onboarding or sql_confinement or language_agnostic"` on the untouched `main` checkout). Definition of Done for later phases = **prove the delta is green** (no new failure; the count-pin edit stays green at 44).

### TRACK
`TRACK: backend — 0/4 touched files under UI paths (pure Python compute + tests)`

### Rule-compliance coverage
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §1.1 (change-type) ✅ | §1.2 (change-type) ✅ | §1.4 (change-type) ✅ | §4.1 (change-type) ✅ | §4.2 (change-type) ✅ | §6.1 (change-type) ✅ | §6.6 (change-type) ✅ | §7.5 (change-type) ✅ | §6.7 (recalled handle derived-not-listed-invariant, PROVISIONAL) ✅`
- **§1.1** — no `if language==`; `layers.py` reasons over generic strings (qname/path/direction), guarded by the CI grep-gate (AC2). Bites on every branch in `layers.py`.
- **§1.2** — YAGNI: `layers.py` is a plain module of pure functions — **no** registry/base-class/factory/DI (adapter #2 absent). No new seam.
- **§1.4** — SRP: `layers.py` reasons only; imports no sqlite; SQL stays in `store.py` (C2). Enforced by `test_sql_confinement`.
- **§4.1** — no LLM/network in `layers.py` (091 LLM refinement is a separate, optional task).
- **§4.2** — byte-stable output over identical input (AC1(a)); sorted, no set-ordering/wall-clock leakage.
- **§6.1** — tests required: fixture tests over a namespaced graph + a flat-namespace fallback graph (AC3).
- **§6.6** — mypy strict clean on `layers.py` (core has mypy; runs in the Docker gate).
- **§7.5** — comments ≤ 3 lines in `layers.py`.
- **§6.7 (PROVISIONAL, recalled handle `derived-not-listed-invariant`)** — if `layers.py` names a set of layer labels / reason codes / valid layer kinds, **derive it from the definition site**, never re-type a literal list; a determinism/enumeration test pins the derivation. *Provisional → surfaces, does not gate-block as codified.*
- **N/A:** §1.3/§1.5/§1.6/§1.7 (adapter-seam / capability / coerced-persistence — no seam, no persistence here), §2.x (not an adapter; AC2's grep-gate is R2.2/R1.1), §3.x (no contract change — `contract.py` untouched), §4.3 (no SQL), §5.x (pure in-memory function, no parse/degradation/payload-execute field), §8.x (stdlib only, no new dep).

### Declarations
`STRUCTURE: native` · `SCOPE: M` · `TIER: full` · `TRACK: backend`
- **SCOPE: M** — new module + 2 fixture-test clauses + a 2-file count-pin bump; mirrors 083 (M).
- **TIER: full** — SCOPE=M, multiple files, N=1 new core module + universal grep-gate requirement; not lite-eligible. Routes through the full five-phase lifecycle (matrix, challenger, sweep, gates).

## Phase 2 — design

### Approach
`layers.py` — a **pure** module (mirrors `metrics.py`) consuming **only** `GraphMetrics` (083). No store
pull, no `node_universe`, no LLM (R1.4/R4.1).

**Prefix source (language-agnostic):** a module's **directory prefix** = the parent directory of its
`file_path` (everything up to the last `/`). Paths are POSIX-normalised at index time
(`indexer.py:468,633` `as_posix()`) and `store.py:690` already groups by the leading `/` segment, so
splitting on `/` is language-agnostic. Deriving the prefix from the **qname namespace** is deliberately
**rejected** — it needs a per-language separator (`\`, `.`, …) → an R1.1 branch the CI grep-gate bans.

**Primary path — namespace/dir prefix refined by dependency direction:**
1. Group modules (`GraphMetrics.modules`, keyed by `file_path`) by parent-dir prefix.
2. Per group, aggregate a direction score `net = Σfan_out − Σfan_in` over its modules.
3. Order groups by `net` **descending** (source-like/entry = rank 0 → sink-like/foundation = last),
   tie-broken by prefix name ascending (deterministic). Each ordered group = one layer named by its
   prefix; every module in it takes that layer + rank. `method = "namespace-prefix"`.

**Fallback — pure dependency-direction — when namespaces uninformative:** trigger when
`len({prefix(m) for m in modules}) <= 1` (all modules share one parent dir, or all sit at root — flat
PSR-0/global legacy). Then ignore prefixes: layer name = each module's `direction` label; bands ordered
source→mixed→sink→isolated; rank = band index. `method = "dependency-direction-fallback"`.

**Output** (frozen dataclasses mirroring `metrics.py`, with deterministic `as_dict`/`to_json` for 086):
- `ModuleLayer(module, layer, rank)`
- `LayerAssignment(layers: tuple[str,...] ordered entry→foundation, modules: tuple[ModuleLayer,...]
  sorted by module key, method: str)` + `as_dict()` / `to_json(sort_keys=True)`.
- `assign_layers(metrics: GraphMetrics) -> LayerAssignment`.

**Derived-set discipline (R6.7):** module tuple `LAYER_METHODS = ("namespace-prefix",
"dependency-direction-fallback")` is the single source; fallback layer names come from
`metrics.DIRECTION_LABELS`. Pin tests derive both sets (mirroring `test_direction_labels_are_derived_not_listed`).

### Rejected alternatives
1. **Prefix from the qname namespace** (split on the namespace separator) — rejected: a per-language
   separator is an R1.1 branch (CI-grep-gated); the `file_path` dir-prefix is language-agnostic and
   mirrors PSR-4 namespaces.
2. **New store SQL pull** for directory grouping — rejected: `GraphMetrics.modules` already carry
   `file_path` + degrees; no SQL needed (R1.4; ticket "no SQL of its own").
3. **Fixed canonical taxonomy** (presentation/domain/infrastructure) — rejected: needs framework
   knowledge (R2/R1.1), not derivable from graph shape; layer names are the repo's own dir prefixes.

### Assumptions
- **verified** — module keys are `/`-separated POSIX `file_path`s (`indexer.py:468,633`; `store.py:690`).
  Prefix-by-`/` is safe.
- **verified** — `GraphMetrics` is sorted/deterministic (083, R4.2; `metrics.py:80` `sorted()`), so
  layering over it is byte-stable.
- **No `novel-untested` third-party/runtime assumption** (pure Python, stdlib only) → Gate 2 is not
  blocked on an unresolved assumption.

### Smallest change-list
| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| New pure module: `assign_layers` + `ModuleLayer`/`LayerAssignment` + `LAYER_METHODS` | `code_atlas/onboarding/layers.py` (new) | future consumers 086/087 (not yet present); onboarding pkg; +1 core module → count-pin (below) | R1,R2,R3,C1,C2,G1 | 1/1 |
| Proving tests: namespaced fixture, flat fallback fixture, byte-stability, derived-set pins | `tests/test_onboarding_layers.py` (new) | none identified — pure fixtures, no `GraphStore` (Windows-runnable) | AC1(a),AC3(i),AC3(ii) | — |
| **Proof collateral (072):** count-pin `43 → 44` | `tests/test_sql_confinement.py:32` | the pin guards the SQL-confinement core-module inventory | AC2,C2 | 1/2 |
| **Proof collateral (072):** count-pin `43 → 44` | `tests/test_core_is_language_agnostic.py:42` | the pin guards the language-agnostic core-module inventory | AC2,C1 | 2/2 |

Every item traces to a matrix row. Mechanical test blast-radius trace (real consumers, not a shallow
grep): `grep -nE "core_modules\(\) == 43"` → exactly the two pins above — both folded in as planned
edits, so `diff ⊆ approved change-list` holds without deviation backfill.

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply | 0 unanswered`
- **`derived-not-listed-invariant`** → **traced**. `grep -nE "DIRECTION_LABELS|derived|pin"
  code_atlas/onboarding/metrics.py tests/test_onboarding_metrics.py` →
  `metrics.py:14-16` (tuple derived from `direction()`'s range, R6.7) and
  `tests/test_onboarding_metrics.py:80` / `:83-87 test_direction_labels_are_derived_not_listed`
  (`produced == set(metrics.DIRECTION_LABELS)`). **Folded:** `layers.py` mirrors it — fallback labels =
  `metrics.DIRECTION_LABELS`, and `LAYER_METHODS` is pinned by a derive-not-list test that breaks if a
  method string is added without a producer.
- **`pin-the-table-a-purity-claim-rests-on`** → **traced**. `grep -nE "byte-stable|to_json|shuffle"
  tests/test_onboarding_metrics.py` → `:68-73 test_metrics_are_byte_stable_across_two_runs` (compute
  twice over reversed input, byte-compare `to_json()`). **Folded:** `layers.py` adds
  `test_layers_are_byte_stable_across_two_runs` — the table AC1(a)'s purity claim rests on.

### Rule compliance
Carries Gate-1 `RULE SECTIONS`. Design specifics: §1.1 no branch (prefix logic keys on `/` + graph
degrees, never language); §1.2 no new abstraction (plain module of pure fns); §1.4 no SQL (consumes
`GraphMetrics`); §4.1 no LLM; §4.2 sorted output + `to_json(sort_keys=True)`; §6.1 tests;
§6.6 mypy-strict-clean typed dataclasses; §6.7 both label/method sets derived + pinned; §7.5 comments ≤ 3 lines.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1(a) byte-stable | logic | unit — `test_layers_are_byte_stable_across_two_runs` | ✅ |
| AC1(b) sensible on anchor repo | runtime/manual (coherence — not falsifiable) | manual-recorded (coverage-gap exclusion) | ✅ recorded exclusion |
| AC2 no PHP-specific logic | logic/integration (CI grep-gate) | existing grep-gate test + count-pin bump | ✅ |
| AC3(i) namespaced graph | logic | unit — `test_namespaced_graph_layers_by_prefix_refined_by_direction` | ✅ |
| AC3(ii) flat fallback | logic | unit — `test_flat_namespace_falls_back_to_dependency_direction` | ✅ |

No `❌`.

**Coverage-gap exclusions (human-approved):**
- **AC1(b)** "sensible on the anchor PHP repo" · risk tier: manual/coherence (not falsifiable — task-023
  note) · **why deferred:** needs the private anchor repo + human judgement · **follow-up:** the
  maintainer runs `assign_layers` over the anchor index and records the sensibility assessment (same
  shape as 083/AC1(b), 074/AC1). Standing exclusion per the PHASE3 §4 lock "coherence = a recorded
  manual check, not a gate".

### Proving test
`tests/test_onboarding_layers.py::test_flat_namespace_falls_back_to_dependency_direction` — fails
pre-change (module absent → `ImportError`), passes post-change; sits at AC3(ii)'s **logic** risk layer
(the fallback clause, the most error-prone). AC3(i) → `test_namespaced_graph_layers_by_prefix_refined_by_direction`;
AC1(a) → `test_layers_are_byte_stable_across_two_runs`.
- **Bare (this Windows host — RECONCILE-close):** `python -m pytest tests/test_onboarding_layers.py -q`
  (pure: imports only `code_atlas.onboarding.{metrics,layers}`; no `fcntl`/`GraphStore`).
- **Full gate (execute/review):** `scripts/docker-test.sh pytest -q -k "onboarding or sql_confinement or language_agnostic"`.

### Rollback + porting
Rollback: delete `code_atlas/onboarding/layers.py` + `tests/test_onboarding_layers.py`, revert the two
count-pins `44 → 43`. No schema/contract/tool change → no migration. Porting: single repo (`app`); no
shared-code fan-out across `config.repos`.

### SCOPE
`SCOPE: M` — unchanged. No tier crossing; the change-list (1 new module + 1 test file + 2 one-line
pin bumps) matches the analysis blast radius. No *outgrew-its-ticket* nudge.

## Phase 3 — execute

Branch `feat/084-onboarding-layer-assignment`. Implemented exactly the Gate-2 change list:
`code_atlas/onboarding/layers.py` (new), `tests/test_onboarding_layers.py` (new), count-pin `43→44` in
`tests/test_sql_confinement.py:32` and `tests/test_core_is_language_agnostic.py:42`.

### Verification sweep — empirical output

**Proving test (bare, this Windows host — pre-change it failed at collection: `code_atlas.onboarding.layers`
did not exist → ImportError):**
```
$ python -m pytest tests/test_onboarding_layers.py -q
......                                                                   [100%]
6 passed in 0.06s
```

**Axis 1 — file set (`git status/diff --stat -- code_atlas/ tests/`):**
```
 M tests/test_core_is_language_agnostic.py
 M tests/test_sql_confinement.py
?? code_atlas/onboarding/layers.py
?? tests/test_onboarding_layers.py
 tests/test_core_is_language_agnostic.py | 2 +-
 tests/test_sql_confinement.py           | 2 +-
```
`diff ⊆ approved change-list` ✅ — exactly the 4 approved files; the two edits are one line each (pin
`43→44`); no untouched-line reformatting. Each hunk maps to a matrix row (layers.py → R1/R2/R3/C1/C2/G1;
test file → AC1a/AC3; pins → AC2/C1/C2). `layers.py` imports only `json`, `dataclasses`, and
`onboarding.metrics` — no stray refs, no `sqlite`, no `if language==` (grep clean).

**Axis 2 — design-conformance self-check (each Gate-2 Approach bullet):**
| Approach bullet | Result | Where |
|---|---|---|
| Prefix = parent dir of `file_path`, split on `/` (language-agnostic) | implemented-as-approved | `layers.py:_prefix` (`rpartition("/")`) |
| Primary: group by prefix, order groups by `net = Σfan_out−Σfan_in` desc, tie-break name | implemented-as-approved | `layers.py:_by_prefix` |
| Fallback when `≤1` distinct prefix → direction bands source→mixed→sink→isolated | implemented-as-approved | `layers.py:_by_direction`, `_FALLBACK_ORDER` |
| Frozen `ModuleLayer`/`LayerAssignment` + `as_dict`/`to_json(sort_keys=True)` | implemented-as-approved | `layers.py:30-62` |
| Derived sets: `LAYER_METHODS` + fallback labels from `DIRECTION_LABELS`, pinned | implemented-as-approved | `layers.py:19-27`, tests `:derived_not_listed`/`:from_direction_labels` |

**0 deviations** (both axes clean). `Ph3 proven by`: AC1(a) `test_layers_are_byte_stable_across_two_runs` ✅;
AC3(i) `test_namespaced_graph_layers_by_prefix_refined_by_direction` ✅; AC3(ii)
`test_flat_namespace_falls_back_to_dependency_direction` ✅ (proving test); AC2/C1/C2 count-pin `43→44`
(proven in the Docker gate below).

**Full Docker gate (`ruff check . && mypy code_atlas && pytest -q`, delta-green — §6.6 mypy strict):**
```
Success: no issues found in 44 source files
1291 passed in 104.23s (0:01:44)
```
ruff clean (silent on success — mypy/pytest ran only because the `&&` chain passed ruff first); mypy
strict clean over **44** source files (43 + `layers.py`, confirming the count-pin bump); **1291 passed,
0 failed, 0 skipped**. Baseline was green → delta is green (added 6 tests + `layers.py`; no
pre-existing failure touched). One ruff round-trip fixed en route: initial E501/F401 in the two new
files (over-long docstrings/comments + an unused `DIRECTION_LABELS` import) — corrected, re-run clean;
recorded here, not hidden. A `_FALLBACK_ORDER == DIRECTION_LABELS` pin was added so a future metrics
label can't ship unplaced (would `KeyError` in `_by_direction`) — a strengthened R6.7 guard, within
the approved design intent (derived-not-listed), not a scope deviation.

## Phase 4 — review

`CHALLENGER: ON` (challenger dispatched; `--no-challenger` not passed). Reviewer selection: `reviewer`
(Sonnet) — `cost_tier=standard`, diff not security/auth/access/schema-tagged. Both inspected
`main..feat/084-onboarding-layer-assignment` @ `dcd044f` read-only (working tree already at the SHA).

**Reviewer (Sonnet) — verdict `LGTM`, no Critical/Important findings.** Scope exactly the 4 approved
files (`git ls-tree … | grep .py | wc -l` = 44, matches the bumped pins). Traced compliant: R1.1 (`_prefix`
splits `file_path` on `/`, no namespace-separator parsing — cross-checked the POSIX-normalisation claim
against `indexer.py:468,633`), R4.2 (all dict/set reads pass through explicit `sorted()`; `to_json`
`sort_keys=True`; byte-stability empirically confirmed), R6.7 (`LAYER_METHODS` + `_FALLBACK_ORDER` both
derived-and-pinned; the `_FALLBACK_ORDER == DIRECTION_LABELS` pin goes red before a 5th label could
`KeyError`), R1.4/R4.1 (no sqlite/LLM/network), R7.5 (comments ≤ 3 lines). Algorithm hand-recomputed
over both fixtures → non-tautological. **Non-blocking note:** empty / single-module / root+nested-mix
cases aren't in a committed test (AC3 requires only the two named clauses, both present) → recorded as a
follow-up, not expanded here (scope discipline).

**Challenger (ticket-blind) — 9 met, 1 not met, 0 can't-tell.** The one "not met" is AC1(b) *"sensible
on the anchor PHP repo (recorded manual check)"* — no artifact visible in the diff. This is exactly the
**recorded, human-approved coverage-gap exclusion** in the design (anchor repo private; coherence not
falsifiable; PHASE3 §4 "a recorded manual check, not a gate") → **does not block clean** per the
clean-decision rule. The challenger also flagged BACKLOG/token-ledger not yet updated — that is
`finalise`'s docs-before-PR step (done there, not at review time). Code half: all 9 code/test
requirements met.

**Clean decision:** reviewer no-Critical ✅ · challenger's only miss is a recorded exclusion ✅ · no
layer-match `❌` ✅ · `k = N` (every matrix row proven; AC1(b) recorded exclusion) ✅ · proving test
green ✅ → **CLEAN** (challenger ON — full criterion, not reviewer-only).

**Ph3/4 proven by (matrix):** G1 no-tool-surface (main.py untouched) ✅ · R1/R2/R3/C1/C2 `layers.py`
+ reviewer trace ✅ · AC1(a) `test_layers_are_byte_stable_across_two_runs` ✅ · AC1(b) recorded
manual-check exclusion (follow-up) · AC2 grep-gate + pin 44 ✅ · AC3(i)
`test_namespaced_graph_layers_by_prefix_refined_by_direction` ✅ · AC3(ii)
`test_flat_namespace_falls_back_to_dependency_direction` ✅.

**Stale-review guard:** `Reviewed at dcd044f`. Reviewed files: `code_atlas/onboarding/layers.py`,
`tests/test_onboarding_layers.py`, `tests/test_sql_confinement.py`,
`tests/test_core_is_language_agnostic.py`. Working doc (exempt from staleness):
`docs/tasks/084_onboarding-layer-assignment.md` (embedded). `finalise` refuses the PR if any non-exempt
file changes beyond this set.

## Phase 5 — finalise

**Stale-review guard:** `git diff --name-only dcd044f..HEAD` = ∅; uncommitted = the exempt working-doc
file + gitignored `.mango/`. Non-exempt set beyond the reviewed list = **empty → not stale → proceed.**

### Learning loop
`CLAIMS: 1 claim from 1 lesson entry | T1=0 T2=0 T3=0 T4=1 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 with seen ≥ 2 | 0 routed | 0 cannot promote | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`
- **Durable lesson (`docs/LESSONS.md` 084-C1, proposed):** a Docker gate piped through `tail` reports
  the pipe's exit (tail's 0), masking a `ruff`/`mypy` failure — judge a piped gate by its **output
  content**, not the pipeline exit. Type 4 (gotcha), first sighting (recurrence 1) → recorded in
  `lessons_path`; `gotchas_path` promotion awaits recurrence + a human ratify (the maintainer, on the
  PR / next session — `autorun` cannot ratify). No mango file written.

### Cost ledger (dispatch-only — main-loop unmeasured; host surfaces no usage block)
| Dispatch | Tokens | Tool-uses | Duration | Result |
|---|---|---|---|---|
| `mango:reviewer` (Sonnet) r1 | 74.0k | 32 | 297 s | LGTM, no findings |
| `mango:challenger` (Sonnet, ticket-blind) | 50.4k | 22 | 170 s | 9 met / 1 recorded-exclusion |
| **Total dispatch** | **124.4k** | 54 | — | — |
- **Completeness gate:** 2 dispatches, 2 rows, both carry a real token value → **complete**. Not
  dispatched (disclosed, not blank): refine exposure-checker (refine self-skipped, 0 unresolved),
  analysis Explore fan-out (main loop), extractor (none needed).
- `LEDGER TOTAL: 124.4k dispatch · top cost driver: mango:reviewer (74.0k)`. Main-loop spend is
  **unmeasured** (host surfaces no usage block); for output-noise savings see `rtk gain` (global, not
  attributable to one task). RTK present; no invented dispatch-vs-noise split.

### Outward actions
Pre-authorised at handover (standing durable approval, `AGENTS.md` *Maintainer workflow* — names exactly
these two), taken now:
1. **Push** `feat/084-onboarding-layer-assignment` to `origin` (carries the code commit `dcd044f` + a
   bookkeeping commit: docs, working doc, LESSONS 084-C1 — so the lesson reaches a shared ref, not an
   orphaned branch).
2. **Open PR** via `gh` from `.github/pull_request_template.md`.

Deferred to the maintainer (NOT taken by `autorun` — on the abort list):
- **Merge** the PR · **tracker transition** (084 → done in any external tracker) · ratify the
  proposed lesson 084-C1 · run the **AC1(b) anchor-repo manual sensibility check** and record it.

**Taken:** branch pushed (`origin/feat/084-onboarding-layer-assignment` @ `5974e21`); PR
[#121](https://github.com/cuongdinhngo/code-atlas/pull/121) opened. No merge, no transition.

### RECONCILE (at close, harness-run — I transcribe the verdict)
```
RECONCILE
  conditions: 4 declared | 4 re-run | 2 holding | 2 BROKEN | 0 UNBOUND
  proven    : 0 shown BROKEN when forced | 2 shown HOLDING on a clean run
  phase     : close | challenger: on | branch: feat/084-onboarding-layer-assignment
    PR-EXISTS: HOLDING — OPEN
    TREE-COMPARISON: BROKEN — (main lacks the change; correct pre-merge, informational)
    LOCAL-HEAD-PUSHED: BROKEN — "The system cannot find the path specified" (Windows shell mismatch, see below)
    PROVING-TEST: HOLDING — 6 passed
  READ THIS FIRST: a BROKEN condition describes the state after the last push; it does not block the
  merge — this version stops at the PR and the human merges.
```
- **`q = 2` does NOT block the merge** (this version stops at the PR). Both BROKENs are accounted for:
  - **TREE-COMPARISON BROKEN = correct and expected** — `main` does not yet carry the change (not
    merged). It flips to HOLDING only post-merge.
  - **LOCAL-HEAD-PUSHED BROKEN = a FALSE-RED from a host shell mismatch**, not a stranded head.
    `reconcile.py` runs each check via `subprocess.run(shell=True)`, which on this Windows host is
    `cmd.exe`; the floor check is bash syntax (`git rev-parse --verify … >/dev/null 2>&1 && test
    "$(…)" = "$(…)"`), and `cmd.exe` errors on `/dev/null`. **Verified the real predicate by hand in
    bash:** `local == remote == 5974e2167805fb5d4ef036e57557ef7ab19e578f` → the branch **is** pushed
    (truly HOLDING). Disclosed below.
- **`--prove` forced controls: all FORCE-UNPROVEN by design.** The `force-broken`/`force-holding` cases
  are deliberate no-ops (`true`/`false`), because forcing these floor conditions would mutate shared
  state (the branch head, the PR, the working tree) during an unattended close — which the abort list
  forbids. So the positive control does not flip and is honestly reported as unproven; each condition's
  real state was read directly instead (PR open, proving test green, head pushed-verified, tree differs).

### DISCLOSURE (read first)
1. **CHALLENGER: ON** — the ticket-blind challenger ran (9 met / 1 recorded-exclusion).
2. **Floor-condition tooling false-red (highest-value item):** `LOCAL-HEAD-PUSHED` reported BROKEN only
   because `reconcile.py`'s bash-syntax check ran under Windows `cmd.exe`. Verified truly HOLDING in
   bash (local == remote head). A future contract on this host should write shell-portable checks or the
   harness should invoke bash. **This did not affect the outcome, but the RECONCILE count over-states
   `q` by one.**
3. **t0 "unchecked agent claims" (2)** — the seed lists TREE-COMPARISON and PROVING-TEST as
   `agent-claim (unchecked)` because their `derived-by` was unset at t0; both were **bound at Gate 2 and
   run for real at close** (BROKEN-pre-merge and HOLDING respectively), so they are no longer unchecked.
4. **AC1(b) anchor-repo "sensible" check** — a recorded manual-check exclusion (private anchor repo;
   coherence not falsifiable — PHASE3 §4). Deferred to the maintainer; the challenger correctly flagged
   it as unproven-from-the-diff.
5. **Reviewer non-blocking coverage note** — empty / single-module / root+nested-mix graphs are not in a
   committed test (AC3 requires only the two named clauses, both present). Left out for scope discipline;
   an optional follow-up.
6. **Execute mid-run correction** — the two new files first tripped ruff E501/F401 (over-long
   docstrings/comments + an unused import); corrected and re-run clean. Recorded, not hidden. Prompted
   lesson 084-C1.
7. **Budget:** call-count ceiling **unknown** (no ledger history for tier=standard). Main-loop spend
   **unmeasured** (host surfaces no usage block); only the 124.4k dispatch is measured. No degradation
   ladder step was taken (reviewer + challenger both ran at full tier).
8. **Not dispatched (disclosed, not silent):** refine exposure-checker (refine self-skipped, 0
   unresolved), analysis Explore fan-out (done in the main loop), extractor (none needed).
9. **Merge-strategy detection = squash-or-rebase** — narrows the TREE-COMPARISON judgement, does not
   remove it (a direct commit to `main` would look identical).
10. **Deferred outward actions** (on the abort list, left for the maintainer): merge PR #121, any
    tracker transition, ratify proposed lesson 084-C1, run + record the AC1(b) anchor check.
