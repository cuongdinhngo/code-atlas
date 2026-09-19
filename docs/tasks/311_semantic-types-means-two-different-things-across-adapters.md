---
id: 311
slug: semantic-types-means-two-different-things-across-adapters
title: "`semantic_types` is declared by TS and Python for a local type table PHP also has and does not declare, so the honesty flag answers two different questions"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [137, 153, 227, 231]
---

## Why this exists

`capabilities` is the R1.6 honesty channel: an adapter declares what it fills so a payload consumer
can tell *absent* from *never looked*. 231 closed the case where an adapter declared a flag it could
not fill. The inverse is open, and it is on the oldest adapter.

`KNOWN_CAPABILITIES` holds `semantic_types` (`contract.py:221`). TS declares it for the local type
table 153 shipped (`tests/test_ts_semantic_types.py:1` — *"a local type table gives the TS adapter
the `semantic_types` capability"*), and Python for the same mechanism from 227
(`tests/test_python_semantic_types.py:1`). PHP ships that mechanism too and declares five flags
without it (`adapters/php/index.php:28-34`), because in 137 the name meant the *other* thing: 137's
out-of-scope list reads **"PHPStan `semantic_types` — the opt-in half"**, i.e. an external checker's
types, which PHP never shipped.

So `get_index_status.capabilities_by_language` today says PHP — the depth standard, 1-4% HEURISTIC
`CALLS` against TS's 54.1% — has no semantic types, while the two shallower adapters say they do.
Both readings are defensible and that is the defect: one flag, two questions, and the payload does
not say which one it answered.

## Scope / Deliverables

1. Decide what `semantic_types` asserts, and write the decision where the flag is defined
   (`contract.py`) rather than in a task file: either **(a)** *a file-at-a-time local type table
   backs member-call receivers* — then PHP declares it and nothing else moves — or **(b)** *types
   come from a checker outside the file* — then TS and Python stop declaring it and the table-backed
   capability gets its own flag.
2. Apply the decision to all four handshakes and to `tests/contract/` conformance.
3. State the chosen meaning in `ADAPTER_PLAYBOOK.md` §3's `capabilities` row, so adapter #5 reads it
   with the other optional-field decisions instead of re-deriving it from three adapters.

## Constraints

- No core language branch; the flag is data the core routes, never a branch (R1.1).
- A flag change is a handshake change: conformance tests move with it (R3).
- No new capability invented for a mechanism no adapter has.

## Acceptance criteria

- AC1: `contract.py` states what `semantic_types` asserts, in one place.
- AC2: every adapter that has the asserted mechanism declares the flag, and no adapter that lacks it
  declares it — asserted per adapter, not by reading one handshake.
- AC3: `ADAPTER_PLAYBOOK.md` §3 carries the meaning.
- AC4: `get_index_status.capabilities_by_language` on a PHP+TS+Python index answers the same question
  for all three.
