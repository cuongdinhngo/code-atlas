---
id: 369
slug: class-property-references-beyond-php
title: 'A TS static field or a Python class attribute is never referenced, so find_references on it answers a confident zero'
phase: 2
milestone: Coverage
status: done
depends_on: [336, 232]
---

## Why this exists

336 made a PHP static property read or write (`Foo::$count`) a `REFERENCES` edge onto the property.
Neither other source adapter emits one. Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `static count = 0` is `Property Foo::count` with `modifiers: ["static"]`.
  `Foo.count`, `Foo.count = 2` and `this.count` emit no edge of any kind. The only `REFERENCES` are
  decorators and type annotations (`adapters/typescript/src/parse.js`).
- **Python:** `count = 0` in a class body is `Property Foo::count`. `Foo.count`, `Foo.count = 1`,
  `self.count` and `cls.count` emit no edge. The only `REFERENCES` are decorators and annotations.

`find_references Foo::count` therefore answers zero for a property the code reads and writes.

## Scope

1. A member access whose receiver the adapter already resolves — the class by name, or the lexical
   receiver (`this` · `self`/`cls`) — onto a **declared** property of that class emits `REFERENCES`.
   Reads and writes alike, as 336 did.
2. Only what the type table can name. An untyped receiver emits nothing (never a bare-name guess),
   and a property the class does not declare is not invented (229).
3. TS: `this.count` reaches a **static** field only inside a static method (there `this` is the
   class); in an instance method it does not. Python: `self.count = …` creates an instance attribute
   that shadows the class one — whether it counts as a write of `Foo::count` is decided in design.
   A property declared on a base class (`Sub.count`) is not followed; that is a documented limit.
4. PHP's own residual stays where it is: `$this->x` / `$obj->x` (BACKLOG Follow-ups, 336). Whether
   this ticket's lexical-receiver rule should land in PHP too is decided in design, not assumed.

## Acceptance criteria

- **AC1:** On a TS fixture, `find_references Foo::count` lists the `Foo.count` read, the write and
  a `this.count` read inside a **static** method; `this.count` in an instance method adds nothing.
- **AC2:** The same on a Python fixture for `Foo.count`, `self.count` and `cls.count`.
- **AC3:** A method call `this.bar()` / `self.bar()` adds no `REFERENCES` (it is already `CALLS`).
- **AC4:** The parity fixture gains the probe, and §7 regenerates with the new row.
- **AC5:** The new edges move graph counts: `cross_repo_validate.py` runs and the floors are re-set (P8).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 369 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges 367's and 368's PRs, then this one. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/369-class-property-references-beyond-php`, stacked on `feat/368-python-module-scope-receiver`
  (both edit the Python adapter's walk); its PR targets that branch. Contract `.mango/run-contract-369.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 2 want-decision asked | 8 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** PHP's `enterStaticPropertyFetch` (336), both adapters' member tables and `--file` mode,
