---
id: 292
slug: a-container-hit-is-crowded-out-by-its-members
title: 'An exact-name hit on a container and a substring hit on the members it contains sit in the same ranking bands, so searching a stored procedure or a table by name returns its own definitions first and then forty of its columns — and on a subject with more members than the page holds, the real answers are truncated away by rows the caller did not ask for'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [265, 277, 245]
---

## Why this exists (field retros — the anchor repo, rounds 16 and 22, 2026-09-15 / 2026-09-14)

Two rounds, two languages, one shape.

Round 16 searched a stored-procedure name: 86 hits, **truncated at the page limit**, and the page was
*"dominated by `#UpdateRecursiveUntilTemp::<column>` rows"*. The procedure's real definitions — the
function node, the file node, the `_beta` twin, three migration copies — were there, and then roughly
forty temp-table **columns** sharing the substring pushed the answer past the page. The retro's verdict:

> *"A `search_symbol` for a procedure name should not return 40 temp-table columns ahead of the
> procedure's own definitions, and should not truncate the real answers at a page limit because of
> them."*

Round 22 §5 logged the same thing on a Table and generalised it: *"When a Table matches exactly, its
columns are rarely what the caller wants."*

The ordering is working as designed and the design has a blind spot. `is_direct_match`
(`store.py:379-391`) bands exact-and-prefix ahead of near-misses over the whole result set (180/167),
and relevance breaks ties inside a band. A column's qname contains its container's name, so
`Container::col_1 … col_40` are all legitimate substring hits — and where the container name is also a
*prefix* of them, they land in the **same** band as the container's own definitions, ranked on
relevance alone. Nothing in the order knows that a column is a *member of the thing asked for* rather
than a competing answer to it.

This is 277's argument applied to containment instead of mirroring: the graph already holds the
relation that decides the order (`CONTAINS`), and the ranking does not read it. It is also 245's
failure mode with the sign flipped — there a truncated near-miss answer had no route; here a truncated
answer is *caused* by rows the caller did not ask for, so a route is not the fix, the order is.

Out of scope, deliberately: a query that is a bare **class** name wanting one of its methods
(round 26 §3). That is a correct near-miss with a correct route — the payload already says
`try_instead: file_outline` — and widening this ticket to cover it would change a working answer.

## Scope / Deliverables

- **A container's own definitions outrank its members** for a query that names the container, using
  the stored `CONTAINS` relation rather than a name-shape heuristic. Members stay in the answer; they
  stop displacing it.
- **Truncation must not be caused by members.** A page that had to drop real hits to make room for
  contained rows is the failure; whether that is fixed by order alone or needs the count reported
  separately is the design call.
- **Decide the scope by kind, once.** Table/Column is the clearest case and Procedure/Function the one
  the field hit; pick the rule from contract vocabulary (R1.1), never per language.

## Constraints

- R1.1: the rule keys on node kinds and `CONTAINS`, never on a language or a naming convention.
- R6.7 / 167: the exactness band stays one predicate. This ticket adds an ordering input, it does not
  fork the band definition.
- 061: a query whose hits contain no container/member pair is byte-identical to today, `reason`
  included.
- R4.2: deterministic order; ties resolve as they do now.
- Do not drop members from the result — the round-22 note is that they are *rarely* wanted, not never.
- Leave 277's mirror ordering and 265's tier-first default intact; this composes with them.

## Acceptance criteria

- An exact-name query on a Table returns the Table before its columns.
- The same query on a Procedure/Function returns its definitions (and its indexed twins) before rows
  merely contained by a same-named object.
- A subject whose members exceed the page no longer truncates a real definition away.
- A query with no container/member relation among its hits is byte-identical to today.
- 277's mirror-order and 265's ordering tests still pass.

