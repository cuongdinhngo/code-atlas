---
id: 155
slug: ts-tsconfig-paths-and-export-star
title: An aliased specifier and an `export *` both resolve to nothing — the two module shapes 019 left bare
phase: 2
milestone: M7
status: todo
depends_on: [019]
---

## Why this exists

Two module shapes resolve to nothing today, both documented as open in
`adapters/typescript/README.md`:

1. **tsconfig `paths`/`baseUrl`.** `imports.js` handles a specifier starting with `.` and returns
   `null` otherwise, so `@app/models` — the alias style most TS monorepos use — never names a file and
   every edge through it stays bare. In a repo built on aliases that is *most* of the import graph.
2. **`export * from "./m"`.** `parse.js` `emitReExport` emits the module dependency (`IMPORTS`) and
   nothing per name, because a file-at-a-time parse cannot enumerate what `./m` exports. A barrel
   built from `export *` therefore stops resolving where a named re-export would have carried through
   (019 shipped the named half as `ALIASES`).

## Scope / Deliverables

- Read `tsconfig.json` `baseUrl`/`paths` — the nearest one up the tree, `extends` followed — and
  resolve an aliased specifier through it to the same repo-relative file a relative specifier gets.
  The file is read from disk by the adapter, so the core stays language-blind (R1.1) and the config is
  the *language's* standard, not any repo's names (R2).
- Cost note: this is per-file work in a fanned-out worker (019's finding #5). Cache per process, and
  say what the lookup costs on a pinned sample rather than assuming it is free.
- `export *`: state the honest answer. Either the core's existing `ALIASES` chain can carry a
  whole-module re-export, or it cannot be resolved file-at-a-time and the `IMPORTS`-only behaviour is
  correct and gets documented as a known limit — **decided in writing**, not left as a silent gap.
- Fixtures: an alias-resolved import, an `extends`-chained tsconfig, and a barrel of both kinds.

## Acceptance criteria

1. An `@alias/...` import produces an edge whose `target_raw` names the defining file, and the proving
   test drives the real indexer+resolver to `RESOLVED` (the shape `test_ts_import_resolution.py` uses).
2. A missing/malformed `tsconfig.json` degrades to bare, never crashes the parse — soft-fail, one file
   at a time (§4.1).
3. The `export *` verdict is written in the adapter README, with the reason.
4. Red run recorded per guard (R6.5); no `contract_version` bump (R3).

## Out of scope

- Node `node_modules` resolution / package `exports` maps. An external package is out of the indexed
  tree by definition; a bare target is the right answer there.
- Path aliases from bundler configs (webpack, vite). Not the language standard (R2).

## References

`adapters/typescript/src/imports.js`, `src/parse.js` `emitReExport`, `README.md` *Still out of scope*;
ENGINEERING_RULES R1.1, R2, R3, R6.5; PLAN §4.1, §4.4; task 019.
