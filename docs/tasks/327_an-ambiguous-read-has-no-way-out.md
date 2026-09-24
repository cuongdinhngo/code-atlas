---
id: 327
slug: an-ambiguous-read-has-no-way-out
title: "read_symbol refuses an ambiguous qname and routes to search_symbol, which returns the same qname — four of five field sessions hit the dead end and sliced the file with sed"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [070, 078, 315, 049]
---

## Why this exists (field retros, 2026-09-23/24 — four batches)

078 made `read_symbol` refuse a qname with several definitions: `reason=subject_ambiguous`,
`ambiguous_definitions` (file + line), no body, `try_instead: search_symbol`
(`read_symbol.py:584-605`). Its re-ask path was *"use `file_outline` / `search_symbol` on a site from
`ambiguous_definitions`"* (078, design table row 5). **That path returns the same qname**, so the
re-ask refuses again. The field has now measured it:

| Batch | Subject shape | Fallback |
|---|---|---|
| FIELD-1621/1615 | a same-named global function in four page files (two regions × two trees) | `sed -n` |
| FIELD-1062/1634 | a table: one `CREATE`, five migration `ALTER`s, one function mentioning it | `grep` |
| FIELD-1426 | a stored procedure: canonical tree + a migration redefinition | `sed` |
| FIELD-1624/1626/1636 | a procedure in a snapshot + two migrations | `sed` |

Every session then did the thing the project rules call the wrong-tool tell. One also found
`line_start` alone refused (`read_symbol.py:137`), and `line_start/line_end` apply inside a resolved
symbol, not to choose between definitions.

**This revisits 078's rejected option 3** (`file=`), rejected for *"largest surface + 049 risk"*.
Both reasons are answerable now: the surface is one tool, not every single-subject tool; and 049's
concern — a second, differently-shaped filter vocabulary — is met by reusing `path_prefix`, which
315 shipped with fixed semantics on `search_symbol` and `find_references`.

## Goal

A caller holding `ambiguous_definitions` can read exactly one of them in one re-ask.

## Scope / Deliverables

1. **`read_symbol(qname, path_prefix=…)`** — filters the definition rows before the ambiguity test;
   one survivor answers with its body, two or more still refuse with the narrowed list.
2. **The refusal routes to itself with the argument named** — `try_instead` names `read_symbol`
   with `path_prefix` (the progress route, R5.4), not `search_symbol`.
3. **070 stands.** This picks a *definition to read*; it adds no per-definition edge scoping.

## Constraints

- **061** — a unique qname, and every call without `path_prefix`, is byte-identical.
- **R6.7** — reuse 315's `path_prefix` validation (`nav_result.py:150`), not a second parser.
- **R1.1** — no language branch; "canonical vs migration" ranking is **not** in scope (it would
  encode a repo's layout, R2.2).
- **R3** — a tool parameter, not contract vocabulary; no `contract_version` bump.

## Acceptance criteria

- **AC1** Fixture: one qname in two files; `path_prefix` naming one returns that body and its site.
- **AC2** A `path_prefix` matching both still refuses, listing both.
- **AC3** A `path_prefix` matching neither answers `no_such_symbol` naming the filter, not a body.
- **AC4** The refusal's `try_instead` names `read_symbol`; regression test for the unique case.
- **AC5** The agent brief teaches the argument in the same change (313's gate).

## Out of scope

- The same selector on `find_callers` / `impact` — do it on a sighting there (R1.2).
- Picking "the latest migration" automatically — a repo convention, not a language fact.

## References
`code_atlas/tools/read_symbol.py:86,137,584-605`; `code_atlas/tools/nav_result.py:150`;
tickets 049, 070, 078 (rejected option 3), 313, 315.
