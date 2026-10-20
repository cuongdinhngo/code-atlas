---
id: 406
slug: php-template-references
title: "A PHP template's `ctrl.X(`, `ng-model` and asset-list references are not in the graph — evidence-gated"
phase: 2
milestone: Coverage
status: deferred
depends_on: [399]
---

## Why this exists

Split out of [399](399_php-view-script-regions.md) on 2026-10-19, so 399 carries only the inline
`<script>` half. The anchor's second field retro (2026-10-10 → 10-17) asked for:

- F2/F3: `ctrl.X(` and `ng-model="…"` in templates.
- F4: `loadScripts(['js/x.js'])` naming an asset.

Template references are not calls, so `keyed_calls` cannot match them. The rule fires on a parsed
call with a one-line string argument. An array-of-paths key (F4) is a new `key_from`.

**Anchor count (2026-10-19, `grep`, maintainer run):** `ng-model=` / `ctrl.X(` 1,716 whole repo, 1,669
under `src/`. **Evidence gate:** the count is in; this opens once 399 has shipped the embedded-region
seam, since a template's controller lives in that `<script>`.

## Scope

1. Template references are read through a declared rule, with no new rule kind unless none fits
   (395 AC3: `ctrl.save(` is a `HEURISTIC` caller; `ctrl.missing(` is counted).
2. An array-of-paths include list (F4) names its assets.

## Acceptance criteria

- **AC1:** 395's AC3, as written there.
- **AC2:** An index with no such files is byte-identical.
