---
id: 016
slug: incremental-git
title: Incremental update via git diff (M5)
phase: 1
milestone: M5
status: in-progress
depends_on: [011, 009]
---

## Goal
Keep the index fresh cheaply (§8.3).

## Scope / Deliverables
- `gitutil.py`: `git diff <last_commit>..HEAD` → changed files.
- `indexer.incremental_update`: add single-hop dependents; reparse `changed ∪ dependents` (hash-skip unchanged); re-run resolver scoped to affected qnames; bump `meta.last_commit`.
- Staleness reported in `get_index_status`.
- **CI:** `actions/checkout@v4` clones with `fetch-depth: 1` by default, so `git diff <last_commit>..HEAD` has no history to diff against and every incremental test would fail or silently degrade on the runner. This task must set `fetch-depth: 0` (or build its own throwaway repo per test, which is the more hermetic option — prefer it and keep CI's checkout shallow).

## Acceptance criteria
- Editing one file updates only affected rows; result equals a full rebuild for that state.
- Status shows staleness (commits behind) accurately.

## References
Plan §8.3, §15 (M5).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 016 — Incremental update via git diff (working doc)

- **Ticket:** 016 · [docs/tasks/016_incremental-git.md](016_incremental-git.md)
- **Type:** enhancement
- **Repo(s):** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `517 passed in 24.42s` (`.venv/bin/pytest -q` on `feat/016-incremental-git` @ `9c9bc69`). baseline exclusions: none
- **work_doc_mode:** `embed`

## Session status

```
phase: finalise
gates: Gate 0–4 clean; Reviewed at f7cfbf2; awaiting per-action push/PR approval
branch: feat/016-incremental-git
```

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous` · `RECALL: 0` · `REFINE: HOW cited + ASSUMED A1–A3 + exposure fold-ins`

**HOW (cited):**

1. Hermetic throwaway git repos in tests; keep CI shallow (`fetch-depth: 0` only on guardrails).
2. `full=false` with no usable `last_commit` → full-build fallback.
3. `gitutil.changed_paths(root, since)` via `git diff --name-only -z since..HEAD`.
4. Single-hop dependents = distinct `edges.file_path` where `target_qname` ∈ qnames of changed files.
5. Hash-skip when `files.hash` equals current byte digest.
6. Wire `build_or_update_index(full=false)` → incremental when usable; honest `mode` in payload.

**ASSUMED (ratified Gate 1 under standing approve):**

| # | Choice |
|---|--------|
| A1 | Staleness stays `current\|behind\|unknown` (no `commits_behind` count) |
| A2 | Proving test = stable ordered node/edge/file content matches fresh full build (ids excluded, R4.2) |
| A3 | Scoped resolve via unlink of targets into affected qnames, then `resolve_edges`; parity with full rebuild required |
| A4 | Deletes → `_reconcile` like full build (gone from collect) |
| A5 | Renames → delete-old (reconcile) + add-new (diff new path) |
| A6 | Invalid/unreachable `last_commit` → soft fall back to full build |
| A7 | Uncommitted dirty tree out of scope; incremental is commit-to-commit only |
| A8 | Always bump `last_commit` after a successful run (same as `full_build`) |

`UNEXPOSED: 6` from exposure-checker → folded as A4–A8 / HOW.

---

## Phase 1 — Analysis

`SECTIONS: 4 found (Goal, Scope, AC, References) | 4 decomposed | ROWS: C=0 R=4 G=1 AC=2+ASSUMED`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| R1 | Scope | gitutil diff → changed files | `changed_paths(root, since)` | gitutil + tests | ✅ |
| R2 | Scope | incremental_update + dependents + hash-skip + scoped resolve + meta | indexer path | indexer + store | ✅ |
| R3 | Scope | Staleness in get_index_status | Keep A1; already shipped; prove behind→current after incremental | existing + tests | ✅ |
| R4 | Scope | CI hermetic throwaway repos | Prefer tests; leave shallow checkout | tests only | ✅ |
| G1 | Goal | Keep index fresh cheaply | R1–R4 | — | ✅ |
| AC1 | AC | One-file edit → affected only; equals full rebuild | A2/A3 | proving test | ✅ |
| AC2 | AC | Staleness accurate | A1; behind then current after incremental | tests | ✅ |

`CLARIFICATION: 0 open | ASSUMED A1–A8 ratified at Gate 1`

`PREMISE: 6 checked | 0 missing | 0 ambiguous`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | A1–A8 ASSUMED | standing “best option / pass all gates” |
| Gate 1 | Ratify ASSUMED; clear | standing approve |
| Gate 2 | Approve design | standing approve |

---

## Phase 2 — Design

### Approach

1. Add `gitutil.changed_paths` (`git diff --name-only -z since..HEAD` → sorted paths or `None`).
2. Store helpers: `qnames_in_files`, `file_paths_targeting`, `unlink_targets` (SQL stays in `store.py`).
3. `indexer.incremental_update`: diff → qnames → dependents → reconcile deletes → unlink targets → hash-skip parse of `changed ∪ dependents ∩ collect` → `_record_meta` → `resolve_edges`.
4. `build_or_update_index`: `full=true` or unusable last_commit/diff → `full_build` + `mode=full`; else incremental + `mode=incremental`.
5. Proving tests on throwaway git repos (fake adapter + dep-edge path); update MCP mode echo test.

### Rejected alternatives

- **Deep CI `fetch-depth: 0` for all jobs** — rejected; hermetic per-test repos are more reliable and leave CI shallow (ticket preference).
- **Always full rebuild when `full=false`** — rejected; that is today's lie and fails the M5 goal.
- **`commits_behind` count in status** — rejected under A1; equality `current|behind|unknown` already shipped.

### Assumptions

| Assumption | Tag | Discharge |
|------------|-----|-----------|
| `git diff since..HEAD` fails loud (nonzero) on unknown since | novel-untested (3p) | proving + unit tests assert fallback |
| Hash-skip + unlink + resolve yields full-rebuild parity | novel-untested | Gate-2 proving test AC1 |
| Staleness equality already correct | verified | existing MCP test |

### Change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | `changed_paths` | `code_atlas/gitutil.py` | R1 | 1 |
| 2 | `qnames_in_files` / `file_paths_targeting` / `unlink_targets` | `code_atlas/store.py` | R2, A3 | 1 |
| 3 | `incremental_update` (+ hash-skip / dependents / reconcile) | `code_atlas/indexer.py` | R2, A4–A8 | 1 |
| 4 | Wire tool; honest `mode` | `code_atlas/tools/build_or_update_index.py` | R2, G1 | 1 |
| 5 | Fake-adapter dep edges for dependents proof | `tests/fixtures/adapter/fake_adapter.py` | AC1 | 1 |
| 6 | Incremental proving + unit tests | `tests/test_incremental.py` (new) | AC1, AC2, R4 | 1 |
| 7 | Update mode-echo MCP test | `tests/test_mcp_server.py` | proof collateral | 1 |
| 8 | Docs PLAN §8.3 / BACKLOG / README / task frontmatter | docs | R7.2 | 1 |

### Rule compliance

- R1.1 — no language branches in core.
- R1.4 — SQL only in `store.py`.
- R4.2 — sorted paths; content snapshots exclude ids.
- R4.3 — single writer on caller thread (same as full_build).
- R5.3 — soft fall back to full, never silent corrupt incremental.

### Verification plan

| AC | Risk layer | Proof | Layer-match |
|----|------------|-------|-------------|
| AC1 parity + affected-only | integration | throwaway git + fake adapter; snapshot vs full_build; unrelated node id stable | ✅ |
| AC2 staleness | integration | behind after commit; current after incremental | ✅ |
| R1/diff fallback | integration | bad `last_commit` → mode full | ✅ |

### Proving test

```text
.venv/bin/pytest -q tests/test_incremental.py::test_one_file_edit_matches_full_rebuild_and_leaves_unrelated_ids
```

---

## Phase 3 — Execute

**Branch:** `feat/016-incremental-git`

**Implemented:** change-list 1–8 as approved.

**Deviations:** none.

**Verification (paste):**
```
.venv/bin/ruff check code_atlas tests/test_incremental.py → All checks passed
.venv/bin/mypy code_atlas → Success
.venv/bin/pytest -q tests/test_incremental.py::test_one_file_edit_matches_full_rebuild_and_leaves_unrelated_ids → PASS
.venv/bin/pytest -q --tb=line → 523 passed in 26.89s (baseline 517)
```

**Axis 1:** diff ⊆ change-list ✅
**Axis 2:** approach bullets implemented-as-approved ✅

**Review fix (post Phase-3):** `unlink_targets` collapses HEURISTIC top-N sibling groups before
re-resolve (R4.2); proving coverage in `test_heuristic_siblings_still_match_a_full_rebuild`.
Committed as `f7cfbf2`.

---

## Phase 4 — Review

**Reviewed at** `f7cfbf2`

**Working-doc path:** `docs/tasks/016_incremental-git.md`

**Reviewed files:** `code_atlas/gitutil.py`, `code_atlas/store.py`, `code_atlas/indexer.py`, `code_atlas/tools/build_or_update_index.py`, `tests/fixtures/adapter/fake_adapter.py`, `tests/test_incremental.py`, `tests/test_mcp_server.py`, `README.md`, `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/tasks/016_incremental-git.md`

| Critic | Result |
|--------|--------|
| mango:reviewer round 1 ([Reviewer](f852bbd7-ef10-450e-83b7-121efa17a716)) | **CHANGES REQUESTED** — HEURISTIC sibling unlink (R4.2) |
| mango:challenger ([Challenger](de2207ce-d48a-4871-9652-9c9ab1eacd68)) | **10 met · 0 not met · 1 can't tell** (goal “cheap” unmeasured) |
| mango:reviewer round 2 ([Reviewer](bdc74828-249b-4656-8ba9-389a28d7fcda)) | **LGTM** — sibling collapse + proving test verified |

### Reviewer detail round 1 ([Reviewer](f852bbd7-ef10-450e-83b7-121efa17a716))

- **Verdict:** CHANGES REQUESTED
- **Scope:** `main...HEAD` @ `9489acc` maps 1:1 onto change-list items 1–8
- **Finding (Important, R4.2):** `unlink_targets` only nulled `target_qname`; HEURISTIC top-N siblings left in place → hash-skipped dependents could diverge from full rebuild after `resolve_edges`
- **Required fix:** collapse natural-key groups to one bare edge + proving test for multi-match CALLS
- **Verification then:** proving test PASS; `tests/test_incremental.py` 5 passed; MCP suite green

### Challenger detail ([Challenger](de2207ce-d48a-4871-9652-9c9ab1eacd68)) — ticket-blind

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | gitutil diff → changed files | **Met** | `gitutil.py:33-41`; `test_changed_paths…` |
| 2 | single-hop dependents | **Met** | `indexer.py` + `file_paths_targeting`; dep fixture |
| 3 | reparse changed ∪ dependents, hash-skip | **Met** | `indexer.py:107-112`, `_hash_matches` |
| 4 | resolver scoped to affected qnames | **Met** (nuance: unlink + unresolved resolve, not a filtered API) | `unlink_targets` + `resolve_edges` |
| 5 | bump `meta.last_commit` | **Met** | `_record_meta` |
| 6 | staleness in `get_index_status` | **Met** | existing tool + incremental bump |
| 7 | hermetic throwaway repos; keep CI shallow | **Met** | `test_incremental.py`; no pytest fetch-depth change |
| 8 | AC: only affected rows | **Met** | unrelated node id stable |
| 9 | AC: equals full rebuild | **Met** | snapshot parity |
| 10 | AC: staleness accurate | **Met** | behind → current (equality, not N-count) |
| 11 | Goal: keep fresh cheaply | **Can't tell** | no perf measurement (acceptable for M5 AC) |

**Orchestrator note:** #11 can't-tell is expected — ticket AC is correctness/parity, not a perf bar.

### Reviewer detail round 2 ([Reviewer](bdc74828-249b-4656-8ba9-389a28d7fcda))

- **Verdict:** LGTM
- **Fix verified:** `store.py:388-442` collapse + `test_heuristic_siblings_still_match_a_full_rebuild`
- **Verification:** `tests/test_incremental.py` → **6 passed**; full suite → **524 passed**

**Scope reconcile:** file axis ✅ · behaviour axis ✅ (sibling fix in-list) · inventory ✅

**Layer-match:** AC1/AC2 integration over hermetic git ✅

**Proving (re-check):** `test_one_file_edit_matches_full_rebuild_and_leaves_unrelated_ids` PASS; sibling parity PASS. Baseline 517 → 524.

**Verdict:** clean for Gate 4.

---

## Cost ledger

| Phase | Dispatch | Round | Tokens | Notes |
|-------|----------|-------|--------|-------|
| refine | challenger (exposure-checker) | 1 | unmeasured (host does not surface usage) | [c00f48c5](c00f48c5-3e90-4ce6-a4cf-954f4134fa5e); UNEXPOSED: 6 |
| review | reviewer | 1 | unmeasured (host does not surface usage) | [f852bbd7](f852bbd7-ef10-450e-83b7-121efa17a716); CHANGES REQUESTED |
| review | challenger | 1 | unmeasured (host does not surface usage) | [de2207ce](de2207ce-d48a-4871-9652-9c9ab1eacd68); 10 met / 0 not met / 1 can't tell |
| review | reviewer | 2 | unmeasured (host does not surface usage) | [bdc74828](bdc74828-249b-4656-8ba9-389a28d7fcda); LGTM |

---

## Follow-ups

- None.

## Durable lesson (candidate — needs ratification at final gate)

When incremental unlinks resolved edges for re-resolve, **collapse HEURISTIC top-N sibling rows** in the same natural-key group to one bare edge. Nulling `target_qname` alone leaves siblings that re-fan-out and break R4.2 parity with a full rebuild.
