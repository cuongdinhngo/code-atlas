---
id: 365
slug: reads-refuse-while-a-refresh-runs
title: 'While a background refresh runs, read_symbol and find_references answer index_stale, so the agent drops to Grep'
phase: 2
milestone: Adoption
status: todo
depends_on: [356, 357, 274]
---

## Why this exists

356 keeps a full rebuild behind a shadow index. Field feedback from evaran-care/rac-anz shows that
the incremental path still refuses. This is the most frequent reason the agent fell back to Grep
(the 7 PRs below), and it still happens after 356 landed.

- #3136, #3135 (2026-10-07): `find_references` on a table → `index_stale` "during the background
  build".
- #3012: index `behind`, and `read_symbol` on `CareControllerIndex` → `index_stale`.
- #2772, #2840, #2839: `read_symbol` → `index_stale` while a build ran.
- #2906: `read_symbol dbo.WoundsTran` → `subject_ambiguous` mid-rebuild.

## Scope

1. Reproduce first. A commit triggers the post-commit refresh (355), and a read arrives while that
   refresh holds the lock. Record which tool answers what, with the built revision.
2. A read whose subject has not changed since the built revision answers from the built graph,
   labelled the way 257/267 label it (`index_behind`). A drifted subject keeps its current
   repair-or-refuse behaviour. `read_symbol` has no `serve_behind` today, so it gains this path.
3. **Open want-decision, for the maintainer:** PLAN §19 records `serve_behind` as opt-in, "off ⇒
   byte-identical" (257 · 267 · 274). Either (a) answer labelled *only while the refresh lock is
   held*, which keeps that default for every other case, or (b) flip the default, which needs a
   §19 entry that reverses 257. This ticket assumes (a) until the maintainer decides.
4. `get_index_status` says that the served graph is usable while the refresh runs (#2927).

## Acceptance criteria

- **AC1:** A test holds the refresh lock and calls `read_symbol` and `find_references` on an
  unchanged subject. Both answer, labelled, with the built revision.
- **AC2:** The same calls on a subject changed since the build give the answer they give today.
- **AC3:** With no refresh running, every answer is byte-identical.
