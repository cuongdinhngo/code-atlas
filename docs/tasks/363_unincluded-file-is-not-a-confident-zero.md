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

## Scope

1. A positive zero applies when two things hold:
   - every include in the index whose basename matches the subject resolves to a *different* file;
   - no include of that basename is unresolved.

   In that case `imported_by` is a positive zero (`no_matches`, `authoritative: true`), and the
   answer names the resolved alternatives.
2. When any same-basename include is unresolved or dynamic, the answer stays non-`ok` and lists
   those sites as candidates.

## Acceptance criteria

- **AC1:** Two files share a basename, and one is included by a path that resolves to it. The other
  answers a confident zero that names the included file.
- **AC2:** Add one dynamic include of that basename: the answer reverts to non-`ok` and lists it.
- **AC3:** Answers for files with at least one includer are unchanged.
