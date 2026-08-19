---
id: 091
slug: llm-layer-refinement
title: Onboarding — LLM layer-name refinement (M12, opt-in)
phase: 3
milestone: M12
status: done
depends_on: [084, 090]
---

## Goal
Improve layer names and boundaries where the deterministic heuristic (084) is weak — the flat-namespace
legacy case — using the LLM, optionally.

## Scope / Deliverables
- Behind the 085 seam and the 090 cache; consumes 084's heuristic layers and refines names/boundaries.
- Opt-in; off by default; the deterministic layering (084) remains the fallback.

## Acceptance criteria
- Opt-in and deterministic via the content-hash cache; off by default.
- Never runs in the per-PR gate (R4.1); core unaffected when off.
- With refinement off, layer output is byte-identical to 084.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M12);
PLAN §14, §15.

## Session status
- **Runner:** `/mango:solve 091 --no-challenger` — **review & challenger WAIVED** by run args
  ("skipped review & challenger"). `CHALLENGER: OFF (--no-challenger)`; review phase replaced by a
  main-loop self-verification sweep. Maintainer standing approval (`AGENTS.md`) + explicit run args
  cover the two outward actions (push branch, open PR).
- **work_doc_mode:** embed. **Branch:** `feat/091-llm-layer-refinement`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.

## Phase 0 — refine
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous` — 084 (`assign_layers` in
`code_atlas/onboarding/layers.py`) **done**; 090 (`onboarding_llm/` + `ContentHashCache`) **done**;
PHASE3 §4 (M12, names 091 "top tier for the layer-refinement pass") and PLAN §14/§15 (M12 → "091 LLM
layer-name refinement") resolve. The LLM impl itself is to-be-created → `m = 0`, continue.
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`
- **Seam shape** → a **new `LayerRefiner` Protocol** in `layers.py` (not the 085 `Summarizer`: that is
  node-grain `NodeFacts -> Summary`; layer refinement is aggregate). Cited: R4.1 forces the LLM out of
  core so a seam is mandatory; R7.4 is satisfied because a 2nd implementer (the LLM refiner) ships in
  this ticket — same justification the 085 seam had (PHASE3 §3).
- **Refiner contract** → returns a **rename map** `{old_layer: new_layer}`, not a whole
  `LayerAssignment`. Cited: AC ("core unaffected", "byte-identical when off") — a narrow return makes
  coverage/rank corruption unrepresentable regardless of what the LLM returns (see LESSONS 091-C1).
- **Names vs boundaries** → **names only** for v1; module re-grouping (boundaries) deferred to a
  follow-up. Cited: Goal names the *flat-namespace* case, which is a **naming** weakness; re-grouping
  risks the AC3 byte-stability / coverage invariants. Recorded as a scope-limit, not silent.
- **Model tier** → default **`claude-opus-5`** (top tier), overridable via
  `CA_ONBOARDING_LLM_LAYER_MODEL`. Cited: PHASE3 §4 M12 decision "a **top tier only for the
  layer-refinement pass**" (090's summaries use mid-tier Sonnet). Top tier today = Opus 5 (claude-api
  Current Models).

