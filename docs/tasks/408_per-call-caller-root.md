---
id: 408
slug: per-call-caller-root
title: "A subagent in a session-spawned worktree gets answers about `main` with `reason: ok` — a per-call `caller_root`"
phase: 2
milestone: Freshness
status: todo
depends_on: [389, 366]
---

## Why this exists

Issue [#100](https://github.com/cuongdinhngo/code-atlas/issues/100), 2026-10-24. On the anchor, about
26 of 68 PRs in 19–23 Oct report answers about the main checkout from an agent working in a worktree
spawned inside the session (`isolation: worktree`, `parallel-tasks`): `no_such_symbol` on a method
only the worktree holds, line numbers off by ~75, new classes invisible. The largest single complaint.

**Confirmed in code (2026-10-24):** `ref_check.caller_checkout` reads `CALLER_ROOTS` (per MCP session)
or `CA_CALLER_ROOT` (per server). A subagent shares the parent's server and roots, which name the
main checkout, so 389's overlay never fires and 366's `ref_mismatch` cannot either — the roots'
checkout *is* the index root. Wrong and confident. Unconfirmed: the version behind the field reports.

## Scope

1. An optional `caller_root` argument on the tools 389 overlays (`read_symbol`, `file_outline`,
   `search_symbol`, `find_callers`, `find_references`). It names a checkout of the indexed repo and
   takes precedence over roots and `CA_CALLER_ROOT` for that call only.
2. Validated exactly as a root is (`ref_check.other_checkout`): another checkout of the same repo,
   otherwise refused with a reason — never a silent fall-back to the session's root.
3. The skill (`contrib/claude-code/plugin/`) and the agent brief tell an agent working in a worktree
   to pass its own top-level path.

Out of scope: per-worktree indexes (`CA_DB_PATH`, already in `docs/runbooks/parallel-agents.md`);
the optional "subject file differs in a known worktree" caveat.

## Acceptance criteria

- AC1: With session roots on the main checkout, `caller_root=<worktree>` answers a symbol that exists
  only in the worktree, labelled with 389's overlay field.
- AC2: A `caller_root` outside the repo, or a non-checkout path, is refused with a named reason.
- AC3: Omitting `caller_root` leaves every answer byte-identical to today (roots, then env).
- AC4: The tool-docstring token budget still holds; the five tools' schemas name the argument.
