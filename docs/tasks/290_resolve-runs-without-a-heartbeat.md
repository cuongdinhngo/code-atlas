---
id: 290
slug: resolve-runs-without-a-heartbeat
title: '`parse` publishes `done`/`total` and ticks per file, and `resolve` — the phase that outlasts it on a large repo — publishes one line with `total=0` and never ticks again, so a slow pass and a hung one are byte-identical in `write.lock`; two independent sessions reached for `py-spy` to learn which they had, and one killed three builds that were still working'
phase: 1.5b
milestone: Agent-trust
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 290 — resolve progress heartbeat (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket
- **Current phase:** finalise
- **Session status:** autorun — reviewer off; challenger CLEAN

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: tick per resolve batch with total=0 (honest — batch count unknown up front); publish done without total; throttle remains PROGRESS_INTERVAL wall time at the sink (cites Constraints cost + "done with no total still beats a frozen line").

## Requirements matrix

`SECTIONS: 5 found (Why · Scope · Constraints · Acceptance · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | resolve no heartbeat | on_batch tick + publish done | D1 | AC1 | ✅ |
| C1 | Constraints | no per-edge publish | batch tick; PROGRESS_INTERVAL | D1 | AC4 | ✅ |
| C2 | Constraints | R4.2 observational | progress only | D1 | AC4 | ✅ |
| C3 | Constraints | 061 status shape | same publish channel | D2 | AC2 | ✅ |
| C4 | Constraints | no false total | total=0 | D1 | AC4 | ✅ |
| R1 | Scope | monotonic count | tick per batch | D1 | AC1 | ✅ |
| R2 | Scope | thread reporter | on_batch into resolve_edges | D1 | AC1 | ✅ |
| R3 | Scope | one publisher | write.lock / --status | D2 | AC2 | ✅ |
| AC1 | AC | advances more than once | proving | D3 | proving | ✅ |
| AC2 | AC | --status shows movement | same sink | D2 | proving | ✅ |
| AC3 | AC | stuck distinguishable | frozen done | D1 | proving | ✅ |
| AC4 | AC | graph unchanged; throttle named | PROGRESS_INTERVAL | D2 | proving | ✅ |
| AC5 | AC | parse untouched | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: resolve phase published once with total=0 and never ticked; sink also omitted done when total=0.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — R4.2 ✅ · 061 ✅`

Ran at e9a8ae7407af114041452e70724157d64dd499dc

```
$ .venv/bin/python -m pytest tests/test_build_progress.py -q --tb=no
.......                                                                  [100%]
7 passed in 3.00s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: resolve_edges(on_batch=progress.tick); publish done when total=0; throttle = PROGRESS_INTERVAL.
- Rejected: per-edge tick (cost); inventing a total from edge count that could stall at 99%.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_resolve_progress_heartbeat.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | on_batch + indexer wire | resolver.py, indexer.py | resolve progress | 1/1 |
| D2 | publish done w/o total | build_or_update_index.py, indexing.md | --status line | 1/1 |
| D3 | proving | tests/test_resolve_progress_heartbeat.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/290-resolve-progress-heartbeat
**Axis 1:** resolver · indexer · sink · proving.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at e9a8ae7407af114041452e70724157d64dd499dc

```
$ .venv/bin/python -m pytest tests/test_resolve_progress_heartbeat.py tests/test_build_progress.py -q --tb=no
..........                                                               [100%]
10 passed in 3.43s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (throttle); round-2 NOT CLEAN (docs named wrong throttle); round-3 CLEAN. agents 761aeadc / 7139ed60 / a5a9e0bf-6344-4dd0-8b44-338cab7bfde3

Verify-only:

Ran at e9a8ae7407af114041452e70724157d64dd499dc

```
$ .venv/bin/python -m pytest tests/test_resolve_progress_heartbeat.py tests/test_build_progress.py -q --tb=no
...........                                                              [100%]
11 passed in 4.37s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_resolve_progress_heartbeat.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN
PR: https://github.com/cuongdinhngo/code-atlas/pull/384

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
