---
id: 377
slug: nudge-only-when-the-index-can-answer
title: 'The grep nudge says "ask the index first" while the index is behind, and a subagent never hears it'
phase: 2
milestone: Adoption
status: todo
depends_on: [345]
---

## Why this exists

Two gaps in `code-atlas-nudge` (`code_atlas/hooks/nudge.py`):

- **It speaks when the index cannot answer well.** The only gate is that `graph.db` exists
  (`nudge.py:202`). While a build runs or the index is `behind`, "ask the index first" steers the
  agent to stale answers. This session's own start reported `behind @ a19b9eb` with a build
  running. context-mode drops every redirect to silence when its target is not ready (its
  `hooks/core/routing.mjs:28-32`; idea only, ELv2).
- **Dedupe is per `session_id` only** (`nudge.py:219-226`, read at `:247`). A subagent starts with
  a fresh context, but if its hook payload carries the parent's `session_id`, the parent's nudge
  silences it. context-mode keys on `agent_id` / `agent_type` (its `hooks/pretooluse.mjs:167`).

Blocking or redirecting Grep stays out of scope (345: grep proves absence).

## Scope

1. The nudge is silent unless the index is current — the same judgement `code-atlas-state`
   already makes (reuse it; no second notion of "current").
2. Dedupe key is `(session_id, agent_id)` when the payload has an `agent_id`, else `session_id`
   as today. The state file stays bounded (`KEPT_SESSIONS`).
3. The log line records the agent key, so 300's measurement can tell parent from subagent.

## Assumptions to prove at design

- **UNVERIFIED:** Claude Code's PostToolUse payload inside a subagent carries the parent's
  `session_id` plus an `agent_id`. Capture a real payload first; if it carries neither, Scope 2
  is void and only Scope 1 ships.
- Reading index state costs no more than the `stamped_symbol_shapes()` read already paid.

## Acceptance criteria

- **AC1:** replay 345's AC1 grep while a build lock is held → no output; release it → one line.
- **AC2:** replay it against a `behind` index → no output.
- **AC3:** two payloads, same `session_id`, different `agent_id` → each nudges once; same
  `agent_id` twice → once.
- **AC4:** a payload with no `agent_id` behaves exactly as today.
