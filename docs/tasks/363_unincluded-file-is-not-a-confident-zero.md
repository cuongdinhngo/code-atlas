---
id: 363
slug: unincluded-file-is-not-a-confident-zero
title: 'A file nothing includes answers relationship_not_modelled, so "this copy is unused" still needs Grep'
phase: 2
milestone: Coverage
status: todo
depends_on: [353]
---

## Why this exists

This comes from field feedback on evaran-care/rac-anz, written after 353 landed (2026-10-06).

- #3079: `include_graph` named `tabs.php:1650` as the only includer of one `financial_screen.php`.
  On the unused copy, it answered `relationship_not_modelled`, not zero.
- #3077: the same answer on `Aus/Financial/ResidentFinancial/View/financial_screen.php`.
- #3103: `include_graph` on a vendored `dompdfnew/autoload.inc.php` answered
  `relationship_not_modelled`. Proving "this `vendor/` tree is unreachable" fell back to Grep over
  four roots.

`relationship_not_modelled` fires only when at least one *unlinked* `INCLUDES` row contains the
basename as a substring (`include_graph.py`, `store.count_unlinked_includes_mentioning`). With no
such row the answer is already `no_matches`. So in each case above, some unlinked row matched.

## Scope

1. Reproduce first: on #3079/#3077/#3103, list the unlinked rows that matched and classify them
   (substring false positive such as `old_financial_screen.php`, a concatenation whose literal tail
   rules this path out, or a truly dynamic include). For #3103, first confirm that the subject was
   indexed at all, since `vendor/` is excluded by default.
2. Count only the unlinked rows that *could* name the subject: the basename matches at a path
   boundary, and any literal path tail is compatible with the subject's path. If none remain,
   `imported_by` is a positive zero (`no_matches`, `authoritative: true`), and the answer names the
   resolved same-basename alternatives.
3. When a compatible unlinked or dynamic include remains, the answer stays non-`ok` and lists
   those sites as candidates.

## Acceptance criteria

- **AC1:** Two files share a basename, and one is included by a path that resolves to it. The other
  answers a confident zero that names the included file.
- **AC2:** Add one dynamic include of that basename: the answer reverts to non-`ok` and lists it.
  An unlinked include of `old_<basename>` does not revert it.
- **AC3:** Answers for files with at least one includer are unchanged.
