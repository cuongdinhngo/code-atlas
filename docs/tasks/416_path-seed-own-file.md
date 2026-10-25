---
id: 416
slug: path-seed-own-file
title: "A path seed covers its own file — a `Namespace` is no path's seed"
phase: 2
milestone: Coverage
status: done
depends_on: [412]
---

## Why this exists

Consumer bug report, 2026-10-25, against unreleased 412. `impact(paths=["a.php"], records="direct")`
seeded `a.php`'s `\ns` Namespace node too. Every file in `ns` declares it, so `seed_files` (412)
gathered every file declaring `\ns`, and `b.php`'s own records read `direct`. The same seed was
disclosed as `ambiguous_definitions` over both files and counted in `seeds_dropped`. Seeding by qname
was already correct.

## Acceptance

1. `ns\A` in `a.php`, `ns\B` in `b.php`, a record on each class and each file:
   `impact(paths=["a.php"], records="direct")` (and `"radius"`) lists only `a.php`'s and `ns\A`'s.
2. `impact(qnames=["ns\\A"], records="direct")` lists the same records.
3. A path seed carries no `ambiguous_definitions` for its namespace, and drops nothing.

## Resolution

- `resolve_seeds` skips a node whose kind is in `contract.SPANNING_KINDS` (`Namespace`) when it
  expands a path, so `impact` and `impact_modules` both seed only the file's own symbols.
- `impact`'s `seed_files` takes a path-derived seed's file from the path alone; a qname seed still
  contributes every file that defines it.
- An explicit `qnames=["\\ns"]` is unchanged: it was asked for.
- Proving: `tests/test_path_seed_own_file.py` (4 failed on `main` 4d9c9863, 4 pass with the fix).
