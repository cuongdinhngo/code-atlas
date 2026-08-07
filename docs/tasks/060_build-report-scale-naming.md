---
id: 060
slug: build-report-scale-naming
title: An incremental run reports deltas under the same field names a full build uses for totals
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [051]
---

## Goal
[051](051_build-report-edge-undercount.md) settled that `BuildReport` means **"what this run wrote"**,
and made the counts honest. It did not do the other half of its own scope, which said in as many words:

> If the delta reading wins, the fields must be named so a total cannot be read out of them.

They were not renamed. So an incremental returns:

```json
{"mode":"incremental","files":21,"parsed":21,"failed":0,"removed":0,
 "nodes":357,"edges":6396,"seconds":61.585,"schema_rebuilt":false}
```

against a graph holding 185,886 nodes and 1,775,839 edges — while a **full** build returns the same
field names meaning the whole graph, because on a full build "what this run wrote" *is* the graph. Only
`mode` distinguishes them, and a caller that does not read it sees `edges: 6396` and has no signal that
it is holding a delta.

Observed in field retro round 2 §A.5, which read the pair and could not tell which scale it was on
without reasoning about the mode.

**Also in scope: re-measure the round-1 disagreement on a clean server.** Round 2 reported a full build
at ~949,808 edges against `get_index_status` at 1,775,812 — the exact figures from before 051 shipped,
observed on a session whose server process predated the fix (its own §0 shows the core reporting
contract v2). 051's tests assert the two agree. Confirm on a restarted server, and record the result
either way; a "not fixed" that is actually a stale process should not stand in the record unchallenged.

## Scope / Deliverables
- **Make the scale unreadable-as-wrong.** Options, to be chosen and justified: distinct field names per
  mode; a nested shape (`wrote: {...}`) that cannot be mistaken for a total; or carrying the graph
  totals alongside the delta so both are present and labelled. Prefer whichever makes the wrong reading
  impossible rather than merely documented.
- **Do not silently change the meaning.** 051's definition stands — the fix is naming, not arithmetic.
- **A test that would fail on the old shape**, in the spirit of
  `test_an_incremental_run_reports_its_delta_not_the_graph`.
- **Re-measure and record** the full-build-vs-status agreement on a server known to be running current
  code, on a repo large enough for the two to differ if they were going to.

## Constraints
- **No schema or contract change (R3).**
- **Determinism (R4.2)** — counts unchanged; only their presentation moves.
- **Cost stays flat** — if totals are carried alongside, they come from `store.counts()`, which
  `get_index_status` already pays for, and not from a new scan.
- **`build_or_update_index` is called rarely**, so a slightly larger payload is acceptable here in a way
  it is not on the nav path.

## Acceptance criteria
- An incremental result cannot be read as a graph size: asserted by a test that fails against today's
  shape.
- A full build and an incremental are distinguishable without reading `mode`.
- 051's existing agreement tests still pass unchanged.
- The re-measurement is recorded in the Outcome, naming the server commit it ran against.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/indexer.py:71-81` (`BuildReport`), `:202-204` (the incremental return),
`:207-218` (`_count_late_writes`); `code_atlas/tools/build_or_update_index.py` (`mode`, `_result`);
`code_atlas/store.py` `counts()` (the totals `get_index_status` reports).
[051](051_build-report-edge-undercount.md) — the definition, the scope line left undone, and
`tests/test_build_report_counts.py`.
Origin: field retro round 2 §A.5.
