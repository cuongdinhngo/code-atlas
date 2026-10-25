---
id: 413
slug: record-attributes
title: "A record's trust tier, region or status is dropped at build, so the agent treats an unverified record as verified"
phase: 2
milestone: Trust
status: todo
depends_on: [407]
---

## Why this exists

A consumer's survey, 2026-10-25. Its records carry attributes the answering agent needs right away:
a trust tier, a region, a status. The `records` field map reads only `id`, `title`, `url`, `kind` and
`targets` (`records.py:30`, `_fields`). To get the rest the agent must look each record up in a second
store. It often skips that lookup and treats unverified records as verified.

## Scope

1. The `records` block declares extra attributes as a list of dotted field paths, for example
   `"attributes": ["tier", "region", "status"]`. They are stored, and returned verbatim on every
   record row in every answer. Design states which JSON value shapes are kept.
2. A `records_filter` parameter on the tools that return records: equality or `in` on declared
   attributes, for example `{"tier": ["A", "B"]}`. A filter on an undeclared attribute is refused,
   not ignored.
3. Undeclared source fields are still ignored, and `exclude` still drops a record before anything
   reads it.
4. Update the user docs for the records rule.

## Acceptance criteria

- **AC1:** A fixture record with `tier: "A", region: "X"` carries both fields in `read_symbol`,
  `find_references` and `impact`.
- **AC2:** `records_filter: {"tier": ["A"]}` keeps it, and `{"tier": ["C"]}` drops it. The answer's
  record total counts what the filter kept.
- **AC3:** A records block without `attributes` answers byte-identically to before.
