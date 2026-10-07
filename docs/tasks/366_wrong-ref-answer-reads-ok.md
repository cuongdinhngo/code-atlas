---
id: 366
slug: wrong-ref-answer-reads-ok
title: 'An answer about a ref other than HEAD reads reason ok, so an agent in a worktree trusts main'
phase: 2
milestone: Adoption
status: todo
depends_on: [354, 360]
---

## Why this exists

This comes from field feedback on evaran-care/rac-anz.

- #3102: after a branch switch, `find_callers` answered for an `answered_about_ref` on another
  branch, and one hit came back `source_stale`. Only a metadata field showed the mismatch.
- #3085, #2758, #2748: a second developer did not use code-atlas at all, because "the index in a
  worktree answers about `main`" while still reporting `reason: ok`. The anchor project's agent
  guide lists this as a standing trap.

## Scope

1. When `answered_about_ref`, or the HEAD of the index root, differs from the caller's working-tree
   HEAD, the answer's `reason` says so (`ref_mismatch`). The answer carries both revisions and is
   not `ok`.
2. The `get_index_status` summary names the mismatch and the route to fix it: a per-worktree index,
   or a refresh.

## Acceptance criteria

- **AC1:** An index is built at commit A and queried from a worktree at commit B. Every navigation
  tool answers `reason: ref_mismatch` with both revisions.
- **AC2:** When HEAD matches, answers are byte-identical.
- **AC3:** The server `instructions` still fit `CLIENT_CAP` (343).
