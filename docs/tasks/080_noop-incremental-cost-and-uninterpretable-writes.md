---
id: 080
slug: noop-incremental-cost-and-uninterpretable-writes
title: 'A no-op incremental costs ~56 s and reports 6,071 edges written for 0 files parsed'
phase: 1.5b
milestone: Cost
status: todo
depends_on: [052, 051, 060]
---

## Goal
Round 4 timed five builds on the anchor monorepo: **273 files → 107.9 s**, **4 files → 57.6 s**,
**0 files → 56.1 s and 57.4 s**. A build that parses nothing costs within 2% of a build that parses
four files, and the no-op payload reports `wrote: {files: 0, parsed: 0, nodes: 0, edges: 6071}` —
6,071 edges written having read no file. [052](052_incremental-noop-cost.md) profiled this cost and
took a decision; the field number says the outcome an agent experiences has not moved. Two things are
wrong: the floor, and a number nobody outside can interpret.

## Evidence (field retro round 4, 2026-08-10, §5 and §11 item 5)
- Five builds, all on the same index, timings above; the two no-ops are independent runs, not one
  outlier.
- No-op payload shape, verbatim from the retro: `wrote:{files:0,parsed:0,nodes:0,edges:6071}`, twice,
  at ~56 s each.
- Same-process build/status pair (probe for §A.12) shows the totals agreeing exactly —
  `graph:{files:18888,parsed:18859,failed:29,nodes:186134,edges:1784018}` vs status
  `18888/18859/29/186133/1784013` — so this is **not** a 051/060 reporting mismatch. 051 and 060 are
  verified fixed; this is a different question about the *no-op* row.
- The evaluator held R-2 (no source reading) and filed the interpretation gap as the finding: *"a
  payload that writes 6 k edges having parsed 0 files is not something I can interpret from outside"*.
- Operational consequence, already recorded in 053's reasoning and now measured again from the field:
  a hook that costs ~56 s per invocation gets uninstalled by whoever waits for it.

## Two deliverables, and they are separable
**A — the floor.** Find where a no-op spends ~56 s on a ~19k-file / 1.78M-edge index and either
remove the work or make it proportional to the delta. 052's profile is the starting point, not the
answer: re-measure on the current tree, because several tasks have landed since (enrichment, rules,
dedupe, freshness) and the profile may have moved.

**B — the number.** `wrote.edges` on a no-op must either be zero or be named for what it counts. If
those 6,071 edges are re-derived sibling/enrichment rows, the payload should say that — a delta field
that is non-zero when the delta is empty is unreadable by construction, and 060 established that the
build payload's field names are the contract an agent reads.

## Scope / Deliverables
- **Re-profile the no-op path on the current code** (full timing breakdown per phase), and record it
  in the ticket so the next round has a baseline to compare against.
- **Cut or bound the fixed cost.** State a target with the field number as the justification; if the
  cost is irreducible, say which phase it is and why, and make that visible in the payload rather than
  as a silent 56 seconds.
- **Make `wrote.*` mean the delta.** Either zero on a no-op, or split into delta vs re-derived groups
  with names that say which is which (060's pattern).
- **Re-check the hook and refresh paths** (036 `code-atlas-poke`, 053 `post-merge`/`post-checkout`)
  against the new floor, since both inherit it.
- **Cover the no-op with a test that asserts the payload shape**, so a future change cannot quietly
  reintroduce a non-zero delta.

## Constraints
- R4 — determinism: two consecutive no-ops must produce identical payloads (today's two runs agree at
  6,071, which is at least consistent).
- 060 / 051 — do not disturb the verified `wrote` vs `graph` split; this is a change *within* `wrote`.
- Cost work must not trade correctness: skipping enrichment or resolver passes to hit a number is a
  regression, not a fix, and 068's precedent (a bookmark that most call sites remembered to skip) is
  the anti-pattern to avoid.
- Measurement on the anchor repo is the operator's; the ticket's own tests run on fixtures.

## Acceptance criteria
- A recorded phase-by-phase profile of a no-op incremental on a large index, current as of this
  ticket.
- A no-op reports a delta of zero, or reports re-derived work under a name that says so; a test pins
  it.
- A stated, justified figure for the no-op floor after the change, with the before number beside it.
- 036 and 053 have a verdict on whether the new floor makes them usable as designed.

## References
Field retro round 4 §5 (five builds, timings), §11 item 5, §A.12 (the totals agree — this is not a
reporting mismatch). Related: [052](052_incremental-noop-cost.md) (the profile and its Outcome
decision), [051](051_build-report-edge-undercount.md) and
[060](060_build-report-scale-naming.md) (what the build payload's fields mean),
[036](036_edit-index-hook.md), [053](053_refresh-on-checkout-hook.md) (the two consumers of this
floor), [016](016_incremental-git.md).
