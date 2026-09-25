---
id: 334
slug: a-name-declared-twice-is-counted-as-two-candidates
title: "A bare EXEC to a proc declared in two files (a snapshot and a migration) links to nothing, because the uniqueness test counts nodes, not qnames — and a partial caller list then answers ok"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [214, 215, 321]
---

## Why this exists (field retros, 2026-09-25)

Two retros on one anchor repo hit the same wall on stored procedures. Every migrated proc is
declared twice: once in the schema snapshot, once in the latest migration. Both nodes carry the
**same** qname.

Probed on `main` (`927aeb9`) with `dbo.Gen` declared in `db/ssdt/Gen.sql` and
`db/migrations/V1__gen.sql`, called by `dbo.Caller` (`EXEC Gen`) and `dbo.Caller2` (`EXEC dbo.Gen`):

- `EXEC dbo.Gen` links: the exact-qname lookup hits (`resolver.py:157-163`).
- `EXEC Gen` stays unlinked (`target_qname` NULL). `_link_by_unique_function` requires
  `len(candidates) == 1` (`resolver.py:316`), and two nodes under one qname are two candidates.
- `find_callers dbo.Gen` answers **`reason: ok`, `total_count: 1`** — `Caller2` only. The
  unlinked-call count that would disclose `Caller` runs only when `total_count == 0`
  (`find_callers.py:461-471`). A partial answer is presented as whole.
- With only bare callers, the same subject answers `relation_unmodelled_for_language`: the relation
  *is* modelled, and the label tells the agent to stop trusting SQL callers altogether.

The BACKLOG follow-up from 321 names the same defect for tables (`resolver.py:230,254,277-279`):
two `Table` rows under one qname count as two candidates. One rule, four sites.

## Goal

Uniqueness means one **qname**, not one node — and an answer that left inbound sites unlinked says
so whether or not it found other callers.

## Scope / Deliverables

1. **Count distinct qnames** in every "unique candidate" test in `resolver.py` (the bare-Function
   pass and both casefold passes). Several nodes under one qname link to that qname.
2. **Disclose unlinked inbound sites on a non-empty answer**: when `find_callers` has hits and
   `count_unlinked_by_target_raw` is non-zero, the payload carries the count and
   `authoritative: false` with a named caveat. Today that count is read only on an empty answer.
3. Remove the 321 follow-up line from BACKLOG in the same commit (R7.6).

## Constraints

- **R1.1** — no language branch; the rule is about qnames, which every adapter emits.
- **R2** — no path convention (`migrations/`, `V<n>`) decides anything; two files, one qname.
- **Two different qnames stay ambiguous** — `dbo.Gen` and `audit.Gen` for a bare `Gen` is still
  unlinked (214's rule).
- **061** — an answer with no unlinked sites is byte-identical.

## Acceptance criteria

- **AC1** The probe above: `find_callers dbo.Gen` returns both callers, `reason: ok`; red on today's code.
- **AC2** `Gen` declared as `dbo.Gen` and `audit.Gen`: `EXEC Gen` stays unlinked (regression).
- **AC3** A table declared in one file and ALTERed in another: an unqualified `INSERT INTO T` links.
- **AC4** One linked caller plus one unlinked same-name site: the answer is non-authoritative and
  counts the unlinked site; red on today's code.

## Out of scope

- Choosing *which* of the two definitions is deployed (`read_symbol` still refuses as 327 designed).
- `impact` / `impact_modules` refusing an ambiguous seed (decision 9-A) — a separate question.

## References
`code_atlas/resolver.py:157-163,211-283,285-322`; `code_atlas/tools/find_callers.py:461-513`;
tickets 214, 215, 321, 327.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 334 — one qname is one candidate; a partial caller list says so (working doc)

- **Ticket:** 334 · local · **SCOPE:** M · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open
- **Reviewed at:** `e272eb3` (challenger round 1, CLEAN) · reviewed: code_atlas/{store,resolver}.py · code_atlas/tools/{find_callers,nav_result}.py · tests/test_name_declared_twice_links.py · working doc: this file

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: distinct-qname counting happens **in the store query** (`distinct_qnames=True` on the three
name lookups), not by deduping a node-limited list — two `dbo.Gen` rows would otherwise spend a
`limit=2` probe and hide a third qname. Citation: AC2 + Constraint "two different qnames stay ambiguous".
HOW2: the non-empty disclosure is **Function subjects only**, the predicate the empty-answer count
already uses (`find_callers.py` "Function-only: Method subjects keep the bare_name_truncated path",
214). A Method's unlinked bare sites are 258/259's surface, not this ticket's.
HOW3: the disclosure reuses the existing `unlinked_same_name_sites` field and
`CAVEAT_UNLINKED_SAME_NAME_SITES` (330); its limit text is made tool-neutral. Citation: R6.7.

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · Out of scope · References) | 7 decomposed | ROWS: C=4 R=3 G=1 AC=4`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | uniqueness = one qname; partial answers say so | D1 · D2 · D3 | ✅ |
| R1 | Scope 1 | every unique-candidate test counts distinct qnames (6 sites, below) | D1 · D2 | ✅ |
| R2 | Scope 2 | Function subject: hits + unlinked inbound → count + `authoritative: false` + caveat | D3 | ✅ |
| R3 | Scope 3 | 321 follow-up line leaves BACKLOG | — (removed in #455 with the ticket) | ✅ |
| C1 | R1.1 | no language branch — qnames only | D1 · D2 | ✅ |
| C2 | R2 | no path convention decides | D1 | ✅ |
| C3 | 214 | two qnames stay ambiguous | D1 · D4 AC2 | ✅ |
| C4 | 061 | no unlinked sites → byte-identical | D3 · D4 AC1 | ✅ |
| AC1–AC4 | AC | proving | D4 | ✅ |

R1 inventory (N = 7): bare-Function · casefold pass 1 · casefold pass 2 · column exact ·
column casefold · the final column check after the casefold fallback (found by the inventory test) ·
bare-name Method fallback.
The FQN pass (`:148`) and File pass (`:136`) are keyed by qname already — N/A.

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: every "unique" test is `len(candidates) == 1` over **node rows** fetched with
  `limit=2`. One qname declared in two files (snapshot + migration; CREATE + ALTER TABLE) is two
  rows, so a unique name reads as ambiguous and the edge stays unlinked.
- Second defect: `find_callers` reads `count_unlinked_by_target_raw` only when `total_count == 0`
  (`find_callers.py:461-471`), so one linked caller hides every unlinked one.
- Blast radius: `store.py` (three lookups gain a keyword, default path byte-identical SQL);
  `resolver.py` (seven checks); `find_callers.py` (one block); `nav_result.py` (caveat text).
  Other callers of the three lookups pass no new keyword — unchanged.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 ✅ (qname-only rule) · R1.4 ✅ (SQL stays in store.py) · R4.2 ✅ (DENSE_RANK over a total order) · R7.2 ✅ (ledger row)`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `distinct_qnames` keyword on `nodes_by_names` / `nodes_by_names_casefold` / `nodes_by_qualified_names_casefold`: rank by DENSE_RANK over qname, one row per qname | code_atlas/store.py | 3/3 |
