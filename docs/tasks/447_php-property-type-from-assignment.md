---
id: 447
slug: php-property-type-from-assignment
title: "PHP: an untyped property assigned `new X` types its receiver"
phase: 2
milestone: "Round-3 field gaps"
status: done
depends_on: [393]
---

## Why this exists

Round-3 field feedback (20 Sep – 7 Nov): untyped receivers are the cause in ~8% of scored PRs, and
the "infer receiver types" idea came up in 17. The commonest shape is still open in the last week:
`find_callers` on a model method lists only the tests, because the production call goes through
`$this->model->m()` where `$this->model` is assigned in the constructor and declared without a type.

What the PHP adapter already types (`adapters/php/src/TypeTable.php`, `MemberTypes.php`): a local
`$x = new X`, a typed property, a constructor-promoted parameter, a return hint, and a `@return`
docblock (393). It does **not** type a property from its assignment, or from a `@var` docblock.

## Scope

1. `MemberTypes` records a property's class when it has no declared type and either:
   - a `@var X` docblock on the property names one class-like (the existing `docClass` rules,
     `NOT_A_CLASS` excluded), or
   - every `$this->p = new X(...)` in the class's own methods assigns the **same** class `X`.
     Two different classes, or any other assignment to `$this->p`, leaves it untyped.
2. A call through such a property links at **`HEURISTIC`** (a declared type stays `RESOLVED`): the
   assignment is a claim about one file, not a guarantee across subclasses.
3. File-local only (R3.3): a property assigned in a parent class declared in another file stays
   untyped; `unresolved_receivers` keeps counting it.

## Out of scope

Parameters with no type hint, factory returns past `@return`, `$var` set in an including file.

## Acceptance

- Fixture: a controller whose constructor sets `$this->model = new Model()`; `find_callers
  Model::m` names the controller's call at `HEURISTIC`, and `unresolved_receivers` drops by one.
- Fixture: two different `new` assignments to one property → no edge, still counted.
- Fixture: `/** @var Model */ private $model;` → the call links.
- Conformance suite green; the anchor's `unresolved_receivers` count before and after is reported.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 447 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 447 - 448 - 449 - 450`, first — `REVIEWER: OFF` (waived: "with skipped
  reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is
  `ASSUMED`, never silent.
