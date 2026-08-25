---
id: 157
slug: r62-inventory-has-no-named-default-export-case
title: R6.2's TS inventory covers only the anonymous `export default` — the named form is the commonest one
phase: 2
milestone: M7
status: todo
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
