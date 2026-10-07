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

This comes from the anchor project's field retro.

- F1 (1 PR): after a branch switch, `find_callers` answered for an `answered_about_ref` on another
  branch, and one hit came back `source_stale`. Only a metadata field showed the mismatch.
- F2 (3 PRs): a second developer did not use code-atlas at all, because "the index in a
  worktree answers about `main`" while still reporting `reason: ok`. The anchor project's agent
  guide lists this as a standing trap.

**Prior art.** 268 (`worktree_guard.py`) already refuses with `index_root_mismatch`, but only when
the *server's* root is a linked worktree whose `CA_DB_PATH` points outside it. The field case is a
server rooted at main while the agent works in a worktree. A stdio server's root is fixed at launch,
so it cannot see the caller's checkout unless the client reports it: the MCP `roots` capability is
the only route.

F1 is a different case: a branch switch in the same tree. Per-subject staleness answers `ok`
for a subject unchanged between the two revisions, by 257's design. Reproduce it before deciding
whether it is a defect.

## Scope

1. When the client reports MCP `roots` and the HEAD of the index root differs from the HEAD of
   the caller's root, the answer's `reason` says so (`ref_mismatch`). The answer carries both
   revisions and is not `ok`. A client that reports no roots gets today's answer, and
   `get_index_status` says that the check could not run.
2. The `get_index_status` summary names the mismatch and the route to fix it: a per-worktree index,
   or a refresh.

## Acceptance criteria

- **AC1:** An index is built at commit A and queried from a worktree at commit B. Every navigation
  tool answers `reason: ref_mismatch` with both revisions.
- **AC2:** When HEAD matches, or the client reports no roots, answers are byte-identical.
- **AC3:** The server `instructions` still fit `CLIENT_CAP` (343).
