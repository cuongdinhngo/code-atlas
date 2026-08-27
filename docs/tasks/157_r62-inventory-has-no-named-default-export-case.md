---
id: 157
slug: r62-inventory-has-no-named-default-export-case
title: R6.2's TS inventory covers only the anonymous `export default` — the named form is the commonest one
phase: 2
milestone: M7
status: done
depends_on: [019, 149]
---

## Why this exists

R6.2's named TS/JS inventory (`docs/ENGINEERING_RULES.md:127-130`) has one `default-export` entry, and
its fixture `tests/fixtures/typescript/default_export.ts` covers the **anonymous** form
(`export default function () {…}`). The **named** form — `export default class Foo {}`, what a React
component file looks like — was never a case.

That gap had a cost: 019's review found that a default-import of a named default export resolved to a
qname no node had, and the whole conformance matrix stayed green because no case exercised the shape.
The defect is fixed (the declaration now emits `ALIASES` from `::default` to its own qname) and is
proven end-to-end in `tests/test_ts_import_resolution.py` — but a **proving test is not an inventory
entry**, and R6.2's contract is that the inventory names every construct the language has.

A file can carry only one default export, so this cannot be folded into the existing fixture: it needs
its own fixture and its own case key, which means the rulebook's named list changes. That rulebook edit
is why this is a ticket rather than a line in 019 — `tests/contract/` already asserts that the case
keys equal the named set exactly, so the two must move together.

## Scope / Deliverables

- A `default-export-named` fixture and conformance case: the node keeps its own name, and the exact
  edge shapes pin the `ALIASES` edge from `::default` including its `source_qname`.
- R6.2's inventory list in `docs/ENGINEERING_RULES.md` grows the entry, with 149's per-entry
  justification extended in the same commit (the map lives there, not in the rule).
- 149's inventory table updated so the count in the rule and the count in the task agree.

## Acceptance criteria

1. The new case is in `TS_R62_CASES`, the fixture exists, and
   `test_the_conformance_inventory_is_the_named_set` passes with the rulebook list and the registry in
   agreement.
2. Reverting the 019 alias fix fails the new conformance case — the case is the guard, so it must be
   observed failing (R6.5).
3. The inventory count is stated in exactly one place; the other reads it (R6.7).

## Out of scope

- Any other missing construct. If the same read turns up a second gap, file it — widening this ticket
  would hide which gap cost what.

## References

`docs/ENGINEERING_RULES.md` R6.2; `tests/contract/adapter_registry.py` `TS_R62_CASES`;
`tests/fixtures/typescript/default_export.ts`; ENGINEERING_RULES R6.5, R6.7; tasks 149, 019.

---

## Session status

- **KEY:** 157 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** the named-default construct had no conformance case (the matrix stayed green blind to it). Delta-green via Docker (node adapter + `fcntl`).

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

