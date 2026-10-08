---
id: 367
slug: constructor-flag-beyond-php
title: 'Only PHP flags its constructor, so find_callers on a TS constructor or a Python __init__ lists no construction site'
phase: 2
milestone: Coverage
status: done
depends_on: [362]
---

## Why this exists

362 made `find_callers` on a flagged constructor read the construction sites of its class, with
their argument shapes (`contract.CONSTRUCTOR_FLAG`, `find_callers._constructed_class`). Only the PHP
adapter sets the flag. Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `class Foo { constructor(a: number) {} }` emits `Method Foo::__construct` with
  `params` and no `extra`. `new Foo(1)` is a `NEW` onto `Foo` with `args: ["number"]`.
- **Python:** `def __init__(self, a=0)` and `__new__` emit `Method` nodes with no `extra`.
  `Foo(1, 'a')` is a `CALLS` onto the class `m.Foo` (no `NEW` — README, by design).

So `find_callers Foo::__construct` / `Foo::__init__` answers with the direct calls only (`super()`,
explicit `__init__`), not the sites that build the object — the exact gap 362's F2 closed for PHP.

## Scope

1. Each adapter sets `extra.constructor = true` on the method its language makes the constructor:
   TS `constructor` (emitted as `__construct`), Python `__init__`. Language spec only (R2.1).
2. Confirm the core reads Python's `CALLS`-onto-class sites through `also_targets`, which matches
   on target only. If it filters on `NEW`, widen it in the core, not by changing Python's edge kind.
3. Decide `__new__` explicitly and record the decision in the Python README.
4. No capability and no `contract_version` move: 362 X1 (ratified) settled it — `extra.constructor`
   is an optional key the core reads; the flag needs one `code-atlas-build --full`, said in CHANGELOG.
5. Python keyword arguments (`Foo(a=1)` emits `args: []`) are 372, not this ticket.

## Acceptance criteria

- **AC1:** `find_callers Foo::__construct` on a TS fixture lists every `new Foo(...)` site, and
  `arg_is` narrows them by a literal argument.
- **AC2:** The same for `find_callers Foo::__init__` on a Python fixture's `Foo(...)` sites, read
  through `also_targets` with no core change (it matches on target, not on `NEW`).
- **AC3:** A method merely named `constructor`/`__init__` outside a class carries no flag.
- **AC4:** ADAPTER_PLAYBOOK §1.1's constructor row names this ticket for both adapters.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 367 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges this PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372, each stacked on the one before;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/367-constructor-flag-beyond-php` off `main`. Contract `.mango/run-contract-367.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 1 want-decision asked | 6 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `contract.CONSTRUCTOR_FLAG`, `find_callers._constructed_class`, `store._target_where`,
`CALLER_KINDS = ("CALLS", "NEW")` (`contract.py:118`) and both adapters' `--file` mode all resolve.

**Recall (by handle).** `362-C1` `widen-every-query-that-shares-the-page` (a widened target must reach
every read behind the answer).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,621 tokens) surfaced X1–X6; the main
loop added X7.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | `__new__` | how | flagged with `__init__`: `Foo(…)` passes its arguments to both (data model §3.3.1), so either answers with the same sites; `_constructed_class` maps any flagged method to its class (`find_callers.py:681`). Python README row |
| X2 | a subclass with no constructor of its own | want | **ASSUMED (delegated by the handover):** not followed, as 362 left it for PHP (TOOLS.md) |
| X3 | TS `constructor` outside a named class | how | flag only a `Constructor` whose parent is a `ClassDeclaration`; a class expression has no Class node to name; an object-literal or interface `constructor` is a plain method. Fixture rows |
| X4 | Python `__init__` outside a class body | how | flag only when the def's container is the class: a def nested in a method is emitted as a class Method (pre-existing, see Follow-ups) |
| X5 | the Python `CALLS` onto a class | how | `_target_where` matches on target and `CALLER_KINDS` holds `CALLS`: AC2 needs no core change (test) |
| X6 | CHANGELOG placement | how | `Unreleased`, flagged full rebuild, no `contract_version` move (362 X1, ratified) |
| X7 | TS `super(…)` emitted `CALLS (dynamic)` `DYNAMIC` | how | a static target is not dynamic (R5.2): `super(…)` calls `<Base>::__construct` when the class's `extends` names one, so a subclass constructor is a caller, as PHP's `parent::__construct` is (362) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

`scripts/gate.sh` on `main` (`e0d84cf1`, a detached worktree with its own venv): `GATE GREEN — all 21
checks passed`. Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "not the sites that build the object" | `find_callers` on a TS/Python constructor lists construction sites | ✅ |
| C1 | Scope 4 | no capability, no `contract_version` move | optional `extra` key | ✅ |
| C2 | Scope 1 | language spec only (R2.1) | keyed on syntax and dunder names | ✅ |
| R1 | Scope 1 | each adapter sets `extra.constructor` | TS `constructor`, Python `__init__` (X1: `__new__` too) | ✅ |
| R2 | Scope 2 | the core reads Python's `CALLS` via `also_targets` | X5 | ✅ |
| R3 | Scope 3 | decide `__new__`, record in the Python README | X1 | ✅ |
| AC1 | AC | TS `new Foo(...)` sites, `arg_is` narrows | | ✅ |
| AC2 | AC | Python `Foo(...)` sites, no core change | | ✅ |
| AC3 | AC | a method merely named so carries no flag | X3/X4 | ✅ |
| AC4 | AC | playbook §1.1 names 367 for both | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — three `new Foo` files and `Sub::__construct`; `number` → one, `string` → two | |
| AC2 | yes — `Sub::__init__`, `build`, `pkg/use.py`; `string` → two; `__new__` → the two calls | |
| AC3 | yes — the flagged set is exactly six qnames (object literal, interface, class expression, module and nested `__init__` absent) | |
| AC4 | yes — the row reads `362 \| 367 \| 367` | |

