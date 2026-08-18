---
id: 103
slug: onboarding-layer-granularity
title: Onboarding — layer granularity: strip common path prefix, group by top segment (M10)
phase: 3
milestone: M10
status: done
depends_on: [084]
---

> **Shipped in PR #122 (merged 2026-08-18) — with a known limitation, tracked by [104].**
> The common-root-segment heuristic fixes 084's over-fragmentation but **under-fragments** in the
> inverse direction: a single top-level file outside the dominant tree (e.g. `routes/web.php` beside
> `app/**`) empties the common prefix and collapses the whole application into one layer (retro F1).
> This shipped deliberately as **deterministic-but-limited scaffolding** — `assign_layers` has **no
> consumer until 086** (`architecture_overview`, still `todo`), so the defect reaches nothing. **104
> replaces the grouping with the dominant-subtree signal and must land before 086 consumes it.**

## Goal
Make the namespace-prefix layer heuristic (084) group modules at the **architectural** grain the ticket
intended, not the **deepest-directory** grain it currently uses. Today `_prefix(module)` takes the
immediate parent directory (`module.rpartition("/")`), so any real nested tree over-fragments: every
leaf directory becomes its own "layer". 084's fixtures are only two levels deep, so the defect is
invisible in tests but would surface on the first real repo.

This is a revision of behaviour **locked and merged in 084 (2026-08-11)** — it goes through the full
lifecycle as a deviation, not a hotfix. It is the cheapest possible moment to change: **no consumer
exists yet** (086 `architecture_overview` is still `todo`), so nothing depends on the current grain.

## Problem, concretely
- `src/App/Http/Controllers/UserController.php` and `src/App/Http/Requests/UserRequest.php` share the
  `Http` layer in any architectural reading, but `_prefix` puts them in `.../Controllers` and
  `.../Requests` — two layers, not one.
- The intended unit is the **top architectural segment** (Http, Domain, Infra), i.e. the first path
  segment **after the tree's common root**, not the last directory before the file.

## Scope / Deliverables
- Change `_prefix` (or introduce a prefix-derivation step in `assign_layers`) so a module's group is the
  **first path segment after stripping the longest common directory prefix** shared by all modules:
  - Compute the longest common directory prefix across every module `key` (POSIX `/`, whole path
    segments only — never a mid-segment character prefix).
  - Strip it, then take the first remaining segment as the layer key.
  - `src/Http/…`, `src/Domain/…`, `src/Infra/…` → common `src/` → `Http` / `Domain` / `Infra`.
  - `src/App/Http/Controllers/X`, `.../Http/Requests/Y`, `.../Domain/Z` → common `src/App/` →
    `Http` / `Http` / `Domain` (Controllers and Requests collapse into Http — the intended grain).
- Keep the existing **dependency-direction fallback** unchanged for the flat / single-prefix case.
- Extend `tests/test_onboarding_layers.py` with a **≥3-deep** fixture proving the collapse, plus the
  common-prefix edge cases below. The current 2-deep fixtures stay (regression pins).

## Acceptance criteria
- **AC1** — A ≥3-deep namespaced fixture where two sibling leaf dirs under one top segment land in the
  **same** layer; asserted on `layer` and `rank`. This test would fail against 084's `_prefix`.
- **AC2 (determinism, R4.2)** — byte-stable across shuffled input, same as 084's existing guard.
- **AC3 (language-agnostic, R1.1/R2)** — the derivation is pure string ops on POSIX paths; it hardcodes
  **no** directory name (`src`, `app`, `lib`, …). The root is *derived from the data*, never named.
- **AC4 (common-prefix edge cases)** — (a) no shared prefix → first segment of each path, no crash;
  (b) all modules under one dir → that dir is stripped, next segment is the layer; (c) a lone module →
  falls back cleanly (no empty layer key).
- **AC5** — the `isolated`-band and method-derivation guards still pass; `LAYER_METHODS` keeps its
  **arity (two members)** and its derived-not-listed pin (R6.7). Its first member is **deliberately
  renamed** `namespace-prefix` → `common-root-segment` (ASSUMED‑2, ratified at PR); "unchanged" here
  means the shape/guard, **not** the literal string. (Clarified after the review challenger flagged the
  original wording as ambiguous against the rename.)

## Out of scope
- LLM layer-name refinement (that is 091).
- Any change to 083 metrics or the `Summarizer` seam (085).

