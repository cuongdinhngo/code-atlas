---
id: 454
slug: session-refresh-and-guard-in-product
title: "The anchors' session refresh and symbol guard become product scripts, so no anchor keeps a copy"
phase: 2
milestone: Freshness
status: todo
depends_on: [453, 377]
---

## Why this exists

Epic 451. the PHP anchor keeps `code-atlas-session-refresh.sh` (6.3 KB) and `code-atlas-symbol-guard.sh`
(19 KB); the Python/TS anchor ported both (4 KB, 11 KB) and they already differ. Both add what the product
lacks: a session-start reminder that survives compaction, an incremental refresh when `behind`,
and a `PreToolUse` refusal of a grep for a symbol until code-atlas was asked about that name. The
product's own nudge (345) runs `PostToolUse`, after the grep already answered.

## Scope

1. `code-atlas-state` on SessionStart (all sources, compaction included) prints the routing
   reminder when the index can answer, and starts the background refresh when `behind`.
2. A `code-atlas-guard` script for `PreToolUse(Grep|Bash)`: refuses a symbol-shaped grep until
   the transcript holds a code-atlas query naming it; any non-argument code-atlas error lifts it
   for the session. The symbol shapes come from the configured adapters, not a hard-coded language
   list (R1.1); unsure always means allow.
3. Mode is configurable (`off` / `nudge` / `refuse`), recorded by `code-atlas-setup`; default `nudge`.
4. Plugin `hooks.json` and the setup-written settings both call it; the anchors' scripts are removed
   in their own repos (listed here, not done by this ticket).

## Acceptance criteria

- **AC1:** a fixture transcript with `grep -rn "def foo"` and no prior query → refused in `refuse`
  mode, nudged in `nudge` mode; after a `search_symbol foo` → allowed.
- **AC2:** a literal-text grep (string, config key) is never touched.
- **AC3:** the guard adds under 50 ms per call on the fixture (measured).
- **AC4:** both anchors run with their own scripts removed and keep the behaviour (field check).
