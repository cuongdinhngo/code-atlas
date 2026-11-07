---
id: 439
slug: verify-refs-patches-and-surfaces
title: "`verify_refs`: ready-to-apply patches, the MCP tool, and a count-only SessionStart line"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [438, 434]
---

## Why this exists

Roadmap R1.4–R1.5 (0.11). The study 438 cites shows a warning alone does not change what an agent
does — it noticed the conflict and followed the file anyway. **Success means the file gets
corrected**, so every finding carries the cheapest correction: a successor, and where it is
deterministic, a patch. And an agent only uses what it can reach: an MCP tool, plus one line at
session start that names the instruction-file count first.

## Scope

1. **Patches, not edits.** For a `moved` row with exactly one successor, emit a unified diff that
   replaces the reference string in place; nothing else on the line changes. Grouped per file and per
   priority class, so all instruction-file rows apply in one step. `gone` / `never_existed` /
   `ambiguous` rows get a hint, no patch. code-atlas never applies one.
2. **CLI:** `--format patch` on 438's `--verify-refs`.
3. **MCP tool `verify_refs`:** globs, class filter, state filter, `format`, limit. Payload: per-file
   summary, capped rows, `total_count`, `truncated`, `untrusted_fields`; reference strings only (429).
   Read-only annotations, closed input schema (428); the description stays within 434's budget.
   Adding a tool moves the count pinned by tests (`main.TOOL_NAMES`, BACKLOG's tool count).
4. **SessionStart line**, opt-in and count-only, inside `hooks/signal.py`'s 150-token budget, the
   instruction class first, e.g. `code-atlas: 3 refs in instruction files no longer resolve (2 moved —
   patch ready); 41 in other docs.` `archive` rows never count. Nothing runs in the edit loop.

## Acceptance

1. Fixture: each single-successor `moved` row yields a patch that `git apply --check` accepts and that
   changes only the reference string; a two-successor row yields none.
2. The MCP payload of a doc holding instruction-like text carries reference strings only (429).
3. The SessionStart line never exceeds the signal budget, reports `unknown` separately from `ok`, and
   is absent unless opted in.
4. The tool surface test and 434's description budget stay green with the new tool counted.