## References
- Revises [`084_onboarding-layer-assignment.md`](084_onboarding-layer-assignment.md); the locked
  heuristic is "namespace/dir prefix refined by dependency direction".
- `code_atlas/onboarding/layers.py` (`_prefix`, `_by_prefix`, `assign_layers`).
- PLAN §14, §15 (M10). Determinism R4.2; language-agnostic core R1.1/R1.5/R2.

---

## Session status
- **Runner:** `/mango:autorun 103` (unattended lifecycle, stops at the PR; challenger ON).
- **Handover authorisation:** the two outward actions (push branch, open PR) are covered by the
  maintainer's standing durable approval in `AGENTS.md` (*Maintainer workflow*) plus the explicit
  "chạy autorun" instruction. Recorded in `.mango/run-contract-103.txt`.
- **Envelope:** RUN CONTRACT written + validated at t0; RECONCILE t0 clean (2 BROKEN bound floor
  conditions, 2 UNBOUND — TREE-COMPARISON + PROVING-TEST, 0 holding → no strikes). Merge-strategy:
  squash-or-rebase (25 first-parent commits since newest merge). Call-ceiling: **unknown** (no token
  budget supplied — recorded, not invented). Windows note: floor POSIX checks wrapped in `bash -c`.
- **Phase:** 5 finalise — pushing the branch + opening the PR (the two pre-authorised outward actions);
  then RECONCILE at close. Full Docker gate green (1299 passed, mypy 44, ruff clean). Review clean
  (reviewer LGTM + challenger 2 findings fixed). Challenger ON.
