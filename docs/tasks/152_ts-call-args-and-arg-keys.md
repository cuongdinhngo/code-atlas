---
id: 152
slug: ts-call-args-and-arg-keys
title: TS call edges carry no `args`/`arg_keys` — two contract fields the core validates and only PHP fills
phase: 2
milestone: M7
status: todo
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
