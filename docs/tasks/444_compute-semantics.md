---
id: 444
slug: compute-semantics
title: "compute: multi_defined is one object per kind and qname; the mention check audited"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [441]
---

## Why this exists

Pre-flight A6. On the anchor `multi_defined` answered 3,253 against the survey's ~161 redefined SQL
routines, and 48 of 50 `unreferenced_objects(Table, php)` rows read `no_edge_no_mention`.

## Scope

1. `multi_defined` groups by (kind, qname): the 3,253 were 1,832 Column, 1,222 Namespace, 362
   Function, 276 Table and smaller groups. A namespace every file re-declares is not an object
   (`contract.SPANNING_KINDS`); `language` scopes it; each row carries `kind`.
2. The mention check, audited: a case-insensitive whole-word `git grep`, kept to files in `language`;
   a schema prefix or `[brackets]` bounds a word, so both are found. 206 of the 1,221 rows are `#temp`
   tables (no PHP mention, correctly); a full-answer grep past its deadline makes every row
   `mention_unchecked`, as designed.
3. `variant_pairs`: the region-twin shape as a config example, placeholders only (`docs/TOOLS.md`).

## Acceptance

- `multi_defined(kind=Function, language=sql)` on the anchor ≈ the survey: 166 = 161 procedures and
  functions + 5 triggers (the same adapter kind).
- The mention-audit numbers reported; fixtures updated (`tests/test_compute_catalogue.py`).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|

Main loop unmeasured.
