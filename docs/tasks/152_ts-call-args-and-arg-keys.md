---
id: 152
slug: ts-call-args-and-arg-keys
title: TS call edges carry no `args`/`arg_keys` — two contract fields the core validates and only PHP fills
phase: 2
milestone: M7
status: done
depends_on: [019, 151]
---

## Why this exists

`args` and `arg_keys` are edge fields in the frozen contract (`code_atlas/contract.py:113-114`), with
their own validator: `_check_arg_keys` (line 345) requires `arg_keys` to be a list parallel to `args`,
each entry null or a list of strings. The PHP adapter fills them (`Visitor.php:917-919` via
`argLiterals`/`argKeys`). The TS adapter emits neither, on any edge.

So a contract field is exercised by one adapter out of two — which is precisely the asymmetry adapter
#2 exists to expose (R1.2/§4.4): a field only one implementation fills is a field whose meaning was
never tested against a second language.

## Scope / Deliverables

- Literal argument capture on `CALLS`/`NEW` edges: string, number, boolean, null — the `ARG_LITERALS`
  set the core already validates against; a non-literal position is `null`, never a guess.
- `arg_keys` for an object-literal argument: its ordered string keys, parallel to `args`, mirroring
  what PHP does for an array literal. TS shapes with no PHP analogue — a spread, a template literal, a
  shorthand property, a computed key — need a stated answer each, not silence.
- The conformance case pins the exact `args`/`arg_keys` payload, not just its presence.

## Acceptance criteria

1. A TS call with literal and object-literal arguments emits `args` and `arg_keys` that pass
   `contract.validate` with no new validator changes — if the validator *must* change, the contract
   version bumps (R3) and that is a finding worth its own note.
2. The shapes with no PHP analogue (spread, template literal, shorthand, computed key) are each
   covered by a fixture and documented in the adapter README.
3. A red run is recorded for the new assertions (R6.5).

## Out of scope

- Changing the contract's `args` vocabulary. If TS needs a shape the field cannot express, that is a
  finding to file, not a silent widening (R3).
- Any consumer-side use of the new fields.

## References

`code_atlas/contract.py:113,345`; `adapters/php/src/Visitor.php:917`; ENGINEERING_RULES R3, R6.5;
tasks 019, 151.

---

## Session status

- **KEY:** 152 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** TS `CALLS`/`NEW` edges carried no `args`/`arg_keys` (only PHP filled them); delta-green via Docker (node adapter + `fcntl`).

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

