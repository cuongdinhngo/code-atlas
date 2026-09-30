---
id: 355
slug: silent-refresh-failures
title: 'A commit never refreshes the index, and a refused refresh never reaches the state line'
phase: 2
milestone: Adoption
status: todo
depends_on: [053, 322, 344]
---

## Why this exists

Field retro, 2026-09-30: "a broken setup looks exactly like a working one." Two gaps are ours.

1. **Hooks cover pull and checkout only.** `contrib/git/` ships `post-merge` and `post-checkout`.
   A local commit, amend or rebase moves HEAD with no refresh, so the anchor project wrote its own
   `post-commit` / `post-rewrite`. Every adopter would do the same.
2. **A refusal is computed, then dropped.** `get_index_status` sets `coverage_loss_pending`
   (`code_atlas/tools/get_index_status.py:257`), but the summary never reads it. So the MCP
   `instructions` line and `code-atlas-state` (silent when `current`) say nothing, while every
   refresh is refused. The refusal reaches only the hook's stderr (344).

## Scope

1. Ship `contrib/git/post-commit` and `post-rewrite`, same shape as the existing two: background,
   stderr kept, exit 0. Update `contrib/git/README.md`'s install line.
2. The one-sentence summary names a pending coverage loss and its route, lifted (316, R6.7); the
   state hook speaks for it even when the index is `current` (as 347 did for the contract era).
3. Nothing auto-rebuilds (202).

## Acceptance criteria

- **AC1:** With the hooks installed, `git commit` and `git commit --amend` trigger one background
  `code-atlas-refresh`; a test runs each hook script against a temp repo.
- **AC2:** On an index where `coverage_loss_pending` is set, the summary names it and its route,
  and `code-atlas-state` prints it on `SessionStart` at an unmoved HEAD.
- **AC3:** The server `instructions` still fit `CLIENT_CAP` (343).
- **AC4:** An index with no pending loss has a byte-identical summary.
