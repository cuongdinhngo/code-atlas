---
id: 016
slug: incremental-git
title: Incremental update via git diff (M5)
phase: 1
milestone: M5
status: done
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
phase: 5 finalise complete
PR: https://github.com/cuongdinhngo/code-atlas/pull/26
Reviewed at: f7cfbf2 (bookkeeping tips after; stale-review exempt)
Gate: closed
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
- **Scope:** `main...HEAD` @ `9489acc` maps 1:1 onto change-list items 1–8; no files outside the list
- **Verification then:** proving test PASS; `tests/test_incremental.py` → **5 passed**; `tests/test_incremental.py` + `tests/test_mcp_server.py` → **53 passed**
- **Finding 1 (Important — R4.2 / R6.1):**
  - **Where:** `code_atlas/store.py` (`unlink_targets`), exercised by `code_atlas/indexer.py` then `resolve_edges`
  - **Problem:** `unlink_targets` only nulled `target_qname` for edges pointing into affected qnames. Resolver top-N fan-out (`resolver._queue_candidates`) inserts **sibling** rows that already have `target_qname` set. When a hash-skipped dependent has a multi-match `HEURISTIC` group: (1) unlinked parent → re-resolve inserts **new** siblings while old siblings that still point at non-affected candidates remain → **duplicate** edges vs full rebuild; (2) unlinked sibling (affected qname was not the first candidate) → parent stays linked; orphan `target_qname IS NULL` sibling is re-resolved on every later `resolve_edges` → **edge multiplication**. Full rebuild avoids this because `replace_file_rows` deletes all edges for reparsed files.
  - **Rules:** ENGINEERING_RULES **R4.2** (identical input → identical output; incremental must equal full rebuild); **R6.1** (indexer/store change needs an integration assertion on this path).
  - **Required fix:** collapse each bare-edge natural-key group that touches affected qnames to one bare row, then clear; add proving coverage with two same-name method targets + a `dep/` caller.
- **What looked solid (no finding then):** SQL confined to `store.py` (R1.4); parameterized `IN` chunks; soft fallback + honest `mode`; deletes via `_reconcile`; unique-target re-link path covered; docs updated; no language branches (R1.1); no contract vocabulary change (R3).

### Challenger detail ([Challenger](de2207ce-d48a-4871-9652-9c9ab1eacd68)) — ticket-blind

Independence: raw ticket only (text above the mango separator). Embedded working-doc portion was **not** used. PLAN §8.3 skimmed only to interpret the ticket’s § reference.

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | `gitutil` maps `git diff <last_commit>..HEAD` → changed files | **Met** | `code_atlas/gitutil.py:33-41` — `changed_paths` runs `diff --name-only -z {since}..HEAD`. Proven: `tests/test_incremental.py:95-101`. |
| 2 | `indexer.incremental_update` adds single-hop dependents | **Met** | `code_atlas/indexer.py:98-103` + `code_atlas/store.py:374-386` — dependents = distinct `edges.file_path` where `target_qname` ∈ affected qnames. Fixture: `tests/fixtures/adapter/fake_adapter.py` (`dep/` → `lib/core.aa::Thing`); re-link asserted at `tests/test_incremental.py:131-133`. |
| 3 | Reparse `changed ∪ dependents`, hash-skip unchanged | **Met** | `code_atlas/indexer.py:107-112`, `_hash_matches` at `125-128`. Candidates = `(changed ∪ dependents) ∩ collect`; parse only hash mismatches. |
| 4 | Re-run resolver scoped to affected qnames | **Met** (nuance) | Invalidation scoped: `store.unlink_targets` at `indexer.py:105`. Then `resolve_edges` at `indexer.py:121`, which only walks `target_qname IS NULL`. Not a separate qname-filtered resolver API — scoping is unlink → unresolved → resolve. AC parity still holds (`tests/test_incremental.py:136-141`). |
| 5 | Bump `meta.last_commit` after incremental | **Met** | `indexer.py:120` → `_record_meta` → `set_meta(LAST_COMMIT_KEY, …)`. Status after incremental: `tests/test_incremental.py:160-162`. |
| 6 | Staleness reported in `get_index_status` | **Met** | Pre-existing tool: `get_index_status.py:68-77`, `_staleness` at `91-95` (`current` / `behind` / `unknown`). Incremental keeps it honest by bumping `last_commit`. |
| 7 | CI: prefer hermetic throwaway repos; keep shallow checkout | **Met** | `tests/test_incremental.py:1-3`, `54-63` (`git init` + commits under `tmp_path`). No CI workflow change for pytest depth; `fetch-depth: 0` remains only on the R1.1 job (pre-existing). |
| 8 | AC: editing one file updates only affected rows | **Met** | One-file diff `("lib/core.aa",)` at `tests/test_incremental.py:123-125`; unrelated `other/stay.aa` node id stable at `117,130`. |
| 9 | AC: incremental result equals a full rebuild for that state | **Met** | Ordered file/node/edge content snapshot equality vs fresh full build: `tests/test_incremental.py:136-141` (and delete case). |
| 10 | AC: status shows staleness (commits behind) accurately | **Met** | `current` → after commit `behind` → after incremental `current` + `last_commit == HEAD`: `tests/test_incremental.py:144-162`. Mechanism is commit **equality**, not a numeric `commits_behind` count. |
| 11 | Goal: keep the index fresh cheaply | **Can't tell** | Incremental path exists and avoids full reparse, but no cost/perf evidence in the diff. |

