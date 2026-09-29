---
id: 343
slug: server-instructions-truncated-at-2048-chars
title: 'Claude Code cuts the server instructions at ~2,048 characters — KEEP_GOING and LIMITS never arrive'
phase: 2
milestone: Adoption
status: todo
depends_on: [300]
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
- 200 is `blocked` on its own measurement; this fix has its own evidence and does not wait on it.

The cap was observed, not read from Claude Code's docs. AC1 measures it rather than assuming 2,048.

## Scope

1. **Priority order, not document order.** Render in this order: state line → LOAD → one sentence
   that fuses WHY and LIMITS (index for resolved who/what/where, Grep for literal text **and for
   absence**) → KEEP_GOING → the recognition map. Whatever the cap cuts is then the least important
   part. The fusion drops LIMITS' first half (read a non-ok `reason` and the coverage fields); that
   half is claimed to ride every tool result already (`tools/coverage.py`, `tools/collection.py`);
   AC3c proves that before the sentence is dropped, and the module docstring says where it went.
2. **Shrink the map for this channel.** Keep the full map in the skill (`gen_skill.py`) and put a
   subset here: the rows flagged `core` on `RECOGNITION_MAP` itself (callers, references, read,
   impact, search, outline, include_graph, explain_path). R6.7 still holds: the subset is a filter
   over that tuple, never a second copy. Until 344 installs the skill, a session without it loses the
   unflagged rows — accepted, since the `core` rows are the questions the field asks.
3. **LOAD names the working set.** Today it tells the client to load two tools, so the first
   `find_callers` costs a second ToolSearch round. Name the core set (`get_index_status`,
   `search_symbol`, `read_symbol`, `find_callers`, `find_references`, `impact`) in the one `select:`
   string, filtered by the registered `names` exactly as the map is: a `CA_TOOLS` that drops a tool
   drops it from LOAD too, since a name the session cannot call is worse than none.

## Acceptance criteria

- **AC1:** The client cap is measured on a running Claude Code (long padded `instructions`, then
  read back where the cut lands) and recorded as a named constant along with the version it was
  measured on.
- **AC2:** The rendered `instructions` fit under that constant minus a 200-character margin (the
  state line varies with sha and counts) on every index state (unindexed, behind, current,
  incomplete) and with `CA_TOOLS` unset. A test pins it.
- **AC3:** A test asserts the order: the LIMITS/absence sentence and KEEP_GOING come before the first
  map line.
- **AC3b:** A test asserts every map line in `instructions` is a `core` row of `RECOGNITION_MAP`.
- **AC3c:** A test asserts every tool result carries `reason` and the coverage fields that LIMITS'
  dropped half names; if any tool lacks them, that half stays in `instructions`.
- **AC3d:** With `CA_TOOLS` cutting a core tool, a test asserts LOAD's `select:` string omits it.
- **AC4:** A fresh Claude Code session on the anchor repo shows the whole `instructions` block with
  no `[truncated]` marker, on the Claude Code version AC1 recorded.

## Out of scope

- Hosts other than Claude Code. Record their caps if known, but don't design for them here.
- Refreshing the state line mid-session. MCP has no push for `instructions`; that job belongs to the
  hook (322, 344).