## References
`code_atlas/store.py:379-396`, `code_atlas/tools/search_symbol.py:116-128`,
`code_atlas/contract.py:98-104` (`CLASS_MEMBER_KINDS`, `CONTAINS`),
[265](265_the-default-page-order-is-the-alphabet.md),
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).
Origin: field retro round 16 §1.2 / §3, 2026-09-15, and round 22 §5, 2026-09-14 — two rounds, same shape.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 292 — container outranks CONTAINS members (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket
- **Current phase:** finalise
- **Session status:** autorun — reviewer off; challenger CLEAN

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: demote only `Column` (`COLUMN_KIND`) when a `CONTAINS` parent is a direct match **and** a hit under the same FTS/kind/namespace filters; key sits between exactness band and mirror prefer. Cites Scope "Decide the scope by kind, once" + Constraints R1.1 / R6.7 / 061; Class members left out (ticket Out of scope).

## Requirements matrix

`SECTIONS: 5 found (Why · Scope · Constraints · Acceptance · References) | 5 decomposed | ROWS: C=5 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | members crowd container | ORDER BY CONTAINS demotion | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 kind+CONTAINS | COLUMN_KIND only | D1 | AC1 | ✅ |
| C2 | Constraints | R6.7 one band predicate | exactness unchanged | D1 | AC4 | ✅ |
| C3 | Constraints | 061 no-pair identical | CASE always 0 | D1 | AC4 | ✅ |
| C4 | Constraints | keep members | demote not drop | D1 | AC1 | ✅ |
| C5 | Constraints | compose 277/265 | after band, before mirror | D1 | AC5 | ✅ |
| R1 | Scope | container outranks members | _SEARCH_CONTAINS | D1 | AC1 | ✅ |
| R2 | Scope | truncation not by members | order alone | D1 | AC3 | ✅ |
| R3 | Scope | scope by kind once | Column only | D1 | AC2 | ✅ |
| AC1 | AC | Table before columns | proving | D2 | proving | ✅ |
| AC2 | AC | Function before same-named cols | proving | D2 | proving | ✅ |
| AC3 | AC | page keeps definitions | proving | D2 | proving | ✅ |
| AC4 | AC | no-pair byte-identical | proving | D2 | proving | ✅ |
| AC5 | AC | 277/265 still pass | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Decision

Demote `Column` rows that are `CONTAINS` targets of a parent whose name/qname `is_direct_match`es the query. Order alone fixes truncation; no separate count field. Class/`CLASS_MEMBER_KINDS` excluded (ticket out of scope).

## Phase 1 — Analysis

- Root cause: same exactness band for container and `Container::col_*`; BM25 alone lets members bury twins.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 (ENGINEERING_RULES) ✅, R6.7 (ENGINEERING_RULES) ✅, 061 (ENGINEERING_RULES) ✅`

Ran at 276059785c58b4fb3412c2b7a49a5343a922eb02

```
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py tests/test_tier_first_page_order.py -q --tb=no
..............                                                           [100%]
14 passed in 0.80s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: SQL `EXISTS` demotion key on `COLUMN_KIND`+`CONTAINS`+direct-match parent that also matches FTS/kind/namespace; bind query in ORDER BY.
- Rejected: name-shape heuristic on `::` (R1.1); demote all CONTAINS targets including Methods (out of scope); drop members from results.

`HANDLES: 0 recalled | 0 traced | 0 does not apply | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_container_member_search_order.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | _SEARCH_CONTAINS in ORDER BY | code_atlas/store.py | search_nodes FTS | 1/1 |
| D2 | proving | tests/test_container_member_search_order.py | — | 1/1 |
| D3 | docs | docs/design/indexing.md, docs/TOOLS.md | search docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/292-container-hit-not-crowded-by-members
**Axis 1:** store ORDER BY · proving · docs.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 276059785c58b4fb3412c2b7a49a5343a922eb02

```
$ .venv/bin/python -m pytest tests/test_container_member_search_order.py tests/test_mirror_aware_search_order.py -q --tb=no
..........                                                               [100%]
10 passed in 0.74s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (F1 graph-wide CONTAINS); fixed hit-set-local parent filter + regression; round-2 CLEAN. agents 32fbe9fb-01bd-4b07-8960-ab117145b1b0 / 93904933-031d-4e18-9435-9a8f64a7760c

Ran at 276059785c58b4fb3412c2b7a49a5343a922eb02

```
$ .venv/bin/python -m pytest tests/test_container_member_search_order.py tests/test_mirror_aware_search_order.py tests/test_tier_first_page_order.py -q --tb=no
...............                                                          [100%]
15 passed in 1.10s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_container_member_search_order.py — 5 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`


## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN
PR: https://github.com/cuongdinhngo/code-atlas/pull/386

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x2)`

