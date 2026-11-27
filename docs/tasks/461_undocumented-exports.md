---
id: 461
slug: undocumented-exports
title: "The other direction: exports of chosen paths that no doc names"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

Same field report as 456. `verify_refs` answers "is what the docs say still true" (docs → code). Drift
also goes the other way: a shared helper is added and the catalogue that tells agents to reuse it is
never updated. The next session doesn't find it and writes a second copy. tiny-studio found 14
copies of the same error ternary, 3 of the native-dialog logic and 6 of the LLM retry loop (ADR 0018
audit, 2026-11-27).

The index already holds both sides (exported symbols, and the refs `verify_refs` extracts). The
missing piece is the set difference.

## Scope

1. A query over a path glob and a doc glob: public top-level symbols under the paths (exported in
   TS, no leading `_` in Python) that no ref in the docs resolves to. Rows: `symbol`, `file:line`,
   `kind`.
2. Surface it as a `compute` template, or as `verify_refs` mode `undocumented`, whichever 443's export
   code already fits. One surface only. CLI too: `code-atlas query --undocumented <paths> --docs
   <globs> --format jsonl|md`, with `--fail-on any`.
3. An allowlist file (one qname per line) for internal helpers.

## Acceptance

1. Fixture: two exports, one named in a doc → one row; an allowlisted export → no row.
2. tiny-studio: run on `web/src/components/ui/**`, `web/src/lib/**` against
   `docs/CONVENTIONS_FE.md`. Report the rows and check them by hand against the catalogue.
3. Runtime on the anchor for one path glob, reported.