| D2 | the seven R1 sites pass it (the column checks dedupe by qname) | code_atlas/resolver.py | 7/7 |
| D3 | Function subject with hits: attach `unlinked_same_name_sites` + caveat; limit text tool-neutral | code_atlas/tools/find_callers.py · nav_result.py | 1/1 |
| D4 | proving | tests/test_name_declared_twice_links.py | 1/1 |
| D5 | bookkeeping | docs/BACKLOG.md · docs/TOKEN_LEDGER.md · this doc | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1–4 | integration (build → resolver → tool) | pytest over a real SQL-adapter build | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_name_declared_twice_links.py -q`

Rejected alternatives: dedupe in the resolver after a larger `limit` (any finite node limit can
still be spent on one qname's twins); picking the "latest" definition (a path convention — R2).

`SCOPE: M`

## Phase 3 — Execute

**Branch:** fix/334-a-name-declared-twice-links

Ran at bb8d5574e10e8da50b9719f3e755920a51b27d47

```
$ .venv/bin/python -m pytest tests/test_name_declared_twice_links.py tests/test_bare_exec_resolves.py tests/test_resolver.py -q
26 passed
$ .venv/bin/python -m pytest -q
4581 passed, 4 skipped
```

Red arm on `main` (`54dafed`, scratch worktree): 5 of 6 fail — AC1, AC3, AC4, the R1 inventory and
the distinct-lookup arm; AC2 passes on `main` only because `limit=2` happened to see two `dbo.Gen`
rows (the arm pins it). Baseline at `54dafed`: `4575 passed, 4 skipped`; delta = the 6 new tests.
`ruff check .` and `mypy` clean.

Design conformance: D1–D4 implemented-as-approved. One deviation, recorded: the R1 inventory grew
from 6 to 7 — the column path re-tests uniqueness after its casefold fallback, which the design's
line list missed; the inventory test went red on it and D2 covers it.
Caveat-limit text for `unlinked_same_name_sites` changed from impact-only wording to tool-neutral
(HOW3); no test pinned it.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `e272eb3`: **CLEAN 10 met / 0 not met /
1 can't tell** (R3: the 321 follow-up line was already gone from `main`, removed with the ticket in
#455). Verdict: `clean (challenger only — REVIEWER: OFF)`. Two low notes, neither blocking:

| # | Note | Disposition |
|---|---|---|
| 1 | the bare-name Method fallback also counts qnames — beyond the three passes the scope names | kept: the Goal says uniqueness is one qname; R1's inventory lists it, the inventory test proves it |
| 2 | a Function with only test callers and unlinked sites keeps 272's count (all inbound kinds) over this ticket's CALLS/NEW count (`setdefault`) | recorded: both are true counts of unlinked sites naming the subject; the caveat attaches either way |

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 334 (`a-uniqueness-test-counts-qnames-not-rows`, first sighting).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 91161 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
