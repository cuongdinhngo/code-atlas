---
id: 453
slug: code-atlas-setup
title: "`code-atlas-setup` installs the freshness hooks, and an index without them reports `unguarded`"
phase: 2
milestone: Freshness
status: todo
depends_on: [452]
---

## Why this exists

Epic 451. Today `contrib/git/README.md` asks each user to copy four scripts into `.git/hooks`, and the
Claude Code hooks come only with the plugin; an anchor that registers the server by hand (the PHP anchor)
wrote its own. Nothing tells an agent or a human that the hooks are missing.

## Scope

1. A console script `code-atlas-setup`, idempotent, run once after install:
   - installs the git hooks (`post-merge`, `post-checkout`, `post-commit`, `post-rewrite`) honouring
     `core.hooksPath`; appends to an existing hook inside a marked block, never overwrites;
   - when the plugin is not enabled, writes the Claude Code hooks into `.claude/settings.json`
     (merge, marked) calling the console scripts — no bash copied into the repo;
   - writes the adapter file of 452;
   - prints what it changed; `--dry-run` prints without changing; `--check` exits non-zero when
     any part is missing or from an older version.
2. Setup records its version under `.code-atlas/`. `get_index_status` and the SessionStart state
   line report `freshness: unguarded` (with `run code-atlas-setup`) when the hooks are missing
   or older than the install.
3. `code-atlas-build` on a repo with no index runs the setup first; `--no-hooks` skips it and is
   recorded, so `unguarded` is not repeated for a choice already made.
4. `/mango:doctor`-style output: one line per part, ✅ / ❌ and the fix.

## Acceptance criteria

- **AC1:** on a temp repo, `code-atlas-setup` then `git commit` triggers one refresh; a second
  setup run changes no byte.
- **AC2:** an existing `post-merge` keeps its own lines and gains the marked block.
- **AC3:** with `core.hooksPath` set, the hooks land there.
- **AC4:** removing one hook makes `--check` exit non-zero and `get_index_status` say `unguarded`.
- **AC5:** the server `instructions` still fit `CLIENT_CAP` (343).
