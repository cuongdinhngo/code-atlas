---
id: 278
slug: the-writer-set-is-computed-for-one-check-and-addressable-from-nothing
title: '"What else writes this table" is the question a data-attribution defect turns on, and the graph holds a `WRITES` edge, an unlinked-writer probe and a column-level target — all reachable only from `check_column_defaults`, so the question is asked as `find_references` on a Table, answered near-empty, and a third write site ships unfixed'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [022, 215, 255, 248]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 22 §7 / §8.1)

A three-ticket batch where all three defects were *which code writes this column*. The session
scoped one of them with `find_callers` on a method, concluded the table had two write paths, and
review found a **third** — a static helper on an unrelated class writing the same table, feeding the
same display. Shipping without it would have re-opened the ticket a third time.

> *"`find_callers` was never going to find it, and that is not the tool's fault. I asked who calls
> this method. The question was what else writes this table."*

The retro ranks this first of five asks: *"the single highest-value gap."* Its floor is modest —
*"even a `find_references` on a Table that returned INSERT/UPDATE statement sites at `HEURISTIC`
would have caught my miss."*

What already exists, none of it addressable by that question:

- `WRITES` is contract vocabulary since v9 (`contract.py:147`), targeting the Column when the
  statement names it and the Table at DYNAMIC when it does not.
- `store.has_unlinked_writes_relating_to` (`store.py:1947`) — the incompleteness the graph *can*
  know — has exactly one consumer: `check_column_defaults.py:248`.
- Only the SQL adapter emits `WRITES` (`adapters/sql/src/scan.js`). A write issued from application
  code is not modelled at all, in any language.

So a Table subject reaches a writer answer through one capability check and no navigation tool.

## Scope / Deliverables

- **The writer set is addressable.** A Table (and a Column) subject can be asked for the routines
  that write it, returning the `WRITES` sources the graph holds, tiered as stored.
- **The answer states its own half.** Where the index covers languages that emit no `WRITES`, an
  answer about a table is the SQL half only, and says so with the 255/264 machinery rather than
  reading as complete. `has_unlinked_writes_relating_to` is the existing evidence that a writer
  reached the graph and never linked — surface it as a count, not as a boolean buried in one check.
- **Decide the application-code half explicitly, and record the verdict.** A write issued as a SQL
  string from a host language is either (a) out of scope, stated in the tool description so nobody
  reads the SQL half as the whole, or (b) a `HEURISTIC` edge an adapter emits from a statement it
  parses out of a literal. Do not leave it undecided — the retro's whole miss lives in that gap.
- Whichever way (b) goes, it is a **language spec / ecosystem** judgement per R2 — never a repo's
  table names or ORM.

## Constraints

- R1.1: no language branch in the core; the Table/Column subject path is a **kind** branch, the way
  248 did it.
- R5.6: a partial writer set is never presented as the writer set — 215's own finding, which this
  ticket must not undo by widening the surface.
- R4.3: bounded like the existing probe (`_WALK_UNLINKED`), never an unbounded scan per query.
- R3: `WRITES` already exists; if no vocabulary changes, `contract_version` does not move.

## Acceptance criteria

- A Table subject returns its writer routines from a SQL fixture, with tier, and a Column subject
  returns the narrower set where the statement names the column.
- On an index whose other languages emit no `WRITES`, the same answer carries the unmeasured-relation
  reason and a route — never a bare `no_matches`.
- Unlinked writers naming the table are reported as a count on the answer, not only inside
  `check_column_defaults`.
- The application-code verdict is written into PLAN §19 and reflected in the tool description.
- `check_column_defaults` keeps its current behaviour and tests.

## References
`code_atlas/contract.py:147,62–78`, `code_atlas/store.py:1947–1965`,
`code_atlas/tools/check_column_defaults.py:248`, `adapters/sql/src/scan.js`,
field retro round 22 §7 / §8.1 / §9, [022](022_sql-schema-adapter.md),
[215](215_a-partial-writer-set-looks-finished-and-a-column-is-counted-twice.md),
[248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md).
