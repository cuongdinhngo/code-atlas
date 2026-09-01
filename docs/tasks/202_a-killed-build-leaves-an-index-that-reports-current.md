---
id: 202
slug: a-killed-build-leaves-an-index-that-reports-current
title: 'A killed build leaves a gutted index that reports staleness current with no suggested action, and no incremental can repair it because last_commit still names HEAD'
phase: 1.5b
milestone: Agent-trust
status: in-progress
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 202 · **work_doc_mode:** embed · **Current phase:** 2 design — complete; Gates 0-2 closed. Contract bound at Gate 2.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run arg *"with skipper reviewer"* = reviewer seat only; the challenger keeps its seat.
- **Branch is STACKED on 201**, not on `main`: AC5 needs all three escalation reasons present, and
  two of them only exist on 201's branch. The PR bases on `feat/201-…`, so **#244 merges first**.
- Contract `.mango/run-contract-202.txt`. RECONCILE t0: 8 declared | 6 re-run | 0 holding | 6 BROKEN
  | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 17 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 6 unresolved surfaced | 1 want-decision asked | 5 how-decision resolved+cited | 0 ASSUMED | skip: no`

The ambiguous reference is the anchor monorepo's field log. Every in-repo claim was re-derived:
`BUILD_COMPLETE_KEY` is written at `indexer.py:177` and `:273`, stamped complete at `:989`, and read
in **exactly one** place — `tools/get_index_status.py:131`. Nothing on the write path consumes it,
exactly as the ticket says. (Line numbers differ from the ticket's by 201's edits above them.)

**Settled want — asked and answered by the maintainer.**

| # | The want | Answer | Consequence |
|---|---|---|---|
| W1 | Scope 2 escalates on the shared `_run()` path, so `code-atlas-refresh` inherits it. After a kill, every `git checkout` background-spawns what is a 73-minute rebuild on the anchor repo — and the ticket's own trigger list includes *"closing the terminal that owns a backgrounded git hook"*, so an interrupted repair repeats indefinitely with no visible signal. Should the hook inherit the escalation? | **The hook reports; it does not rebuild.** | The MCP tool escalates exactly as AC2 says. `code-atlas-refresh` passes `repair_incomplete=False`, gets the refusal, prints one line naming `code-atlas-build --full`, and exits 0 — keeping 053's *"never builds"* contract and making a rebuild storm impossible |

**Resolved + cited.** H1–H3 are mine; H4–H5 come from the exposure-checker.

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Does `staleness` gain a value, or reuse `behind`? | **A new value, `incomplete`.** `behind` means *HEAD moved*, which is false here; one value for two causes is `one-field-two-questions`, and R5.6 forbids attesting past what the payload can distinguish | `staleness.py:18-20`; R5.6; ticket Scope 1 |
| H2 | Which layer learns about incompleteness — `get_index_status`, or the shared vocabulary? | **`compute_staleness`, the shared module.** It has **six** consumers, four of them nav tools that sign a payload; a `find_callers` zero over a gutted graph is the confident-wrong-zero the ticket's own *Why this exists* names. Fixing it in the status tool alone would leave every other tool lying | `staleness.py:1-6`; the trace in Phase 2; ticket *Why this exists* (065/054) |
| H3 | Does the incomplete-index escalation **refuse** like 201, or **perform** like 172? | **Perform** on the MCP path. AC2 and AC5 both say the build *takes* the escalation and names it. Unlike a contract lag, a gutted index is actively serving wrong answers, so the cost of continuing to serve it exceeds the wait. The refusal shape is reused only for the opted-out caller (W1) | ticket Scope 2, AC2, AC5 |
| H4 | Which reason wins when a contract lag **and** an incomplete build both hold? | **The contract refusal**, by existing code order: `_build` checks `contract_rebuild_required` before `_run` is reached. Recorded rather than left to discovery | `build_or_update_index.py:198-201` (201's check) |
| H5 | Is the doc-budget constraint still live? | **Already discharged.** Commit `aced82e` raised `BACKLOG.md` 8,200 → 8,300 and `TIER1_BUDGET` 25,200 → 25,300, argued in both test comments, for exactly the 200/201/202 rows | `tests/test_doc_size_budget.py`; `tests/test_agent_chain_budget.py` |

**Recalled claims — advisory.** `one-field-two-questions` (189, 022) and
`gate-on-the-invariant-not-on-presence` (196-C1) by handle; `drift-is-vs-the-index-commit-not-the-working-tree`
(166) and `identity-names-the-loaded-process-not-the-disk` (164) by area. Two skipped as retired:
`derived-not-listed-invariant` (**R6.7**) and `prove-the-guard-fails` (**R6.5**).

## Phase 1 — analysis

`PREMISE: 17 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists [+ Why this is reachable], Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=8 R=4 G=2 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