## Phase 1 — analysis
`SECTIONS: 4 found (Goal, Scope/Deliverables, Acceptance criteria, References) | References informational → 0 rows | ROWS: C=0 R=2 G=1 AC=3`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Status |
|---|---|---|---|---|
| G1 | Goal | Improve layer names where 084's heuristic is weak (flat-namespace legacy), via the LLM, optionally | `LLMLayerRefiner` renames the weak dependency-direction bands; opt-in, off by default | done |
| R1 | Scope | Behind the seam + the 090 cache; consumes 084's layers; refines names/boundaries | New `LayerRefiner` seam; `LLMLayerRefiner` in `onboarding_llm/` reusing `ContentHashCache`; renames names (boundaries deferred) | done |
| R2 | Scope | Opt-in; off by default; 084 remains the fallback | `CA_ONBOARDING_LAYER_REFINER` gates it; `None`/Identity default → 084 unchanged | done |
| AC1 | AC | Opt-in and deterministic via the content-hash cache; off by default | env opt-in; per-layer membership cache → replay; hermetic tests inject a fake client | done |
| AC2 | AC | Never runs in the per-PR gate (R4.1); core unaffected when off | no `code_atlas/**` LLM import (090's confinement sweep covers all core files); Identity default is a pure no-op | done |
| AC3 | AC | With refinement off, layer output is byte-identical to 084 | `refine_layers(..., IdentityLayerRefiner())` returns the 084 assignment verbatim; `to_json()` equality test | done |

### AC validation (falsifiability)
- **AC1** falsifiable — the proving test's second run uses a client that **raises if called**; a cache
  miss would surface as that exception, so green proves the rename replayed from cache.
- **AC2** falsifiable —090's `test_no_core_module_imports_an_llm` greps every `code_atlas/**` file for
  `anthropic`/`onboarding_llm`; 091 adds **no** core file, so that guard already covers it (and the
  count-pin `core_modules() == 51` stays green — the seam types live in the existing `layers.py`).
- **AC3** falsifiable — `test_off_by_default_is_byte_identical_to_084` asserts
  `refine_layers(base, m, Identity).to_json() == base.to_json()`; any drift goes red.

### Blast radius
- **New (outside core):** `onboarding_llm/layer_refiner.py`, `onboarding_llm/client.py` (shared
  client Protocol + `first_text`, extracted from `summarizer.py` for DRY); `tests/test_onboarding_llm_layers.py`.
- **Modified (core):** `code_atlas/onboarding/layers.py` — add `LayerRefiner` Protocol,
  `IdentityLayerRefiner`, `refine_layers` (existing file → **no new core module**, count-pins
  untouched); `main.py` (widen `build_server(..., layer_refiner=None)`); `architecture_overview.py`,
  `artifact.py`, `generate_onboarding.py` (thread + apply the refiner).
- **Modified (plugin/docs):** `onboarding_llm/{__init__,server,summarizer}.py` (export + wire + repoint
  to the shared client); `README.md`, `onboarding_llm/README.md`, `docs/BACKLOG.md`,
  `docs/phase3-onboarding/PHASE3_ONBOARDING.md`, `docs/LESSONS.md`, this working doc + frontmatter.
- **Untouched:** `store.py`, `contract.py`, `summary.py`, adapters, resolver, query tools; no contract
  or schema change; no `contract_version` bump. `pyproject.toml` unchanged (reuses the 090 `llm` extra).

`TRACK: backend` · `SCOPE: M` · `TIER: full` · `STRUCTURE: native`.

### RULE SECTIONS
`RULE SECTIONS: R1.1 · R1.2 · R4/R4.1 · R4.2 · R7.4`
- **R1.1** — no language branch; the refiner names layers from generic path/direction strings only.
- **R1.2** — a second enrichment seam, but each is forced by R4.1 and each ships with a 2nd
  implementer; no registry/factory (the entry point injects with one `if opted-in`).
- **R4/R4.1** — the LLM lives outside `code_atlas/`; deferred `anthropic` import; CI never runs it.
- **R4.2** — the layer cache is sorted-key content-hash JSON → byte-stable, committable; the applier is
  deterministic given the map.
- **R7.4** — no dead abstraction: `LayerRefiner` has `IdentityLayerRefiner` (default) + `LLMLayerRefiner`
  (ships now); `client.py` is shared by both LLM impls (DRY).

## Phase 2 — design

### Approach
1. **New seam in the existing `layers.py` (no new core module).** `LayerRefiner` Protocol
   (`refine_names(assignment, metrics) -> Mapping[str, str]`), `IdentityLayerRefiner` (returns `{}`),
   and `refine_layers(assignment, metrics, refiner)` — applies the rename map, renormalises ranks by
   the min original rank of each new name, preserves coverage, leaves `method` untouched (its pin
   covers `assign_layers`). Empty/inapplicable map → returns the input object unchanged (AC3).
2. **Thread through the composition root.** `build_server(config, summarizer=None, layer_refiner=None)`
   passes the refiner to `architecture_overview.create` and `generate_onboarding.create`;
   `architecture_overview` and `artifact.build_artifact` apply `refine_layers(assign_layers(m), m, r)`.
   Defaults resolve to `IdentityLayerRefiner` → 084 output unchanged.
3. **`onboarding_llm/` (outside core).** `layer_refiner.py` — `LLMLayerRefiner` refines only the
   **weak** layers (`source`/`sink`/`mixed`/`isolated`/`(root)`), each cached by membership;
   `anthropic` imported only in the factory. `client.py` — the shared client Protocol + `first_text`,
   extracted from `summarizer.py` (repointed) so the two LLM impls share one shape (DRY, R7.4).
   `server.py` — `build_layer_refiner(config, env)` returns `None` unless
   `CA_ONBOARDING_LAYER_REFINER ∈ {llm, claude}`.

### Rejected alternatives
1. **Reuse the 085 `Summarizer` seam** → rejected: it is node-grain (`NodeFacts -> Summary`); layers are
   aggregate. A forced fit would abuse the type.
2. **Refiner returns a whole `LayerAssignment`** → rejected: a bad LLM output could drop modules /
   scramble ranks; the core would re-validate everything. A rename map makes corruption
   unrepresentable (LESSONS 091-C1).
3. **Refine boundaries (re-group modules) now** → deferred: risks AC3 byte-stability + coverage; the
   ticket's target (flat namespaces) is a naming weakness. Recorded as a scope-limit.
4. **Refine every layer, not just weak ones** → rejected: a real directory name is already good; the
   top-tier pass is spent only where 084 is weak (matches PHASE3 §4 "on demand, budget the pass").
5. **`method += "+llm-refined"` for observability** → rejected: `LAYER_METHODS` is a pin cross-checked
   against `assign_layers` output (`test_onboarding_layers.py`); tagging would churn it. Refinement-on
   is an operator-known config fact, not a data concern.

### Smallest change-list
| change | file/area | Ph2 covered by |
|---|---|---|
| `LayerRefiner` + `IdentityLayerRefiner` + `refine_layers` | `code_atlas/onboarding/layers.py` | G1, R1, AC3 |
| widen `build_server(..., layer_refiner=None)` + thread | `code_atlas/main.py` | R2, AC2 |
| apply `refine_layers` in both consumers | `architecture_overview.py`, `artifact.py`, `generate_onboarding.py` | G1, R1 |
| `LLMLayerRefiner` (weak-only, membership cache) | `onboarding_llm/layer_refiner.py` | G1, R1, AC1 |
| shared client Protocol + `first_text` | `onboarding_llm/client.py` (+ repoint `summarizer.py`) | R7.4 |
| opt-in gate + deferred anthropic import | `onboarding_llm/server.py` | R2, AC1 |
| export + package docs | `onboarding_llm/__init__.py`, `README.md`s | R1, R2 |
| hermetic + AC3 + replay tests | `tests/test_onboarding_llm_layers.py` | AC1, AC2, AC3 |
| status + narrative + token row | `docs/BACKLOG.md` | bookkeeping |
| 091 shipped + 2nd-seam note | `docs/phase3-onboarding/PHASE3_ONBOARDING.md` | bookkeeping |

### Verification plan (per-AC)
| AC | proof artifact |
|---|---|
| AC1 | `test_cache_replays_without_a_second_call` — 2nd refiner's client raises if called; identical rename |
| AC2 | 090's `test_no_core_module_imports_an_llm` (covers all `code_atlas/**`); count-pin 51 green |
| AC3 | `test_off_by_default_is_byte_identical_to_084` — `refine_layers(base, m, Identity).to_json() == base.to_json()` |

### Proving test
`tests/test_onboarding_llm_layers.py::test_cache_replays_without_a_second_call`.

## Phase 3 — execute
Branch `feat/091-llm-layer-refinement` off `main`. Implemented exactly the approved change-list:

- **Core seam (no LLM name):** `layers.py` gains `LayerRefiner`, `IdentityLayerRefiner`,
  `refine_layers`. `main.py` widened to `build_server(config, summarizer=None, layer_refiner=None)`
  (imports the `LayerRefiner` *type* only). `architecture_overview.py` + `artifact.py` apply
  `refine_layers(assign_layers(m), m, refiner)`; `generate_onboarding.py` threads the refiner into
  `build_artifact`. Defaults → `IdentityLayerRefiner` → 084 output unchanged.
- **`onboarding_llm/` (outside core):** `layer_refiner.py` (`LLMLayerRefiner`, weak-only rename map,
  membership cache, deferred `anthropic`), `client.py` (shared client Protocol + `first_text`;
  `summarizer.py` repointed to it, its private copies removed), `server.py` (`build_layer_refiner` +
  opt-in gate), `__init__.py` (exports).
- **Tests:** `tests/test_onboarding_llm_layers.py` — 10 hermetic tests (fake client, no network):
  AC3 byte-identical, empty-map no-op, weak-layer rename + coverage, rank renormalisation, named-layer
  left-alone (0 LLM calls), cache replay (raising client), empty-generation skip-and-not-cached,
  malformed-entry-is-a-miss, committable sorted JSON, off-by-default gate (Windows-skip → Docker).
- **Docs:** BACKLOG (status + narrative + token row), PHASE3 (091 shipped + §3 2nd-seam note), LESSONS
  (091-C1), README + `onboarding_llm/README.md`, this doc.

### Verification sweep
**Axis 1 — file set.** `git status`: new `onboarding_llm/{layer_refiner,client}.py`, new
`tests/test_onboarding_llm_layers.py`, modified `code_atlas/onboarding/layers.py`, `main.py`,
`architecture_overview.py`, `artifact.py`, `generate_onboarding.py`,
`onboarding_llm/{__init__,server,summarizer}.py`, docs. **No new file under `code_atlas/`** → the
`core_modules() == 51` count-pins are untouched (confirmed: `test_core_is_language_agnostic` **103
passed**). `diff ⊆ approved change-list`; no recorded deviation.

**Axis 2 — design-conformance (per Approach bullet).** All `implemented-as-approved`: seam in
`layers.py` returns a rename map, renormalises ranks, `method` untouched ✅ · composition root widened
and threaded ✅ · `LLMLayerRefiner` weak-only + membership cache + deferred import ✅ · shared
`client.py` (DRY) ✅ · opt-in gate ✅. No `deviated` bullet.

**Empirical (Windows dev host):**
```
$ ruff check code_atlas onboarding_llm tests                        → All checks passed!
$ pytest tests/test_onboarding_llm_layers.py tests/test_onboarding_llm.py -q   → 67 passed
$ pytest tests/test_onboarding_layers.py tests/test_architecture_overview.py -q → 28 passed
$ pytest tests/test_core_is_language_agnostic.py -q                 → 103 passed (count-pin 51 intact)
```
Full-suite delta-green proven in **Docker** (the Windows `fcntl` exclusion): `scripts/docker-test.sh`
→ **1443 → 1453 passed, 0 failed** (+10 authored 091 tests), ruff clean, mypy clean including
`onboarding_llm` (51 source files — no new core module). (The opt-in `build_layer_refiner` test that
skips on Windows runs green here.)

`Ph3 proven by:` the 10 authored tests + the reused 090 confinement sweep pass; ruff clean; mypy clean
on the new package.

## Phase 4 — review (WAIVED by run args)
`CHALLENGER: OFF (--no-challenger)`. Review phase **waived** ("skipped review & challenger"). No
`mango:reviewer`/`mango:challenger` dispatched. In place of the review phase, a main-loop
self-verification sweep (above) confirmed: diff ⊆ approved list, every Approach bullet
implemented-as-approved, all matrix rows k=N, count-pins intact, rules R1.1/R1.2/R4/R4.1/R4.2/R7.4
satisfied. **Result recorded as `clean (self-verified — REVIEW & CHALLENGER: OFF by run args)`.**

### k/N + matrix close-out
G1 ✅ · R1 ✅ · R2 ✅ · AC1 ✅ · AC2 ✅ · AC3 ✅ — every row `k = N`.

## Phase 5 — finalise
Stale-review guard: review waived, so the guard is N/A (no `Reviewed at` marker); self-verification
covers the same tree. Ledger: **0 dispatch rows** (no subagent dispatched) — complete. Main-loop
spend **unmeasured (host does not surface usage)**.

### Cost ledger (subagent dispatch only)
| Dispatch | Tokens | Outcome |
|---|---|---|
| *(none — review & challenger waived; refine/analysis/design/execute all main-loop)* | — | — |
**Total dispatch: 0.** Main-loop unmeasured (host surfaces no usage block).

### Outward actions (maintainer standing approval + explicit run args cover these two)
1. **Commit** the code + tests + docs in logical units.
2. **Push** `feat/091-llm-layer-refinement` and **open the PR** from the template.
Merge, tracker transition, and branch deletion remain the maintainer's.

### Learning loop
`CLAIMS: 1 | T2=1 | 0 unclassified` — one durable, type-2, seen-once lesson recorded to
`docs/LESSONS.md` (091-C1 `seam-returns-constrained-delta-not-rebuilt-whole`): when a seam's implementer
may be an LLM, make invariant-violating outputs *unrepresentable* by returning a constrained delta (a
rename map) rather than a rebuilt whole the core must re-validate. `PROMOTION: 0` (seen once; promote
only at seen ≥ 2 via `/mango:promote`).
