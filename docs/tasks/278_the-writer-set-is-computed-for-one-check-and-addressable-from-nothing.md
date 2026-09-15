---
id: 278
slug: the-writer-set-is-computed-for-one-check-and-addressable-from-nothing
title: '"What else writes this table" is the question a data-attribution defect turns on, and the graph holds a `WRITES` edge, an unlinked-writer probe and a column-level target — all reachable only from `check_column_defaults`, so the question is asked as `find_references` on a Table, answered near-empty, and a third write site ships unfixed'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [022, 215, 255, 248]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 22 §7 / §8.1)

A three-ticket batch where all three defects were *which code writes this column*. The session
scoped one of them with `find_callers` on a method, concluded the table had two write paths, and
review found a **third** — a static helper on an unrelated class writing the same table, feeding the
same display. Shipping without it would have re-opened the ticket a third time.

> *"`find_callers` was never going to find it, and that is not the tool's fault. I asked who calls
> this method. The question was what else writes this table."*

The retro ranks this first of five asks: *"the single highest-value gap."* Its floor is modest —
*"even a `find_references` on a Table that returned INSERT/UPDATE statement sites at `HEURISTIC`
would have caught my miss."*

What already exists, none of it addressable by that question:

- `WRITES` is contract vocabulary since v9 (`contract.py:147`), targeting the Column when the
  statement names it and the Table at DYNAMIC when it does not.
- `store.has_unlinked_writes_relating_to` (`store.py:1947`) — the incompleteness the graph *can*
  know — has exactly one consumer: `check_column_defaults.py:248`.
- Only the SQL adapter emits `WRITES` (`adapters/sql/src/scan.js`). A write issued from application
  code is not modelled at all, in any language.

So a Table subject reaches a writer answer through one capability check and no navigation tool.

## Scope / Deliverables

- **The writer set is addressable.** A Table (and a Column) subject can be asked for the routines
  that write it, returning the `WRITES` sources the graph holds, tiered as stored.
- **The answer states its own half.** Where the index covers languages that emit no `WRITES`, an
  answer about a table is the SQL half only, and says so with the 255/264 machinery rather than
  reading as complete. `has_unlinked_writes_relating_to` is the existing evidence that a writer
  reached the graph and never linked — surface it as a count, not as a boolean buried in one check.
- **Decide the application-code half explicitly, and record the verdict.** A write issued as a SQL
  string from a host language is either (a) out of scope, stated in the tool description so nobody
  reads the SQL half as the whole, or (b) a `HEURISTIC` edge an adapter emits from a statement it
  parses out of a literal. Do not leave it undecided — the retro's whole miss lives in that gap.
- Whichever way (b) goes, it is a **language spec / ecosystem** judgement per R2 — never a repo's
  table names or ORM.

## Constraints

- R1.1: no language branch in the core; the Table/Column subject path is a **kind** branch, the way
  248 did it.
- R5.6: a partial writer set is never presented as the writer set — 215's own finding, which this
  ticket must not undo by widening the surface.
- R4.3: bounded like the existing probe (`_WALK_UNLINKED`), never an unbounded scan per query.
- R3: `WRITES` already exists; if no vocabulary changes, `contract_version` does not move.

## Acceptance criteria

- A Table subject returns its writer routines from a SQL fixture, with tier, and a Column subject
  returns the narrower set where the statement names the column.
- On an index whose other languages emit no `WRITES`, the same answer carries the unmeasured-relation
  reason and a route — never a bare `no_matches`.
- Unlinked writers naming the table are reported as a count on the answer, not only inside
  `check_column_defaults`.
- The application-code verdict is written into PLAN §19 and reflected in the tool description.
- `check_column_defaults` keeps its current behaviour and tests.

## References
`code_atlas/contract.py:147,62–78`, `code_atlas/store.py:1947–1965`,
`code_atlas/tools/check_column_defaults.py:248`, `adapters/sql/src/scan.js`,
field retro round 22 §7 / §8.1 / §9, [022](022_sql-schema-adapter.md),
[215](215_a-partial-writer-set-looks-finished-and-a-column-is-counted-twice.md),
[248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 278 — Table/Column writer set via find_references (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: application-code / host-language string writes → **(a) out of scope**, stated via `writes_sql_adapter_only` + PLAN §19 + tool description (ticket Scope third bullet; R2 forbids ORM/repo names). Citation: ticket Scope / Deliverables bullet 3 option (a).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | writer set only from check_column_defaults | addressable via find_references | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 kind branch not language | TABLE/COLUMN kind path | D1 | — | ✅ |
| C2 | Constraints | R5.6 never present partial as whole | caveat + §19 | D1 | AC2 | ✅ |
| C3 | Constraints | R4.3 bounded unlinked probe | count_unlinked_writes | D1 | AC3 | ✅ |
| C4 | Constraints | R3 no vocab bump | WRITES exists | D1 | — | ✅ |
| R1 | Scope | writer set addressable Table/Column | find_references WRITES filter | D1 | AC1 | ✅ |
| R2 | Scope | answer states SQL half | writes_sql_adapter_only | D1 | AC2 | ✅ |
| R3 | Scope | unlinked writers as count | unlinked_writes_count | D1 | AC3 | ✅ |
| AC1 | AC | Table/Column writers + tier | proving | D2 | proving | ✅ |
| AC2 | AC | multi-lang caveat not bare no_matches | proving | D2 | proving | ✅ |
| AC3 | AC | unlinked count on answer | proving | D2 | proving | ✅ |
| AC4 | AC | application-code verdict in §19 + tool desc | PLAN/TOOLS/docstring | D3 | docs | ✅ |
| AC5 | AC | check_column_defaults unchanged | existing tests | D2 | adjacent | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: WRITES + unlinked probe exist but only `check_column_defaults` consumes them; nav on Table returns near-empty.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 ✅ · R4.3 ✅ · R5.6 ✅ · R7.6 ✅`

Ran at edb89be30f2d501d1f539c6d69d15e0bc8a9dfd7

```
$ .venv/bin/python -m pytest tests/test_check_column_defaults.py -q --tb=no
.......                                                                  [100%]
7 passed in 1.44s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: kind-branch on Table/Column → `kinds=(WRITES,)`; Table unions CONTAINS columns; surface `count_unlinked_writes_relating_to`; multi-lang caveat; host writes out of scope in §19/TOOLS/docstring.
- Rejected: (b) HEURISTIC host-language edges (new adapter work, out of this ticket's nav floor).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_table_writer_set_via_find_references.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | WRITES filter + count + caveat | store · find_references · nav_result | Table/Column nav | 3/3 |
| D2 | proving + check_column_defaults green | tests | — | 4/4 |
| D3 | §19 + TOOLS + docstring | PLAN · TOOLS · find_references | docs | 3/3 |

## Phase 3 — Execute

**Branch:** feat/278-the-writer-set-is-computed-for-one-check-and-addressable-from-nothing
**Axis 1:** store, find_references, nav_result, proving test, PLAN, TOOLS.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at edb89be30f2d501d1f539c6d69d15e0bc8a9dfd7

```
$ .venv/bin/python -m pytest tests/test_table_writer_set_via_find_references.py tests/test_check_column_defaults.py -q --tb=line
...........                                                              [100%]
11 passed in 1.93s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (9 met · 0 not met · 0 can't tell); agent d9e46f97-2182-4006-a6d2-353534533068

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_table_writer_set_via_find_references.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-278d.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/362

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