- Branch `feat/447-php-property-type-from-assignment` from `main` at `89ecb16d`. Contract
  `.mango/run-contract-447.txt` (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 5 want-decision asked | 2 how-decision resolved+cited | 5 ASSUMED | skip: no`

`TypeTable.php`, `MemberTypes.php`, `docClass` / `NOT_A_CLASS`, `unresolved_receivers` (`find_callers.py:493`) and
393's `doc_type` resolve. Ambiguous: "the anchor" (a prose noun — the private index 442 names). Recalled by handle:
369-C1 `a-name-receiver-needs-its-scope` (the change threads a receiver type to the resolver). The exposure-checker
(1 dispatch) returned 6; they fold into the table.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | contract bump? | how | none: 393 put `doc_type` on a Method with no bump (CHANGELOG 0.10, 393) — `extra` is free-form; a file reads it when it re-parses |
| H2 | "same class" | how | the resolved FQN, as `TypeTable::classNameOf` resolves `new X` (aliases, `self`/`static`) |
| W1 | what counts as "any other assignment" | want | **ASSUMED:** `$this->p = new X(...)` and `$this->p ??= new X(...)` type; any other `$this->p =`, `??=`, compound or by-reference write, `new $v`, `new class` → untyped. A declared default of `null` (or none) is not an assignment; any other default → untyped |
| W2 | `@var` vs the assignments | want | **ASSUMED:** a usable `@var` wins; the assignments are read only when there is none |
| W3 | `@var`'s tier | want | **ASSUMED:** `HEURISTIC` like the assignment — scope 2 says "such a property", and 393 put a `@return` docblock there |
| W4 | whose methods count | want | **ASSUMED:** the declaring class-like's own methods (and closures in them); a subclass's write never types the parent's property (scope 3's file-local claim) |
| W5 | the anchor bar | want | **ASSUMED:** reported, not gated — the count of PHP CALLS with a bare (receiver-less) target, before and after, privacy rules of 442 |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Out of scope · Acceptance) | 4 decomposed | ROWS: C=3 R=3 G=1 AC=4`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "`$this->model` is assigned in the constructor and declared without a type" | that receiver types | ✅ |
| R1 | Scope 1 | "a `@var X` docblock … or every `$this->p = new X(...)` … the same class" | `MemberTypes::propertyClass`, W1/W2/W4 | ✅ |
| R2 | Scope 2 | "links at `HEURISTIC` (a declared type stays `RESOLVED`)" | the property carries `doc_type`, read by 393's path | ✅ |
| R3 | Scope 3 | "a property assigned in a parent class declared in another file stays untyped" | a child's write to a parent's property never types it; **deviation**: the parent's own claim reaches the child (Phase 3) | ⚠ |
| C1 | Out of scope | "Parameters with no type hint, factory returns past `@return`, `$var` set in an including file" | untouched | ✅ |
| C2 | Scope 3 | "File-local only (R3.3)" | the adapter reads one file; the graph links | ✅ |
| C3 | R2 | standard over sample | PHP's assignment and PHPDoc `@var`, no repo names | ✅ |
| AC1 | Acc 1 | "`find_callers Model::m` names the controller's call at `HEURISTIC`, and `unresolved_receivers` drops by one" | fixture | ✅ |
| AC2 | Acc 2 | "two different `new` assignments to one property → no edge, still counted" | fixture | ✅ |
| AC3 | Acc 3 | "`/** @var Model */ private $model;` → the call links" | fixture | ✅ |
| AC4 | Acc 4 | "Conformance suite green; the anchor's `unresolved_receivers` count before and after is reported" | `tests/contract`; anchor counts (W5) | ✅ |

**Gap.** `MemberTypes::addProperty` (`MemberTypes.php:150`) records only the declared type, so `TypeTable::memberOf`
resolves an untyped property to `null` and `enterInstanceCall` (`Visitor.php:752`) emits the bare name at `HEURISTIC`.
**P6, run on `main`:** the fixture's `Ctl::run` reached `Model::m` only as a `proximity_candidates` row; and a child's
call through a parent's property declared in another file is emitted as a `\Child::$model()::m` chain, which
`unresolved_receivers` (bare names only, `find_callers.py:486`) never counted — so "keeps counting it" was not today's
behaviour for that shape.

`BASELINE: green — PHP receiver, local types, factory receiver, untyped receiver and contract suites on main at 89ecb16d: 412 passed`

Ran at 89ecb16d (pre-change)
```
$ .venv/bin/pytest -q -x tests/test_factory_receiver.py tests/test_php_local_type_table.py tests/test_php_receiver_resolution.py tests/test_untyped_receiver_and_constructor_calls.py tests/contract
412 passed in 17.48s
```

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §2 (change-type) ✅ R2.1 the assignment and @var are PHP and PHPDoc, no repo name · §3 (change-type) ✅ R3.1/R3.3 no vocabulary moves (extra.doc_type as 393), the adapter claims one file · §5 (change-type) ✅ R5.2 an inferred type links at HEURISTIC, never RESOLVED · §6 (change-type) ✅ R6.1 a fixture over the tool, R6.5 seen red on main, R6.6 PHPStan max · §7 (change-type) ✅ R7.2 ledger, R7.5 comments ≤ 3 lines`

## Phase 2 — design

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `a-name-receiver-needs-its-scope` — does not apply because the receiver is `$this->p`, which no parameter or local
  can rebind; the only thing that rebinds it is a write to `$this->p`, and every such write is read (W1).

**Approach.** (1) `MemberTypes` collects, per property of the class-like that declares it: a `@var` naming one class
(the `@return` reader, now keyed by tag), and every write to `$this->p` in that class's own code (on leave, after
`NameResolver`) — one `new X` class, else poisoned; a promoted parameter or a non-`null` default poisons. (2)
`TypeTable::memberOf` defers such a property to the graph, as a `@return` docblock does. (3) `Visitor::enterProperty`
emits `extra.doc_type`, so the resolver's documented walk (393) links at `HEURISTIC`.
**Rejected:** resolving the type inside the adapter as `RESOLVED` (R5.2: a claim about one file); a new edge or node
field (a contract bump for what `doc_type` already carries).
**Proving test:** `tests/test_property_type_from_assignment.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| infer the property's class | `adapters/php/src/MemberTypes.php` | `docClass` callers (the `@return` path, 393's tests) | R1, R3 · 1/1 |
| defer an inferred property | `adapters/php/src/TypeTable.php` | every receiver chain through a property | R2 · 1/1 |
| emit `doc_type` on a Property | `adapters/php/src/Visitor.php` | Property node `extra` (conformance, body hash) | R2 · 1/1 |
| proving test | `tests/test_property_type_from_assignment.py` | — | AC1–AC3 · 3/3 |
| docs | `adapters/php/README.md`, `CHANGELOG.md` | — | R7.2 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration (adapter → resolver → tool) | integration: a full build + `find_callers` | authored | ✅ |
| AC4 | integration | `tests/contract` + the anchor counts | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Assumptions: NameResolver has qualified a `new X` by the time its `Assign` is left — verified (the fixture's
`\App\Model`). Rollback: revert the two commits; the index re-reads on the next parse. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer` (`f2b7d43d`, `7bd55c5a`). **Sweep.** Axis 1: the diff is the six approved files (bookkeeping
follows at finalise), every hunk on R1–R3 or the docs row; PHPStan `level: max` clean. Axis 2: approach bullets 1–3
implemented-as-approved. **Deviation (P3, R3).** The ticket says a property assigned in a parent declared in another
file "stays untyped". What shipped: a *child's* write to its parent's property never types it (the fixture
`test_scope3_…`), but a *parent* that types its own property makes the claim in its own file, and the resolver's
ancestry walk carries `doc_type` to the child's call (`test_deviation_…`) — the same path 393's `@return` takes
across files. Holding it back would need the resolver to ignore one file's claim for another's caller.

The new tests on the base (only the test file added) — 7 red, the 3 negative guards green both ways:

Ran at 89ecb16d (pre-change)
```
$ .venv/bin/pytest -q tests/test_property_type_from_assignment.py
FAILED tests/test_property_type_from_assignment.py::test_ac1_a_constructor_assignment_types_the_property_at_heuristic
FAILED tests/test_property_type_from_assignment.py::test_ac1_unresolved_receivers_drops_by_one
FAILED tests/test_property_type_from_assignment.py::test_ac3_a_var_docblock_types_the_property
FAILED tests/test_property_type_from_assignment.py::test_w1_any_other_write_leaves_it_untyped
FAILED tests/test_property_type_from_assignment.py::test_w2_a_var_docblock_wins_over_the_assignments
FAILED tests/test_property_type_from_assignment.py::test_deviation_a_parent_typing_its_own_property_reaches_the_child
FAILED tests/test_property_type_from_assignment.py::test_the_property_node_carries_the_inferred_type
7 failed, 3 passed in 4.65s
```

Re-run at the review-fix tree (the first run, at `7bd55c5a`, read 422 passed):

Ran at 8398aa08
```
$ .venv/bin/pytest -q tests/test_property_type_from_assignment.py tests/test_factory_receiver.py tests/test_php_local_type_table.py tests/test_php_receiver_resolution.py tests/test_untyped_receiver_and_constructor_calls.py tests/contract
423 passed in 24.75s
$ (cd adapters/php && vendor/bin/phpstan analyse --no-progress --memory-limit=1G)
 [OK] No errors
