---
id: 297
slug: the-member-demote-is-keyed-to-one-kind-so-a-class-still-buries-itself
title: '292 stopped a Table being crowded off page one by its own Columns by demoting, inside the band, any hit whose CONTAINS parent is also a hit — but the SQL it shipped tests `nodes.kind = COLUMN_KIND`, and the crowding is not a Column fact: a qualified query puts a Class and every one of its Methods in the same direct band, so the container an agent asked for still ranks behind its own members in php, typescript and python'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [292, 265, 245]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

292's mechanism is right and its key is narrow. `_search_contains_demote` (`code_atlas/store.py:410`)
builds an `ORDER BY` term reading `CASE WHEN nodes.kind = '{contract.COLUMN_KIND}' AND EXISTS (…
CONTAINS parent that is itself a direct match …)`, so it fires for Columns and for nothing else.

The band collision it fixes is a qname fact, not a Column fact. A member's qname is its container's
qname plus `MEMBER_SEPARATOR` plus its own name, so any query spelled as the container is a *prefix*
of every member's qname, and the prefix arm of `is_direct_match` puts them all in the direct band
together. Measured against the shipped predicate:

```
is_direct_match('App\UserService',          'getUser', 'App\UserService::getUser')          -> True
is_direct_match('src/user.ts::UserService', 'getUser', 'src/user.ts::UserService::getUser')  -> True
```

Both are the `dbo.Trans` / `dbo.Trans::ChangeUser` shape 292 was filed for, in the two adapters 292
does not cover. On a class with forty methods the class declaration is one row among forty-one in the
same band, ordered by whatever `_SEARCH_ORDER` decides — which is 265's tier order, not "the thing
that was asked for first". The cost is 245's shape: the agent pages, or re-asks with a narrower
query it had no reason to think it needed.

## Scope / Deliverables

- **Generalise the demote to containment, not kind:** any hit whose `CONTAINS` parent satisfies the
  same query, kind and namespace filters ranks after non-members within its band. The `COLUMN_KIND`
  literal goes; the parent-side filter parity 292 established stays exactly as it is.
- **One definition site** (R6.7) — the same ORDER BY term serves every kind, so Table/Column and
  Class/Method cannot drift apart.
- **No language branch** (R1.1): `CONTAINS` is contract vocabulary, and the fix must read no kind
  name that belongs to one adapter.

## Constraints

- **061 / byte-identical:** a hit set with no container/member pair in it produces the same order as
  today, and every SQL result 292 pinned stays pinned.
- The parent sub-select already costs one EXISTS per candidate row; generalising must not widen it —
  same index path, same filters, no second join.
- Band, mirror order and tier order (265 / 277) keep their precedence; this is a within-band tiebreak
  and stays one.

## Acceptance criteria

- A PHP fixture searching the qualified class name returns the `Class` row above its `Method` rows, and
  the same for a TypeScript and a Python fixture.
- 292's SQL tests pass unchanged, and a fixture with no container/member pair returns a byte-identical
  page.
- No `COLUMN_KIND` (or any other single kind) literal remains in the demote term.

## References
`code_atlas/store.py:407-445`, `:2514-2540`, `code_atlas/contract.py:243`,
[292](292_a-container-hit-is-crowded-out-by-its-members.md),
[265](265_the-default-page-order-is-the-alphabet.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 297 — CONTAINS demote any kind (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: drop `nodes.kind = COLUMN_KIND` from `_search_contains_demote` CASE; keep parent filter parity — cites ticket Scope bullets 1–3.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | Class buried by Methods | generalise demote | D1 | AC1 | ✅ |
| C1 | Constraints | 061 no-pair identical | keep EXISTS parent filters | D1 | AC2 | ✅ |
| C2 | Constraints | no widen EXISTS | same SQL shape | D1 | — | ✅ |
| C3 | Constraints | band precedence | within-band only | D1 | — | ✅ |
| R1 | Scope | demote by containment | drop COLUMN_KIND | D1 | AC3 | ✅ |
| R2 | Scope | one definition site | _search_contains_demote | D1 | AC3 | ✅ |
| R3 | Scope | R1.1 no kind name | CONTAINS only | D1 | AC3 | ✅ |
| AC1 | AC | PHP/TS/Python Class first | proving | D2 | proving | ✅ |
| AC2 | AC | 292 SQL + no-pair | proving | D2 | proving | ✅ |
| AC3 | AC | no COLUMN_KIND in term | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: demote keyed to COLUMN_KIND only.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R6.7 (change-type) ✅ · R4.2 (change-type) ✅`

Ran at 9398501499bb86bf84fbc507b7b83687a3a26ad3

```
$ .venv/bin/python -m pytest tests/test_container_member_search_order.py -q --tb=no
.........                                                                [100%]
9 passed in 1.78s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: remove kind gate from CASE WHEN EXISTS (CONTAINS parent hit).
- Rejected: language branch; second demote term.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_container_member_search_order.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | generalise demote | store.py | search order | 1/1 |
| D2 | proving | tests/test_container_member_search_order.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/297-contains-demote-any-kind

**Verification sweep**

Ran at 9398501499bb86bf84fbc507b7b83687a3a26ad3

```
$ .venv/bin/python -m pytest tests/test_container_member_search_order.py -q --tb=no
.........                                                                [100%]
9 passed in 1.78s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (9 met)
agent d022b027-6028-4b92-9f4e-a721557e2a61

Ran at 4b3064ffbe653d221d883414b43acc027564b9e5

```
$ .venv/bin/python -m pytest tests/test_container_member_search_order.py -q --tb=no
.........                                                                [100%]
9 passed in 0.67s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

## Phase 5 — Finalise

Outward: push + PR. Never merge.

## Cost ledger

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
