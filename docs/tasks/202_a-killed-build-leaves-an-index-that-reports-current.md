---
id: 202
slug: a-killed-build-leaves-an-index-that-reports-current
title: 'A killed build leaves a gutted index that reports staleness current with no suggested action, and no incremental can repair it because last_commit still names HEAD'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [072, 077, 052, 050, 035]
---

## Why this exists

Field run on the anchor monorepo, 2026-08-31, minutes after the 73-minute rebuild in
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md). An operator wrapped
`code-atlas-refresh` in `timeout 300` to check a freshly installed git hook. The incremental was
killed mid-`reconcile`, after it had committed its delete batches.

`get_index_status` then answered:

```
files: 20221   nodes: 203526   edges: 1990979      (was 21588 / 216804 / 2087606)
staleness: "current"        next_tool_suggestions: []
last_commit: 009510c == HEAD                       index_complete: false
```

**1,367 files, 13,278 nodes and 96,627 edges are gone, and the payload's headline fields say the
index is current with nothing to do.** `index_complete: false` is present and is the only true
thing in that answer — a single boolean, carried beside `staleness: "current"`, which
[077](077_index-cannot-name-the-revision-it-describes.md) taught a reader to trust.

**It cannot repair itself.** `last_commit` is stamped by the *previous successful* build and HEAD
has not moved, so `gitutil.changed_paths` returns an empty set and the next incremental is a no-op
over a gutted graph. `build_or_update_index._run()` reads `full`, `last_commit` and the git diff —
it never reads `BUILD_COMPLETE_KEY`. Grepped: the key is written at `indexer.py:177` and `:250`,
stamped complete at `:966`, and read in exactly one place, `tools/get_index_status.py:124`. Nothing
on the write path consumes it.

So the terminal state is: an index missing 6 % of its files, reporting `current`, suggesting
nothing, unrepairable by the incremental path, and repairable only by a 73-minute full rebuild that
nothing tells the caller to run. Every tool answers from it meanwhile — a `find_callers` zero on a
symbol in one of those 1,367 files is a confident, wrong zero, which is
[065](065_empty-answer-cannot-explain-itself.md)'s and 054's defect class arriving through a door
neither of them watches.

This is [072](072_busy-build-hides-staleness.md)'s bug class — a build state that misleads a reader
— on the branch 072 did not cover. 072 made the *in-progress* claim self-invalidating by putting it
under a `flock`; nobody asked what the claim says once the build is dead and the graph is half
written. The `flock` did its job here: the lock was released, `build_in_progress` correctly said no.
The lie is in `staleness`.

### Why this is reachable, not exotic

The window is as long as an incremental takes, and on this repo a **no-op** incremental — index
already `current`, zero changed files — runs **over 5 minutes at 100 % of one CPU** (measured:
`real 5m0s`, `user 2m28s + sys 2m24s`, killed at the cap without finishing).
[052](052_incremental-noop-cost.md) measured that flat fee at ~62 s. Anything that ends a process
inside that window — a timeout, a Ctrl-C, a reboot, an OOM, closing the terminal that owns a
backgrounded git hook — produces this state. The operator here hit it on the first try.

## Scope

1. **An incomplete index must reach the fields a reader acts on.** `staleness` and
   `next_tool_suggestions` are computed from `build_complete`, not only `index_complete`: a
   half-written graph is not `current` however recent its `last_commit`, and the suggestion names
   the tool that actually repairs it. The routing precedent is
   [158](158_routing-suggestions-fire-on-index-state-not-on-the-question.md).
2. **The write path reads the key it writes.** `_run()` consults `BUILD_COMPLETE_KEY` and escalates
   to `full_build`, because an incremental over a graph that was mid-write is not equivalent to a
   full one — the same argument 030 and [172](172_incremental-is-blind-to-a-scope-change.md) already
   make for a vocabulary or scope change, and 201 asks to disclose. The escalation is reported, not
   silent.