and the parity report all resolve. Measured: TS `Foo.count`/`this.count` and Python
`Foo.count`/`self.count`/`cls.count` emitted no edge.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,104 tokens) surfaced X1–X10.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | Python `self.count = …` shadows the class attribute | want | **ASSUMED (delegated by the handover):** a write of `Foo::count` — `find_references` on the declared attribute lists every site that touches its name; a confident zero is the worse error |
| X2 | the lexical-receiver rule in PHP | want | **ASSUMED (delegated):** not here; PHP's `$this->x` stays in BACKLOG Follow-ups (336), so PHP counts do not move |
| X3 | receiver forms | how | a static name or the lexical receiver only (Scope 1/2): a same-file class's name, `this` in a TS static member, `self`/`cls`; a typed variable, an element access and a class from another file are not followed (README) |
| X4 | TS static vs instance | how | `Foo.x` and static `this.x` reach a **static** field only; an arrow inherits `this`, a `function` rebinds it; an instance field is not followed (the ticket's title and AC1) |
| X5 | Python `self`/`cls` | how | by name inside a class's methods, as `self.m()` already resolves (`emit_call`) |
| X6 | a base class's property | how | not followed (Scope 3) |
| X7 | which Python attributes are declared | how | only names the class body itself assigns — the `Property`/`ClassConst` nodes (229: nothing invented) |
| X8 | source and line | how | the enclosing scope, one edge per occurrence, as 336 |
| X9 | parity and P8 | how | a parity probe row; cross-repo run and re-floor |
| X10 | a new field | how | none: `REFERENCES` exists (336) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=5`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

The base is 368's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "answers zero for a property the code reads and writes" | the reads and writes are references | ✅ |
| C1 | Scope 2 | "never a bare-name guess" | a shadowed or untyped receiver emits nothing | ✅ |
| C2 | Scope 2 | "a property the class does not declare is not invented" | onto declared members only | ✅ |
| R1 | Scope 1 | class name or lexical receiver, reads and writes | X3 | ✅ |
| R2 | Scope 3 | TS `this` only in a static method | X4 | ✅ |
| R3 | Scope 3 | Python `self.x = …` decided in design | X1 | ✅ |
| R4 | Scope 4 | PHP lexical rule decided in design | X2 | ✅ |
| AC1 | AC | TS `Foo.count` read, write, static `this.count` | | ✅ |
| AC2 | AC | Python `Foo.count`, `self.count`, `cls.count` | | ✅ |
| AC3 | AC | a method call adds no `REFERENCES` | | ✅ |
| AC4 | AC | the parity fixture gains the probe, §7 regenerates | | ✅ |
| AC5 | AC | cross-repo runs and the floors are re-set | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — four sites; an instance method's, a `function`'s and a shadowing parameter's absent | |
| AC2 | yes — four sites; a shadowing parameter and local absent | |
| AC3 | yes — no `REFERENCES` target ends with `::inc`, `::bump` or `::missing` | |
| AC4 | yes — `scripts/adapter_parity_report.py --check` (`tests/test_adapter_parity.py`) | |
| AC5 | yes — `cross_repo_validate.py` 11 ok with the new floors | |

### Blast radius

- Both adapters' body walks; `scripts/adapter_parity_report.py` (the annotations row now excludes a use);
  the three parity fixtures; `scripts/cross_repo_samples.json`.
- Contract, parity and the TS/Python suites: `362 passed` on the first commit.

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no core change · §R2.1 (change-type) ✅ member access syntax only · §R3.1 (change-type) ✅ no vocabulary move · §R5.2 (change-type) ✅ only a same-file class's declared member, never a guess · §R6.7 (change-type) ✅ the parity table is generated · §R7.7 (change-type) ✅ no formatter run over untouched lines`

## Phase 2 — design

### Approach

1. Python: `class_attrs` (names a class body assigns); `emit_attribute_ref` on every non-callee
   `Attribute` and on assignment targets; `scope_names` (parameters, body bindings, an enclosing
   def's included) rejects a shadowed receiver.
2. TS: `staticFields` per class; `emitStaticFieldRef` on every non-callee property access;
   `thisClass` walks to the binding member; `boundLocally` rejects a shadowed class name.
3. Parity: each fixture gains a typed static counter read and written; a probe counts references
   onto a declared field, and the annotations probe excludes them.
4. READMEs, playbook §1.1 and §7, TOOLS.md, CHANGELOG; cross-repo re-floor.

### Rejected alternatives

- **Emitting for an imported class, as PHP's `Foo::$x` does** — PHP's syntax says "class"; `X.y` in
  TS/Python does not, so every module or object member would become an unlinked reference.
- **TS instance fields through `this`** — every `this.x` in a TS codebase; PHP's equivalent is still open.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | attribute references | `adapters/python/src/parse.py` | Python emission | R1, R3, C1, C2 | 1/1 |
| 2 | static field references | `adapters/typescript/src/parse.js` | TS emission | R1, R2, C1, C2 | 1/1 |
| 3 | proving test | `tests/test_class_property_references_beyond_php.py` (new) | — | AC1–AC3 | 1/1 |
| 4 | parity probe | `scripts/adapter_parity_report.py`, `tests/fixtures/parity/{php.php,python.py,typescript.ts}` | `tests/test_adapter_parity.py` | AC4 | 4/4 |
| 5 | floors | `scripts/cross_repo_samples.json` | weekly job | AC5 | 1/1 |
| 6 | docs | both READMEs, `docs/ADAPTER_PLAYBOOK.md`, `docs/TOOLS.md`, `CHANGELOG.md` | doc budget | R4 | 5/5 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration | real TS + Python build, `find_references` | authored | ✅ |
| AC4 | generated doc | the parity table pin | authored | ✅ |
| AC5 | real corpus | `cross_repo_validate.py` on the pinned samples | pinned | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_class_property_references_beyond_php.py`.

### Rollback

`git revert`; restore the three floors with it.

## Phase 3 — execute

Commit `0d7a2cf8` (code, tests, parity, docs). **Red first** — the test on the prior parsers:
`3 failed`. **P8:** `cross_repo_validate.py --public-only --skip-clone` 11 ok / 0 failed; nodes
unchanged everywhere, edges up on the Python samples only — flask 7317→7368, pydantic
78731→79577, requests 4417→4686; floors re-set at ≈80% in `d2c9e04f`. **Corrected:** rerun with
`CA_*_CMD` unset (the shell pointed them at the main checkout and the harness prefers them), the TS
samples move too — mqttjs 6150→6151, socketio 28229→28241 (static fields); their floors hold.

**Sweep.** Axis 1: `git diff --name-only feat/368-python-module-scope-receiver..HEAD` = items 1–6;
`ruff check`, `mypy` (core, Python adapter), `tsc --checkJs --strict` clean. Axis 2: as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `89be92bc` — `0d7a2cf8` after the rebase —, 57,985 tokens): 4 met · 2 not met · 1 can't tell.**

1. **F1 (high): a parameter or local named like the class, or a rebound `self`, was read as the class.**
   **Fixed** in `cddc1a25`: both adapters check the receiver's scope; red `2 failed, 1 passed` on the prior parsers.
2. **F2: two dependency symlinks were committed.** **Fixed** before push (the commit was amended).
3. **F3 / AC5: no cross-repo run.** **Fixed:** run and re-floored (`d2c9e04f`).
4. **F4: TS `Foo["count"]` is not read.** **Left:** a documented limit (element access).
5. **F5: a class name declared twice in a file is ambiguous and emits nothing.** **Left:** the file's
   ambiguity rule, never a pick.
6. **F6: the probe ran twice.** **Fixed.**
7. **F7: no shadowing negatives.** **Fixed** with F1.
8. **Can't tell: Scope 4's PHP decision.** Recorded as X2.

Verify-only (main loop):

Ran at d2c9e04f:
```
$ .venv/bin/python -m pytest -q tests/test_class_property_references_beyond_php.py
3 passed
```

`Ph3/4 proven by`: G1, C1, C2, R1–R4, AC1–AC5 — 12/12.

Verdict: **clean (challenger only — REVIEWER: OFF)** — every not-met finding landed.

Reviewed at d2c9e04f — the diff `feat/368-python-module-scope-receiver..d2c9e04f`. Working doc:
`docs/tasks/369_class-property-references-beyond-php.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `d2c9e04f` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

New lesson `369-C1` (`a-name-receiver-needs-its-scope`): a receiver read by its spelling — a class
name, `self` — needs the scope that could rebind it; first sighting.

### Outward actions

1. Push `feat/369-class-property-references-beyond-php` — pre-authorised.
2. Open the PR against `feat/368-python-module-scope-receiver` — pre-authorised.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 48,104 |
| 2 | review | `challenger`, round 1 | 57,985 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 106,089 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits, floors included.

**Gate.** `scripts/gate.sh` on `7d875b5b`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
