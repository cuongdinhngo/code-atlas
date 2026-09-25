---
id: 338
slug: a-caller-row-hides-its-second-call-site
title: "find_callers returns one row per caller with the first line only — a method that calls the subject twice shows one site, and a fix applied there is a half-fix"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [037, 273]
---

## Why this exists (field retro, 2026-09-25)

A session needed to add a call beside every call to a context-setup method. `find_callers` returned
2 production callers. Grep showed one of them calls the subject **twice** (the main path and a
fallback), and the retro *"nearly patched only one site"*.

Probed on `main` (`927aeb9`): `init()` calls `ctx()` at lines 7 and 9. Both `CALLS` edges are
stored; `find_callers \App\Db::ctx` returns one row, `line: 7`.

One row per caller is right: 273 made the hit set the distinct callers so that
`production_count + test_count == total_count`. What is lost is the other lines, not the row.

## Goal

A caller row names every line it calls the subject from, without changing what is counted.

## Scope / Deliverables

1. **`call_lines`** on a depth-1 row whose caller has two or more edges to the subject: the sorted
   lines. Omitted at one (061). `line` stays the first, so existing readers are unaffected.
2. **`include_source`** quotes each listed line (037's `annotate` already reads per file once).

## Constraints

- **273** — `total_count` and the partition still count callers; the invariant test stays green.
- **Bounded** — the lines come from the edges already fetched for the page, not a query per row.

## Acceptance criteria

- **AC1** The probe above → the `init` row carries `call_lines: [7, 9]`; red on today's code.
- **AC2** A caller with one call site → byte-identical row.
- **AC3** 273's invariant test passes unchanged.

## References
`code_atlas/store.py:1794-1830` (`edges_by_target`, `distinct_sources`);
`code_atlas/tools/call_site.py:17-39`; tickets 037, 273.
