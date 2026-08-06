---
id: 043
slug: duplicate-decl-resilience
title: Duplicate-declaration resilience — a repeated qualified_name must not abort the build
phase: 1.5
milestone: Robustness
status: in-progress
depends_on: [004, 009]
---

## Goal
A single source file that declares the same symbol name twice must **not** abort the whole build. Real
PHP does this legally and often — conditional definitions (`if (!function_exists('f')) { function f(){}
}`, `class_exists` guards), PHP-version branches, and interface/class same-name test fixtures. Static
parsing emits two nodes with the same `qualified_name` for one file, which trips the store's
`UNIQUE(qualified_name, file_path)` and raises `sqlite3.IntegrityError`. That error is unguarded in the
writer, so it kills `full_build` entirely — a **violation of R5.1** ("a bad *file* is a soft failure and
the stream continues"). Surfaced by a full-build validation against a large private PHP monorepo (24
offending files, real app code among them).

## Scope / Deliverables
- **Store-side keep-first dedupe.** In `store.replace_file_rows`, before insert, drop nodes whose
  `qualified_name` already appeared **for this file**, keeping the first occurrence. Leave `NULL` /
  anonymous qnames untouched (SQLite treats NULLs as distinct, so they never collide).
- **Deterministic.** Adapters emit in source order; keep-first is stable → identical input, identical
  rows (R4).
- **Optional transparency.** Count deduped nodes and surface the count (build report / task 028
  `index-health`) rather than dropping silently.
- **Optional defense-in-depth (may split out).** Guard the per-file store write in `indexer._write`
  so *any* future per-file store error becomes a soft failure (`parsed_ok=0`), never a build abort —
  the dedupe fixes the known case, the guard closes the class.

## Constraints
- Dedupe key is exactly the UNIQUE key `(qualified_name, file_path)`; within one file `file_path` is
  constant, so it reduces to `qualified_name`. This is **language-agnostic** — it lives in the store
  (SRP, R1.4) and adds **no** language branch to the core (R1.1).
- Restores **R5.1**: a duplicate-declaration file soft-fails at worst, the build continues.
- Keep-first, not skip-file: the symbol must stay resolvable (the common polyfill/guard case indexes
  one real declaration); dropping the whole file would lose real app code.
- Deterministic (R4): identical input → identical rows.

## Acceptance criteria
- A fixture file with a conditional double-definition (`function f` twice) **and** an
  `interface X {}` + `class X {}` pair: `full_build` completes with **no** `IntegrityError`, the file
  is `parsed_ok=1`, and each duplicated name resolves to exactly **one** node (asserted).
- Store unit test: `replace_file_rows` given two same-qname nodes for one path persists exactly one,
  deterministically the first (asserted).
- Re-running the build on the same tree yields identical rows (determinism, asserted).
- (If the defense-in-depth guard is included) a simulated per-file store error marks that file
  `parsed_ok=0` and the build still completes (asserted).

## References
`code_atlas/store.py:59` (`UNIQUE(qualified_name, file_path)`), `:242-254` (`replace_file_rows`),
`:256-263` (`_insert`); `code_atlas/indexer.py:590-600` (`_write`, unguarded store call),
`:565-573` (the soft-fail path for a bad parse/adapter — the asymmetry this task removes).
R5.1 (bad file soft-fails), R1.1 (no core language branch), R1.4 (store owns SQLite), R4
(determinism). Origin: large-private-monorepo full-build validation (duplicate-qualified_name abort);
sibling optional follow-up = parser-OOM size cap for multi-MB generated files (see BACKLOG follow-ups).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 043

## Session status
- **Phase:** 4 (review) **CLEAN** (Gate 4 approved). Reviewed at `aadc569`. → finalise, awaiting **✋ final gate**.
- **work_doc_mode:** embed → this doc lives below the separator in `docs/tasks/043_duplicate-decl-resilience.md`.
- **Branch:** `fix/043-duplicate-decl-resilience` — source in commits `651b3f1` (fix) + `aadc569` (docs); working-doc/BACKLOG bookkeeping pending its own commit.
- **Next action:** finalise — record token spend (working-doc ledger + BACKLOG table), sync 043 status, then per-action approval for push / PR.

