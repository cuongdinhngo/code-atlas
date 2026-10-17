---
id: 389
slug: worktree-overlay
title: 'An agent in a worktree gets main''s spans and main''s staleness, and the per-worktree index is too expensive to be the route'
phase: 2
milestone: Trust
status: todo
depends_on: [366, 365, 268]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17, answered by 0.3.0).
366 made a worktree mismatch visible (`ref_mismatch`). The field still loses the answer itself.
5 PRs worked from a `.worktrees/` checkout, against a server rooted at main:

- F1 (2 PRs): `search_symbol` and `read_symbol` gave line numbers from main (a method at 892,
  where the worktree has it at 981). The agent re-read the worktree file with Grep.
- F2 (2 PRs): main was switched to another branch partway through the session. The answers
  followed main, and the agent saw only a metadata change, or nothing at all.
- F3 (1 PR): main had uncommitted changes, so the index was `behind`, and the worktree's queries
  were refused even though the worktree itself was clean (see 388 F2).

366's route is a per-worktree index (`CA_DB_PATH`). On the anchor repo that is a full build, about
550 s and 1.1 GB per worktree. Agents run 3–5 worktrees in parallel, so nobody takes that route.

## Scope

1. Measure whether Claude Code reports MCP `roots` to the server. If it does not, `ref_mismatch`
   never fires there. Record the result in the ticket, and record the client's `ref_check`.
2. **Worktree overlay.** When the caller's root is a worktree of the indexed repo, the files that
   differ between the built commit and the worktree (by `git diff --name-only`, plus untracked
   files) are parsed unstored, as 365's `parsed_unstored` already does. `read_symbol`,
   `file_outline` and `search_symbol` answer with the worktree's bodies and spans, labelled
   `overlay: worktree`. The store is untouched (R1.4).
3. Inbound tools (`find_callers`, `find_references`) answer from the built graph, plus the
   overlay's outbound edges at `HEURISTIC`. They are labelled, never `ok`.
4. If roots are not available, an opt-in `CA_CALLER_ROOT` (or a tool argument) names the
   worktree.

## Acceptance criteria

- **AC1:** Index built on main at A, worktree at B with a method moved 90 lines down:
  `read_symbol` from the worktree returns B's span and body, labelled `overlay: worktree`.
- **AC2:** A new file in the worktree is found by `search_symbol` without a build.
- **AC3:** Main switched to another branch after the build: the worktree's answers do not change
  (the overlay is keyed on the worktree, not on main's HEAD).
- **AC4:** No roots and no `CA_CALLER_ROOT`: answers are byte-identical to today.
