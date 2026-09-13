---
id: 265
slug: the-default-page-order-is-the-alphabet
title: 'Page 1 of every caller and reference answer is ordered by qualified name, so what an agent sees first is an accident of spelling — a correct, cheap, unrepresentative page that terminates the reasoning which would have reached the truth; make tier the default order, and let a page that is a partition return a census with no rows at all'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [251, 252, 067, 259]
---

## Why this exists

`_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"` (`store.py:170`). Every paged edge answer is alphabetical by source name. Three independent records of the damage:

- [067](067_first-page-not-representative.md): a **fully correct 23-of-23** `find_callers` page that steered the session off `src/` — page 1 was 100 % of the tree it must not touch. The session *"briefly read that page as no `src/` callers"* before grep contradicted it.
- [251](251_the-resolved-caller-can-be-off-the-page.md): on a common method name the one `RESOLVED` caller sat on page 12 while page 1 was vendor `build()` noise.
- [074](074_does-the-index-harm-mechanism-questions.md): the mechanism question that was **right when the index was denied and wrong when it was granted** — still at n = 1, still the only datapoint suggesting the index costs accuracy.

251 shipped `confidence_tier` as a *filter the agent must know to pass*. Agents terminate on page 1; a knob nobody discovers is not a fix.

**Ordering before [259](259_one-knob-sets-both-index-size-and-page-truthfulness.md) is cosmetic**: the anchor's page cap is 10 because one knob also sets index size. 259 lands first.

## Scope / Deliverables

- **Tier-first default order** for caller/reference edge reads: `RESOLVED` before `HEURISTIC` before `DYNAMIC`, then today's stable keys. In SQL, **before truncation**, never a post-filter over a truncated page.
- **`confidence_tier` keeps its filter role**, unchanged. This ticket changes the default *order*, not the default *set*.
- **A page that is a partition of a differently-tiered set** returns `authoritative: false` plus a tier census, and **is permitted to return zero rows**. Uglier and more honest than ten plausible wrong callers.
- **Bound the class-level union to the page** — `252`'s `_member_caller_union` issues one `edges_by_target` per `CONTAINS` child and collects every hit before `cap`/`offset` apply, so cost scales with the class's total inbound set. A tool that looks cheap and is not is an honesty defect, not a performance note.
- **Write PLAN §19 first, before any code in this ticket**: that [074](074_does-the-index-harm-mechanism-questions.md) will be measured **after** this fix, that the baseline is the 2026-08-08 cell plus 067, and why — 074's "do not change a tool to make the number come out" governs tuning during a run, not shipping an already-named mechanism before measuring whether it closed.

## Constraints

- R4.2: the new order must be total and stable — identical input, identical rows, identical order.
- No unnamed ranking. Tier is the stated basis; nothing heuristic, nothing learned. (181's `ranked_by: "path"` is the anti-pattern.)
- Do not raise the page cap here — that is 259's knob.

## Acceptance criteria

- A fixture where the sole `RESOLVED` caller sorts last alphabetically returns it **on page 1**.
- A test pins the ordering is applied in the store query, not after truncation.
- A partition page returns `authoritative: false` + census; a test covers the zero-row arm.
- Class-level union: a test pins that cost scales with the page, not with the class's whole inbound set.
- PLAN §19 carries the 074-ordering decision, committed **before** the code change.

## References
`code_atlas/store.py:170`, [067](067_first-page-not-representative.md), [251](251_the-resolved-caller-can-be-off-the-page.md), [252](252_a-class-reference-question-costs-n-plus-one-calls.md), [074](074_does-the-index-harm-mechanism-questions.md), [259](259_one-knob-sets-both-index-size-and-page-truthfulness.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 265 — tier-first default page order (working doc)

- **Ticket:** 265
- **Type:** bug
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** ticket locks tier-first order, section-19-first, page-bounded union, no page-cap raise.
**INPUT KIND:** ticket.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-----|-------|--------|
| G1 | Why | alphabet page terminates reasoning | tier-first default | store | D2 | proving | ✅ |
| C1 | Constraints | R4.2 total stable | CASE + keys | store | D2 | proving | ✅ |
| C2 | Constraints | no unnamed ranking | tier stated | store | D2 | proving | ✅ |
| C3 | Constraints | do not raise page cap | 259 knob | — | — | — | ✅ |
| R1 | Scope | tier-first before truncation | EDGE_ORDER_TIER_FIRST | store | D2 | AC2 | ✅ |
| R2 | Scope | confidence_tier filter unchanged | 251 | callers | D2 | 251 tests | ✅ |
| R3 | Scope | partition authoritative false + census; zero rows ok | caveat | callers | D3 | AC3 | ✅ |
| R4 | Scope | class union page-bounded | edges_by_targets | refs | D4 | AC4 | ✅ |
| R5 | Scope | PLAN section 19 first | decision | PLAN | D1 | a2ab64c | ✅ |
| AC1 | AC | RESOLVED on page 1 | | | D2 | proving | ✅ |
| AC2 | AC | order in store query | | | D2 | AC2 test | ✅ |
| AC3 | AC | partition zero-row arm | | | D3 | AC3 test | ✅ |
| AC4 | AC | union cost scales with page | | | D4 | AC4 test | ✅ |
| AC5 | AC | section 19 before code | | | D1 | commit order | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause: alphabetical EDGE_ORDER on inbound pages; agents terminate on page 1.
- TRACK: backend — 0/0 touched files under UI paths
- SCOPE: M · TIER: full

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ · R5.5 (change-type) ✅ · R5.6 (change-type) ✅ · R7.6 (change-type) ✅`

### BASELINE

```
Ran at a5fb9a568e5e1e22dede328df47bdc39e34f7713
$ .venv/bin/python -m pytest tests/test_find_callers_tier_control.py -q --tb=no
6 passed
```

`BASELINE: green` for the change-adjacent suite.

---

## Phase 2 — Design

- Approach: section-19 decision first; EDGE_ORDER_TIER_FIRST on edges_by_target; edges_by_targets for via_members; partition caveat + empty filtered census; update 251.
- Rejected: post-page sort (AC2); raise page cap (259).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_tier_first_page_order.py::test_resolved_caller_on_page_one_under_tier_first_order -q`

| # | Change | File |
|---|--------|------|
| D1 | section-19 decision | PLAN.md (committed first as a2ab64c) |
| D2 | tier-first order | store.py |
| D3 | partition honesty | find_callers + nav_result |
| D4 | page-bounded union | find_references + edges_by_targets |
| D5 | proving + 251 update + TOOLS | tests · TOOLS |

---

## Phase 3 — Execute

**Branch:** feat/265-default-page-order-is-the-alphabet
**Implemented:** D1–D5.

**Verification sweep**

```
Ran at 464ec1e1abee83f9ea279e2b989df3c94538650c
$ .venv/bin/python -m pytest tests/test_tier_first_page_order.py tests/test_find_callers_tier_control.py tests/test_find_references_via_members.py -q --tb=no
16 passed
```

diff subset of approved list.

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived.
**CHALLENGER: ON** — ticket-blind, 1 dispatch CLEAN (7/7 met, 5/5 AC).

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward actions authorised at handover: push feature branch; open PR.
