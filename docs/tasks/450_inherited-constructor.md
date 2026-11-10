---
id: 450
slug: inherited-constructor
title: "PHP: `Child::__construct` resolves to the inherited constructor, and `new Child` reaches it"
phase: 2
milestone: "Round-3 field gaps"
status: done
depends_on: [362]
---

## Why this exists

The follow-up 362 left: an inherited constructor misses its subclass's `new` sites. Round-3 field
feedback hit both halves: `search_symbol` / `read_symbol` on `Child::__construct` for a class that
declares none returns nothing, and "who constructs this" on the parent misses every `new Child(...)`.
PHP inherits `__construct` like any method, so this is the language rule (R2).

## Scope

1. `read_symbol Child::__construct`, when `Child` declares no constructor, walks the linked
   ancestry (the resolver's existing inherited-member walk) and answers the nearest ancestor's
   constructor, marked `inherited_from: <Parent>`.
2. A `NEW` edge onto a class that declares no constructor also counts as a caller of the inherited
   constructor: `find_callers Parent::__construct` lists `new Child(...)` sites, each marked
   `via_subclass: Child`, at the tier of the `NEW` edge.
3. An unlinked ancestor (a class in an unindexed path) answers `no_such_symbol` with
   `ancestry_unresolved`, never a confident absence.

## Acceptance

- Fixture: `class Child extends Base {}` + `new Child()` → `read_symbol Child::__construct` returns
  `Base::__construct` with `inherited_from`, and `find_callers Base::__construct` includes the site.
- Fixture: a `Child` that declares its own constructor is unchanged.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 450 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 447 - 448 - 449 - 450`, fourth — `REVIEWER: OFF` (waived: "with skipped
  reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is
  `ASSUMED`, never silent.
- Branch `feat/450-inherited-constructor` from `main` at `89ecb16d`, built in a worktree. Contract
  `.mango/run-contract-450.txt` (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 4 want-decision asked | 3 how-decision resolved+cited | 4 ASSUMED | skip: no`

`read_symbol`, `find_callers`' constructor targets (362: `contract.CONSTRUCTOR_FLAG`, `_constructed_class`), the
resolver's ancestry walk (`resolver.ancestry`) and `no_such_symbol` resolve. Recalled by handle (the change widens the
target set every `find_callers` query shares): 362-C1 `widen-every-query-that-shares-the-page` (R5.5). The
exposure-checker (1 dispatch) returned 6; they fold in below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | language-neutral | how | the constructor is the member flagged `CONSTRUCTOR_FLAG` (362); what hands it down is `EXTENDS`/`USES_TRAIT` (`contract.BODY_INHERIT_KINDS`) — no `__construct` in the core (R1.1) |
| H2 | `parent::__construct(...)` inside a child's constructor | how | already a `CALLS` edge onto the parent's constructor (362); unchanged |
| H3 | a grandchild | how | transitive, stopping at a class that declares its own (PHP's inheritance rule, R2) |
| W1 | `via_subclass`'s value | want | **ASSUMED:** the class the `new` names (`Grand`, not `Child`) — the one the reader sees at the site |
| W2 | `read_symbol`'s answer | want | **ASSUMED:** the ancestor's constructor read as itself (`qname` = `Base::__construct`) plus `inherited_from` (the ancestor class) and `asked` (the qname asked) |
| W3 | other tools | want | **ASSUMED:** `read_symbol` and `find_callers` only (scope 1–2); `search_symbol`, `find_references`, `impact` unchanged — follow-ups if wanted |
| W4 | an unlinked ancestor as near as the one with a constructor | want | **ASSUMED:** `ancestry_unresolved`, never the farther answer — the unlinked one may declare its own |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=2`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "an inherited constructor misses its subclass's `new` sites" | both halves close | ✅ |
| R1 | Scope 1 | "walks the linked ancestry … answers the nearest ancestor's constructor, marked `inherited_from`" | W2, W4 | ✅ |
| R2 | Scope 2 | "`find_callers Parent::__construct` lists `new Child(...)` sites, each marked `via_subclass: Child`, at the tier of the `NEW` edge" | W1 | ✅ |
| R3 | Scope 3 | "An unlinked ancestor … answers `no_such_symbol` with `ancestry_unresolved`" | `ancestry_unresolved` | ✅ |
| C1 | Why | "PHP inherits `__construct` like any method, so this is the language rule (R2)" | H1 | ✅ |
| AC1 | Acc 1 | "`read_symbol Child::__construct` returns `Base::__construct` with `inherited_from`, and `find_callers Base::__construct` includes the site" | fixture | ✅ |
| AC2 | Acc 2 | "a `Child` that declares its own constructor is unchanged" | fixture | ✅ |

**Gap.** `_constructed_class` (`find_callers.py:704`) returns the constructor's own class only; `read_symbol`'s miss
path (`_resolve_miss`) never consults the hierarchy.

`BASELINE: green — find_callers, read_symbol, constructor, callers, resolver, contract and tool-surface suites on main at 89ecb16d: 636 passed, 54 skipped (TS adapter not installed in that worktree)`

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q <find_callers*, read_symbol*, *constructor*, untyped_receiver*, *callers*, contract*, resolver*, tool_manifest, tool_surface*> tests/contract
636 passed, 54 skipped in 34.73s
```

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 the constructor is a contract flag, never a name, R1.4 SQL in store.py · §5 (change-type) ✅ R5.5 the widened target set feeds every query (also_targets), R5.6 an unlinked ancestor is not an absence · §6 (change-type) ✅ R6.1 a fixture over both tools, R6.5 seen red · §7 (change-type) ✅ R7.2 ledger`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: every `find_callers` query reads the one `also` tuple, so heirs
  join the page, the count, the test census, the tier census and the arg counts together:

Ran at 89ecb16d (pre-change)
```
$ git show 89ecb16d:code_atlas/tools/find_callers.py | grep -n "also_targets=also"
247:                also_targets=also,
264:                also_targets=also,
268:                    lookup, kinds=CALLER_KINDS, also_targets=also, keyword=_by_name(args_at)
281:                also_targets=also,
341:                    also_targets=also,
359:                    also_targets=also,
363:                        lookup, kinds=CALLER_KINDS, also_targets=also, keyword=_by_name(args_at)
376:                    also_targets=also,
451:                    also_targets=also,
739:        also_targets=also_targets,
768:        qname, kinds=CALLER_KINDS, args_at=args_at, also_targets=also_targets
898:        also_targets=also_targets,
925:            also_targets=also_targets,
934:            also_targets=also_targets,
951:            also_targets=also_targets,
```

**Approach.** (1) `store.flagged_members` — a class's member carrying a flag, by a range seek. (2)
`_constructed_class` returns the class plus `_constructor_heirs` (descendants over `BODY_INHERIT_KINDS`, stopping at a
class with its own constructor); `_callers` marks a hit onto an heir `via_subclass`. (3) `read_symbol` is wrapped:
on `no_such_symbol` for `Class::member`, `inherited_constructor` walks the linked ancestry nearest first and reads the
ancestor's constructor when its name is `member`; an unlinked ancestor reached first answers `ancestry_unresolved`.
**Rejected:** a synthetic `Child::__construct` node or alias edge at build time (a graph row for code that does not
exist; a contract change); the resolver's whole-graph `hierarchy_parents()` map per call (one seek per class is enough).
**Proving test:** `tests/test_inherited_constructor.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| `BODY_INHERIT_KINDS` | `code_atlas/contract.py` | `test_contract_sole_source.py` | R1–R2 |
| `flagged_members` | `code_atlas/store.py` | — | R1–R2 |
| heirs + `via_subclass` | `code_atlas/tools/find_callers.py` | every `also_targets` query (traced above) | R2 · 1/1 |
| inherited read | `code_atlas/tools/read_symbol.py` | every `no_such_symbol` answer | R1, R3 · 2/2 |
| proving test | `tests/test_inherited_constructor.py` | — | AC1–AC2 · 2/2 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | — | R9.4 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC2 | integration (a built index → both tools) | integration: full build + `read_symbol` / `find_callers` | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert the branch; nothing is stored. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer` (`9e518037`), in a worktree. **Sweep.** Axis 1: the diff is the approved files; `ruff`,
`mypy` clean. Axis 2: the approach implemented-as-approved.

The new tests on the base (only the test file added):

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_inherited_constructor.py
FAILED tests/test_inherited_constructor.py::test_ac1_read_symbol_answers_the_inherited_constructor
FAILED tests/test_inherited_constructor.py::test_ac1_a_grandchild_reaches_the_nearest_constructor
FAILED tests/test_inherited_constructor.py::test_ac1_find_callers_lists_the_subclass_new_sites
FAILED tests/test_inherited_constructor.py::test_scope3_an_unlinked_ancestor_is_never_a_confident_absence
4 failed, 2 passed in 0.93s
```

At `9e518037` that run read 696 passed; the review fix's run is in Phase 4.

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone, at `9e518037`; payload = the raw ticket (`git show 89ecb16d:<this file>`) + the branch diff.

- **`challenger` round 1** (64,184 tokens): 8 rebuilt · 7 met · 1 not met (row 8, a trait's constructor: for
  `class X extends P { use T; }` the walk answered `P`'s by edge order, and `new X` counted under both). **Taken:** F1 —
  a used trait's members are the class's own (`contract.USES_TRAIT`), so a class's traits are read before its parents,
  two traits that both supply one give no answer, and the heir walk stops at a child whose own trait supplies one
  (`8c77fe14`, `test_challenger_…`). F2 — documented: any `Class::member` miss behind an unlinked supertype says
  `ancestry_unresolved`. **Recorded:** F3 (500 heirs at most, no flag past it).
- **`challenger` round 2** (verify-only, resumed, at `8c77fe14`): its final line, transcribed:

`CHALLENGER VERDICT: 8 requirement(s) rebuilt | 8 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

  Advisory, not taken: a trait that itself uses a trait supplying the constructor is not walked.

Ran at 8c77fe14
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_inherited_constructor.py tests/test_core_is_language_agnostic.py <the baseline's suites> tests/contract
1034 passed in 63.19s (0:01:03)
```

Reviewed at 8c77fe14 — files: `code_atlas/contract.py`, `code_atlas/store.py`, `code_atlas/tools/find_callers.py`,
`code_atlas/tools/read_symbol.py`, `tests/test_inherited_constructor.py`, `docs/TOOLS.md`, `CHANGELOG.md`; working doc
`docs/tasks/450_inherited-constructor.md`.

`Ph3/4 proven by`: AC1–AC2, R1–R3 → `tests/test_inherited_constructor.py` (7).

## Phase 5 — finalise

**Durable lesson.** 450-C1 `inheritance-walk-needs-the-languages-precedence` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/450-inherited-constructor`; open its PR against `main`. Deferred: ratify W1–W4; merge;
follow-ups for a trait using a trait, and a flag past 500 heirs.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 46,523 |
| 4 review | ticket-blind `challenger` | 1 | 64,184 |
| 4 review | ticket-blind `challenger` | 2 | 7,649 (resumed: 71,833 cumulative − 64,184) |

`LEDGER TOTAL: 118,356 · top cost driver: 4 review / challenger` — main loop unmeasured.
