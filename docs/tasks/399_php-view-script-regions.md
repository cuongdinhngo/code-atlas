---
id: 399
slug: php-view-script-regions
title: "A PHP view's inline <script> is not in the graph"
phase: 2
milestone: Coverage
status: in-progress
depends_on: [395]
---

## Why this exists

Split out of 395, which shipped only its Scope 2: ES5 constructor members as Methods. The anchor's
second field retro (2026-10-10 → 10-17) also asked for:

- F1: handlers in a `.php` view's inline `<script>`.
- Prototype members (395 review): `Ctor.prototype.m = function` and `Ctor.prototype = {…}` are not
  read. A pass for them must share 395's per-constructor `seen` set, or a member is declared twice.

Template references (F2–F4) were split to [406](406_php-template-references.md) on 2026-10-19.

The script half does not fit today's seams. Each suffix has exactly one adapter
(`code_atlas/adapter.py` `extension_index`). Handing a `.php` file's `<script>` regions to the JS
reader therefore needs a new handshake field plus a second `parse` call from the core, which is a
`contract_version` bump (R3). The other route is a JS reader inside the PHP adapter.

**Evidence gate — met 2026-10-19.** 395's Scope 1 count, run by the maintainer with `grep` on the anchor
(no `vendor/`, no `.worktrees/`):

| Metric | Whole repo | `src/` only |
|---|---|---|
| PHP files containing `<script` | 1,122 | 960 |
| Total PHP files | 8,475 | 4,738 |
| `this`/`self.X = function` | 1,947 | 230 |
| `$scope.X =` | 8,387 | 1,230 |

The last two rows count `.php` and `.js` together. 13% of the anchor's PHP files carry a script the
graph cannot see, which the maintainer judged worth a contract bump: core fan-out, not a second JS
reader (2026-10-19).

## Scope

1. The anchor count above, and the route chosen from it: core fan-out with a contract bump, or an
   in-adapter reader.
2. Embedded `<script>` functions become symbols of the `.php` file at their true lines (395 AC2).

## Acceptance criteria

- **AC1:** 395's AC2, as written there.
- **AC2:** An index with no such files is byte-identical.
