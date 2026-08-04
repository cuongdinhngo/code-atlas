---
id: 035
slug: read-through-freshness
title: Read-through freshness — inline reparse on hash drift
phase: 1.5
milestone: Freshness
status: todo
depends_on: [009, 011]
---

## Goal
Make liveness a property of the answer, not a chore the user remembers. Today a tool answers from the
last build; only `read_symbol` detects staleness, and it returns `stale: true` with empty source and
punts to a rebuild rather than fixing it. For an AI consumer that will not rebuild on its own, this is
correctness: when a tool is about to return rows touching file X, compare X's current hash to the
stored `files.hash`, and if it drifted, reparse **just X** through the adapter inline before
answering. One adapter call, milliseconds, no daemon, no determinism violation (§19 agent-first pivot).

## Scope / Deliverables
- A query-time staleness check shared across the read/nav tools: hash the on-disk file, compare to
  `store.file_hash(rel)`, and on mismatch reparse that single file through the adapter and update its
  rows before shaping the response.
- Promote `read_symbol`'s existing check (`code_atlas/tools/read_symbol.py:50-61`) from
  "report stale" to "repair inline" using the same mechanism.
- A bound: cap the number of files reparsed per call; beyond it, fall back to the stale signal + a
  reason code (pairs with task 033).

## Constraints
- **Determinism preserved** — inline reparse uses the same adapter/store path as the full build, so
  the repaired rows are identical to what a rebuild would produce (R4). Add a test proving equality.
- No language branches (R1.1); adapter parses, store persists, never the reverse (R1.4).
- Single-file scope only — a read never triggers a full rebuild; never load the whole graph.

## Acceptance criteria
- Edit a file on disk after indexing; a nav/read query touching it returns rows reflecting the new
  content **without** an explicit rebuild.
- A query not touching the edited file performs no reparse (asserted — no adapter call).
- Determinism: the inline-reparsed rows for a file equal the rows a full build produces for it.
- The per-call reparse cap is enforced; overflow yields a stale reason code, not an unbounded stall.

## References
`code_atlas/tools/read_symbol.py:50-61` (existing staleness check to generalise);
`code_atlas/indexer.py:141-144` (incremental reparse-on-hash-mismatch — the path to reuse);
`code_atlas/store.py` (`file_hash`). PLAN §5 (incremental), §19. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 3 ("freshness has to be enforced, not surfaced").