```

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone, at `7bd55c5a`; payload = the raw ticket above the separator + the branch diff.

- **`challenger` round 1** (63,800 tokens): 11 rebuilt · 8 met · 1 not met (row 3, "any other assignment") · 2 can't
  tell (rows 10–11, conformance and the anchor). **Taken:** F1 (a destructure or `foreach` target), F2 (a trait's write), F3 (a same-file subclass's write) — each
  now untypes the property (`8398aa08`, `test_challenger_…`, red on `7bd55c5a`). F5 / can't-tell row 11: the anchor
  counts below. Can't-tell row 10 (conformance): `tests/contract` is in the run below. **Not taken:** F4 (a
  by-reference argument `fill($this->p)`): which parameter is by-reference lives in the callee's declaration, often
  another file — a follow-up, at `HEURISTIC` in the meantime.
- **`challenger` round 2** (verify-only, resumed, at `8398aa08`): F1, F3 fixed; F2 fixed for a trait in the same file
  — a trait in another file stays unseen, the file-local rule (scope 3); F4 accepted. Its final line, transcribed:

`CHALLENGER VERDICT: 11 requirement(s) rebuilt | 11 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

  The regression scan over the Phase-1 suites, in the main loop:

Ran at 8398aa08
```
$ .venv/bin/pytest -q tests/test_property_type_from_assignment.py tests/test_factory_receiver.py tests/test_php_local_type_table.py tests/test_php_receiver_resolution.py tests/test_untyped_receiver_and_constructor_calls.py tests/contract tests/test_php_adapter_grammar.py
446 passed in 22.24s
```

