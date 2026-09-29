---
id: 343
slug: server-instructions-truncated-at-2048-chars
title: 'Claude Code cuts the server instructions at ~2,048 characters — KEEP_GOING and LIMITS never arrive'
phase: 2
milestone: Adoption
status: todo
depends_on: [300, 200]
---

## Why this exists

[300](../PLAN.md#19-project-context--decision-log) made the server's `instructions` the one routing
channel that needs nothing installed in the consumer repo. On Claude Code that channel is capped, and
`instructions.render` overruns the cap by half, so the model receives only a prefix of it.

## Evidence (anchor repo, 2026-09-29, server at `4c913e5`)

- `instructions.render(config, main.TOOL_NAMES)` on the anchor index: **3,047 characters**. The
  parts measure WHY 300 · LOAD 320 · recognition map 1,780 · KEEP_GOING 175 · LIMITS 412, plus the state
  line.
- The copy that reached the session's system prompt ends mid-line at **character 2,045**:
  `- Write committable onboarding docs (overvi… [truncated]`.
- KEEP_GOING starts at character 2,458 and LIMITS at 2,635, so **neither has ever reached a Claude
  Code session**. LIMITS is the sentence that stops the confident wrong answer ("the graph cannot answer
  an ABSENCE"), and KEEP_GOING answers 300's held-out H4, where a session called the index once and
  then did 29 grep/read calls. Both are exactly the sentences 300 wrote the channel for.
- `tests/test_server_instructions.py` checks content, not length, so nothing catches the overrun.
- The state line is frozen at `initialize`: the session showed `incomplete @ e3f4427` for its whole
  length, long after the build finished. 322's `code-atlas-state` hook covers this, but only where
  someone installed it (see 344).

The cap was observed, not read from Claude Code's docs. AC1 measures it rather than assuming 2,048.

## Scope

1. **Priority order, not document order.** Render in this order: state line → LOAD → one sentence
   that fuses WHY and LIMITS (index for resolved who/what/where, Grep for literal text **and for
   absence**) → KEEP_GOING → the recognition map. Whatever the cap cuts is then the least important
   part.
2. **Shrink the map for this channel.** Keep the full map in the skill (`gen_skill.py`) and put a
   top-N subset here, chosen by the questions the field actually asks (callers, references, read,
   impact, search, outline, include_graph, explain_path). R6.7 still holds: the subset is a *slice* of
   `RECOGNITION_MAP`, never a second copy.
3. **LOAD names the working set.** Today it tells the client to load two tools, so the first
   `find_callers` costs a second ToolSearch round. Name the core set (`get_index_status`,
   `search_symbol`, `read_symbol`, `find_callers`, `find_references`, `impact`) in the one `select:`
   string.

## Acceptance criteria

- **AC1:** The client cap is measured on a running Claude Code (long padded `instructions`, then
  read back where the cut lands) and recorded as a named constant along with the version it was
  measured on.
- **AC2:** The rendered `instructions` fit under that constant on every index state (unindexed,
  behind, current, incomplete) and with `CA_TOOLS` unset. A test pins it.
- **AC3:** A test asserts the order: the LIMITS/absence sentence and KEEP_GOING come before the first
  map line.
- **AC4:** A fresh Claude Code session on the anchor repo shows the whole `instructions` block with
  no `[truncated]` marker.

## Out of scope

- Hosts other than Claude Code. Record their caps if known, but don't design for them here.
- Refreshing the state line mid-session. MCP has no push for `instructions`; that job belongs to the
  hook (322, 344).
