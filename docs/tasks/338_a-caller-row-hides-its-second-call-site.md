---
id: 338
slug: a-caller-row-hides-its-second-call-site
title: "find_callers returns one row per caller with the first line only — a method that calls the subject twice shows one site, and a fix applied there is a half-fix"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [037, 273]
---

## Why this exists (field retro, 2026-09-25)

A session needed to add a call beside every call to a context-setup method. `find_callers` returned
2 production callers. Grep showed one of them calls the subject **twice** (the main path and a
fallback), and the retro *"nearly patched only one site"*.

Probed on `main` (`927aeb9`): `init()` calls `ctx()` at lines 7 and 9. Both `CALLS` edges are
stored; `find_callers \App\Db::ctx` returns one row, `line: 7`.

One row per caller is right: 273 made the hit set the distinct callers so that
`production_count + test_count == total_count`. What is lost is the other lines, not the row.

## Goal

A caller row names every line it calls the subject from, without changing what is counted.

## Scope / Deliverables

1. **`call_lines`** on a depth-1 row whose caller has two or more edges to the subject: the sorted
   lines. Omitted at one (061). `line` stays the first, so existing readers are unaffected.
2. **`include_source`** quotes each listed line (037's `annotate` already reads per file once).

## Constraints

- **273** — `total_count` and the partition still count callers; the invariant test stays green.
- **Bounded** — the lines come from the edges already fetched for the page, not a query per row.

## Acceptance criteria

- **AC1** The probe above → the `init` row carries `call_lines: [7, 9]`; red on today's code.
- **AC2** A caller with one call site → byte-identical row.
- **AC3** 273's invariant test passes unchanged.

## References
`code_atlas/store.py:1794-1830` (`edges_by_target`, `distinct_sources`);
`code_atlas/tools/call_site.py:17-39`; tickets 037, 273.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 338 — a caller row names every line it calls the subject from (working doc)

- **Ticket:** 338 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open
- **Reviewed at:** `962d034` (challenger round 1, CLEAN) · reviewed: code_atlas/store.py · code_atlas/tools/find_callers.py · code_atlas/tools/call_site.py · tests/test_caller_row_names_every_call_line.py · docs/TOOLS.md

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1 (Constraint "Bounded"): the distinct-source page read keeps one edge per caller (`MIN(id)`),
so the other lines are not in the fetched rows. They come from **one** extra read per page —
`call_lines_by_source(qname, <the page's callers>)` under the page's own filters — never a query per
row. Citation: Constraint 2; 331's one-query-per-page precedent.
HOW2: `include_source` quotes the lines as `call_sources`, parallel to `call_lines`; `source` stays
the quote of `line`, so a one-site row is unchanged. Citation: Scope 2; AC2 (061).
HOW3: `call_lines` lists the lines in the row's own `file`. A qname declared in two files (334)
calling from both is still one row; its other file's lines are not attributed to this `file`.
Depth > 1 already returns one row per edge, so `call_lines` is depth-1 only, as Scope 1 says.

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=2 R=2 G=1 AC=3`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | every line a caller calls the subject from is named, counts unchanged | D1 · D2 | ✅ |
| R1 | Scope 1 | depth-1 row with ≥ 2 lines → sorted `call_lines`; omitted at one; `line` unchanged | D1 · D2 | ✅ |
| R2 | Scope 2 | `include_source` quotes each listed line, one file read per file | D3 | ✅ |
| C1 | 273 | `total_count` and the partition still count callers | D2 (count path untouched) | ✅ |
| C2 | Bounded | one read per page, not per row | D1 | ✅ |
| AC1–AC3 | AC | proving + 273's invariant test unchanged | D4 | ✅ |

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `_callers(hops=1)` reads `edges_by_target(distinct_sources=True)`, whose SQL keeps
  `MIN(id)` per `source_qname` (273); the other edges are stored but never read.
- Blast radius: `store.py` (new read), `find_callers._callers` depth-1 arm, `call_site.annotate`
  (shared with `find_references`, whose rows never carry `call_lines` — unchanged). Count paths
  (`count_edges_by_target`, `inbound_test_rows`) untouched.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.4 ✅ (the SQL lives in store.py) · R1.1 ✅ (no language branch) · R7.5 ✅ (comments ≤ 3 lines)`

`BASELINE: green`

Baseline: bare `pytest` on `833564c` (Linux, php · composer · node on PATH) → `4589 passed, 4 skipped`.

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `GraphStore.call_lines_by_source` — sorted distinct lines per (caller, file), same filters as the page | code_atlas/store.py | 1/1 |
| D2 | `_attach_call_lines` on the depth-1 page; set only at ≥ 2 lines | code_atlas/tools/find_callers.py | 1/1 |
| D3 | `annotate` reads the extra lines in the same per-file pass; `call_sources` | code_atlas/tools/call_site.py | 1/1 |
| D4 | proving (real PHP build) | tests/test_caller_row_names_every_call_line.py | 1/1 |
| D5 | tool description · TOOLS line · bookkeeping | code_atlas/tools/find_callers.py · docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | integration (PHP build → resolver → find_callers) | pytest over a real build | authored | ✅ |
| AC2 | row shape | pytest, key absence with and without `include_source` | authored | ✅ |
| AC3 | count invariant | `tests/test_partition_counts_callers.py` unchanged + a count assertion | existing + authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_caller_row_names_every_call_line.py tests/test_partition_counts_callers.py -q`

Rejected alternatives: `GROUP_CONCAT(line)` inside the distinct-source SQL (changes the row shape
every `distinct_sources` reader gets, for one tool's field); returning every edge and folding in
Python (pages by edge, breaking 273's caller paging).

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/338-caller-row-names-every-call-line

Ran at 962d034edff1d1b27a5b98a856e06d9a6c128046

```
$ .venv/bin/python -m pytest tests/test_caller_row_names_every_call_line.py tests/test_partition_counts_callers.py -q
12 passed
```

Red arm on `main` (`833564c`): AC1 and the `include_source` test fail; AC2 and the count test pass.
`ruff` + `mypy` clean; 15 neighbouring test files (callers, call sites, nav tools, descriptions,
payload weight) → 114 passed.

Design conformance: D1–D5 implemented-as-approved.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `962d034`: **CLEAN 10/0/0**. Verdict:
`clean (challenger only — REVIEWER: OFF)`. Probed beyond the ACs: `confidence_tier`, `exclude_tests`
and `arg_position` narrow `call_lines` with the page (a filter leaving one site drops the field);
two calls on one line dedupe to one; CALLS + NEW onto one qname aggregate; a `limit=2, offset=2`
page issues one `call_lines_by_source` read for its two callers; depth 2 never carries the field.

| # | Note | Disposition |
|---|---|---|
| 1 | a dirty tracked file re-indexed by the freshness guard moves `line` and `call_lines` together | pre-existing guard behaviour; both read `edges.line`, so they stay consistent |
| 2 | "red on today's code" not re-run by the challenger (it was told not to use the main checkout) | the red arm is in Phase 3, run by stashing `code_atlas/` in the worktree |

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 338 — a sighting of `do-not-attest-past-the-payloads-resolution` (R5.6);
class index bumped to 14.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 133920 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
