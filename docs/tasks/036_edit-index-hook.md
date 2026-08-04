---
id: 036
slug: edit-index-hook
title: Claude Code Edit/Write index-poke hook
phase: 1.5
milestone: Distribution
status: todo
depends_on: [016, 035]
---

## Goal
Use the client's own hook system so the agent's edits keep the index live. code-atlas is built for a
consumer that has a hook mechanism (Claude Code) — a `PostToolUse` hook on `Edit`/`Write` that pokes
the index turns freshness from opt-in into automatic. This is a distribution move worth more than
several features (§19 agent-first pivot).

## Scope / Deliverables
- A hook script + a `settings.json` snippet (documented) that, after `Edit`/`Write`, marks the
  touched file(s) stale or triggers an incremental update for them, reusing the incremental path
  (task 016).
- README/docs section: how to install the hook and what it does.

## Constraints
- The hook is **opt-in configuration outside the core** — no core change beyond what the incremental
  path already exposes; no language branches.
- Must be a safe no-op when no index (`.code-atlas/graph.db`) exists — never build implicitly.
- Cheap and non-blocking: poking one file must not stall the editor tool round-trip.

## Acceptance criteria
- With the hook installed, editing a file via Claude Code makes the next query reflect the change
  (via task 035 read-through or an incremental poke) without a manual rebuild.
- With no index present, the hook exits cleanly and does nothing.
- Install steps documented and reproducible.

## References
`code_atlas/indexer.py` (`incremental_update`); task 016 (incremental via git diff); task 035
(read-through freshness). PLAN §5, §19. Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3
("ship a Claude Code PostToolUse hook on Edit/Write — a distribution move worth more than several
features").