### Blast radius

- Two adapters' emission (`extra` on a node; one edge per `super(…)` changes from `(dynamic)` to a qname).
- Contract, parity, TS/Python adapter suites and 362's suite: `487 passed`.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no core change · §R2.1 (change-type) ✅ constructor syntax and the data model's dunders only · §R3.1 (change-type) ✅ no vocabulary move: an optional extra key (362 X1) · §R5.2 (change-type) ✅ super(…) to a named base is static, unnamed stays DYNAMIC · §R6.1 (change-type) ✅ fixture build per adapter`

## Phase 2 — design

### Approach

1. TS `nodeExtra`: `constructor: true` on a `Constructor` under a `ClassDeclaration`.
2. TS `super(…)`: `CALLS <Base>::__construct` through the same `resolveExpr` the heritage edge uses.
3. Python: `extra.constructor` on `__init__`/`__new__` whose container is the class.
4. READMEs, playbook §1.1 and §3, TOOLS.md's `find_callers` row, CHANGELOG.

### Rejected alternatives

- **Flag `__init__` only** — a class defining only `__new__` would lose its sites, for no gain.
- **Changing Python's `Foo()` to a `NEW` edge** — the ticket forbids it; the core already reads it.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | flag + `super(…)` | `adapters/typescript/src/parse.js` | TS emission | R1, X7 | 1/1 |
| 2 | flag | `adapters/python/src/parse.py` | Python emission | R1, R3 | 1/1 |
| 3 | proving test | `tests/test_constructor_flag_beyond_php.py` (new) | — | AC1–AC3, X7 | 1/1 |
| 4 | docs | both READMEs, `docs/ADAPTER_PLAYBOOK.md`, `docs/TOOLS.md`, `CHANGELOG.md` | doc budget | R3, AC4 | 5/5 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`widen-every-query-that-shares-the-page`** — traced: `grep -n "also_targets=also" code_atlas/tools/find_callers.py`
  lists every read (rows, count, unrecorded-args count, census, subtree spread) on the one
  `_constructed_class` result, and it keys on the flag, not on the language, so the new flags reach all of them.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real TS build, `find_callers` | authored | ✅ |
| AC2 | integration | real Python build, `find_callers` | authored | ✅ |
| AC3 | integration | the flagged `nodes` rows | authored | ✅ |
| AC4 | doc | the playbook row | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_constructor_flag_beyond_php.py`.

### Rollback

`git revert`; an index built with the flags keeps them until the next full rebuild.

## Phase 3 — execute

Commit `bf75f16d`. **Red first** — the file on `main`: `3 failed` (no flagged node, no construction
site in either language).

**Sweep.** Axis 1: `git diff --name-only main..HEAD` = change-list items 1–4; `ruff check`, `mypy`
(core and Python adapter), `tsc --checkJs --strict` clean. Axis 2: Approach 1–4 as approved.

**P8.** `scripts/cross_repo_validate.py --public-only --skip-clone`: 11 ok / 0 failed on `main` and on
`bf75f16d`; every sample's node and edge count unchanged (a `super(…)` edge changes target, not
count), so no floor moves.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `a4675c58`, 60,271 tokens): 11 met · 0 not met · 0 can't tell.**

1. **F1: `super(…)` is beyond the ticket's words.** **Kept:** design X7, approved in the change list;
   on `main` it was `CALLS (dynamic)` `DYNAMIC`, measured by `--file`.
2. **F2: a namespace or mixin base.** `ns.Foo` resolves through `resolveExpr`; a mixin stays `DYNAMIC`.
3. **F3: TS overloads emit one flagged node per signature.** **Left:** pre-existing duplicate qnames,
   kept first by the store; the flag is consistent.
4. **F4: docs.** **Left:** TOOLS.md's "a subclass that inherits it … not followed" covers TS and Python.
5. **F5: no test pins the unresolvable `super(…)`.** **Fixed** in `34b91166`.

Verify-only (main loop):

Ran at 34b91166:
```
$ .venv/bin/python -m pytest -q tests/test_constructor_flag_beyond_php.py
4 passed in 0.48s
```

`Ph3/4 proven by`: G1, C1, C2, R1–R3, AC1–AC4 — 10/10.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 34b91166 — the diff `main..34b91166`. Working doc:
`docs/tasks/367_constructor-flag-beyond-php.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `34b91166` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson. Per P1, `362-C1` gains 367 (traced in Phase 2): `seen: 362, 364, 367`. Falsify: still
true — every `find_callers` read takes the one `_constructed_class` result. **cannot promote:
unattended run** — `/mango:promote` is the maintainer's pass.

### Outward actions

1. Push `feat/367-constructor-flag-beyond-php` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: `/mango:promote` on `362-C1`.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 48,621 |
| 2 | review | `challenger`, round 1 | 60,271 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 108,892 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits; an index keeps the flags until the next full rebuild.

**Gate.** `scripts/gate.sh` on `3366adee`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
