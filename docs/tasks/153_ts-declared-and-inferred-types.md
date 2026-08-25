---
id: 153
slug: ts-declared-and-inferred-types
title: The TS adapter announces no `semantic_types` — inferred receivers need 137's type table, not a tsc Program
phase: 2
milestone: M7
status: todo
depends_on: [019, 151, 137]
---

## Why this exists

`semantic_types` is the one entry in `contract.KNOWN_CAPABILITIES` (`code_atlas/contract.py:156`) and
the TS adapter announces `capabilities: {}` (`adapters/typescript/index.js` META). Declared types
already ride on a node's `extra.type` (019), so what is missing is exactly the **inferred** half: the
class an expression evaluates to, so `obj.method()` can resolve to `<Class>::method` instead of a bare
name.

019 settled that this needs **no** protocol change and no tsc `Program`. Task 019's finding #4 is the
route: [137](137_php-local-type-table.md) shipped that machinery for PHP — `TypeTable.php`,
`MemberTypes.php`, `TypeName.php` — per-function local variable types plus the class an expression
evaluates to, syntactic and file-at-a-time. A TS equivalent is a port of a proven shape, and PLAN §4.4's
`open_project`/two-pass options stay unneeded (019 resolved that gate; the one-program-per-worker cost
in 019's finding #5 is what made them expensive anyway).

**Sequencing.** [151](151_ts-member-calls-emit-no-edge.md) must land first: today `obj.method()` emits
*nothing*, so there is no edge for a type table to upgrade. 151 makes the edge exist at `HEURISTIC`;
this ticket promotes it to `RESOLVED`.

## Scope / Deliverables

- A TS/JS local type table in 137's shape: `const x = new Foo()`, an annotated parameter/property, a
  `let` narrowed by assignment — the syntactic cases, no checker.
- Promote a member call whose receiver the table names to `<Class>::method`, leaving the rest at the
  tier 151 set. The **measured HEURISTIC share** before and after is the deliverable, as 137 did.
- Announce `semantic_types` in the handshake once — and only once — the table actually backs it, with
  the core's meaning of the capability unchanged (R1.6: data the adapter announces, no core branch).
- A written verdict on the tsc-checker question: whether anything real still wants a `Program`, given
  019's answer and this table.

## Acceptance criteria

1. A named target HEURISTIC share on a pinned TS sample, met and reported by a committed reporter, in
   the shape 137 used (R6.3's reporter half) — not a session number.
2. `semantic_types` is announced only when the table is in place, and the core still has zero language
   branches (R1.1, CI-gated).
3. No `contract_version` bump. If one turns out to be needed, that reopens §4.4 and is a finding, not
   a quiet edit (R3).
4. Red run recorded per new guard (R6.5).

## Out of scope

- Cross-file type flow (a type that only a whole-program view could know). File-at-a-time is the
  contract; anything beyond it is a finding to write down, not to build here.
- `allowJs`/JSDoc as a *type source* — [154](154_ts-allowjs-and-jsdoc-types.md).

## References

PLAN §4.4, §8.2; `code_atlas/contract.py:156`; `adapters/php/src/TypeTable.php`; ENGINEERING_RULES
R1.1, R1.6, R3, R6.3, R6.5; tasks 137, 019, 151.