**Anchor (AC4, W5 — counts only, `~/code-atlas-review/447-anchor.md`).** The anchor's tracked PHP at its HEAD, one
fresh build per adapter: untyped-receiver CALLS left unlinked 114,430 → 112,546 (−1,884); receiver-chain CALLS linked at
`HEURISTIC` 6,452 → 12,799; 1,402 properties carry `doc_type`; build 212 s → 219 s.

Reviewed at 8398aa08 — files: `adapters/php/src/{MemberTypes,TypeTable,Visitor}.php`,
`tests/test_property_type_from_assignment.py`, `adapters/php/README.md`, `CHANGELOG.md`; working doc
`docs/tasks/447_php-property-type-from-assignment.md`.

`Ph3/4 proven by`: AC1–AC3, W1–W4 → `tests/test_property_type_from_assignment.py` (11); AC4 → `tests/contract` + the anchor.

## Phase 5 — finalise

**Durable lesson.** 447-C1 `every-write-form-the-grammar-has` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Gate at `8344fd63` (the tip but this record; after review only bookkeeping and the test file's line wraps moved):

```text
scripts/gate.sh
26 passed · 0 failed · 0 skipped
GATE GREEN — all 26 checks passed
```

The first gate run, at `6029e736`, was red on `ruff` (five E501 lines in the test) and on
`test_backlog_bookkeeping.py` (the ledger row named no PR); both fixed in `8344fd63`.

**P8.** `scripts/cross_repo_validate.py --public-only --skip-clone` on this branch's code: `public_ok: 11,
public_failed: 0` — no floor moved, so none re-floored.

### Outward actions

Under the handover: push `feat/447-php-property-type-from-assignment`; open its PR against `main`. Deferred: ratify
W1–W5 and the scope-3 deviation; merge; follow-ups for F4 and a trait in another file.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 47,000 |
| 4 review | ticket-blind `challenger` | 1 | 63,800 |
| 4 review | ticket-blind `challenger` | 2 | 6,009 (resumed: 69,809 cumulative − 63,800) |

`LEDGER TOTAL: 116,809 · top cost driver: 4 review / challenger` — main loop unmeasured.