3. **The three escalations are distinguishable** in the payload: contract bump (201), scope change
   (172), incomplete index (202). A caller can tell which one it hit.
4. **A regression test that kills a build for real.** Not a mocked flag: start an incremental, kill
   it mid-write, then assert the status payload and that the next build escalates. The fixture is
   the deliverable — this class of defect is only ever found by killing a process.

### Explicitly not in scope

- **Making the incremental transactional.** Wrapping a 21,588-file reconcile in one transaction so
  a kill rolls back cleanly is the deeper fix and a much larger one — it changes the write path's
  memory and lock profile, and it needs its own measurement. 202 makes the damaged state *honest
  and repairable*; a follow-up can make it *impossible*. Note it, do not smuggle it in.
- **The >5 minute no-op incremental.** Real, measured above, and 5× what 052 recorded — but it is a
  cost defect on a different axis. It belongs with 052 / 080 / 096, not here.
- **201's contract-bump disclosure.** Same payload, different trigger; 202 depends on the shape 201
  introduces but must not re-litigate it.
- **Repairing the field index.** Already done out of band by `code-atlas-build --full`.

## Constraints

- **No contract bump** (R3), **no language branch** (R1.1), deterministic (R4.2).
- **No new durable claim.** 072's rule stands: nothing may be written that outlives the process and
  can lie later. `build_complete` is already on disk and already survives a kill — this ticket makes
  the *readers* honest, it does not add a second flag.
- **`index_complete` keeps its meaning.** It is correct today; 202 adds consumers, it does not
  redefine or remove the field (061 — a payload contract does not churn).
- **Both doc budgets are already breached before this row lands.** Measured: `BACKLOG.md` 8,192
  against 8,200 after 201 pruned the `015 AC2` follow-up, and the tier-1 chain sum 25,248 against
  25,200 — 42 of that overshoot pre-dates 201 and 202 (200's row alone puts it over, from 10 tokens
  of headroom at HEAD). Three tickets arriving at once is the argument for the raise; make it in the
  PR, or prune (R7.6, `tests/test_doc_size_budget.py`, `tests/test_agent_chain_budget.py`).

## Acceptance criteria

1. With `build_complete = 0` on disk, `get_index_status` does **not** report
   `staleness: "current"` and does **not** return an empty `next_tool_suggestions`. Red before the
   fix against the exact field payload above.
2. With `build_complete = 0`, `build_or_update_index(full=false)` escalates to a full build and says
   so — proven from a killed build, not a hand-set flag.
3. A completed build still reports exactly as it does today on both surfaces: no field added, no
   wording changed, on the healthy path (061).
4. The kill-a-real-build fixture is committed and is what turns AC1 and AC2 red when reverted.
5. The three escalation reasons are distinct values a caller can branch on, and each is named in the
   payload of the build that took it.
6. `index_complete: false` and the new `staleness` answer cannot disagree — one derivation, one
   definition site (R6.7).

## References

[072](072_busy-build-hides-staleness.md) (the bug class, and the branch it did not cover),
[077](077_index-cannot-name-the-revision-it-describes.md) (`last_commit` / `last_ref`, and why a
reader trusts them), [052](052_incremental-noop-cost.md) (the flat fee whose length is this
window), [050](050_schema-version-mismatch-recovery.md) (a returned refusal naming the recovery),
[035](035_read-through-freshness.md) (query-time repair, which does not reach a file the graph no
longer lists), [065](065_empty-answer-cannot-explain-itself.md) / 054 (the confident-zero class this
produces), [158](158_routing-suggestions-fire-on-index-state-not-on-the-question.md) (suggestions
keyed on index state), [201](201_a-forced-full-rebuild-is-silent-and-unroutable.md) (the disclosure
shape this reuses), [172](172_incremental-is-blind-to-a-scope-change.md) (escalation, recorded and
surfaced).
Field log: anchor monorepo, 2026-08-31 — `timeout 300 code-atlas-refresh --verbose` → exit 124,
then the status payload quoted above.
