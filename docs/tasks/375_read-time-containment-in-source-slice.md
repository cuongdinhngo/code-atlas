---
id: 375
slug: read-time-containment-in-source-slice
title: 'A file indexed inside the repo and later swapped for a symlink is read through to wherever it points'
phase: 2
milestone: Trust
status: todo
depends_on: [342]
---

## Why this exists

Containment is checked when a file is indexed (`containment.resolves_inside`, `indexer.py`), not
when its source is read back. `source_slice.declaration_slice` and `comment_block`
(`code_atlas/source_slice.py:38-59`) guard only with `path.is_file()`, which follows symlinks.

So a path that was a regular file at index time and is now a link to `/etc/…` or to a sibling
repo is read through by `read_symbol` and by onboarding's docblock read (`module_facts.py:58`,
which feeds the committable map). Worse, the swap changes the hash, so `FreshnessGuard.ensure`
and `poke` re-parse the outside file and store its rows before any read is checked.

Found while comparing context-mode's `isPathInsideProject`, which re-checks the realpath at use
time as well as lexically (context-mode `src/security.ts:686-728`; idea only, ELv2). 342 contained
the index-time walks; its two listed residuals (stub roots, the index directory) are separate.

## Scope

1. Every read in `source_slice` that returns file text resolves the path and refuses one that
   does not resolve inside the project root (`containment.resolves_inside`).
2. A refused read is an honest answer, never empty text signed as the body: the caller reports a
   reason (reuse an existing `NavReason` if one fits; a new one is a design decision).
3. No change to index-time containment. `read_symbol` refuses before it repairs, so it stores no
   outside rows; making `reparse_file` itself refuse (shared by `poke`) is a filed residual.

## Assumptions to prove at design

- The project root is reachable at every `source_slice` call site without a new parameter chain;
  if not, the check moves one level up to the tool.
- The realpath cost per read is negligible next to the file read itself.

## Acceptance criteria

- **AC1:** index a fixture, replace an indexed file with a symlink to a file outside the repo;
  `read_symbol` on a symbol in it returns no outside text and names why.
- **AC2:** a symlink that resolves *inside* the repo still reads as today (byte-identical answer).
- **AC3:** `comment_block` obeys the same check (no docblock read through a link out), and so
  does `generate_onboarding` on the swapped fixture.