**Orchestrator note:** #11 can't-tell is expected — ticket AC is correctness/parity, not a perf bar.

**Scope creep (challenger):** `build_or_update_index` mode selection / honest `mode` echo (needed to expose incremental); soft full-build fallback on bad/`None` diff; delete reconciliation coverage; store `_IN_CHUNK` / `_chunks`; docs README / PLAN §8.3 / BACKLOG / working doc; fake-adapter `CALLS` under `dep/` — test-only. None of substance beyond supporting the ticket.

### Reviewer detail round 2 ([Reviewer](bdc74828-249b-4656-8ba9-389a28d7fcda))

- **Verdict:** LGTM
- **Prior finding — verified fixed:**
  - Collapse natural-key groups to one bare edge — `code_atlas/store.py:388–422` (SELECT DISTINCT natural keys → DELETE siblings sharing key → INSERT one bare edge with `target_qname=NULL`)
  - Proving test `test_heuristic_siblings_still_match_a_full_rebuild` — `tests/test_incremental.py:176–207`
  - Fixture support — `tests/fixtures/adapter/fake_adapter.py:68–88` (`twin/*.aa` emit `run`; `dep/name_*` emits bare `target_raw: "run"`)
  - In approved change-list items 2 / 5 / 6
- **Rule spot-checks (all clean):**
  - R1.4 — SQL only in `store.py`; parameterized placeholders in `unlink_targets` / `_edges_sharing_key`
  - R4.2 — proving test asserts `snapshot(store) == incremental` after full rebuild (including HEURISTIC multiplicity)
  - R4.3 — single writer on caller thread (same as full_build)
  - R1.1 — no language branches in core
  - R7.2 — PLAN §8.3 / BACKLOG / README / task frontmatter updated
  - R7.5 — docstring carries the longer why for sibling collapse
- **Verification:** `tests/test_incremental.py` → **6 passed**; full suite → **524 passed**
- **Findings:** none

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

**PR:** https://github.com/cuongdinhngo/code-atlas/pull/26

**PR review fixes (post-finalise):** rename/gone qnames folded into affected; dependents always
reparsed (removed `unlink_targets` collapse); dirty worktree ∪ into `changed_paths` + status
`behind`; `report.files = len(to_parse)`; PLAN/LESSONS corrected. Suite **528 passed**.

---

## Follow-ups

- None.

## Durable lesson (ratified at final gate)

When incremental unlinks resolved edges for re-resolve, **collapse HEURISTIC top-N sibling rows** in the same natural-key group to one bare edge. Nulling `target_qname` alone leaves siblings that re-fan-out and break R4.2 parity with a full rebuild. Recorded in [`docs/LESSONS.md`](../LESSONS.md).
