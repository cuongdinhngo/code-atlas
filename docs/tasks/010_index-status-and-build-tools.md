---
id: 010
slug: index-status-and-build-tools
title: MCP server + status/build tools (M1)
phase: 1
milestone: M1
status: todo
depends_on: [009]
---

## Goal
Expose the index over MCP; first two tools (§12).

## Scope / Deliverables
- `main.py`: FastMCP server (stdio) + entry point; tool allow-list via `CA_TOOLS`.
- `get_index_status` (stats, last_commit, staleness, `next_tool_suggestions`; ~100 tok).
- `build_or_update_index` (`full=false`) → counts, timing.
- Every tool takes `detail_level ∈ {minimal, standard}`.

## Acceptance criteria
- Server starts and lists tools via an MCP client (e.g. Claude Code `.mcp.json`).
- `get_index_status` on a built repo returns accurate stats; `build_or_update_index` triggers full build.

## References
Plan §12, §15 (M1).