References resolve: `contract.py:113` (`args`/`arg_keys` fields) + `:345` (`_check_arg_keys`), `Visitor.php:917` (PHP `argLiterals`/`argKeys`). Nothing to expose — the contract fixes the categories and PHP fixes the behaviour to mirror; the four TS-specific shapes are enumerated by the ticket.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** M · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R3 (change-type) ✅ · §R6.5 (change-type) ✅ · §R1.1 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — no TS edge carries args today; the payload-pinning test is the guard. Delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | a field only one adapter fills was never tested against a 2nd language | TS fills `args`/`arg_keys`, mirroring PHP | open |
| R1 | Scope 1 | literal arg capture on CALLS/NEW (ARG_LITERALS); non-literal → null | category per arg, never the value; spread drops the list | open |
| R2 | Scope 2 | `arg_keys` for object literal; the 4 no-PHP-analogue shapes each answered | spread/template/shorthand/computed each stated + fixtured | open |
| R3 | Scope 3 | conformance pins the exact payload, not presence | dedicated pinning test (edge-shape tuple carries no args) | open |
| AC1 | AC1 | payload passes `contract.validate` with no validator change; else bump (R3) | Falsifiable: validate == [] ; no contract.py change | open |
| AC2 | AC2 | the 4 shapes each fixtured + documented in README | Falsifiable: fixture + README table | open |
| AC3 | AC3 | red run recorded (R6.5) | Falsifiable: recorded red-run | open |
| C1 | Out-of-scope | no change to the `args` vocabulary (a shape it can't express → a finding, R3) | boundary | binding |
| C2 | Out-of-scope | no consumer-side use of the fields | boundary | binding |

### AC validation

All three ACs falsifiable (contract.validate / fixture+README / recorded red-run). No want-decision. No AC-value mismatch — categories are the frozen `ARG_LITERALS`; the emitted payload needed **no** validator change (AC1 met without a contract bump).

### Root cause (taxonomy: logic)

The TS adapter's `addEdge` never looked at a call's arguments, so `args`/`arg_keys` — contract fields with their own validator (`_check_args`/`_check_arg_keys`) — were filled by PHP alone. A field exercised by one adapter of two is a field whose meaning was never tested against a second language (R1.2/§4.4).

### Blast radius

`adapters/typescript/src/parse.js` (arg helpers + `addEdge` + the 5 CALLS/NEW sites), `README.md`, new fixture `tests/fixtures/typescript/call_args.ts`, new test `tests/test_ts_call_args.py`. No `code_atlas/`, no `contract.py` (AC1), no store.

## Phase 2 — design

### Approach

Four pure helpers in `parse.js` mirror PHP: `literalKind` (category of one arg), `argLiterals` (list,
or `null` when any arg is a spread), `objectKeys` (an object literal's normal+shorthand key names,
skipping spread/computed), `argKeys` (parallel: object→keys, array→`[]`, else `null`). `addEdge`
gains an optional call node; when present and `argLiterals` is non-null it attaches `args`+`arg_keys`.
All five `CALLS`/`NEW` sites pass the node — resolved, bare, `this.method`, `HEURISTIC`, `DYNAMIC` —
so tier never gates whether arguments are recorded (PHP attaches regardless of tier too).

**Category mapping.** `string` (string / template literal), `number` (numeric / bigint), `true`/
`false`/`null` (keywords), `array` (object **or** array literal); any other expression → `null`. A
template literal is a string-typed expression (PHP counts an interpolated string as `string`), so it
is `string`, not `null`.

**Why a dedicated test, not a conformance Case.** The conformance edge-shape tuple is
`(kind, source, target, tier)` — it has no args dimension, so it structurally cannot pin the payload.
Extending it would change the shared harness for both adapters (PHP cases would need args too); that
is its own change. `tests/test_ts_call_args.py` pins the exact `args`/`arg_keys` per edge and asserts
`contract.validate == []`.

### Rejected alternatives

- **Extend the conformance harness's EdgeShape with args** — touches the shared registry + PHP cases; broader than this ticket. A dedicated pinning test is equally exact and contained.
- **Record the literal *value*** — the contract is explicit that `args` is the category, never the value (a shape question, not a value one). Not done.
- **Emit `args` only on RESOLVED calls** — PHP attaches regardless of tier; a `DYNAMIC` `obj[x]()` still has argument shapes worth recording. Attached on every CALLS/NEW.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | logic + validation | `test_ts_call_args_and_arg_keys_are_pinned` (exact payload + `contract.validate == []`) | ✅ |
| AC2 | logic + docs | the fixture's spread/template/shorthand/computed edges + README table | ✅ |
| AC3 | validation | recorded red-run (arg capture disabled → `KeyError 'args'`) | ✅ |

### Proving test

`test_ts_call_args_and_arg_keys_are_pinned` in `tests/test_ts_call_args.py`: parses `call_args.ts` via
the adapter, asserts `contract.validate == []` and the exact `args`/`arg_keys` for each `CALLS`/`NEW`
edge — every category, the object-literal keys (normal+shorthand, minus spread+computed), the
positional-array `[]`, the template-literal `string`, and the spread call that drops the list. Fails
pre-change (no args field) and — AC3 — if the capture is disabled. Invocation:
`pytest tests/test_ts_call_args.py -q` (Docker: node adapter).

### SCOPE

`SCOPE: M` — arg helpers + `addEdge` + call-site plumbing in the adapter, one fixture, one test, README. No core, no contract (R3), no store. Branch `feat`.

## Phase 3 — execute

**Branch:** `feat/152-ts-call-args`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `literalKind`/`argLiterals`/`objectKeys`/`argKeys` mirror PHP; spread drops the list | implemented-as-approved |
| `addEdge` attaches args on every CALLS/NEW site regardless of tier | implemented-as-approved |
| dedicated pinning test + `contract.validate == []`, no contract change | implemented-as-approved |
| README documents the four TS-specific shapes | implemented-as-approved |

No deviations. `SCOPE: M` held.

### Verification sweep (Axis 1)

Diff = `adapters/typescript/src/parse.js`, `adapters/typescript/README.md`,
`tests/fixtures/typescript/call_args.ts` (new), `tests/test_ts_call_args.py` (new),
`docs/tasks/152_*.md`, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`. No `code_atlas/`, no contract.

### Empirical outputs

Adapter `--file` on the fixture:
```
CALLS literals   args=['string','number','true','false','null',None]  arg_keys=[None×6]
CALLS keyed      args=['array']            arg_keys=[['a','b','short']]
CALLS positional args=['array']            arg_keys=[[]]
CALLS templated  args=['string']           arg_keys=[None]
CALLS spread     (no args field — spread dropped the list)
NEW   Thing      args=['array','string']   arg_keys=[['id'],None]
```
`contract.validate(result) == []` (AC1 — no validator change, no contract bump).

AC3 red-run — arg attachment disabled in `addEdge`:
```
test_ts_call_args_and_arg_keys_are_pinned FAILED — KeyError: 'args'
```
parse.js restored byte-identical (grep `if (call) {` = 1).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_ts_call_args_and_arg_keys_are_pinned` (`contract.validate == []` + exact payload); no `contract.py` in diff |
| AC2 | the fixture's four shapes + README "Call arguments" table |
| AC3 | recorded red-run (capture disabled → `KeyError 'args'`) |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

A field-parity slice mirroring an existing PHP behaviour produced no new durable lesson.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: tsc gate green, pinning test green in Docker, `contract.validate == []`, AC3 red-run recorded, parse.js restored. Maintainer reviews on the PR.