## Decision log
- **D1 (Gate 1):** include the `indexer._write` defense-in-depth guard in this ticket (not split). Human-approved.
- **R3 surfacing (Gate 2 proposal):** implement "not silent" via `replace_file_rows` returning the dropped count + a store test asserting it; **defer** threading `deduped` into the frozen `BuildReport`/`asdict` tool response + its tests to an optional follow-up (keeps the change surgical; R3 is marked optional).

## Phase 1 — Analysis

`SECTIONS: 5 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

`STRUCTURE: native`
`BASELINE: red — 56 pre-existing failures on this Windows host, ALL adapter-subprocess launch (adapter.start → subprocess.Popen → CreateProcess WinError 2; shlex(posix=False) leaves literal quotes around sys.executable/script path). Unrelated to 043 and OUTSIDE its change surface (store dedupe + writer guard touch no subprocess). Delta-green DoD: introduce no new failure; new store/_write tests pass on this host. 603 passed / 98 skipped otherwise.`
`TRACK: backend — 0/N touched files under UI paths`
`SCOPE: S`
`TIER: full` (2 source files + 2 test files, 4 ACs — not a single-file/single-requirement change; cost_tier=standard → Sonnet reviewer; not security-tagged)
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision` → **no Gate 0**; both self-resolved items are surfaced at Gate 1 as decisions/《FYI》 below.

### Requirements matrix

