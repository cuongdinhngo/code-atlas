---
id: 294
slug: a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured
title: '279 made an unmodelled resolution strategy visible so `find_orphans` cannot answer a confident zero on a repo whose wiring the graph does not model — but the detection lives only in `adapters/php/src/Visitor.php`, so a TypeScript repo using dynamic `import()` or a computed `require()` produces no stamp, and the same tool returns the same bare orphan population 279 was filed to refuse'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [279, 019, 255]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

279's core half is language-agnostic and shipped that way: `File.extra.unmodelled_resolution` is
unioned per language (`store.py:1252`), stamped into `meta` (`indexer.py:1273`), and read by
`find_orphans` to answer `status=resolution_unmodelled` instead of a population
(`tools/find_orphans.py:82-95`). Nothing in it knows what PHP is.

The detection half is PHP-only. `markUnmodelledResolution` exists at
`adapters/php/src/Visitor.php:1341` and nowhere else — grep over `adapters/` returns one hit. So the
honesty 279 bought applies to one of the four adapters, and a TypeScript repo gets the pre-279
answer: a confident orphan list built on an import graph that is missing every edge the code
resolves at runtime.

The TypeScript adapter already *sees* the construct and already declines to invent an edge for it —
`const x = require(...)` is skipped as an import binding (`adapters/typescript/src/parse.js:160`) and
a call it cannot name becomes `(dynamic)` / `DYNAMIC` (`parse.js:508-509`). That is the correct
per-edge answer and it is not the file-level one: an edge marked `DYNAMIC` says *this call* is
unresolved, while the stamp says *this file resolves things the graph does not model*, which is the
claim `find_orphans` needs before it is allowed to say "nothing reaches this".

## Scope / Deliverables

- **A strategy token in `contract.py`** beside `RESOLUTION_AUTOLOAD`, naming runtime module
  resolution (`dynamic_import`), with the same one-line comment discipline.
- **Detection in the TypeScript adapter**, from the language standard only (R2): a dynamic `import()`
  whose specifier is not a string literal, and a CommonJS `require()` whose argument is not a string
  literal. No bundler API, no framework convention, no repo path list.
- **The stamp on the File node**, same shape as PHP's — a sorted, de-duplicated list under
  `extra.unmodelled_resolution`, merged into `extra` rather than rewriting it.
- **A gate-1 fixture** in the adapter's own fixtures, and the gate-2 registry row updated if the
  handshake changes.

## Constraints

- R5.6: the stamp says *unmeasured*, never *these modules are reachable*. No inferred `IMPORTS` edge.
- R1.1: no core change beyond the token constant — `find_orphans` already reads the stamp.
- 061: a repo with no dynamic resolution pays nothing and every payload stays byte-identical.
- A literal specifier is still resolved as today; only the non-literal case stamps.

## Acceptance criteria

- A TS fixture with `await import(name)` where `name` is a variable produces
  `unmodelled_resolution: ["dynamic_import"]` on its File node; a fixture with only literal
  specifiers produces no key at all.
- `find_orphans` over the stamped fixture answers `status=resolution_unmodelled` with the route, and
  over the unstamped one is byte-identical to today.
- The strategy token is emitted by the adapter and never constructed in the core.

## References
`adapters/typescript/src/parse.js:160`, `:508-509`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[019](019_typescript-adapter.md).
