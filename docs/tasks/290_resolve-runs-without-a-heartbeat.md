---
id: 290
slug: resolve-runs-without-a-heartbeat
title: '`parse` publishes `done`/`total` and ticks per file, and `resolve` — the phase that outlasts it on a large repo — publishes one line with `total=0` and never ticks again, so a slow pass and a hung one are byte-identical in `write.lock`; two independent sessions reached for `py-spy` to learn which they had, and one killed three builds that were still working'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [177, 201, 051]
---

## Why this exists (field retros — the anchor repo, 2026-09-15)

Two sessions on the same day, neither aware of the other, reported the same blindness from opposite
ends.

A build retro spent two days on three full rebuilds that all reached `resolve` and stayed there for
hours. The only way it learned the phase was *working* rather than *wedged* was attaching `py-spy` and
watching the same frame for 88 minutes, plus reading the build process's CPU counter climb. Its ask:

> *"`resolve` emits **no per-item heartbeat**, so 'slow' and 'hung' look identical without py-spy. Add
> a coarse progress line … so staleness/ETA is visible without attaching a profiler."*

Round 24 §6 hit the same wall from the other side and drew the same conclusion in one line — the
frozen `at=` through resolve *"looks like a hang and is not."*

The asymmetry is in one file. `_Progress.phase(name, total=…)` and `_Progress.tick()`
(`indexer.py:131-141`) are both used for `parse`, which publishes `total=len(kept)` and ticks per file
(`indexer.py:238,482,1084,1133`). `resolve` gets a bare `progress.phase("resolve")` with no total
(`indexer.py:611-612`), and `resolve_edges` is called without a progress object at all
(`indexer.py:619`) — so nothing inside it can report. 177 built this channel precisely so *"a long
build is not read as a hang"*, and the phase where that misreading actually happens is the one phase
it does not reach.

The cost is not cosmetic: on the evidence above, three builds that were still converging were killed
and restarted, each restart discarding work. A phase with no heartbeat is a phase every operator
eventually kills.

## Scope / Deliverables

- **`resolve` publishes progress a reader can act on** — at minimum a monotonically advancing count,
  so an unchanging line is evidence of a wedge rather than the normal case. Whether the denominator is
  edges, passes or work items is the design call; a `done` with no `total` still beats a frozen line.
- **The pass carries the reporter.** `resolve_edges` (and the sub-passes that dominate it) need the
  sink threaded in, the way the parse loops already have it.
- **One publisher.** The line format is `write.lock`'s existing one (`publish_build_progress`), read by
  `--status` (177); no second channel, no second spelling.

## Constraints

- Cost: the publish is a best-effort file write (`index_lock.py:143`) — it must not run per edge on a
  10⁶-edge pass. Throttle by count or by elapsed work, and say which.
- R4.2: progress is observational. Nothing published here may change what the build writes, and the
  resulting graph stays byte-identical.
- 061: `--status` output stays the shape 177 defined; this fills a phase, it does not add a report.
- Never publish a total the pass cannot honour — an ETA that stalls at 99% is the same failure with a
  number on it.

## Acceptance criteria

- A `resolve` pass over a non-trivial graph advances the published line more than once.
- `--status` during `resolve` shows movement between two reads taken far enough apart.
- A build whose resolve pass is genuinely stuck shows a line that does **not** advance, and the two
  cases are distinguishable without a profiler.
- The published graph is unchanged (R4.2), and the throttle is named where a reader can find it.
- `parse`'s existing progress is untouched.

## References
`code_atlas/indexer.py:115-141,238,482,611-619,1084,1133`, `code_atlas/index_lock.py:143-170`,
`code_atlas/cli.py:61-78` (`--status`),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md),
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md).
Origin: field retro "index rebuild never finishes", Rec 4, and round 24 §6 — 2026-09-15, two
independent sessions.