| ID | Src | Verbatim (condensed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | A file declaring the same symbol twice must not abort the build | Restore R5.1: dup-decl file soft-fails at worst, build continues | `store.py:59` UNIQUE; `indexer.py:600` unguarded `_write`; spike reproduced `IntegrityError` | ✅ understood |
| R1 | R | Store-side keep-first dedupe in `replace_file_rows` | Drop nodes whose qname already appeared for this file; keep first; leave NULL untouched | `store.py:242-254` `replace_file_rows`, `:256-263` `_insert`, `:1415-1427` `_grouped` | ✅ |
| R2 | R | Deterministic (adapters emit source order; keep-first stable) | first-wins ordering; identical input→rows (R4) | spike: NULL non-collision confirmed; `_grouped` preserves row order | ✅ |
| R3 | R | Optional transparency — count deduped nodes | count dropped; optional surfacing (build report / task 028) | `indexer.BuildReport`, `store.counts()` | ⚠ optional |
| R4 | R | Optional defense-in-depth — guard `indexer._write` store call | any per-file store error → `parsed_ok=0`, never abort | `indexer.py:590-600` `_write`; `:565-573` the `_work` soft-fail path (the asymmetry) | ⚠ optional → **decision D1** |
| C1 | C | Dedupe key = (qname, file_path); reduces to qname per file | language-agnostic; lives in store (R1.4); no core branch (R1.1) | `store.py` only; no `if language` | ✅ |
| C2 | C | Restores R5.1 | dup-decl file soft-fails; build continues | rulebook R5.1 | ✅ |
| C3 | C | Keep-first, not skip-file | symbol stays resolvable; don't drop real app code | ticket rationale | ✅ |
| C4 | C | Deterministic (R4) | identical input → identical rows | rulebook R4.2 | ✅ |
| AC1 | AC | fixture: dup `function f` + `interface X`/`class X` → build completes, `parsed_ok=1`, each dup name → exactly 1 node | prove at store-write layer | see verification plan | ⏳ design |
| AC2 | AC | store unit test: two same-qname nodes for one path persist exactly one, deterministically the first | `replace_file_rows` keep-first | see plan | ⏳ design |
| AC3 | AC | re-running the build yields identical rows | determinism | see plan | ⏳ design |
| AC4 | AC | (if guard) simulated per-file store error → file `parsed_ok=0`, build completes | `_write` guard | see plan | ⏳ design (gated on D1) |
| REF | References | code/rule pointers | evidence only, not a requirement | cited above | ✅ n/a |

### AC validation (falsifiability)
- **AC1** — falsifiable: "build completes" = no exception raised by the per-file write step; `parsed_ok=1` = column read; "exactly one node" = `COUNT==1`. ✅
- **AC2** — falsifiable: persisted node count for the path == 1, and the survivor is the first (assert `line_start` of the first emit). ✅
- **AC3** — falsifiable: two runs → byte-identical node rows ordered by stable key (existing determinism-test pattern, `test_store.py`). ✅
- **AC4** — falsifiable: inject a store error for one file → that file's `files.parsed_ok==0` and the loop still processes the rest. ✅
- No vague/unmeasurable AC → no manual-check exclusion needed.

### CLARIFICATION detail (both self-resolved; surfaced at Gate 1)
1. **AC1 says "full_build completes" but full_build needs an adapter subprocess, which is baseline-red on this host.** *Self-resolved (cited):* the bug lives entirely in the store insert (`store.py:59/256-263`) and the unguarded writer (`indexer.py:600`); the per-file build-write step **is** `indexer._write`. Proving `_write` with a dup-qname `ParseResult` against a real `GraphStore` falsifies the abort at exactly the risk layer, with no subprocess. The subprocess/adapter layer is orthogonal to this bug (and separately broken on Windows). → AC1 proven at the `_write`+`GraphStore` integration layer; the subprocess-driven end-to-end variant adds no risk coverage for *this* AC and is not added.
2. **Include the R4/AC4 defense-in-depth guard, or split to a follow-up?** *Self-resolved (cited) → recommendation, human confirms at Gate 1 (D1):* the ticket lists the guard as an in-scope deliverable (marked "optional / may split out"), and the Goal frames the whole bug as an R5.1 violation + the `_work`/`_write` asymmetry (`indexer.py:565-573` vs `:590-600`). It is small (a `try/except` re-marking `parsed_ok=0`) and closes the class, not just the case. → **Recommend include.**

### Universal inventory
`INVENTORY: N=2` — the fixture's distinct duplicated qnames that must each resolve to exactly one node: (1) `\f` (function declared twice), (2) `\X` (interface + class, same qname). Review confirms **each**, not an aggregate.

### Cause / gap analysis
- **Cause (taxonomy = `validation` / `data`):** a legal-but-duplicate declaration in one source file emits two nodes sharing `qualified_name`; the schema's `UNIQUE(qualified_name, file_path)` (`store.py:59`) rejects the second; `store._insert` uses a plain `INSERT executemany` with no de-dup (`store.py:256-263`); `indexer._write` calls `replace_file_rows` **unguarded** (`indexer.py:600`), so the `IntegrityError` propagates through `collect` (`indexer.py:533`) → `full_build` and aborts the whole build. Violates **R5.1** (bad *file* must soft-fail).
- **Gap vs target:** the writer must let a per-file store conflict degrade to `parsed_ok=0` (guard, R4/AC4), and the store must not raise on the *legitimate* dup-decl case at all (keep-first dedupe, R1/AC2) so the symbol stays indexed (C3).

### Blast radius
- **Handler:** `store.replace_file_rows` (`store.py:242`) and its `_insert` (`:256`) — the single SQLite writer (R4.3). `_grouped` (`:1415`) builds the insert tuples in emit order → the ordering keep-first relies on.
- **Callers of `replace_file_rows`:** `indexer._write` (`:600`), `resolver`/incremental paths, and ~15 call sites in `tests/test_store.py`. Dedupe changes behaviour **only** when a caller passes two same-qname nodes for one path — every existing single-decl caller is unaffected (verified: no current test passes a dup).
- **Writer:** `indexer._write` (`:590`) — guard adds a `try/except`; the soft-fail tally path already exists (`:605-606`).
- **Repos touched:** `app` (`.`) only.
- **Determinism:** dedupe is order-preserving (keep-first over `_grouped`'s emit order); incremental update of a dup file must equal a full rebuild (R4.2) — covered by AC3.

## Phase 2 — Design

### Approach
1. **Store-side keep-first dedupe (R1/C1/C3/C4).** Add a module-level `_dedupe_by_qname(nodes) -> (list, int)` in `store.py`: iterate the node rows once in emit order, keep the first row per **non-NULL** `qualified_name`, skip later duplicates, count drops. `replace_file_rows` calls it before `_grouped(NODE_FIELDS, …)` and **returns the dropped count** (was `None` → now `int`). NULL/anonymous qnames are never de-duped (SQLite treats NULLs as distinct — spike-verified). Dedupe key `(qualified_name, file_path)` reduces to `qualified_name` because `file_path` is constant within one call.
2. **Writer guard (R4/C2/G1).** In `indexer._write`, wrap the `store.replace_file_rows` call in `try/except sqlite3.Error`; on error re-`upsert_file(path, …, parsed_ok=False)` (correcting the earlier optimistic upsert), `tally["failed"] += 1`, and return — a per-file store error becomes a soft failure (R5.1), never a build abort. The `with self._conn:` transaction in `replace_file_rows` rolls back the delete+insert on exception, so the path keeps no partial rows (code-read-verified). Adds `import sqlite3` to `indexer.py`.
3. **Transparency (R3, minimal).** The returned dedupe count makes the store non-silent at its seam and is asserted by a store test; threading it into `BuildReport`/the tool response is a **deferred optional follow-up** (see Decision log).

### Rejected alternatives
- **`INSERT OR IGNORE` on nodes** — one-liner, but masks *every* UNIQUE violation (not just intra-file dup), hiding real bugs. Less targeted than keep-first. Rejected.
- **Adapter-side dedupe** — pushes a language-agnostic invariant into every future adapter (violates R1.4 "store owns the SQLite invariant" + the one-seam rule). Rejected.
- **Guard-only, skip the whole file on dup** — honors R5.1 but discards the entire file's graph, losing real app code (e.g. a file with a legal `function_exists` guard). Keep-first indexes the one real declaration (C3). Rejected — but the guard is *kept* as defense-in-depth for the residual error class.

### Assumptions
- **A1 (verified — spike):** two same-qname nodes for one path raise `sqlite3.IntegrityError: UNIQUE constraint failed: nodes.qualified_name, nodes.file_path`.
- **A2 (verified — spike):** two NULL-qname nodes for one path do **not** collide (SQLite distinct-NULL). Keep-first must skip `None`.
- **A3 (verified — code read `_grouped` `store.py:1415-1427`):** `_grouped` preserves input row order within a field-group; de-duping upstream on the ordered list makes the **first** emit the survivor → determinism (R4.2).
- **A4 (verified — code read `store.py:251-254`):** `replace_file_rows` runs delete+insert inside one `with self._conn:` block, which rolls back fully on exception, so the guard can safely re-mark `parsed_ok=0` with no partial rows.
- No unresolved `novel-untested` third-party/runtime assumption remains (both novel ones spiked).

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|---|---|---|---|
| 1 | `_dedupe_by_qname` helper + call in `replace_file_rows`; return dropped count | `code_atlas/store.py` (`:242-254`, new helper near `:1415`) | R1, R2, R3(seam), C1, C3, C4, AC2, AC3 | 8/8 |
| 2 | `import sqlite3`; `try/except sqlite3.Error` guard in `_write` → `parsed_ok=0`, tally failed, return | `code_atlas/indexer.py` (`:16`, `:590-606`) | R4, C2, G1, AC4 | 4/4 |
| 3 | Store tests: keep-first persists one (first) + returns count; NULL not deduped; re-run identical rows | `tests/test_store.py` | AC2, AC3 | 2/2 |
| 4 | Indexer tests: `_write` dup-decl → no abort, `parsed_ok=1`, each dup qname → 1 node; injected store error → `parsed_ok=0` + build continues | `tests/test_indexer.py` | AC1, AC4 | 2/2 |
| 5 | R5.1 worked example (dup-decl file soft-fails) | `docs/ENGINEERING_RULES.md` (R5.1) | G1, C2 (docs-before-PR) | 1/1 |
| 6 | §-note: duplicate-declaration reality + keep-first store dedupe | `docs/PLAN.md` (store/§8.1 or §10) | R1 (docs-before-PR) | 1/1 |

**Test blast-radius (mechanical).** All ~15 existing `replace_file_rows` call sites are statements, none assign/assert its return (grep-verified) → changing `None`→`int` is safe. No existing test passes two same-qname nodes for one path (grep-verified) → dedupe changes no current test's outcome. No test asserts `_write`'s internal tally exact-shape beyond parsed/failed/nodes/edges. `BuildReport`/`asdict` untouched (R3 deferred) → no tool-response test churn.

### Rule compliance
- **R1.1** — dedupe lives in `store.py`; no `if language ==` anywhere. ✅
- **R1.4** — the store owns the SQLite UNIQUE invariant; the writer only guards. Parsing code untouched. ✅
- **R4.2** — keep-first over emit order is deterministic; identical input → identical rows; incremental == full for a dup file (AC3). ✅
- **R5.1 / R5.3** — a bad *file* (dup decl / per-file store error) soft-fails (`parsed_ok=0`), build continues; config/programmer errors (e.g. `SchemaVersionError` at construction) still fail loud, untouched. ✅
- **R3 (contract frozen)** — no node/edge vocabulary or qname change → **no `contract_version` bump**, no conformance-test change. ✅
- **R6.1/R6.2** — store+indexer changes get integration tests; fixtures are spec-shaped (dup-qname rows), not repo-driven. ✅
- **R7.5** — every new comment ≤ 3 lines. ✅

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1 build write survives dup file, `parsed_ok=1`, each dup name → 1 node | integration (store write during build) | `test_indexer.py` — `_write` + real `GraphStore`, dup-decl `ParseResult` | ✅ |
| AC2 keep-first persists exactly one (the first) + count | integration (SQLite) | `test_store.py` — `replace_file_rows` keep-first + returned count | ✅ |
| AC3 re-run yields identical rows | integration (SQLite) | `test_store.py` — two runs, byte-identical node rows by stable key | ✅ |
| AC4 injected per-file store error → `parsed_ok=0`, build continues | integration/runtime (writer error path) | `test_indexer.py` — `GraphStore.replace_file_rows` patched to raise `sqlite3.IntegrityError`; assert `files.parsed_ok==0` + next file still written | ✅ |
| R3 surface in `BuildReport` | n/a (optional) | **deferred, human-approved** — return-count + store test satisfy "not silent" | ⚠ recorded deferral |

No layer-match ❌. `INVENTORY N=2` (`\f`, `\X`) proven **item-by-item** in the AC1 test (each asserted to resolve to exactly one node).

### Proving test (at the matching layer)
`tests/test_indexer.py::test_write_survives_duplicate_declarations` — drives `_write` with a `ParseResult` carrying `\f`×2 + `interface X`/`class X` (same `\X`) against a real `GraphStore`. **Fails pre-fix** (`IntegrityError` propagates out of `_write` → a build would abort), **passes post-fix** (returns; file `parsed_ok=1`; `\f` and `\X` each resolve to one node).
Invocation: `pytest tests/test_indexer.py -k duplicate_declarations`.

### Rollback + porting
- **Rollback:** `git revert` the two source edits + the two test files + two doc notes. No schema change (UNIQUE stays), **no `contract_version` bump**, no data migration, no index change → old indexes keep working.
- **Porting:** single repo `app` (`.`); no shared-code porting.

### SCOPE
`SCOPE: S` confirmed — 2 small source edits + 2 test files + 2 doc notes. No tier crossing, no branch/PR-type drift (a `fix` carrying a fix).

## Phase 3 — Execute

**Branch:** `fix/043-duplicate-decl-resilience`.

**Implemented (approved change list):**
- `code_atlas/store.py` — `_dedupe_nodes(nodes)` keep-first helper; `replace_file_rows` calls it and now returns the dropped count (`int`). Added `WRITE_ERRORS` module constant.
- `code_atlas/indexer.py` — `_write` wraps the store write in `try/except WRITE_ERRORS` → re-`upsert_file(parsed_ok=False)`, tally failed, return; node tally corrected by the dropped count.
- `tests/test_store.py` — keep-first persists one/first + count; NULL not deduped; dedupe determinism (AC2, AC3).
- `tests/test_indexer.py` — `_write` dup-decl → no abort, `parsed_ok=1`, each dup qname → 1 node (AC1); injected store error → `parsed_ok=0` + build continues (AC4).
- `docs/PLAN.md` §10 — same-file duplicate-declaration keep-first note. `docs/ENGINEERING_RULES.md` R5.1 — bad-store-write worked example.

**Proving test:** `tests/test_indexer.py::test_write_survives_duplicate_declarations` — **verified FAIL pre-fix** (stashed the two source edits → `sqlite3.IntegrityError` out of `_write`), **PASS post-fix**.

**Deviations from the literal Gate-2 design (surfaced to review):**
- **D2 — guard exception type.** Design said `except sqlite3.Error`. Implemented `except store.WRITE_ERRORS` (a store-owned `(sqlite3.Error,)` tuple). Reason: importing `sqlite3` into `indexer.py` trips `tests/test_sql_confinement.py::test_exactly_one_core_module_touches_sqlite` (R1.4/R4.3 — only `store.py` may reference SQLite). Same behaviour (catches every `sqlite3.Error`); the SQLite reference stays confined to the store. Design's own Rule-compliance already claimed R1.4 — this makes the code match it.
- **D3 — dedupe key.** Approach prose said "reduces to `qualified_name`"; implemented the **full UNIQUE key `(qualified_name, file_path)`** (matching the design's own C1). Reason: `test_resolver.py` legitimately passes same-qname nodes for **different** files through one `replace_file_rows` call (multi-candidate siblings); a qname-only key wrongly collapsed them. Full-key dedupe fixes the known intra-file case and preserves cross-file siblings. Also: `_write` now subtracts the dropped count from `tally["nodes"]` so `BuildReport.nodes` equals stored nodes.

**Verification sweep — Axis 1 (file set):** diff ⊆ approved list (store, indexer, their two test files, PLAN, ENGINEERING_RULES, BACKLOG bookkeeping, this ticket). No file outside the list; no untouched-line reformatting; no stray/dangling refs (`grep sqlite3 indexer.py` = 0; no `_dedupe_by_qname` stragglers). Each hunk maps to a change-list row.

**Verification sweep — Axis 2 (design conformance):** Approach bullet 1 (dedupe) = implemented, refined to the full UNIQUE key (D3, conforms to C1). Bullet 2 (guard) = implemented, exception routed via `WRITE_ERRORS` (D2). Bullet 3 (transparency) = implemented (return count + honest node tally). No feature self-marked ✅ that was not implemented.

**Tests:** full suite **608 passed / 56 failed / 98 skipped**. The 56 failures are the pre-existing Windows adapter-subprocess baseline (unchanged set — byte-diffed baseline vs after: **NEW failures = NONE**). `ruff` + `mypy` clean on both source files.

**`Ph3 proven by`:** AC1 3/3 (`test_write_survives_duplicate_declarations`, INVENTORY N=2 item-by-item), AC2 1/1, AC3 1/1, AC4 1/1 (`test_write_soft_fails_a_per_file_store_error`).

## Phase 4 — Review

**Reviewed at `aadc569`** (CLEAN, human-approved Gate 4). Reviewed files: `code_atlas/store.py`, `code_atlas/indexer.py`, `tests/test_store.py`, `tests/test_indexer.py`, `docs/PLAN.md`, `docs/ENGINEERING_RULES.md`. Working-doc path (exempt from the finalise stale-review guard): `docs/tasks/043_duplicate-decl-resilience.md`; bookkeeping exempt: `docs/BACKLOG.md`, `docs/LESSONS.md`.

**Reviewer (`mango:reviewer`, Sonnet):** **LGTM**, zero findings. Independently confirmed R1.4 SQL confinement (`grep sqlite3 indexer.py` = 0; `test_sql_confinement.py` 4 passed), R1.1 (no core branch), R4.2 (dedupe order-stable + NULL-safe), R5.1/R5.3 (soft per-file, `SchemaVersionError` still loud; `enrichment.py`'s direct call correctly left unguarded as a config-error path), R3 (no `contract_version` bump), R7.5 (comments ≤3 lines), and the node-tally correction. Ran ruff + mypy clean.

**Challenger (`mango:challenger`, ticket-blind):** 9 met, 0 not-met, plus:
- **AC1 — gap vs literal wording.** The `_write`-layer test faithfully proves AC1's *mechanism* but not literal end-to-end `full_build()` with a real PHP fixture. Challenger notes the `fake_command()` pattern could drive `full_build` without a real PHP subprocess.
- **D3 (optional) — thin surfacing.** The dedupe count is *used* (node tally) but not surfaced as a distinct `BuildReport` field. (Optional deliverable; matches the Gate-2 deferral.)
- **C1/D3 keying** — praised: the full `(qualified_name, file_path)` key is "more careful than the ticket's own stated reduction" and avoids collapsing cross-file siblings.

**Scope reconciliation (both axes):** File axis — diff ⊆ approved list, no untouched-line reformatting. Behaviour axis — deviations D2 (guard via `store.WRITE_ERRORS`) and D3 (full UNIQUE key) recorded in Phase 3; both strictly better-honor the design's own C1/R1.4 and are adjudicated clean (D3 is required correctness, D2 required for SQL confinement). No unrecorded deviation.

**Regression check:** full suite byte-diffed baseline vs after → **NEW failures = NONE**; 608 passed / 56 (unchanged Windows-subprocess baseline) / 98 skipped.

**Proving test:** `test_write_survives_duplicate_declarations` — verified FAIL pre-fix (`IntegrityError`), PASS post-fix.

**Layer-match re-confirmation (binding):** every AC proved at its integration risk layer (real SQLite / real `_write`) — no unit-mock-below-risk-layer. No layer-match ❌.

**k/N:** AC1 mechanism 1/1 (INVENTORY N=2 item-by-item) · AC2 1/1 · AC3 1/1 (store layer) · AC4 1/1. The only open denominator is AC1's *literal full_build end-to-end* proof — proposed as a coverage-gap exclusion below.

**Coverage-gap exclusion (human-approved at Gate 4):**
> **AC1 literal `full_build()` end-to-end proof** — deferred, **approved**. Risk tier: integration/e2e. Why deferred: this Windows host cannot launch any adapter subprocess (pre-existing `shlex(posix=False)`/`CreateProcess` harness bug — the root cause of all 56 baseline failures), so a `full_build`-driven proof cannot run or be verified here; the bug's actual surface (store insert + unguarded writer) is fully proven at the `_write`+real-store layer, which is the per-file step `full_build` runs. Follow-ups filed in BACKLOG: (a) CI-gated fake-adapter `full_build` dup-declaration test; (b) optional PHP-adapter dup-declaration fixture.

**Verdict: CLEAN** — reviewer no Critical; every challenger item met except the one human-approved coverage-gap exclusion above; no layer-match ❌; proving test green; regression NONE.

**Cost ledger (subagent dispatch only):**

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| review | mango:reviewer (Sonnet) | 1 | 86,364 |
| review | mango:challenger (ticket-blind) | 1 | 64,333 |

Ledger completeness: 2 dispatches this run → 2 rows, both carrying a measured value (returned `<usage>` blocks). Complete.

## Phase 5 — Finalise

**Stale-review guard:** nothing committed since the `Reviewed at aadc569` marker; the only working-tree changes are exempt (working doc + `docs/BACKLOG.md` + `docs/LESSONS.md`). Not stale → proceed.

**LEDGER TOTAL: 150,697 tokens** (subagent dispatch only) · top cost driver: `review / mango:reviewer` (86.4k). Main-loop spend is unmeasured (mango measures dispatch only — see `rtk gain` for the RTK-side global figure; it cannot be attributed to one task).

**Durable lesson:** recorded in `docs/LESSONS.md` (043 / 043-C1) — dedupe on the full UNIQUE key `(qualified_name, file_path)`, and a core guard catches a store-owned `WRITE_ERRORS` tuple, never `sqlite3` (SQL-confinement R1.4). Both were caught only by the existing regression suite via the delta-green baseline diff.

**Follow-ups filed (BACKLOG):** (a) CI-gated fake-adapter `full_build` dup test; (b) Windows adapter-subprocess test-harness `shlex` bug (separate `fix`); (c) optional PHP-adapter dup fixture.

**Revert path:** branch `fix/043-duplicate-decl-resilience`. Source commits `651b3f1` (fix) + `aadc569` (docs) — `git revert` both (no schema change, no `contract_version` bump, no migration; old indexes keep working). Bookkeeping is a separate commit. If a PR merges and must be undone: revert the merge commit on `main`.

**Session status:** review clean at `aadc569`; token spend recorded in both places; 043 → `in-progress` (both places). PR #49 opened.

**Post-PR CI fix (Linux-only regression):** `test_every_write_happens_on_the_single_writer_thread` failed in CI — the `RecordingStore` test double's `replace_file_rows` override swallowed `super()`'s return, so `_write`'s `len(result.nodes) - deduped` hit `deduped=None` → `TypeError`. Masked locally because that test fails-at-launch on this Windows host (fake-adapter subprocess), so the baseline failure-set diff scored it "not new." Fixed by propagating the return (`tests/test_indexer.py:108`); verified by driving `RecordingStore.replace_file_rows` directly (returns 0 / drop-count). Lesson recorded in `docs/LESSONS.md` (043). Next: on merge, flip 043 → `done`.

