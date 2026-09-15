---
id: 273
slug: the-partition-counts-edges-and-the-total-counts-callers
title: '`production_count` + `test_count` counts edge rows while `total_count` counts the caller set, so a real answer reported 78 callers and 102 production ones — a partition that exceeds its whole is a number no reader can interpret, and the correct response to it is to ignore every count on the payload'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [262, 258]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §6)

One `find_callers` answer, quoted verbatim: `total_count: 78`, `production_count: 102`,
`test_count: 0`, `result_subtrees: {legacy: 42, src: 36}`. 42 + 36 = 78. The retro's verdict:

> *"I still do not know what the 102 counts. I ignored it, which is the correct response to a number
> you cannot interpret, but a number nobody can interpret is a number that should not ship."*

262 shipped the partition with the stated invariant *"`production_count` + `test_count` summing to the
hit set"*. Two things break it:

- `inbound_test_rows` (`store.py:1746–1776`) is `SELECT … COUNT(*) FROM edges JOIN nodes src …
  GROUP BY 1, 2` — it counts **edge rows**, so two calls from one caller count twice, while
  `outcome.total_count` is the size of the BFS hit set (one row per caller).
- That join is `src.qualified_name = edges.source_qname`, so a qname declared in more than one file
  multiplies every edge by its definition count — the same fan-out [258](258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md)
  names, arriving here as inflation rather than as rows.

The consequence is worse than a wrong number: a partition that can exceed its total teaches a reader
to discount `production_count`, which is the field [272](272_a-partition-that-is-all-tests-answers-ok.md)
needs them to act on.

## Scope / Deliverables

- **One census over one hit set.** The partition counts the same distinct sources the answer counts,
  so `production_count + test_count == total_count` holds by construction at depth 1 — not by
  a second query that happens to agree.
- **A test that pins the invariant**, not the two numbers: any fixture, any tier filter, any argument
  filter — the partition adds up or the test fails.
- **Multi-call and multi-definition fixtures**: one caller calling the subject three times, and a
  subject whose caller qname is declared in two files. Both are single callers.
- **`find_references` audited for the same shape** and fixed or pinned as already correct.

## Constraints

- R4.3: the count stays one grouped store read; no per-row Python counting over an unbounded pull.
- The partition must keep respecting `args_at` / `confidence_tier`, which today it does — the filter
  predicates are the part that is right.