### BASELINE

`.venv/bin/python -m pytest -q`, run at d7fba46 — the **pre-change** tree, which is this branch's
point (201's tip, since 202 is stacked):

```
........................................                                 [100%]
2704 passed in 160.09s (0:02:40)
```

Green, so the DoD stays *all green*, no baseline exclusions. Written as a reference point rather
than an empirical-output block for the tree under review (lesson 201-C1).

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why this exists | a half-written graph must not report `current` with nothing to do | `staleness_of` never reads the completion key | open |
| G2 | Why this exists | it must be repairable, and the caller told how | `_run` reads `full`, `last_commit`, git diff — never the key | open |
| R1 | Scope 1 | `staleness` + `next_tool_suggestions` derive from `build_complete` | `_suggestions` already fires on `staleness != CURRENT` | open |
| R2 | Scope 2 | the write path reads the key it writes and escalates, reported | H3 | open |
| R3 | Scope 3 | three escalations distinguishable | three disjoint `scope` keys | open |
| R4 | Scope 4 | a fixture that kills a real build | the deliverable, not a mocked flag | open |
| C1 | Not in scope | no transactional incremental | none attempted; noted as a follow-up | open |
| C2 | Not in scope | not the >5 min no-op cost | no build-path cost changes | open |
| C3 | Not in scope | do not re-litigate 201 | 201's shape is reused verbatim | open |
| C4 | Not in scope | the field index is already repaired | n/a | open |
| C5 | Constraints | no contract bump, no language branch, deterministic | `contract.py` untouched | open |
| C6 | Constraints | **no new durable claim** — 072's rule | nothing new is written to disk; `build_complete` already exists | open |
| C7 | Constraints | `index_complete` keeps its meaning (061) | the field stays; consumers are added | open |
| C8 | Constraints | doc budgets | **already discharged** — H5 | open |
| AC1 | AC | with `build_complete = 0`, not `current` and not an empty suggestion list | red before the fix | open |
| AC2 | AC | escalates to a full build and says so, **from a killed build** | | open |
| AC3 | AC | the healthy path is byte-identical on both surfaces (061) | | open |
| AC4 | AC | the kill fixture is what turns AC1/AC2 red when reverted | | open |
| AC5 | AC | three distinct reasons, each named in the payload of the build that took it | | open |
| AC6 | AC | `index_complete` and `staleness` cannot disagree — one derivation (R6.7) | | open |

### AC validation

| AC | Ticket's value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | not `current`, not `[]` | `staleness == "incomplete"` and the suggestion list contains `build_or_update_index` | yes, both halves |
| AC2 | *"escalates … proven from a killed build"* | a real subprocess started and `SIGKILL`ed mid-write, then the next build's `mode` and `scope` key | yes |
| AC3 | *"no field added, no wording changed"* | the healthy payload's exact key set, compared before and after | yes |
| AC4 | *"turns AC1 and AC2 red when reverted"* | the fixture is the input to both; reverting the production change makes both fail | yes |
| AC5 | three reasons | `contract_change` · `scope_change` · `incomplete_index` — **disjoint keys**, N = 3 | yes, per state |
| AC6 | *"cannot disagree"* | both read `build_incomplete(store)`; asserted on the same payload | yes |

No AC is input-shape-dependent.

### Clarifications — all three self-resolved

1. **Does adding a `staleness` value break 061 (a payload contract does not churn)?** No — 061 forbids
   *churn on the healthy path*. `incomplete` appears only where the index is incomplete, which today
   has no honest answer at all. AC3 pins the healthy path byte-for-byte. *Cited:* ticket AC3, C7.
2. **Do the four nav tools need their own change?** No — they call `compute_staleness`, so H2's
   single edit reaches them. That is R1.8, and it is why the fix goes in the shared module.
   *Cited:* `find_callers.py:157`, `find_references.py:128`, `impact.py:207`, `impact_modules.py:137`.
3. **How is "killed for real" achieved deterministically in a test?** Start the build in a
   subprocess, wait for the lock's progress line to show it is past `announce`, then `SIGKILL`. The
   progress line is 177's, already published into the lock. *Cited:* `index_lock.read_build_progress`;
   `build_or_update_index.py` `_progress_sink`.

### Universal inventory — N = 3

| # | Escalation | Payload |
|---|---|---|
| 1 | contract bump (201) | `mode: refused` · `reason: contract_rebuild_required`, or `contract_change` when opted in |
| 2 | adapter scope moved (172) | `mode: full` · `scope_change` |
| 3 | incomplete index (202) | `mode: full` · `incomplete_index` |

Review confirms **every** row.

### Blast radius

`compute_staleness` has **six** consumers — `find_callers`, `find_references`, `impact`,
`impact_modules`, `get_index_status`, and the build tool's busy refusal. All six inherit the new
value by design (H2). Eleven test files mention `staleness`; the trace is in Phase 2.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) N/A (no adapter is touched and no language is named) · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency is added or moved)`

- **§1** — R1.1; R1.8: one predicate feeds `index_complete`, `staleness` and the escalation.
- **§3** — checked, not N/A: a new `staleness` value is payload vocabulary. No node/edge vocabulary,
  field or qname rule moves, so R3.1 needs no bump; `contract.py` is untouched.
- **§4** — R4.2: the predicate is one meta read.
- **§5** — R5.4 (`staleness` holds one register), R5.6 (never attest past what the payload can
  distinguish — hence a fourth value rather than overloading `behind`).
- **§6** — R6.5 (the kill fixture is the observed failure), R6.7 (one derivation), R6.9 (assert at
  the consumers — the status payload and a nav-tool payload, not the predicate alone).
- **§7** — R7.2, R7.6.

No section is `PROVISIONAL`.

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**One predicate, and the shared vocabulary carries it to every reader.**

1. `indexer.build_incomplete(store)` — the single definition site (R1.8/R6.7), beside 201's
   `contract_rebuild_required`, plus the reason and route constants.
2. `staleness.py` gains `INCOMPLETE = "incomplete"`, and `compute_staleness` returns it when the
   predicate holds. Its **six** consumers inherit at once — which is the point: a `find_callers` zero
   over a gutted graph is the confident-wrong-zero the ticket's own opening names.
3. `get_index_status` derives `index_complete` from the **same** predicate, so AC6 holds by
   construction. `_suggestions` needs no edit at all — it already returns the build tool whenever
   `staleness != CURRENT`.
4. `build_or_update_index._run` escalates to `full_build` when the predicate holds, recording
   `incomplete_index` into the existing `scope` dict — the third disjoint key beside 172's
   `scope_change` and 201's `contract_change`.
5. `repair_incomplete: bool = True`. `code-atlas-refresh` passes `False`, gets a refusal naming
   `code-atlas-build --full`, prints one line and exits 0 — W1's ratified answer, and 053's
   *"never builds"* contract kept.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A1 | Report `behind` instead of a new value | `behind` means *HEAD moved*, which is false here. One value for two causes is `one-field-two-questions`, and R5.6 forbids attesting past what the payload can distinguish |
| A2 | Fix it in `get_index_status` only, as Scope 1 literally reads | Four nav tools sign payloads with `staleness` from the same helper. Fixing the status tool alone leaves every other tool reporting `current` over a gutted graph — the exact defect class the ticket's opening cites |
| A3 | Let the git hook self-repair | The ticket's own trigger list includes closing the terminal that owns the backgrounded hook, so an interrupted repair repeats with no signal. Ratified against by the maintainer (W1) |
| A4 | A second on-disk flag for "needs repair" | C6 and 072: nothing new may be written that outlives the process and can lie later. `build_complete` already survives a kill |

### Assumptions

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| A-1 | `build_complete` survives a kill and is readable afterwards | **verified** — it is `set_meta` at `indexer.py:177`/`:273` before the write phases, and the field log's own payload reported `index_complete: false` after the kill |
| A-2 | A subprocess build can be killed deterministically mid-write | **verified by spike** — the proving test does exactly this and is recorded in Phase 3; the lock's progress line (177) is the synchronisation point |
| A-3 | No third-party or runtime behaviour is assumed | **verified** — one extra meta read on paths that already open the store |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `build_incomplete()` + `INCOMPLETE_INDEX` reason/route constants | `code_atlas/indexer.py` | imported by the staleness helper, the build tool and the status tool | R2, AC6 | 1/1 |
| 2 | `INCOMPLETE` value; `compute_staleness` derives it | `code_atlas/tools/staleness.py` | **six** consumers, traced below — all intended | R1, AC1 | 1/1 |
| 3 | `index_complete` from the same predicate | `code_atlas/tools/get_index_status.py` | `_suggestions` unchanged by design | R1, AC6 | 1/1 |
| 4 | `_run` escalates; `repair_incomplete` gate | `code_atlas/tools/build_or_update_index.py` | the MCP signature gains one optional arg | R2, R3, AC2, AC5 | 2/2 |
| 5 | opt out and report | `code_atlas/hooks/refresh.py` | `tests/test_git_refresh_hook.py` — proof collateral | W1 | 1/1 |
| 6 | the kill-a-real-build fixture and AC1-AC6 | `tests/test_killed_build_is_honest.py` (new) | none identified | AC1-AC6 | 6/6 |
| 7 | the tool row and the staleness vocabulary | `docs/TOOLS.md`, `docs/CONVENTION.md` §6 if it enumerates the values | `tests/test_documented_tool_count.py`, `tests/test_doc_size_budget.py` | R7.6 | 1/1 |
| 8 | status, frontmatter, ledger row | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file | `tests/test_backlog_bookkeeping.py` | R7.2 | 1/1 |

**Proof collateral, traced.** `compute_staleness`, run at d7fba46 — the **pre-change** tree:

```
code_atlas/tools/impact_modules.py:137
code_atlas/tools/impact.py:207
code_atlas/tools/build_or_update_index.py:175
code_atlas/tools/get_index_status.py:221
code_atlas/tools/find_callers.py:157
code_atlas/tools/find_references.py:128
```

Six consumers, none of which needs its own edit. Eight existing assertions pin
`staleness == "current"` (`test_incremental.py:176,185,317`, `test_busy_build_staleness.py:57`,
`test_index_ref.py:41`, `test_staleness_scope.py:61,98`, `test_mcp_server.py:348`) — every one on a
**completed** build, so AC3 predicts all eight stay green untouched. That prediction is the
regression check, and it is recorded before the change rather than after.

### Recalled handles — traced

**`one-field-two-questions`** (189, 022). `grep -rn "CURRENT\b" code_atlas/tools/staleness.py`, run
at d7fba46 — the pre-change tree:

```
code_atlas/tools/staleness.py:16:CURRENT = "current"
code_atlas/tools/staleness.py:45:    return CURRENT
```

`current` is returned from one place and answers one question — *is the index at HEAD and clean?*
Folded in as **A1 rejected**: incompleteness gets its own value rather than a second meaning for
`behind`.

**`gate-on-the-invariant-not-on-presence`** (196-C1).
`grep -n "complete is not None and complete != BUILD_COMPLETE" code_atlas/tools/get_index_status.py`,
run at d7fba46:

```
134:    if complete is not None and complete != BUILD_COMPLETE:
```

The existing `index_complete` gate is already on the **invariant** — a recorded `"0"`, not the key's
presence — and an absent key stays silent because it is unknowable. `build_incomplete()` is that
same expression, extracted verbatim, so the new consumers inherit the distinction rather than
re-deriving it.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | integration — kill a real build, then read the status payload | authored | ✅ |
| AC2 | integration | integration — the next build's `mode` and `scope` key after that kill | authored | ✅ |
| AC3 | integration | integration — the healthy payload's key set, plus the eight existing pins | authored | ✅ |
| AC4 | integration | the fixture **is** the artifact; AC1 and AC2 both consume it | authored | ✅ |
| AC5 | logic | integration — three states, three disjoint keys, per state | authored | ✅ |
| AC6 | logic | integration — both fields read off one predicate, asserted on one payload | authored | ✅ |
| W1 | integration | integration — the hook returns 0, builds nothing, and names the route | authored | ✅ |

No ❌, so no exclusion is recorded and the counted line closes with zeros. No AC is
input-shape-dependent; `config.real_corpus_path` is unset and costs this plan nothing.

### Proving test

**`tests/test_killed_build_is_honest.py::test_a_killed_build_does_not_report_current`** — red before
the change, where the payload answers `staleness: "current"` with an empty suggestion list.

```
.venv/bin/python -m pytest tests/test_killed_build_is_honest.py -q
```

### Rollback + porting

`git revert`. Additive: one predicate, one staleness value that appears only on a path with no
honest answer today, one optional argument defaulting to the escalation AC2 asks for. **This branch
is stacked on 201**, so a revert of 202 alone leaves 201 intact. One repo, no porting order.

`SCOPE: M` — unchanged.
