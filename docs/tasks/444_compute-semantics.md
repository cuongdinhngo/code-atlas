---
id: 444
slug: compute-semantics
title: "compute: multi_defined is one object per kind and qname; the mention check audited"
phase: 2
milestone: "0.11 Verify & Compute"
status: done
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
   a schema prefix or `[brackets]` bounds a word, so both are found. Of 10 seeded "strong" non-temp
   rows re-grepped on the anchor, 4 had no PHP text at all and 6 sat in PHP only inside a longer name
   — so the check now counts a substring too (`whole_word=False`): a strong candidate has no trace at
   all. 206 of the 1,221 rows are `#temp` tables (no PHP mention, correctly); a grep past its
   deadline makes rows `mention_unchecked`, as designed.
3. `variant_pairs`: the region-twin shape as a config example, placeholders only (`docs/TOOLS.md`).

## Acceptance

- `multi_defined(kind=Function, language=sql)` on the anchor ≈ the survey: 166 = 161 procedures and
  functions + 5 triggers (the same adapter kind).
- The mention-audit numbers reported; fixtures updated (`tests/test_compute_catalogue.py`).

## Result (anchor scratch copy, counts only)

- `multi_defined`: 3,253 → 2,582 (no namespaces); `kind=Function, language=sql` 166.
- Mention audit: 10 seeded strong non-temp rows — 4 no PHP text, 6 PHP substring only → substring
  counts now. `unreferenced_objects(Function, php)` spent its 3 s grep deadline on a 1-char name
  (190 MB of matches): names under 3 chars stay out, the grep keeps to the language's suffixes —
  3.5 s all unchecked → 1.8 s with evidence (16 strong, 33 mentioned, 1 unchecked on the page).
- 10 answers checked against direct counts on the copy: 10/10 match, caveat on each.

## Cost ledger

Covered by 443's one review (90,836). Main loop unmeasured.

Merged in #170 as `83da5186`; released as `v0.11.0`.
