---
id: 275
slug: four-green-rows-frame-two-red-ones-as-absence
title: 'A batched `search_symbol` spends one repair budget across every subject, so a sweep returns `index_stale, total_count: 0` beside four `ok` subjects in one payload with nothing on the envelope to separate them — and a refusal read as an absence nearly shipped a query against a table that does not exist'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [101, 246, 073]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 23 §4b)

One sweep, six subjects, `kind=Table`. Four resolved. `TranTypes` and `Schedule_Detail` came back
`reason: index_stale, total_count: 0` **inside the same response**. The docstring documents the
mechanism (`search_symbol.py:105–107`: *"a sweep shares one read-through repair budget across every
subject, so a subject whose file drifted may answer `index_stale` where a single call would have
repaired it"*), and the envelope says nothing.

Read in place, four green rows frame the two red ones as *these do not exist*. The two were not even
the same failure: `TranTypes` genuinely does not exist — the table is `dbo.LedgerTranType`, which the
same call surfaced under another subject — while `Schedule_Detail` exists as a **VIEW**, which the
`kind=Table` filter would have excluded regardless. One label hid both.

The near-miss is the point. A contract doc claimed a join against `TranTypes`. `index_stale` is
*consistent with* "stale index, table is fine", which would have shipped a read returning zero rows
forever. What caught it was querying the database, not the payload.

## Scope / Deliverables

- **A mixed sweep is flagged on the envelope** (call-level, never per subject — 061): when any
  subject answered `index_stale` while another answered `ok`, the envelope names the refused
  subjects and says the budget decided, not the graph.
- **A route on the refusal**: the single-subject call that would have spent the whole budget on it.
  A refusal an agent cannot act on is one it learns to ignore (267).
- **Spend the budget where it was asked for, not where it fell.** Today the order of `queries`
  decides which subject gets the one repair. Either state that rule in the payload or make it
  deterministic and stated; silence is what makes the mixed answer unreadable.
- **A filtered-out kind is not a miss.** `kind=Table` excluding a `View` of the same name is the
  other half of this misread: an excluded exact-name hit says so, rather than reading as absence
  (this is the 265 census rule, applied to `kind`).

## Constraints

- The per-call repair cap stays at 1 ([246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md)):
  this ticket changes what the payload *says*, not how much it reparses.
- 101's batch bound and the per-subject isolation stay — one miss must still not colour the rest.
- 061: a sweep where every subject answered `ok` gains nothing.
- R5.6: the envelope names the budget as the cause only where that is what happened.

## Acceptance criteria

- A fixture sweep with one drifted subject and three current ones returns the envelope flag naming
  the refused subject, and the three `ok` subjects are unchanged.
- The refused subject's entry carries the single-subject route.
- A sweep whose subject matches only a kind the filter excluded reports the exclusion, not an empty
  result set.
- A fully-`ok` sweep is byte-identical to today's payload.

## References
`code_atlas/tools/search_symbol.py:105–107,189–195`, `code_atlas/tools/freshness.py` (read-through
cap), field retro round 23 §4b / §4g #2,
[246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md),
[265](265_the-default-page-order-is-the-alphabet.md),
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 275 — mixed sweep budget envelope (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | mixed sweep looks like absence | envelope flags budget | D1 | AC1 | ✅ |
| C1 | Constraints | repair cap stays 1 | payload only | D1 | — | ✅ |
| C2 | Constraints | 101 isolation | per-subject reasons | D1 | AC1 | ✅ |
| C3 | Constraints | fully-ok unchanged | 061 | D1 | AC4 | ✅ |
| C4 | Constraints | R5.6 budget named only when true | mixed only | D1 | AC1 | ✅ |
| R1 | Scope | envelope mixed flag | repair_budget_shared + subjects | D1 | AC1 | ✅ |
| R2 | Scope | route on refusal | retry_as=query | D1 | AC2 | ✅ |
| R3 | Scope | state budget order | repair_budget_order=queries | D1 | AC1 | ✅ |
| R4 | Scope | kind exclusion | kind_excluded reason | D2 | AC3 | ✅ |
| AC1 | AC | mixed fixture envelope | proving | D3 | proving | ✅ |
| AC2 | AC | refused carries route | proving | D3 | proving | ✅ |
| AC3 | AC | kind exclusion not empty miss | proving | D3 | proving | ✅ |
| AC4 | AC | fully-ok identical | proving | D3 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: envelope silent on mixed repair-budget outcomes; kind filter empty reads as absence.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R5.4 ✅ · R5.6 ✅ · R6.1 ✅ · R7.6 ✅`

```
Ran at 99116ca801ea4ee620380496310d04e76754de92
$ .venv/bin/python -m pytest tests/test_batched_subject_sweep.py::test_the_whole_batched_payload_is_pinned -q --tb=no
1 passed
```

`BASELINE: green`

## Phase 2 — Design

- Approach: envelope fields on mixed ok+stale; retry_as on stale entries; REASON_KIND_EXCLUDED for exact-name other-kind hits.
- Rejected: raising repair cap (246). Rejected: try_instead=search_symbol (R5.4c self-loop).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_mixed_sweep_budget_envelope.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | envelope + retry_as | search_symbol.py | batch path | 3/3 |
| D2 | kind_excluded reason | nav_result.py + search | search | 1/1 |
| D3 | proving + TOOLS | tests · TOOLS | — | 4/4 |

## Phase 3 — Execute

**Branch:** feat/275-four-green-rows-frame-two-red-ones-as-absence
**Axis 1:** search_symbol, nav_result, tests, TOOLS.
**Axis 2:** implemented-as-approved.

**Verification sweep**

```
Ran at 99116ca801ea4ee620380496310d04e76754de92
$ .venv/bin/python -m pytest tests/test_mixed_sweep_budget_envelope.py -q --tb=line
3 passed
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (12 met · 0 not met · 0 can't tell); agent b0e8e9c0-23fa-469d-bc1d-d9f4b9e5792d

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_mixed_sweep_budget_envelope.py — 3 passed (plus vocab pin)`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-275c.log)

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

