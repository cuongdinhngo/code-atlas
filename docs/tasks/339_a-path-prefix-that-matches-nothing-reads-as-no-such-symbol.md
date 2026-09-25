---
id: 339
slug: a-path-prefix-that-matches-nothing-reads-as-no-such-symbol
title: "read_symbol with a path_prefix that excludes every definition answers no_such_symbol — the symbol exists; search_symbol says path_excluded for the same miss"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [315, 327]
---

## Why this exists (field retro, 2026-09-25)

`path_prefix` is the way out of `subject_ambiguous` for a proc declared in two files (327). A
session passed `path_prefix=database/migrations/V136` — a file-name prefix — and got
`no_such_symbol`. The retro: *"it looks like the symbol doesn't exist, which is the worst failure
for an agent."*

`path_prefix` matches whole directories by design (`is_under_path_prefix`, `nav_result.py:154-157`),
so the miss is correct. The **reason** is not: `_apply_path_prefix` (`read_symbol.py:622-640`)
returns `no_such_symbol` for a symbol that is indexed, while `search_symbol` answers the same miss
with `path_excluded` and the files the symbol lives in (`search_symbol.py:461,523`).

## Goal

A symbol excluded by the filter says so and names where it is.

## Scope / Deliverables

1. `_apply_path_prefix` answers `reason: path_excluded` with the definition sites, reusing
   `search_symbol`'s shape (R6.7).

## Constraints

- **315 / 327** — prefix semantics unchanged; whole directories only.
- **R6.7** — one `path_excluded` payload shape across both tools.

## Acceptance criteria

- **AC1** `read_symbol dbo.Gen path_prefix=db/migrations/V1` (file `db/migrations/V1__gen.sql`) →
  `path_excluded` listing that file; red on today's code.
- **AC2** A qname that does not exist, with any prefix → `no_such_symbol` (regression).

## References
`code_atlas/tools/read_symbol.py:622-640`; `code_atlas/tools/search_symbol.py:461,523,576`;
`code_atlas/tools/nav_result.py:100,154-157`; tickets 315, 327.