All references resolve: R6.2 (`ENGINEERING_RULES.md:127`), `TS_R62_CASES` (`adapter_registry.py:166`), `default_export.ts` fixture, task 149 inventory, task 019. Nothing to expose — the fixture shape (`export default class Foo {}`), the case key (`default-export-named`), and the ALIASES pin are all given by the ticket; the exact edge shapes are read from the adapter, not chosen.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** S · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=3`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R6.2 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (change-type) ✅ · §R6.1 (change-type) ✅`
`BASELINE: red — the named-default construct has no conformance case; adding it (case + fixture) is the proving guard. Delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | "the inventory names every construct the language has" | The named `export default` is an inventory case, not just a proving test | open |
| R1 | Scope 1 | `default-export-named` fixture + conformance case pinning the `::default`→`::Foo` ALIASES | New fixture + `TS_CASES` entry + `TS_R62_CASES` key | open |
| R2 | Scope 2 | R6.2 inventory grows the entry; 149's per-entry map extended same commit | R6.2 list + 149 table both gain it | open |
| R3 | Scope 3 | 149's count agrees with the rule | Count authoritative in 149's table; R6.2 points to it | open |
| AC1 | AC1 | new case in `TS_R62_CASES`, fixture exists, inventory-is-named-set passes | Falsifiable: conformance run green, set equality holds | open |
| AC2 | AC2 | reverting the 019 alias fix fails the new case (R6.5) | Falsifiable: observed red-run | open |
| AC3 | AC3 | count stated in exactly one place; other reads it (R6.7) | Count in 149 table; R6.2 holds no number | open |
| C1 | Out-of-scope | any other missing construct is filed, not folded | boundary | binding |

### AC validation

All three ACs falsifiable (conformance green / recorded red-run / single-count-source). No want-decision. No AC-value mismatch — the fixture/case/pin are given verbatim by the ticket.

### Root cause (taxonomy: validation)

R6.2's TS inventory had one `default-export` case (anonymous form only). The named form — the common React-component shape — was never a case, so 019's matrix stayed green while a default-import of a named default resolved to a qname no node had. A proving test (`test_ts_import_resolution.py`) fixed the defect but is not an inventory entry.

### Blast radius

`tests/contract/adapter_registry.py` (`TS_R62_CASES` + `TS_CASES` + shapes), `tests/fixtures/typescript/default_export_named.ts` (new), `docs/ENGINEERING_RULES.md` (R6.2 list), `docs/tasks/149_*.md` (inventory table + count), BACKLOG, TOKEN_LEDGER. No `code_atlas/`, no adapter source (the 019 fix already exists).

## Phase 2 — design

### Approach

Add the fixture `export default class Widget { render() {…} }` + `export function helper(){}`, run the
adapter to read the exact emitted shapes (never guessed), and pin them: nodes `{File,Class,Method,Function}`,
edges `{CONTAINS:3, ALIASES:1}`, with the load-bearing `ALIASES ::default → ::Widget`. Add the case key
to `TS_R62_CASES` and the Case to `TS_CASES` (the set-equality test keeps the two in lockstep). Grow the
R6.2 list and 149's table; make 149's table the single count source (14) and have R6.2 point to it (R6.7).

### Rejected alternatives

- **Fold into the existing `default_export.ts` fixture** — a file can carry only one default export, so the named form needs its own fixture and case key (the ticket's own reasoning).
- **Leave it as the proving test in `test_ts_import_resolution.py`** — a proving test is not an inventory entry; R6.2's contract is that the inventory names every construct (G1).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | validation | `test_adapter_conforms[typescript:default-export-named]` + inventory-set test green | ✅ |
| AC2 | validation | recorded red-run (019 fix disabled → case fails on missing ALIASES) | ✅ |
| AC3 | docs | count in 149 table only; R6.2 points to it | ✅ |

### Proving test

`test_adapter_conforms[typescript:default-export-named]` in `tests/contract/test_adapter_conformance.py`
(driven by the new `TS_CASES` entry): asserts the node/edge histograms and exact edge shapes, including
`ALIASES ::default → ::Widget`. Fails pre-change (no such case) and — per AC2 — fails if the 019 alias
emission is reverted. Invocation: `pytest tests/contract/test_adapter_conformance.py -q` (Docker: node adapter).

### SCOPE

`SCOPE: S` — one fixture + one registry case + two doc edits. No adapter source, no core. Branch `feat`.

## Phase 3 — execute

**Branch:** `feat/157-named-default-export-inventory`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `default_export_named.ts` fixture (named default class + helper) | implemented-as-approved |
| `TS_R62_CASES` key + `TS_CASES` Case + shapes read from the adapter | implemented-as-approved |
| R6.2 list + 149 table/count grow; count single-sourced in 149 (R6.7) | implemented-as-approved |

No deviations. `SCOPE: S` held.

### Verification sweep (Axis 1)

Diff = `tests/contract/adapter_registry.py`, `tests/fixtures/typescript/default_export_named.ts`,
`docs/ENGINEERING_RULES.md`, `docs/tasks/149_*.md`, `docs/tasks/157_*.md`, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md`. No `code_atlas/`, no adapter source (parse.js byte-identical after the AC2 red-run).

### Empirical outputs

Conformance (Docker, node adapter): `28 passed` — the new `default-export-named` case green, the
inventory-set equality (`TS_R62_CASES` == `TS_CASES` keys, both 14) holds.

AC2 red-run — 019 alias emission (`parse.js:260`) disabled:
```
test_adapter_conforms[typescript:default-export-named] FAILED
  histogram mismatch: Right contains 1 more item: {'ALIASES': 1}
```
parse.js restored byte-identical (grep confirms the emission line count = 1).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_adapter_conforms[typescript:default-export-named]` + `test_the_conformance_inventory_is_the_named_set` green (28 passed) |
| AC2 | recorded red-run: 019 fix disabled → case fails on missing `{'ALIASES':1}` |
| AC3 | 149 count line (14, single source); R6.2 holds no number, points to 149 |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

Closing an inventory gap the sibling 148/150 class already names (`fixture-shape-begs-the-question` /
guardrail-that-cannot-fail) produces no new durable lesson of its own.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: conformance green in Docker, AC2 red-run recorded, parse.js byte-identical. Maintainer reviews on the PR.
