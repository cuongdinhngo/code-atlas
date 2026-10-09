---
id: 368
slug: python-module-scope-receiver
title: 'A Python call on a module-level variable built by Foo() is unqualified, though the same call in a function resolves'
phase: 2
milestone: Coverage
status: done
depends_on: [227, 362]
---

## Why this exists

362's F1 taught the PHP type table to bind `$x = new X()` at a file's top level, so `$x->m()` in an
included view resolves. TS already does this at module scope. Python does not. Measured with
`adapters/python/index.py --file` on 2026-10-08:

```python
class Foo:
    def bar(self): ...
x = Foo()
x.bar()                      # CALLS target_raw "bar", HEURISTIC — unqualified
def g():
    y = Foo(); y.bar()       # CALLS "m.Foo::bar" — resolved
if __name__ == '__main__':
    z = Foo(); z.bar()       # CALLS "m.Foo::bar" — resolved
```

Module-level scripts, notebooks exported to `.py`, and settings modules are where this shape lives.
The unqualified edge falls to `_link_by_bare_name`, which links only a unique same-language match.

## Scope

1. The module-level walk keeps one local type table across the module's top-level statements,
   with pass 2's forgetful rules unchanged (playbook §2): a rebind the table cannot read re-opens it.
2. A binding made inside a module-level `if`/`for`/`while`/`try`/`with` branch re-opens the name
   after it (forgetful: no join across branches); `if __name__ == '__main__'` keeps today's handling.
3. A function body does not see a module binding made after it, or rebound before it is called —
   only the module's own top-level statements read the table.

## Acceptance criteria

- **AC1:** On the fixture above, `x.bar()` is `CALLS m.Foo::bar`.
- **AC2:** `x = Foo(); x = make(); x.bar()` leaves `x.bar()` unqualified (forgetful).
- **AC3:** A function reading a module-level `x` stays unqualified (no flow across scopes).
- **AC4:** `if c: x = Foo()` then `x.bar()` at module level stays unqualified.
- **AC5:** ADAPTER_PLAYBOOK §1.1's module-scope row reads `368` for Python.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 368 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges 367's PR, then this one. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/368-python-module-scope-receiver`, stacked on `feat/367-constructor-flag-beyond-php`
  (both edit `adapters/python/src/parse.py`); its PR targets that branch. Contract `.mango/run-contract-368.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 0 want-decision asked | 9 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `walk_stmt`, `_bind_or_forget`, the per-statement `{}` at the module walk
(`adapters/python/src/parse.py`, the last loop) and the playbook §2 forgetful rule all resolve. Measured
with `--file`: the ticket's fixture gives `x.bar()` → `bar` `HEURISTIC`, the function and `__main__`
cases resolved.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 51,702 tokens) surfaced X1–X9.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | compound statements at module level | how | each is walked with a copy of the table, and every name it stores is re-opened after it (AC4); function-body branches keep 227's behaviour — the ticket scopes the module walk |
| X2 | an UPPER-case module constant never reached the bind step | how | the Const branch binds too, so a settings module's `DEFAULT = Foo()` types `DEFAULT.bar()` |
| X3 | AC3 | how | holds by construction: a module-level def starts from its parameters (`param_type_map`); pinned by a test |
| X4 | writes the table cannot read | how | re-open on tuple unpack, loop target, `with … as`, `except … as`, walrus, `del`, `import`, `def`/`class`, augmented assignment, `match` captures — one store-context walk (`_stored_names`) |
| X5 | `global x` in a function | how | a name any function declares `global` is never typed at module level: a call may rebind it at any point (forgetful, playbook §2) |
| X6 | `if __name__ == '__main__'` | how | binds inside its branch, re-opened after it, like any `if` |
| X7 | class bodies | how | unchanged: a class body starts from `{}` |
| X8 | docs | how | README row, playbook §1.1, CHANGELOG |
| X9 | P8 | how | counts measured before and after; floors move only if counts do |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=5`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

The base is 367's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Module-level scripts … settings modules" | a module-level receiver built by `Foo()` resolves | ✅ |
| C1 | Scope 1 | "pass 2's forgetful rules unchanged" | an unreadable write re-opens | ✅ |
| R1 | Scope 1 | one table across the top-level statements | | ✅ |
| R2 | Scope 2 | a branch binding re-opens after it | X1/X6 | ✅ |
| R3 | Scope 3 | only top-level statements read the table | X3 | ✅ |
| AC1 | AC | `x.bar()` is `CALLS m.Foo::bar` | | ✅ |
| AC2 | AC | `x = Foo(); x = make(); x.bar()` unqualified | | ✅ |
| AC3 | AC | a function reading `x` stays unqualified | | ✅ |
| AC4 | AC | `if c: x = Foo()` then `x.bar()` unqualified | | ✅ |
| AC5 | AC | playbook row reads 368 | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — line 5's target is `m.Foo::bar`; the constant (line 15) and an annotation (line 31) too | |
| AC2 | yes — lines 6, 16, 19, 23, 28, 29, 30, 34, 36 stay `bar` | X4/X5 |
| AC3 | yes — line 8 stays `bar` | |
| AC4 | yes — line 11 `bar`; `__main__`'s own call resolves (13), the one after it does not (14) | |
| AC5 | yes — the row reads `368` | |

### Blast radius

- The Python adapter's module-level walk; a function body's walk is unchanged.
- Contract, parity, Python adapter suites and 367's: `388 passed`.

### Rule sections

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R2.1 (change-type) ✅ only Foo() and annotations the file writes · §R4.2 (change-type) ✅ set iteration only pops names, output order unchanged · §R5.2 (change-type) ✅ an unreadable write re-opens instead of guessing · §R6.1 (change-type) ✅ adapter fixture per case`

