---
id: 399
slug: php-view-script-regions
title: "A PHP view's inline <script> and its template references are not in the graph — evidence-gated"
phase: 2
milestone: Coverage
status: deferred
depends_on: [395]
---

## Why this exists

Split out of 395, which shipped only its Scope 2: ES5 constructor members as Methods. The anchor's
second field retro (2026-10-10 → 10-17) also asked for:

- F1: handlers in a `.php` view's inline `<script>`.
- F2/F3: `ctrl.X(` and `ng-model="…"` in templates.
- F4: `loadScripts(['js/x.js'])` naming an asset.

Neither half fits today's seams:

- **Scripts.** Each suffix has exactly one adapter (`code_atlas/adapter.py` `extension_index`).
  Handing a `.php` file's `<script>` regions to the JS reader therefore needs a new handshake field
  plus a second `parse` call from the core, which is a `contract_version` bump (R3). The other route
  is a JS reader inside the PHP adapter.
- **Template references.** These are not calls, so `keyed_calls` cannot match them. The rule fires
  on a parsed call with a one-line string argument. An array-of-paths key (F4) is a new `key_from`.

**Evidence gate:** 395's Scope 1 count must come first: PHP files with inline `<script>`, and
`$scope.X =` / `this.X = function` assignments on the anchor index. This ticket opens only when that
count justifies a contract bump.

## Scope

1. The anchor count above, and the route chosen from it: core fan-out with a contract bump, or an
   in-adapter reader.
2. Embedded `<script>` functions become symbols of the `.php` file at their true lines (395 AC2).
3. Template references are read through a declared rule, with no new rule kind unless (1) shows
   none fits (395 AC3: `ctrl.save(` is a `HEURISTIC` caller; `ctrl.missing(` is counted).

## Acceptance criteria

- **AC1:** 395's AC2 and AC3, as written there.
- **AC2:** An index with no such files is byte-identical.
