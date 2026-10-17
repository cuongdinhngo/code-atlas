---
id: 398
slug: keyed-string-arg-span
title: 'A keyed_calls string key is read from the call''s first line, so a wrapped call names no key and nothing counts the miss'
phase: 2
milestone: Coverage
status: todo
depends_on: [222, 352, 364]
---

## Why this exists

This comes from the anchor project (2026-10-17). Its draft `keyed_calls` rules map a data-access
helper's first argument to a table write: `insertRow('Items', $row)` → WRITES `dbo.Items`.
`key_from: "string"` re-reads the source line at the edge's `line` and splits the arguments of the
one `<callee>(` on it (`enrichment.py:519-555`).

- F1: a call wrapped after `(`, or with the key on a later line, returns `None` from
  `_call_argument`, so the site emits nothing. The anchor's setup doc has to warn "only when the call
  is one line"; `find_references` on the table lists fewer writers and still says only
  `authoritative: false`.
- F2: two calls of one callee on a line also return `None` (352). Neither miss is counted, so a
  rule's coverage cannot be measured.
- `key_from: "array_keys"` has no such limit: the adapter captures `arg_keys` (063).

## Scope

1. Adapters that already advertise the `args` capability also capture a string literal's value
   for a `string` arg (e.g. `arg_strings`, parallel to `args`), so the key is read from the edge.
   A contract change: bump the version and say so.
2. `key_from: "string"` reads the captured value first and falls back to today's line read for an
   index built before the bump.
3. A `keyed_calls` rule may name its key by keyword (`key_kw`), and the PHP adapter reads PHP 8
   named arguments into `kwargs` — the line read could not see either (372's follow-up).
4. Each `keyed_calls` rule reports how many of its call sites had a string arg at `key_arg` but
   named no key (`keys_unread`), in the build report and `get_index_status`.

## Acceptance criteria

- **AC1:** PHP fixture `insertRow(\n  'Items',\n  $row\n)` under a WRITES rule: `find_references`
  on `dbo.Items` lists the site.
- **AC2:** Two calls of the callee on one line: both sites are linked.
- **AC3:** `insertRow($table, $row)`: no edge, and `keys_unread` counts it only if arg 1 was a string
  literal (here it is not, so 0).
- **AC4:** `insertRow(row: $row, table: 'Items')` under `key_kw: "table"`: the site is linked.
- **AC5:** An index built before the bump still answers single-line sites exactly as today.

- **AC-field:** on the anchor index, the writers listed for three tables known to be written by
  wrapped helper calls; record the before/after counts in the working doc.
