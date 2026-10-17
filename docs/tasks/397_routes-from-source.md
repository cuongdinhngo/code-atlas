---
id: 397
slug: routes-from-source
title: 'A routes table must be a generated TSV, so the consumer keeps a script and a copy that drift from the census it came from'
phase: 2
milestone: Coverage
status: todo
depends_on: [385, 396]
---

## Why this exists

This comes from the anchor project (2026-10-17). The anchor already keeps a JSON census of its
endpoints: URL plus handler, the handler by short class name (`OrderController::listAction()`).
385's `routes` block reads only an inline `table` or a two-column TSV whose target is a stored
qname, so the anchor wrote a ~100-line script to turn the census into a 1,162-row TSV.

- F1: the script re-implements name resolution. It scans `namespace` + `class` declarations to
  turn a short class into a qname and picks a regional twin by a hand-written order. The index
  already holds every class's qname.
- F2: the TSV is a copy. When the census changes and nobody re-runs the script, routes answer from
  the old table; 396's digest sees the TSV, not the census behind it.

## Scope

1. A `routes` block may name a JSON source: a path, the row selector, and the fields for `key` and
   `target`. The file is digested like a TSV (396).
2. A target written `Class::method()` or `Class::method` with a short class resolves against the
   index's stored qnames. Exactly one class: linked. Several: an optional `prefer` list of qname
   segments picks one in order, else the row counts as unresolved and the status lists its
   candidates. None: unresolved, as today.
3. TSV and inline tables are unchanged.

## Acceptance criteria

- **AC1:** A fixture census with three endpoints whose handlers name short classes: the build
  links all three, and `trace_capability(route=…)` answers as it does for the equivalent TSV.
- **AC2:** Two classes with one short name, `prefer` absent: the row is unresolved and the status
  names both candidates. With `prefer`, the preferred one is linked.
- **AC3:** Edit the census only: 396's `rules_stale` turns on, and the next incremental build
  applies it.
- **AC4:** An existing TSV block answers byte-identically.

- **AC-field:** the anchor deletes its generator script and TSV, points the block at its census,
  and gets at least the TSV's resolved count; record both counts in the working doc.
