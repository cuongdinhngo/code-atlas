---
id: 287
slug: the-spelling-every-stack-trace-uses-is-a-near-miss
title: '`is_direct_match` bands a search hit on exact-or-prefix over name and qname, so `Class::method` — the spelling every stack trace, code review and ticket uses — is a qname *suffix* and lands in the substring band with `reason: substring_match`, while 249''s separator repair is gated on `no_matches` and can never reach the case that has hits'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [249, 167, 253]
---

## Why this exists (field retro — the anchor repo, round 25 §4, 2026-09-15)

`search_symbol(query="EntityPlan::getItem")` returns `reason: substring_match` with near-misses
ranked oddly. It still surfaced the right row, so nothing was lost — but the retro's objection is that
the query is not an odd spelling:

> *"`Class::method` is the most natural way to write a subject down, it is how every stack trace and
> every code review comment spells it, and the tool treats it as a trigram soup."*

The mechanism is one predicate. `is_direct_match` (`store.py:379-391`) is exact-or-prefix over `name`
and `qualified_name`; a stored qname is namespace-qualified, so `Class::method` is a **suffix** of it
and never a prefix. 167 made that predicate the single definition site for both the `reason` and the
ordering band (R6.7), so the miss is consistent — and consistently wrong for this one shape.

249 built the repair for the adjacent case (the member separator spelled with the wrong character) but
gated it on an *empty* answer: `if reason == REASON_NO_MATCHES and offset == 0`
(`search_symbol.py:283-284`). A `Class::method` query has hits, so the retry never runs. The two
half-measures do not compose: one handles a wrong separator with no results, the other handles a right
separator with results, and the gap between them is the spelling people actually type.

Same predicate, different complaint, worth separating so this ticket does not over-reach: round 26 §3
hit `substring_match` on a bare **class name** wanting one of its methods. That one is correct
behaviour with a correct route — the payload already says `try_instead: file_outline` — and is out of
scope here.

## Scope / Deliverables

- **A qname-suffix match on the member separator is a direct match.** When the query contains
  `MEMBER_SEPARATOR` and matches a stored qname on a component boundary, it bands with exact and
  prefix rather than with trigram near-misses — so `reason` and order both change, because 167 keeps
  them one predicate.
- **Boundary-anchored, not substring.** `getItem` must not become a direct match for
  `OtherClass::getItem` by accident; the match is on the separator-delimited tail, not on any
  substring ending the qname.
- **249's retry stays.** This ticket does not move the `no_matches` gate; it removes the case that
  needed it.

## Constraints

- R1.1: `MEMBER_SEPARATOR` is contract vocabulary (`contract.py:289` already derives the variant) —
  no language branch, no per-adapter spelling.
- R6.7: one definition site. Whatever changes must change `is_direct_match` (or a named helper beside
  it), never a copy in the ordering SQL — 167's whole point.
- 061: a query with no member separator is byte-identical to today, `reason` and order included.
- R4.2: deterministic ordering, unchanged tie-breaks inside the band.
- Cost: the predicate runs as a SQLite UDF per candidate row (`store.py:394-396`); no added query.

## Acceptance criteria

- `Class::method` against an indexed method returns `reason: ok`, with the exact member first.
- `method` alone is unchanged — still whatever band it earns today.
- `Class::method` does **not** direct-match a same-named method on another class.
- A query with no member separator produces a byte-identical payload.
- 249's separator retry and 167's banding tests still pass.

## References
`code_atlas/store.py:379-396`, `code_atlas/tools/search_symbol.py:118-128,279-284`,
`code_atlas/contract.py:289` (`member_separator_variant`),
[249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md),
[253](253_a-zero-overlap-guess-gets-no-route.md).
Origin: field retro round 25 §4 / §8.2, 2026-09-15 — "removes a recurring papercut with no downside".

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 287 — Class::method is a direct match (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: boundary rule = qname.casefold().endswith(query) and prior char not alnum — cites ticket Scope bullet 2 (separator-delimited tail, not any suffix).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | Class::method is substring | extend is_direct_match | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 MEMBER_SEPARATOR | contract.MEMBER_SEPARATOR | D1 | — | ✅ |
| C2 | Constraints | R6.7 one site | store.is_direct_match only | D1 | — | ✅ |
| C3 | Constraints | 061 no separator | early return | D1 | AC4 | ✅ |
| C4 | Constraints | R4.2 | deterministic | D1 | — | ✅ |
| C5 | Constraints | cost UDF | same UDF | D1 | — | ✅ |
| R1 | Scope | suffix direct | endswith + boundary | D1 | AC1 | ✅ |
| R2 | Scope | boundary not substring | alnum guard | D1 | AC3 | ✅ |
| R3 | Scope | 249 stays | no search_symbol gate change | D1 | AC5 | ✅ |
| AC1 | AC | reason ok + first | proving | D2 | proving | ✅ |
| AC2 | AC | bare method unchanged | proving | D2 | proving | ✅ |
| AC3 | AC | no cross-class | proving | D2 | proving | ✅ |
| AC4 | AC | no-sep identical band | proving | D2 | proving | ✅ |
| AC5 | AC | 249/167 still pass | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: is_direct_match only exact/prefix; Class::method is qname suffix.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — R6.7 ✅ · R1.1 ✅`

Ran at 3cfb88018bfb87c2d0429d24ff3b16d881cb04a4

```
$ .venv/bin/python -m pytest tests/test_search_exactness_band.py tests/test_separator_spelling_near_miss.py -q --tb=no
...................                                                      [100%]
19 passed in 1.65s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: extend is_direct_match with MEMBER_SEPARATOR suffix + non-alnum boundary.
- Rejected: copy predicate into SQL (167/R6.7); move 249 gate (out of scope).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_class_method_direct_match.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | is_direct_match suffix | store.py | search reason+order | 1/1 |
| D2 | proving | tests/test_class_method_direct_match.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/287-class-method-is-direct-match
**Axis 1:** store · proving.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 3cfb88018bfb87c2d0429d24ff3b16d881cb04a4

```
$ .venv/bin/python -m pytest tests/test_class_method_direct_match.py -q --tb=no
....                                                                     [100%]
4 passed in 0.18s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (underscore boundary); fixed to \\ /. ; round-2 CLEAN (can't-tell AC5 → verify-only). agents 5c72f9a8-5812-400f-a892-d4d77acf5e84 / 92c21627-0dcb-465a-b038-e42eb975fa05

Verify-only:

Ran at 3cfb88018bfb87c2d0429d24ff3b16d881cb04a4

```
$ .venv/bin/python -m pytest tests/test_search_exactness_band.py tests/test_separator_spelling_near_miss.py tests/test_class_method_direct_match.py -q --tb=no
.......................                                                  [100%]
23 passed in 1.72s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_class_method_direct_match.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: (pending)
PR: https://github.com/cuongdinhngo/code-atlas/pull/381

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
