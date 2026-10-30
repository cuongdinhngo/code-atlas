---
id: 428
slug: tool-surface-manifest
title: "The tool surface is pinned — every tool declares honest annotations and closed schemas, and a committed manifest makes any change a reviewed diff"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

The 24 tools declare no MCP `annotations`, so a client cannot tell the read-only queries from the
two tools that write (`build_or_update_index`, `generate_onboarding`). Input schemas are whatever
FastMCP generates, unaudited. Nothing pins tool names, descriptions or schemas, so a changed
description — the vector a "rug pull" uses — would ship as an unreviewed side effect. Error answers
and stdout discipline are not tested for what they leak.

## Acceptance

1. **Annotations:** every query tool `readOnlyHint: true`, `openWorldHint: false`; the two writers
   `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: true`. A test reads them from
   the live server.
2. **Closed schemas:** `additionalProperties: false` on every input schema; closed domains are
   enums; free strings are length-bounded. A test walks every schema.
3. **Manifest:** `tests/fixtures/tool_manifest.json` (names, descriptions, schemas, annotations)
   generated from the live server by a script that prints the diff; a test fails on drift; a change
   needs a CHANGELOG line (R9 rule from 423). Seen failing on an edited description.
4. **Error hygiene:** a tool error is an `isError` result with no traceback and no host path
   outside the repo (fixtures: a bad argument, an unreadable index).
5. **stdout is MCP only:** a test starts the server over stdio with an adapter that prints to
   stdout and sees only well-formed JSON-RPC frames.

## Call sites

`code_atlas/main.py` (tool registration, `TOOL_NAMES`), `code_atlas/tools/*`, new
`scripts/gen_tool_manifest.py`, `tests/fixtures/tool_manifest.json`, `docs/TOOLS.md`;
standard rows SEC-MCP-02..05, 07.
