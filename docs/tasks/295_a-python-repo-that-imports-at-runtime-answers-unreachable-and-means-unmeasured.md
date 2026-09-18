---
id: 295
slug: a-python-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured
title: '`importlib.import_module` and `__import__` are the stdlib way a Python codebase loads a module the source never names, and the adapter emits `IMPORTS` from `import` / `from` statements only — so the resolution the graph does not model leaves no trace, no `unmodelled_resolution` stamp is set, and `find_orphans` returns the confident orphan population 279 taught it to refuse'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [279, 020, 255, 299]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

**Blocked on [299](299_a-confident-hit-list-does-not-say-the-index-never-saw-this-extension.md).**
This stamp cannot see an extension the adapter never parsed. Run 299 first.

Same gap as [294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md),
different language standard. 279 shipped the core mechanism language-agnostically — the per-language
union in `store.py:1252`, the `meta` stamp in `indexer.py:1273`, the `resolution_unmodelled` status in
`tools/find_orphans.py:82-95` — and the detection only in `adapters/php/src/Visitor.php:1341`.

The Python adapter emits `IMPORTS` from exactly three sites, all of them `ast.Import` /
`ast.ImportFrom` (`adapters/python/src/parse.py:645`, `:667`, `:672`). `importlib.import_module(name)`
and `__import__(name)` are ordinary calls: they get a `CALLS` edge, `(dynamic)` where the callee
cannot be named (`parse.py:740`), and no import relation at all. That is correct — the adapter must
not invent the edge — and it is invisible, which is the half 279 exists to fix.

The population this matters for is not exotic: plugin registries, entry-point loading, settings
modules named by string, and any `importlib` call in a bootstrap path. On such a repo every
"nothing reaches this" answer is a claim about an import graph that is missing by construction.

## Scope / Deliverables

- **A strategy token in `contract.py`** naming runtime module resolution for Python (reuse
  `dynamic_import` from [294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md)
  if the shape matches; a second token only if the two are genuinely different claims).
- **Detection in the Python adapter**, stdlib only (R2): `importlib.import_module`, `__import__`, and
  `importlib.util.spec_from_file_location`. Not a framework list, not a settings-module convention.
- **The stamp on the File node** — sorted, de-duplicated, merged into `extra`, same shape as PHP's.
- **A gate-1 fixture**, plus the gate-2 registry row if the handshake moves.

## Constraints

- R5.6: unmeasured, never reachable. No inferred `IMPORTS` edge from a call.
- R1.1: no core change beyond the token constant.
- 061: a repo with no runtime import pays nothing; byte-identical payloads.
- A call whose module argument *is* a literal still gets no `IMPORTS` edge in this ticket — modelling
  that resolution is a different ticket, and stamping it is this one.

## Acceptance criteria

- A Python fixture calling `importlib.import_module(name)` stamps `unmodelled_resolution` on its File
  node; a fixture with only statement imports does not.
- `find_orphans` answers `status=resolution_unmodelled` over the stamped fixture and is byte-identical
  over the unstamped one.
- No new `IMPORTS` edge is emitted by this ticket.

## References
`adapters/python/src/parse.py:645`, `:667`, `:672`, `:740`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[020](020_python-adapter.md).