## Phase 2 — design

### Approach

1. The module walk keeps one table; an `Assign`/`AnnAssign` binds or forgets its plain-name targets
   and re-opens any other name it stores; any other statement is walked on a copy and re-opens every
   name it stores; names declared `global` anywhere are popped after every statement.
2. The module-constant branch also calls `_bind_or_forget`.
3. README row, playbook §1.1, CHANGELOG.

### Rejected alternatives

- **Join across branches** (keep a binding both arms agree on) — the playbook's forgetful rule says no join.
- **Fixing function-body branches in the same change** — 227's behaviour, outside the ticket.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | module table, store walk, constant bind | `adapters/python/src/parse.py` | Python emission | R1–R3, C1 | 1/1 |
| 2 | proving test | `tests/test_python_module_scope_receiver.py` (new) | — | AC1–AC4 | 1/1 |
| 3 | docs | `adapters/python/README.md`, `docs/ADAPTER_PLAYBOOK.md`, `CHANGELOG.md` | doc budget | AC5 | 3/3 |
| 4 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC4 | adapter | `--file` edges per line | authored | ✅ |
| AC5 | doc | the playbook row | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_python_module_scope_receiver.py`.

### Rollback

`git revert`; the next build emits the old edges.

## Phase 3 — execute

Commits `73ad78b8` (code, test) and `cf92b1b8` (docs). **Red first** — the test on 367's tip:
`1 failed, 3 passed` (AC1: `assert 'bar' == 'm.Foo::bar'`; AC2–AC4 already held, since nothing bound).

**Sweep.** Axis 1: `git diff --name-only feat/367-constructor-flag-beyond-php..HEAD` = items 1–3;
`ruff check`, `mypy --strict` (Python adapter) clean. Axis 2: Approach 1–3 as approved.

**P8.** `scripts/cross_repo_validate.py --public-only --skip-clone`: 11 ok / 0 failed; every sample's
node and edge count equals `main`'s (a bound call changes its target, not the count), so no floor moves.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `842aa1fa` — `cf92b1b8` after the rebase — 49,934 tokens): 8 met · 0 not met · 0 can't tell.**

1. **F1: `from m import *` re-opened nothing.** **Fixed** — a star import clears the table.
2. **F2: a loop's back edge kept a binding its own body overwrites.** **Fixed** — what any loop in the
   statement writes is open from its first pass.
3. **F3: `globals()[…] =`, `exec`, `vars`, `locals` writes went unseen.** **Fixed** — such a call
   clears the table.
4. **F4: a bare `p: Foo` binds.** **Left:** an annotation types its name, as pass 2 does in a function.
5. **Noise in the test source.** **Fixed.**

Fixes in `f83b8bc5` (code, test: red `1 failed, 4 passed` on the prior parser) and `6311eefe` (README).

Verify-only (main loop):

Ran at 910482bd:
```
$ .venv/bin/python -m pytest -q tests/test_python_module_scope_receiver.py
5 passed in 0.16s
```

`Ph3/4 proven by`: G1, C1, R1–R3, AC1–AC5 — 10/10.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 6311eefe — the diff `feat/367-constructor-flag-beyond-php..6311eefe`. Working doc:
`docs/tasks/368_python-module-scope-receiver.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `6311eefe` only the rebase onto 367's gate-record commit and bookkeeping —
this doc, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson: the forgetful rule is the playbook's (§2), and the challenger's three holes are
instances of it, not a new class.

### Outward actions

1. Push `feat/368-python-module-scope-receiver` — pre-authorised.
2. Open the PR against `feat/367-constructor-flag-beyond-php` — pre-authorised.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 51,702 |
| 2 | review | `challenger`, round 1 | 49,934 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 101,636 · top cost driver: refine/exposure-checker`

**Revert path.** `git revert` the branch commits; the next build emits the old edges.

**Gate.** `scripts/gate.sh` on `59dcc44d`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