- **Next action (maintainer):** review & **merge PR [#122](https://github.com/cuongdinhngo/code-atlas/pull/122)**
  (squash); ratify the 2 proposed learning-loop claims (or discard); on merge, flip 103 status → done.
- **Revert path:** unmerged → close the PR + `git push origin --delete feat/103-onboarding-layer-granularity`.
  Merged → revert the single squash-merge commit on `main` (no schema/contract/tool change to undo).
- **work_doc_mode:** embed. **Branch:** `feat/103-onboarding-layer-granularity`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: S` · `TIER: full`.

## Phase 0 — refine (did NOT skip)

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 2 ASSUMED | skip: no`

- **Premise (all resolve):** `code_atlas/onboarding/layers.py` (`_prefix`:59, `_by_prefix`:66,
  `assign_layers`:93), `tests/test_onboarding_layers.py`, `docs/tasks/084_...md`, rules R1.1/R1.5/R2/R4.2,
  `docs/PLAN.md` §14/§15. No `PREMISE FALSIFIED`.
- **Why refine did NOT skip:** a ticket-blind exposure-checker (1 dispatch, ticket-blind challenger)
  raised **5 raw items** that consolidate to **3 distinct product-decisions**: the fallback trigger
  under the new scheme + the boundary/near-flat edge (checker #1/#2/#5, one underlying decision),
  segment-wise-vs-character-wise prefix (#3, a HOW), and the emitted `method` label (#4). This is the
  autorun-quality signal: a maintainer-approved-looking ticket still hid product decisions in the
  **byte-stable output contract** that a future consumer (086) would lock onto.

**Settled wants (want-decision — from the user).** None asked: the maintainer declined the menu and
delegated ("you can suggest the best options"), so the two want-decisions are recorded **ASSUMED** below.

**Resolved direction + citation (how-decision — refine-resolved + CITED):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Common-prefix computed on path **segments** or raw **characters**? | **Segment-wise** — whole path components only; `src/Http` shares no prefix with `src/HttpUtils` | ticket AC4 ("whole path segments only — never a mid-segment character prefix"); reintroduces the over-fragmentation bug otherwise |

**ASSUMED (awaiting ratification) — confirmed by the maintainer at the PR (they merge):**

| # | Assumed choice | Why ASSUMED | Confirm at | Reverses a prior decision? |
|---|----------------|-------------|------------|----------------------------|
| 1 | **Fallback trigger = Conservative.** Use the prefix path only when the tree yields **≥2 non-empty named groups** after stripping the common segment prefix; any boundary file directly in the common-root dir, or <2 clean groups → **dependency-direction fallback**. Never emit an empty-string or sentinel layer. | Maintainer delegated ("suggest best options"); keeps output contract clean + preserves 084's flat→direction behavior | PR review | no (084 never decided this edge; fixtures 2-deep) |
| 2 | **Rename emitted `method` label** `"namespace-prefix"` → `"common-root-segment"`; update `LAYER_METHODS` + the derived-not-listed test. | Same delegation; new grouping semantic differs from "namespace/dir parent"; cheapest now (no consumer) | PR review | changes an output label 084 shipped, but **no consumer exists yet**; not an explicit prior human want |

**Recalled claims (ADVISORY — surfaced only):**

| # | Claim | Type | Matched by (handle) | Relevant here? |
|---|-------|------|---------------------|----------------|
| 1 | LESSONS **009** — a green negative control is a question, not a verdict; a fixture discovered *in order* makes a test too weak to see its own subject | 2 | determinism / fixture-ordering | **Yes** — 103's new ≥3-deep fixture must provably exercise the collapse, and the byte-stability guard must shuffle input; a fixture that passes by accident of order proves nothing |
| 2 | LESSONS **084-C1** — judge a piped command's result by its output, not the pipe's exit status | 2 | test-runner / Docker gate | **Yes** — run the Docker delta-green gate without piping through `tail`; read ruff/mypy/pytest output directly |

**Constraints surfaced from the scan:**
- 103 **modifies** `layers.py` (existing) — it adds **no new core module**, so the `len(core_modules()) == 44`
  pin in `test_sql_confinement.py:32` + `test_core_is_language_agnostic.py:42` **stays 44** (no bump; unlike 084's 43→44).
- R1.1/R2: the derivation must hardcode **no** directory name (`src`, `app`, `lib`) — the common root is
  derived from the data. R7.5: comments ≤3 lines. Lines ≤100 chars.
- Pre-existing uncommitted work folded into this branch: the `isolated`-band test added to
  `tests/test_onboarding_layers.py` during the 084 review (a pure coverage addition; 103 AC5 keeps it).

**Exposure-checker** (ticket-blind challenger, 1 dispatch): raised 5 items → 3 distinct decisions
(2 ASSUMED, 1 how-cited above). No other undecided product choice surfaced. Cost-ledger row below.

## Phase 1 — analysis

Premise + recall carried forward from Phase 0 (not re-run):
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

### Decompose
`SECTIONS: 5 found (Goal, Scope/Deliverables, Acceptance criteria, Out of scope, References) | 5 decomposed | ROWS: C=2 R=2 G=1 AC=5 (Out-of-scope + References = context)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | Group modules at the **architectural** grain (first segment past the common root), not the deepest dir | Replace deepest-parent `_prefix` with common-segment-prefix-stripped first segment | `layers.py:59-63` `_prefix` uses `rpartition` | ✅ planned |
| R1 | Scope | Group = **first path segment after stripping the longest common directory prefix** (whole segments) | Compute LCP of dir-segment lists over all modules; group = first remaining segment | `layers.py:66-79` `_by_prefix` | ✅ planned |
| R2 | Scope | Keep the **dependency-direction fallback** unchanged for flat / single-group | `_by_direction` untouched; only the trigger changes | `layers.py:82-90` `_by_direction` | ✅ planned |
| C1 | Scope/AC3 | Deterministic (R4.2) + language-agnostic, **hardcodes no dir name** (R1.1/R2) | Pure segment string ops; common root derived from data, no `src`/`app` literal | R1.1; `test_core_is_language_agnostic.py`; R4.2 | ✅ planned |
| C2 | ASSUMED-2 | Rename `method` label `namespace-prefix` → `common-root-segment` | Update `LAYER_METHODS[0]` + the emitted method + derived-not-listed test | `layers.py:19,107`; `test_...:97-106` | ✅ planned |
| AC1 | AC | ≥3-deep fixture: two sibling leaf dirs under one top segment share **one** layer; fails vs 084 `_prefix` | New unit test (Http/Controllers + Http/Requests → "Http") | — | ⏳ proving test (design) |
| AC2 | AC | Byte-stable across shuffled input (R4.2) | Shuffle + byte-compare `to_json`, **over the deep fixture** (lesson 009: prove the NEW code) | R4.2; existing byte-stable test | ⏳ proving test |
| AC3 | AC | Language-agnostic; hardcodes no dir name | Existing grep-gate + reviewer confirms no dir literal; derivation is data-driven | `test_core_is_language_agnostic.py:48` | ✅ planned |
| AC4 | AC | Edge cases: (a) no shared prefix; (b) all under one dir; (c) boundary/lone → clean fallback, no empty layer | Unit tests incl. the **conservative** boundary-file → direction fallback (ASSUMED-1) | — | ⏳ proving test |
| AC5 | AC | `isolated`-band + derived-not-listed guards still pass; `LAYER_METHODS` stays **2** members | Existing tests unchanged; count assertion | `test_...:79-113` | ✅ planned |

### AC validation (falsifiability)
- **AC1** — falsifiable: a ≥3-deep fixture asserts Controllers+Requests collapse into "Http"; would fail against 084's deepest-parent `_prefix`. ✅
- **AC2** — falsifiable: compute twice over shuffled input, byte-compare `to_json`. Strengthened per **lesson 009** — the shuffle runs over the **deep** fixture so the *new* common-prefix code (the determinism-sensitive addition) is what's proven order-independent, not only the old 2-deep path. ✅
- **AC3** — "hardcodes no dir name" — the language-name grep-gate (`test_core_is_language_agnostic`) covers language tokens; the stronger "no `src`/`app` dir literal" is **falsifiable-by-inspection** (the reviewer confirms the common root is derived from the module set, no directory string literal) — recorded as such, **not** a bare ✅. ✅
- **AC4** — falsifiable: unit tests for no-shared-prefix (top dirs become layers), all-under-one-dir (dir stripped), and the **boundary/lone → dependency-direction fallback** (ASSUMED-1, conservative: never emits an empty/sentinel layer). ✅
- **AC5** — falsifiable: existing `isolated` + derived-not-listed tests must stay green; `len(LAYER_METHODS)==2`. ✅

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`j = 0` — the two product-decisions are recorded **ASSUMED** (maintainer delegated: "you can suggest the best options"), not open clarifications; ratified at the PR. No stated-vs-computed acceptance-value mismatch. Gate 0 clear → autorun proceeds.

### Universal inventory
R1.1/AC3 "no language branch / no hardcoded name" is universal but **covered by the existing CI grep-gate** (`test_core_is_language_agnostic`), not a per-item checklist. N (new core modules) = **0** — 103 modifies `layers.py` only. AC4 is multi-clause (3 edge clauses) → **one proof row per clause** at design, never one aggregate row.

### Cause / gap (enhancement)
Gap: `_prefix` (`layers.py:59-63`) returns the **deepest** parent dir (`module.rpartition("/")[0]`), so a nested tree fragments — every leaf dir is its own layer, contradicting the "architectural layer" intent (G1). 084's fixtures are 2-deep, hiding it. Target: derive each module's group from the **first segment past the longest common dir-segment prefix**; fall back conservatively when the tree doesn't cleanly split.

### Blast radius
- **Modified:** `code_atlas/onboarding/layers.py` (`_prefix`→common-prefix helpers; `_by_prefix`; `assign_layers` trigger; `LAYER_METHODS[0]`; header docstring). `tests/test_onboarding_layers.py` (update the 2-deep namespaced test's expectations; add AC1 deep + AC4 edge + AC2 deep-byte-stable tests; keep isolated/derived-not-listed).
- **Untouched:** `metrics.py`, `store.py`, `main.py`, `contract.py`, adapters, resolver. **No count-pin change** — module count stays **44**, so `test_sql_confinement.py:32` + `test_core_is_language_agnostic.py:42` are **NOT** touched (smaller blast radius than 084's 43→44).

### Baseline
`BASELINE: green — 100 passed` (scoped `pytest tests/test_onboarding_layers.py tests/test_sql_confinement.py tests/test_core_is_language_agnostic.py`, bare on the untouched checkout — these three modules import only `metrics`/`layers`/`contract`, no `fcntl`, so no Docker needed at this grain). DoD for later phases = **prove the delta is green** (the full Docker gate is run at execute/finalise per 084-C1: read output, don't pipe through `tail`).

### TRACK
`TRACK: backend — 0/2 touched files under UI paths (pure Python compute + tests)`

### Rule-compliance coverage
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §1.1 (change-type) ✅ | §1.2 (change-type) ✅ | §1.4 (change-type) ✅ | §4.1 (change-type) ✅ | §4.2 (change-type) ✅ | §6.1 (change-type) ✅ | §6.6 (change-type) ✅ | §7.5 (change-type) ✅ | §6.7 (recalled handle derived-not-listed-invariant) ✅`
- **§1.1** — the new grouping is pure segment string ops over generic paths; **no** `if language==`, no dir-name literal; CI grep-gate bites (AC3).
- **§1.2** — YAGNI: two small module-private helpers (`_common_dir_prefix`, `_group_key`); **no** registry/base-class/factory/DI, no new seam.
- **§1.4** — SRP: `layers.py` still imports no sqlite; SQL stays in `store.py` (`test_sql_confinement`).
- **§4.1** — no LLM/network added (091 is separate).
- **§4.2** — byte-stable over identical input; the common-prefix fold is order-independent (no set-ordering/wall-clock leak); proven over the deep fixture (lesson 009).
- **§6.1** — fixture tests: deep collapse (AC1) + edge/fallback (AC4) + byte-stability (AC2).
- **§6.6** — mypy strict clean: `_group_key` returns `str | None`; the trigger narrows to `dict[str, str]` before `_by_prefix` (no `Optional` key into `rank_of`).
- **§7.5** — comments ≤3 lines; lines ≤100 chars (current file: 0 over 100).
- **§6.7 (recalled handle `derived-not-listed-invariant`)** — renaming `LAYER_METHODS[0]` must keep the derived-not-listed pin true: the emitted method and the tuple change together, and `test_layer_methods_are_derived_not_listed` re-derives the produced set. Bites on `layers.py:19,107`.
- **N/A:** §1.3/§1.5/§1.6/§1.7 (no adapter seam / capability / persistence), §2.x (not an adapter), §3.x (`contract.py` untouched — no vocab change), §4.3 (no SQL), §5.x (pure in-memory), §8.x (stdlib only).

### Declarations
`STRUCTURE: native` · `SCOPE: S` · `TIER: full` · `TRACK: backend`
- **SCOPE: S** — one source file (~15-line logic change) + its test file; no new module, no count-pin, no contract change. Smaller than 084 (M).
- **TIER: full** — not lite-eligible: 2 files, 5 ACs / multi-clause proof, and it **revises a merged/locked output contract** (084) — precisely where the challenger + review earn their keep. Routes through the full five-phase flow.

## Phase 2 — design

### Approach
Compute the **longest common leading run of whole directory segments** across every module's path, once,
in `assign_layers`. A module's group = the **first directory segment past that common prefix**; a file
sitting directly in the common-prefix dir (no further segment) has **no group** (`None`). Use the
prefix path (`_by_prefix`, ordered by net dependency direction — unchanged) **only when the tree splits
cleanly**: every module has a group AND ≥2 distinct groups exist. Otherwise fall back to the untouched
`_by_direction`. Layer name = the group segment (e.g. `"Http"`). Method label → `"common-root-segment"`.

New module-private helpers: `_dirs` (segments, filename dropped), `_common_dir_prefix` (order-independent
fold), `_group_key` (first segment past the common prefix, or `None`). `_prefix` is removed. `_by_prefix`
takes a precomputed `dict[str, str]` group map (so the `str | None` is narrowed before `rank_of`).

### Rejected alternatives
- **First path segment always** (`path.split("/")[0]`): collapses everything under a shared root like
  `src/` into a single `"src"` layer — no architectural grain at all. Rejected.
- **Fixed depth** (e.g. always the 2nd segment): not repo-agnostic — breaks on any repo whose root depth
  differs, and bakes in a structural assumption (violates R2 "encode the standard, not a sample"). Rejected.
- **Character-wise common prefix** (`os.path.commonprefix`): would treat `src/Http` and `src/HttpUtils`
  as sharing `src/Http`, reintroducing a subtler over-fragmentation. Rejected (how-decision #1: segment-wise).

### Assumptions
| Assumption | Tag | Evidence |
|---|---|---|
| `NodeMetric.key` at module grain is a **POSIX-normalised `file_path`** (so `split("/")` is language-agnostic) | verified | module unit = `file_path`, POSIX-normalised, locked 2026-08-11 (084 doc; `metrics.py` module grain) |
| The common-prefix fold is **order-independent** (byte-stable input→output, R4.2) | verified | it is a repeated leading-run intersection over a set; proven by the AC2 shuffle test over the deep fixture |
| No LLM / network / 3p / runtime behaviour is involved | verified | pure stdlib string ops in a pure function |

No `novel-untested` third-party/runtime assumption → no spike required; Gate 2 is not blocked on one.

### Smallest change-list
| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Remove `_prefix`; add `_dirs` / `_common_dir_prefix` / `_group_key` | `layers.py:59-63` | module-private; only caller is `_by_prefix`/`assign_layers` (traced below) | G1, R1, C1 | 1/1 |
| 2 | `_by_prefix` takes a `dict[str,str]` group map; ranks/names by group segment | `layers.py:66-79` | output layer **names** change (`src/Http`→`Http`); only consumer is the test (traced) | R1, C1 | 1/1 |
| 3 | `assign_layers` trigger: usable = all-grouped AND ≥2 distinct; else fallback | `layers.py:93-112` | changes which path fires on the boundary/near-flat case (ASSUMED-1) | R2, AC4 | 1/1 |
| 4 | Rename `LAYER_METHODS[0]` + emitted method → `"common-root-segment"` | `layers.py:19,107` | derived-not-listed pin (§6.7); proof collateral #6 | C2, AC5 | 1/1 |
| 5 | Header docstring: "namespace/dir prefix" → "common-root segment" wording (≤3-line comments) | `layers.py:1-8` | doc only | C2 | 1/1 |
| 6 | **Proof collateral:** update the 2-deep namespaced test's expectations (`method`, layers `Http/Domain/Infra`) at `test:52-63`; the `namespace-prefix` assert at `test:54` | `tests/test_onboarding_layers.py` | the single consumer of `assign_layers` | AC1, AC5 | 1/1 |
| 7 | Add AC1 deep-collapse test, AC4 edge tests (no-shared-prefix, all-under-one-dir, boundary→fallback), AC2 deep byte-stability (shuffle) | `tests/test_onboarding_layers.py` | new tests | AC1, AC2, AC4 | 1/1 |

Every item traces to a matrix row. The `isolated`-band + derived-not-listed + flat-fallback + FALLBACK-order tests stay unchanged (AC5).

`HANDLES: 2 recalled | 0 traced | 2 does not apply (reason) | 0 unanswered`
- **`derived-not-listed-invariant` (009-adjacent / R6.7)** — *does not apply because* it is not a shared-symbol blast-radius trace: no external consumer imports `LAYER_METHODS` (traced: only `test_onboarding_layers.py`). Its content **is** honored — change-list #4 renames the tuple and the emitted method together, and `test_layer_methods_are_derived_not_listed` re-derives the produced set (AC5).
- **lesson 009 (fixture reached in-order → test too weak)** — *does not apply because* it constrains **test design**, not a code producer/consumer to fold into the change list. Honored in the AC2 verification-plan row: the byte-stability shuffle runs over the **deep** fixture, so the *new* common-prefix code is what's proven order-independent.

*(Blast-radius commands run, verbatim results:* `grep -rn assign_layers\|LayerAssignment code_atlas/ tests/` → only `tests/test_onboarding_layers.py`; `grep -rn namespace-prefix` → `layers.py:19,107` + `test:54` + docs; `grep importer onboarding.layers` → only the test. `mypy code_atlas/onboarding/layers.py` → *No issues found.)*

### Rule compliance
Per Phase-1 `RULE SECTIONS` (9 applicable, all ✅/N/A). Design-specific: §6.6 mypy — `_group_key -> str | None`; `assign_layers` builds `groups: dict[str, str | None]`, checks `None not in groups.values()`, then passes a narrowed `dict[str, str]` to `_by_prefix` (no `Optional` reaches `rank_of`). §4.2 — the fold is a set intersection, no ordering leak.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 (deep collapse) | logic | unit (deep fixture) | ✅ |
| AC2 (byte-stable) | logic | unit (shuffle + byte-compare over deep fixture) | ✅ |
| AC3 (no dir literal / language-agnostic) | logic | unit grep-gate (`test_core_is_language_agnostic`) + **manual-recorded** (reviewer confirms common root is data-derived, no `src`/`app` literal) | ✅ |
| AC4 (edge: no-prefix / one-dir / boundary→fallback) | logic | unit (3 clauses, one assertion each) | ✅ |
| AC5 (isolated + derived-not-listed intact; LAYER_METHODS==2) | logic | unit (existing + count) | ✅ |

No integration/runtime/e2e risk — all pure in-memory deterministic functions. **No ❌** in the plan.

### Proving test (at the logic layer)
`test_deep_tree_collapses_sibling_leaf_dirs_into_one_layer` — a ≥3-deep fixture (`src/App/Http/Controllers/*`,
`src/App/Http/Requests/*`, `src/App/Domain/*`) asserting Controllers+Requests both land in layer `"Http"`
and `method == "common-root-segment"`. **Fails pre-change** (084's `_prefix` yields `.../Controllers` and
`.../Requests` as separate layers), **passes post-change**. Invocation:
`python -m pytest tests/test_onboarding_layers.py -k deep_tree_collapses -q`.

### Rollback + porting
- **Rollback:** unmerged → close the PR + `git push origin --delete feat/103-onboarding-layer-granularity`.
  Merged → revert the single squash-merge commit on `main` (no schema/contract/tool change to undo).
- **Porting:** none — single repo (`app`), pure core module; no adapter/shared code.

### SCOPE
`SCOPE: S` (re-affirmed) — one source file + its test file; no new module, no count-pin, no contract change. Did **not** outgrow its ticket.

## Phase 3 — execute

### Implemented (approved change list only)
- `layers.py`: removed `_prefix`; added `_dirs` / `_common_dir_prefix` (order-independent segment fold,
  `zip(..., strict=False)`) / `_group_key` (`str | None`); `_by_prefix` now takes a `dict[str, str]`
  group map; `assign_layers` computes the common prefix once, uses the prefix path only when **every
  module is grouped AND ≥2 distinct groups** else falls back; `LAYER_METHODS[0]` + emitted method →
  `"common-root-segment"`; header docstring reworded. `_by_direction` untouched.
- `tests/test_onboarding_layers.py`: updated the 2-deep namespaced test to the segment grain
  (`Http/Domain/Infra`, method `common-root-segment`); added the AC1 proving test + 4 tests (no-shared-
  prefix, multi-segment root, boundary→fallback, deep byte-stability). Kept the flat, isolated,
  derived-not-listed and FALLBACK-order tests.

### Verification sweep — EMPIRICAL OUTPUT
**Axis 1 (file set):** `git status --short` → `M layers.py · M BACKLOG.md · M test_onboarding_layers.py ·
?? docs/tasks/103_...md` (+ untracked `.mango/` envelope). **diff ⊆ approved change list ✅**; no
untouched-line reformatting; each hunk maps to a matrix row.

**Axis 2 (design-conformance):** every Gate-2 Approach bullet `implemented-as-approved` — LCP computed
once; group = first segment past the common prefix; conservative trigger (all-grouped ∧ ≥2 distinct);
`_by_direction` untouched; method renamed. **0 deviations.**

**Proving test** — `python -m pytest tests/test_onboarding_layers.py -k deep_tree_collapses -q` →
`1 passed, 11 deselected`. Fails against 084's `_prefix` (which yields `.../Controllers` + `.../Requests`
as two layers); passes post-change (both → `Http`).

**Local scoped** (bare) — `pytest test_onboarding_layers.py test_sql_confinement.py test_core_is_language_agnostic.py -q` → `105 passed` (baseline 100 + 5 new). `mypy layers.py` → `no issues`. `ruff` → `All checks passed!`.

**Full Docker gate** (`scripts/docker-test.sh`, exit 0 read directly — lesson 084-C1, not piped) —
```
All checks passed!                              (ruff)
Success: no issues found in 44 source files     (mypy)
1299 passed in 73.41s                           (pytest)
```
**BASELINE was green → DoD met: the delta is green** (0 new failures; module count still 44, no pin touched).

### Design-invalidation / deviations
None. No escalation triggered (proving test passed first try; stuck-counter 0).

## Phase 4 — review

`CHALLENGER: ON` (default). Two subagents, ref-based read-only on the committed diff.

- **reviewer** (Sonnet — cost_tier standard, diff touches no auth/access/schema) → **LGTM**, no
  Critical/Important. Traced every edge case (empty set, single module, boundary, no-shared-prefix,
  multi-segment root, deep tree); confirmed R4.2 order-independence (the fold is a set intersection;
  every downstream dict consumed via `sorted`), R1.1/R2 (no hardcoded dir name), R1.4 (no SQL), R6.7
  (LAYER_METHODS rename consistent), R7.5 + ≤100 chars, mypy/ruff clean. Minor nit (the `keyed` filter
  is "redundant") — **kept**: it narrows `str | None`→`str` for mypy strict, not truly redundant.
- **challenger** (ticket-blind) → 8 met, **2 not-met on tested deliverables** + 1 ambiguity + 1 flag:
  1. **AC1 rank** — proving test asserted `layer` only, not `rank`. **Fixed** (`test_deep_tree_...` now
     asserts `(layer, rank)` tuples) — commit `0dcb5b1`.
  2. **AC4(c) lone-module** — behavior correct (challenger probed it) but **no test**. **Fixed**
     (`test_single_module_falls_back_cleanly_with_no_empty_layer`) — commit `0dcb5b1`.
  3. **AC5 "LAYER_METHODS unchanged (still two members)"** — ambiguous vs the rename. **Reconciled** in
     the ticket AC5 (arity + derived-not-listed guard, not the literal string; rename is ASSUMED‑2).
  4. **Boundary-file trigger** — flagged as beyond AC4(a/b/c); it is **ASSUMED‑1** (disclosed), which
     the ticket-blind challenger could not see. Not a violation.

**Verify-only re-review** (main-loop, no re-dispatch — fixes stayed inside the named findings, touching
only the test file + the exempt ticket doc): affected proof + regression scan → **106 passed**; both
proving tests green with rank; ruff/mypy clean.

### Clean decision
Clean: reviewer no Critical; every challenger not-met **fixed** (none deferred as an exclusion); no
layer-match ❌ (all ACs logic-layer, unit-proven); `k = N` on the matrix; proving test green.

**`Reviewed at 0dcb5b1`** — files reviewed: `code_atlas/onboarding/layers.py`,
`tests/test_onboarding_layers.py` (+ verify-only re-run after the fix commit). Working-doc path
(embedded): `docs/tasks/103_onboarding-layer-granularity.md` — **exempt** from the staleness comparison,
along with `docs/BACKLOG.md`/`docs/LESSONS.md` bookkeeping.

## Phase 5 — finalise

**Stale-review guard:** `git diff --name-only 0dcb5b1..HEAD` empty; uncommitted = only the embedded
working doc (exempt) + untracked `.mango/` envelope → **not stale**. Proceed.

### Cost ledger (subagent dispatch only — main-loop unmeasured on this host)
| Phase | Dispatch | Tokens | Tool-uses / s | Result |
|---|---|---|---|---|
| refine | exposure-checker (ticket-blind challenger) | 38.9k | 3 / 103s | raised 5 items → 3 product-decisions |
| review | `mango:reviewer` (Sonnet) | 77.1k | 22 / 295s | **LGTM**, no Critical/Important |
| review | `mango:challenger` (ticket-blind) | 59.5k | 13 / 259s | 8 met / 2 not-met (fixed) / 1 ambiguity (fixed) |

`LEDGER TOTAL: 175.4k dispatch · top cost driver: review/reviewer (77.1k)`. Main-loop **unmeasured**
(host surfaces no usage block). Ledger complete: 3 dispatches, 3 rows, every token cell filled.

### Learning loop
`CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true | 0 falsified | 0 not cheaply checkable`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed | 0 cannot promote | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

**Proposed claims (status: proposed — awaiting maintainer confirm; NOT yet written to `LESSONS.md`):**
1. **[type 5, environment · area: mango-autorun-windows · verified-at 2026-08-18]** mango's RECONCILE
   floor checks run under **cmd.exe** on this Windows host (`run_contract.py` uses `subprocess.run(shell=True)`
   → COMSPEC), so a POSIX check (`test "$(…)"`, `&&`, `>/dev/null`) misbehaves at `close --prove`. Wrap
   `LOCAL-HEAD-PUSHED` in `bash -c "…"` in the contract (bash is reachable from cmd.exe here) so the
   floor flips correctly. **Why:** the first three autoruns (083/084/102) used `solve`/never hit `--prove`;
   103 is the first to bind the POSIX floor for a close reconcile.
2. **[type 2, process · handle: ticket-blind-proof-completeness · seen: 103]** A self-authored ticket
   with explicit ACs still shipped a proving test that asserted *layer* only (AC said "layer **and**
   rank") and left AC4(c) untested — the ticket-blind challenger's per-AC reconstruction caught both
   proof-completeness gaps the author's own tests missed. **How to apply:** value the challenger even
   (especially) when the ticket looks well-specified; its independence is on the *proof*, not just the code.

Neither claim is recurring (both `seen`-once / new) → no promotion this run; both surfaced for the
maintainer to ratify into `LESSONS.md` (or discard). `/mango:promote` not applicable (no `seen ≥ 2`).