- Above depth 1 the partition stays omitted (262's rule); this ticket does not widen it.
- 061: no new field; the fix is to the numbers already shipped.

## Acceptance criteria

- A property test over the existing caller fixtures: for every depth-1 answer, the partition sums to
  `total_count`.
- A fixture with one caller and three call sites reports `production_count: 1`.
- A fixture whose caller qname is declared in two files reports `production_count: 1`.
- `test_role_source` still names the deciding source on every partitioned payload.

## References
`code_atlas/store.py:1746–1776`, `code_atlas/tools/find_callers.py:579–599,519–523`,
field retro round 20 §6, [262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[258](258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md),
[272](272_a-partition-that-is-all-tests-answers-ok.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 273 — partition counts distinct callers (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** ticket locks distinct-source census = hit set at depth 1; two fixtures; find_references audit; R4.3; 061; no depth>1.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | partition can exceed total | one census over one hit set | D1 | AC1 | ✅ |
| C1 | Constraints | R4.3 one grouped read | SQL GROUP BY, not Python over all edges | D1 | store | ✅ |
| C2 | Constraints | keep args_at / tier filters | same `_edge_where` extra | D1 | — | ✅ |
| C3 | Constraints | depth>1 stays omitted | `_test_census` unchanged | — | AC omit | ✅ |
| C4 | Constraints | 061 no new field | numbers only | D1 | — | ✅ |
| R1 | Scope | distinct sources | COUNT(DISTINCT source_qname) | D1 D2 | AC2 AC3 | ✅ |
| R2 | Scope | property: sum == total | proving | D4 | AC1 | ✅ |
| R3 | Scope | multi-call + multi-def | fixtures | D4 | AC2 AC3 | ✅ |
| R4 | Scope | find_references audit | pin: hit set is edges | D3 | AC4 | ✅ |
| AC1 | AC | depth-1 partition sums to total_count | proving | D4 | proving | ✅ |
| AC2 | AC | 3 call sites → production_count 1 | proving | D2 D4 | proving | ✅ |
| AC3 | AC | two definition files → 1 | proving | D1 D4 | proving | ✅ |
| AC4 | AC | test_role_source still named | proving | D4 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause (bug, `logic`): `inbound_test_rows` JOIN on `qualified_name` cartesian-multiplies, and COUNT(*) counts edges while the ticket's hit set is distinct callers. Depth-1 `_callers` also used `count_edges_by_target` (edge rows).
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R4.2 ✅ · R4.3 ✅ · R1.4 ✅ · R6.1 ✅`

```
Ran at 24747395000ba20f810baeb41e113c768f8f2e5b
$ .venv/bin/python -m pytest tests/test_callers_test_role_census.py -q --tb=no
7 passed in 0.40s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: `distinct_sources` on `inbound_test_rows` / `edges_by_target` / `count_edges_by_target`. find_callers depth-1 uses it for list + count + census (one hit set). One node per qname (MIN id / LIMIT 1) kills 258 cartesian. find_references keeps edge rows (hit set is edges) but uses the one-node join so census cannot exceed `count_edges_by_target`.
- Rejected: Python-side unique over unbounded edges (R4.3). Rejected: changing find_references total_count to callers (results are edge hits).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_partition_counts_callers.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | one-node join + distinct_sources | store.py | inbound_test_rows callers | 1/1 |
| D2 | depth-1 list+count distinct | find_callers.py | pagination of unique callers | 1/1 |
| D3 | find_references pin (edge rows, one-node join) | store.py default | test_find_references_carries_census | 1/1 |
| D4 | proving fixtures | tests/test_partition_counts_callers.py | — | 4/4 |
| D5 | CONVENTION row + backlog | docs | bookkeeping | 1/1 |

## Phase 3 — Execute

**Branch:** feat/273-the-partition-counts-edges-and-the-total-counts-callers
**Axis 1:** store.py, find_callers.py, tests/test_partition_counts_callers.py, CONVENTION.md, BACKLOG.md, task file.
**Axis 2:** implemented-as-approved.

**Verification sweep**

```
Ran at fe436253c3972deae8b12ad1c8b4019d9a5daa54
$ .venv/bin/python -m pytest tests/test_partition_counts_callers.py tests/test_callers_test_role_census.py -q --tb=line
11 passed in 1.49s
```

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)**
**CHALLENGER: ON** — round-1 NOT CLEAN (property test over existing fixtures / filters). Verify-only round-2: MET — `test_partition_sums_under_tier_filter`, `test_partition_sums_under_arg_filter`, `_assert_partition` on `tests/test_callers_test_role_census.py` depth-1 answers.

**Clean?** clean (challenger only — REVIEWER: OFF)

`Reviewed at 3da07bb32baee8f25dc43967c8c9602a476b8484` · reviewed files: `code_atlas/store.py`, `code_atlas/tools/find_callers.py`, `tests/test_partition_counts_callers.py`, `tests/test_callers_test_role_census.py`, `docs/CONVENTION.md`, `docs/BACKLOG.md`. Working-doc path `docs/tasks/273_the-partition-counts-edges-and-the-total-counts-callers.md` (embedded) is staleness-exempt.

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1 dispatch)`

Outward (handover-authorised): push feature branch; open PR. Deferred: merge.

---

## Session status

- **Last updated:** 2026-09-14
- **Current phase:** finalise
- **Next action:** push branch and open PR
- **Blocked on:** none
