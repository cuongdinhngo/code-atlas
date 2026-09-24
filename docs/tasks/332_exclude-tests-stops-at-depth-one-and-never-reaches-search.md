---
id: 332
slug: exclude-tests-stops-at-depth-one-and-never-reaches-search
title: "exclude_tests is refused past depth 1 on find_callers and absent from search_symbol — the two places three field sessions wanted it"
phase: 1.5b
milestone: Agent-trust
status: in-progress
depends_on: [262, 313, 315]
---

## Why this exists (field retros, 2026-09-23/24)

- **find_callers, depth 2** (FIELD-1426): `exclude_tests=true, depth=2` → hard error
  *"exclude_tests applies at depth 1 only"* (`find_callers.py:203-204`); the session dropped the
  filter and read test noise through the walk.
- **search_symbol, class-name queries** (FIELD-1449/1506/1586, FIELD-1621/1615, FIELD-1062/1634):
  66–87-row truncated pages *"dominated by `…Test::test*` methods"*, the wanted class near the top
  but the page spent on tests. `search_symbol` takes `kind`, `namespace`, `path_prefix` and no test
  filter.

262 filters **in SQL before paging** at depth 1, which is why it refuses deeper walks rather than
filter a page it already cut. 313 then made `impact` filter *inside the walk*, so the repo already
holds the second shape. The test role is one fact (`symbol_role.py`); it just is not offered here.

## Goal

The same `exclude_tests` meaning is available on a multi-hop caller walk and on symbol search.

## Scope / Deliverables

1. **find_callers depth > 1**: filter test-role sites inside the walk, as 313 does for `impact` —
   design call whether a test node is pruned (its callers unreached) or only hidden, stated in the
   payload.
2. **search_symbol `exclude_tests`**: filter in SQL before paging, 262's shape; `total_count`
   counts the filtered set.
3. **One predicate** — the test role 262 / 313 already read.

## Constraints

- **061** — `exclude_tests=false` (the default) is byte-identical on both tools.
- **R6.7** — no second test-path heuristic.
- **R1.1** — test role from the contract / adapter, never a directory-name branch.
- **313's gate** — the agent brief teaches both in the same change.

## Acceptance criteria

- **AC1** `find_callers(depth=2, exclude_tests=true)` answers, with no test-role site in the rows.
- **AC2** `search_symbol(query=<class>, exclude_tests=true)` on a fixture with the class and three
  test methods returns the class, and `total_count` excludes the tests.
- **AC3** Defaults are byte-identical (regression).

## References
`code_atlas/tools/find_callers.py:203-204`; `code_atlas/tools/search_symbol.py`;
`code_atlas/symbol_role.py`; `code_atlas/tools/impact.py`; tickets 262, 313, 315.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 332 — exclude_tests multi-hop + search (working doc)

- **Ticket:** 332 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR
- **Session status:** review clean → finalise

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW (prune vs hide on depth>1): prune test-role sources inside the walk, same as 313 `impact` (`exclude_test_sources` on expand). Citation: ticket Scope §1 + impact.py docstring.

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | same exclude_tests on multi-hop callers + search | remove depth gate; add search arg | D1 D2 | AC1 AC2 | ✅ |
| R1 | Scope 1 | depth>1 filter inside walk as 313 | pass exclude to BFS edges_by_target | D1 | AC1 | ✅ |
| R2 | Scope 2 | search_symbol exclude_tests SQL before paging | store.search_nodes flag | D2 | AC2 | ✅ |
| R3 | Scope 3 | one predicate (is_test) | _exclude_test_sources / nodes.is_test | D1 D2 | review | ✅ |
| C1 | Constraints | 061 default byte-identical | omit-when-false | D3 | AC3 | ✅ |
| C2 | Constraints | R6.7 no second heuristic | reuse is_test | D1 D2 | review | ✅ |
| C3 | Constraints | R1.1 no directory branch | stored is_test | D2 | review | ✅ |
| C4 | Constraints | 313 brief teaches both | gen_skill prose | D4 | review | ✅ |
| AC1 | AC | depth=2 exclude_tests answers, no test rows | proving | D3 | proving | ✅ |
| AC2 | AC | search class+tests → class, total excludes tests | proving | D3 | proving | ✅ |
| AC3 | AC | defaults byte-identical | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: depth gate refused exclude_tests; search had no filter; BFS omitted the store predicate.
- Blast radius: find_callers, search_symbol, store search_* , gen_skill brief.

`TRACK: backend — 0/5 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 ✅ · R6.7 ✅ · R1.4 ✅ · R7.2 ✅`

`BASELINE: green`

## Phase 2 — Design

- Approach: remove depth ValueError; thread exclude_test_sources into BFS; add exclude_tests to search_symbol → store; gen_skill teaches both.
- Rejected: hide-without-prune (ticket asks walk filter as 313).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | multi-hop exclude | find_callers.py | BFS | R1 AC1 | 1/1 |
| D2 | search exclude + store | search_symbol.py · store.py | SQL | R2 AC2 | 1/1 |
| D3 | proving AC1–3 | tests/test_exclude_tests_multi_hop_and_search.py | — | AC* | 1/1 |
| D4 | brief | scripts/gen_skill.py | USAGE | C4 | 1/1 |
| D5 | bookkeeping | docs/tasks/332 · BACKLOG · TOKEN_LEDGER | — | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest | authored | ✅ |
| AC2 | integration | pytest | authored | ✅ |
| AC3 | integration | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_exclude_tests_multi_hop_and_search.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/332-exclude-tests-multi-hop-and-search

Ran at PLACEHOLDER

```
$ .venv/bin/python -m pytest tests/test_exclude_tests_multi_hop_and_search.py -q
...
3 passed
```

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer) — waived at handover.
CHALLENGER: ON — CLEAN 10/0/0 after brief regen (round-1 NOT-CLEAN 9/1/0 brief stale).

## Phase 5 — Finalise (learning loop)

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger round 1`
