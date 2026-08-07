---
id: 047
slug: staleness-scoped-to-indexed-files
title: Staleness must reflect the index, not the working tree — a docs-only edit is not "behind"
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [028, 035, 016]
---

## Goal
`_staleness` (`tools/get_index_status.py:97-105`) reports `behind` when `working_tree_dirty` is true,
and `working_tree_dirty` (`gitutil.py:51-60`) is `git status --porcelain -uno` over **every tracked
file**. Nothing in that path knows which files the index actually covers. So editing a `.md` file — or a
`.json`, a `.sql`, a `.yml`, anything the adapters do not parse — flips `staleness` to `behind` while
`last_commit == head_commit`.

Observed in the field (first external session, retro round 1): ~11 markdown edits, zero code edits,
`staleness: "behind"`. The agent then ran `build_or_update_index(full=false)` and got
`files: 0, parsed: 0, removed: 0, nodes: 0, edges: 0, seconds: 62.296` — **62 seconds to establish that
nothing needed reindexing.**

The cost is not the minute. It is that the signal is *systematically* wrong in the direction that
manufactures work, and agents are being told to act on it: `_suggestions` (`:108-113`) puts
`build_or_update_index` in `next_tool_suggestions` whenever `staleness != current`, and the field session
had just written that into a repo rule gating a multi-agent fan-out. An advisory signal that cries wolf
on every documentation commit trains its consumer to ignore it — which is the one failure mode a
freshness signal cannot survive (R5.3 is about failing loud; this is failing loud about nothing).

## Scope / Deliverables
- **Scope the dirty check to indexable paths.** `working_tree_dirty` returns a bool over all tracked
  files; it needs to answer "are any *indexed-relevant* files dirty". The filter already exists — the
  walk decides what to index via the ignore rules and the adapter extension map — so this is about
  reusing that decision, not inventing a second definition of "indexable". A second definition would
  drift from the first and is worse than the bug.
- **Keep the three-state answer honest.** `None` (git cannot answer) must stay distinct from "clean":
  the current code returns `unknown` only when a *commit* is unknown, and a `None` from
  `working_tree_dirty` currently falls through to `current` (`:103-105` — `if dirty:` treats `None` as
  falsey). Decide that deliberately and test it, rather than inheriting it.
- **Say what is stale, not just that something is.** At `detail_level="standard"`, a count (or a short
  capped list) of dirty indexed files turns "rebuild, maybe" into "rebuild, these N". Cheap, and it is
  what a caller needs to decide whether the minute is worth paying.
- **Tests for the shape that was actually wrong**: a dirty ignored/non-indexable file → `current`; a
  dirty indexed file → `behind`; both dirty → `behind`; git unavailable → the decided state.

## Constraints
- **No language branch in the core (R1.1).** "Which extensions are indexable" comes from configuration
  and the adapter map, never from an `if language == …`.
- **Determinism (R4).** Same tree, same git state → same answer. No mtime heuristics.
- **Cheap (§19).** `get_index_status` is the one tool the field session actually depended on and its
  verdict was "must stay cheap and honest". One extra git call is acceptable; walking the tree is not.
  Prefer passing pathspecs to the existing `git status` invocation over post-filtering a large list.
- **Never report `current` when an indexed file is dirty.** A false `current` is far worse than a false
  `behind`: read-through freshness (035) covers the file a read tool touches, but nothing covers a nav
  query over stale edges. If the filter cannot be applied confidently, fall back to today's behaviour.
- **`minimal` payload shape is fixed** (§12: stats, `last_commit`, staleness, suggestions). Any new
  field is `standard`-only.

## Acceptance criteria
- A repo whose only dirty tracked files are non-indexable (e.g. `.md`) reports `staleness: "current"`
  (asserted), and `next_tool_suggestions` does not contain `build_or_update_index`.
- A repo with one dirty indexed source file still reports `behind` (asserted) — the guard against
  over-correcting.
- A dirty *ignored* file (matched by `.gitignore`/`.codeatlasignore` yet tracked) reports `current`
  (asserted).
- Git-unavailable and detached/unknown-commit paths keep their current states, asserted rather than
  incidental.
- `get_index_status` at `minimal` returns the same keys as today (asserted; no payload growth).
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/tools/get_index_status.py:97-105` (`_staleness`), `:108-113` (`_suggestions` — why a false
`behind` costs a tool call), `:74` (the call site), `:84-94` (the `minimal` / `standard` split).
`code_atlas/gitutil.py:51-60` (`working_tree_dirty`, `-uno`, and the docstring explaining why untracked
paths are already excluded — the same reasoning applied one level further). Ignore rules:
`code_atlas/ignore.py`. Incremental build: [016](016_incremental-git.md). Read-through freshness:
[035](035_read-through-freshness.md) — covers the read path, which is why a false `current` on the *nav*
path is the dangerous direction. Health payload: [028](028_index-health-metrics.md).
Origin: field retro round 1 (`v0.1.0`, commit `e117b47`) §4 and §7 — the tool the session depended on,
and the only misleading behaviour it observed.
