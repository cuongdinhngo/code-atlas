---
id: 339
slug: a-path-prefix-that-matches-nothing-reads-as-no-such-symbol
title: "read_symbol with a path_prefix that excludes every definition answers no_such_symbol — the symbol exists; search_symbol says path_excluded for the same miss"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [315, 327]
---

## Why this exists (field retro, 2026-09-25)

`path_prefix` is the way out of `subject_ambiguous` for a proc declared in two files (327). A
session passed `path_prefix=database/migrations/V136` — a file-name prefix — and got
`no_such_symbol`. The retro: *"it looks like the symbol doesn't exist, which is the worst failure
for an agent."*

`path_prefix` matches whole directories by design (`is_under_path_prefix`, `nav_result.py:154-157`),
so the miss is correct. The **reason** is not: `_apply_path_prefix` (`read_symbol.py:622-640`)
returns `no_such_symbol` for a symbol that is indexed, while `search_symbol` answers the same miss
with `path_excluded` and the files the symbol lives in (`search_symbol.py:461,523`).

## Goal

A symbol excluded by the filter says so and names where it is.

## Scope / Deliverables

1. `_apply_path_prefix` answers `reason: path_excluded` with the definition sites, reusing
   `search_symbol`'s shape (R6.7).

## Constraints

- **315 / 327** — prefix semantics unchanged; whole directories only.
- **R6.7** — one `path_excluded` payload shape across both tools.

## Acceptance criteria

- **AC1** `read_symbol dbo.Gen path_prefix=db/migrations/V1` (file `db/migrations/V1__gen.sql`) →
  `path_excluded` listing that file; red on today's code.
- **AC2** A qname that does not exist, with any prefix → `no_such_symbol` (regression).

## References
`code_atlas/tools/read_symbol.py:622-640`; `code_atlas/tools/search_symbol.py:461,523,576`;
`code_atlas/tools/nav_result.py:100,154-157`; tickets 315, 327.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 339 — a path_prefix miss on an indexed symbol is path_excluded (working doc)

- **Ticket:** 339 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open
- **Reviewed at:** `736e7c3` (challenger round 1, CLEAN) · reviewed: code_atlas/tools/read_symbol.py · tests/test_path_prefix_miss_is_path_excluded.py · tests/test_read_symbol_path_prefix.py · docs/TOOLS.md

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: the payload is search_symbol's — `reason: path_excluded` plus `path_excluded: [sorted file
paths]` — and read_symbol keeps its existing `path_prefix` echo (327), so no field it emitted before
is dropped. Citation: Scope 1; C2 (R6.7).
HOW2: 327's AC3 test asserted `no_such_symbol` for this exact miss; 339 supersedes that assertion,
so the test is updated in place, not duplicated. Citation: Goal; 339 Why ("the reason is not
[correct]").

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=2 R=1 G=1 AC=2`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | an excluded symbol says so and names where it is | D1 | ✅ |
| R1 | Scope 1 | `_apply_path_prefix` → `path_excluded` + definition files, search_symbol's shape | D1 | ✅ |
| C1 | 315 / 327 | prefix semantics unchanged — `is_under_path_prefix` untouched | D1 | ✅ |
| C2 | R6.7 | one payload shape across both tools — asserted equal in a test | D2 | ✅ |
| AC1–AC2 | AC | proving | D2 | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `_apply_path_prefix` reached its empty branch only with definition rows in hand (the
  qname resolved), yet built the miss with `REASON_NO_SUCH_SYMBOL`.
- Blast radius: `_apply_path_prefix`'s two call sites (first read and the post-repair re-read) share
  it; a non-existent qname misses earlier in `_resolve_miss`, so AC2 is structurally unaffected.
  `tests/test_read_symbol_path_prefix.py` AC3 is the one existing assertion of the old reason.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — R6.7 ✅ (one reason constant, one field name, shape asserted across tools) · R7.5 ✅ (comment ≤ 3 lines)`

`BASELINE: green`

Baseline: bare `pytest` on `833564c` (Linux, php · composer · node on PATH) → `4589 passed, 4 skipped`.

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `_apply_path_prefix` answers `REASON_PATH_EXCLUDED` + `path_excluded` | code_atlas/tools/read_symbol.py | 1/1 |
| D2 | proving + 327's AC3 assertion updated | tests/test_path_prefix_miss_is_path_excluded.py · tests/test_read_symbol_path_prefix.py | 1/1 |
| D3 | tool description · TOOLS line · bookkeeping | code_atlas/tools/read_symbol.py · docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | tool payload | pytest through `read_symbol.create` over a seeded store | authored | ✅ |
| AC2 | regression | pytest, three prefixes on a missing qname | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_path_prefix_miss_is_path_excluded.py tests/test_read_symbol_path_prefix.py -q`

Rejected alternatives: a shared payload helper in `nav_result` (two one-line assignments; the
constant and the field name are already the single sites — YAGNI, R1.2); a prefix-matches-a-file-name
hint (would widen 315's semantics, which C1 fixes).

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/339-path-prefix-miss-is-path-excluded

Ran at 73bad8148a52607d899831c4ecab71678cdf8fe4

```
$ .venv/bin/python -m pytest tests/test_path_prefix_miss_is_path_excluded.py tests/test_read_symbol_path_prefix.py -q
7 passed
```

Red arm on `main` (`833564c`): AC1 and the cross-tool shape test fail; AC2 passes. `ruff` + `mypy`
clean; 101 neighbouring tests (read_symbol, path_prefix, nav reasons, descriptions) green.

Full verification at `73bad81` (the reviewed source `736e7c3` plus docs only): `scripts/gate.sh` →
`GATE GREEN — all 20 checks passed`; `scripts/docker-test.sh` → `4591 passed, 5 skipped` (Linux
host, Docker). Later commits touch this working doc only.

Design conformance: D1–D3 implemented-as-approved.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `736e7c3`: **CLEAN 6/0/0**. Verdict:
`clean (challenger only — REVIEWER: OFF)`. Probed beyond the ACs: a prefix matching one of two
definitions still reads that one; the ambiguous-neither case lists both files; the post-repair
re-read shares `_apply_path_prefix`, so it answers the same way.

| # | Note | Disposition |
|---|---|---|
| 1 | a separator-normalised hit (`\Foo\bar` → `Foo::bar`) returns a body from a file `path_prefix` excluded | pre-existing, outside Scope 1 (which names `_apply_path_prefix`) — BACKLOG follow-up |
| 2 | `find_references` with a prefix excluding every reference answers `no_matches`, naming no `path_excluded` | honest (not `no_such_symbol`), outside scope — same follow-up line |
| 3 | read_symbol's miss also echoes `path_prefix`, which search_symbol's does not | kept: 327 already emitted it, and dropping a field breaks 061 |

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 339 — a sighting of `do-not-attest-past-the-payloads-resolution` (R5.6);
class index bumped to 15 (338 and 339 both sighted it).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 126350 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
