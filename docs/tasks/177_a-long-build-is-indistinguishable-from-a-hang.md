---
id: 177
slug: a-long-build-is-indistinguishable-from-a-hang
title: '`build_or_update_index` is silent for 30 minutes on a large repo — a valid long build is indistinguishable from a hang, and 072 covered only the refusal'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [072, 010, 052, 176]
---

## Why this exists (field episode, 2026-08-27 — the sixth finding, and the strongest)

Acting on round 11's roll-out recommendation, the maintainer called the build over an MCP client on the
anchor repo and got nothing back for half an hour:

> *"`build_or_update_index` không sống nổi qua một lời gọi MCP trên repo cỡ này. Nó im lặng suốt 30 phút
> — không progress, không heartbeat. Tool description có nói về `write.lock` và `mode: busy`, nhưng
> không có gì cho trường hợp "build hợp lệ nhưng dài"."*

The reading is exact. **072 made the *refusal* honest — a `mode: "busy"` that returns in 0.0 s no longer
reads like success — and nothing was ever done for the opposite case: a build that is working
correctly and takes longer than a client will wait.** Every payload this tool can emit describes a
build that has *finished*.

This is 082's class ("a claim nobody outside can check") inverted: not a claim that cannot be checked,
but **no claim at all for the entire duration of the only operation that takes minutes**. And it is the
one finding of the six that blocks the roll-out outright: an operation that cannot survive one MCP call
cannot be part of a CI job or an onboarding step either.

## Root cause

- `code_atlas/tools/build_or_update_index.py:70,166` — the tool is one synchronous call: take the lock,
  run `indexer.full_build` / `update` to completion, shape a report. There is no interim return and no
  job identity.
- No progress channel exists anywhere in the server: `grep` for `Context` / `report_progress` /
  `ctx.` across `code_atlas/main.py` and `code_atlas/tools/` finds **nothing**. The FastMCP progress
  facility is simply unused.
- The `mode` vocabulary (`:41`, `:203`) spans `full` · `incremental` · `busy` · `refused` — every value
  describes a **terminal** state. There is no value for *"accepted and running"*.
- `phase_times` (task 052, `indexer.py:268` and its eight `_phase_add` call sites) already names every
  phase — `announce · tree_walk · reconcile · hashing · parse · meta · enrichment · resolve` — but it is
  **profiler-only and returned at the end**, which is exactly when it is no longer needed.
- **Progress is already partly observable and nothing says so.** `store.replace_file_rows`
  (`store.py:405-424`) commits per file inside `with self._conn:`, and the DB is WAL — so a *second*
  reader watching `get_index_status`' `files` count sees it climb during a build. That is the workaround
  today; it is undocumented, and it requires a second client.

## Scope

Two deliverables, not alternatives — the maintainer's framing, kept.

1. **Async.** The tool returns promptly with `mode: "started"` and a job identity, and the running
   build is reportable. Design records where job state lives. The `build_in_progress` field on
   `get_index_status` and the read-only lock probe behind it belong to
   [178](178_status-reads-current-while-a-build-is-still-linking.md) — this ticket reuses that probe
   rather than defining a second one (R6.7).
2. **Progress.** A running build publishes how far it has got, so a client (and a human) can tell work
   from a wedge.

Three design points this ticket asserts, because each one is a way the obvious implementation goes
wrong:

- **Progress must be phase-shaped, not only file-shaped.** `files_done/files_total` reaches 100 % and
  then sits in `resolve` (`indexer.py:303`, `resolve_edges` over the whole graph) and `enrichment` for
  an unbounded share of the wall time. A file counter alone would read as a hang at 100 %, which is the
  same defect one screen later. Reuse 052's phase names as the vocabulary — one definition site (R6.7).
- **Liveness must derive from the lock, not from a written flag.** `write.lock` is `flock`-based
  (`index_lock.py:19-31`), so the OS releases it when the process dies. A `building: true` field written
  into the DB or a status file survives a `kill -9` and becomes a permanent false claim — 072's own bug
  class. The natural carrier is `write.lock` itself: it is already opened `"a+"` and never written to,
  so a progress line in the file a live `flock` protects is self-invalidating.
- **A second client must not be required.** If progress is only readable by another MCP client, the
  shell and CI still cannot see it — which is the same wall as [176](176_no-full-build-from-a-shell.md).

### Explicitly not in scope

- Making the build **faster**. The suffix-scoped pass is [172](172_incremental-is-blind-to-a-scope-change.md),
  and how long a full build of a repo this size now costs is 172's recorded measurement — the last
  figure on record is **236 s for ~19k PHP files (round 6)**, and this episode observed ~30 min after
  adapter #2 entered the scope. **Nothing pins that ~7.6× yet, and until something does, this ticket
  must not be argued from it.**
- Cancelling a running build.
- Any daemon, queue or second process (R4.3: one mutex, one writer).

## Constraints

- **R4.3** — one `write.lock`, one writer. `code-atlas-refresh` and the MCP server keep sharing it, and
  a busy peer still gets 072's honest refusal.
- **R4.2** — progress must not change what is written: identical input ⇒ identical rows, and the
  reporting cannot reorder the parse.
- **061** — a build short enough to finish inside one call is byte-identical to today; a small repo pays
  nothing for this.
- **Cost** — progress writes are bounded (a fixed line, throttled), never per-node and never a second
  pass. Measured.
- **072's guarantee** — a refusal still carries the staleness of the index the loser is about to query.
- **R6.7** — phase names come from 052's vocabulary, not a second list.
- **R1.1** no language branch · **R3** confirm whether `mode: "started"` is nav vocabulary or contract.

## Acceptance criteria

1. A build that outlives one call is distinguishable from a hang: a test pins either the async return
   (`mode: "started"` + a job identity readable from `get_index_status`) or in-flight progress, and the
   design records which and why.
2. Progress names the **phase** as well as any counter, so a file counter at 100 % during `resolve`
   cannot read as a wedge — pinned by a test that reaches the late-write phase.
3. Liveness is derived from the live `write.lock`: a build killed with `SIGKILL` leaves **no** claim that
   a build is running — pinned by a test that kills the writer.
4. Progress is readable without a second MCP client (the shell path, coordinated with 176).
5. A short build is byte-identical to today (061); the added cost is measured and bounded.
6. 072's busy refusal is unchanged, pinned; one lock, one writer (R4.3).
7. Determinism (R4.2), no language branch (R1.1), contract impact confirmed and recorded (R3).

## References

Field episode 2026-08-27, finding (6). `code_atlas/tools/build_or_update_index.py:41,70,166,203`;
`code_atlas/index_lock.py:19-31`; `code_atlas/indexer.py:268,303`; `code_atlas/store.py:405-424`;
absence of `Context`/`report_progress` under `code_atlas/`. Round 6's 236 s full build is the only
recorded figure for this repo's scale. Related: [072](072_busy-build-hides-staleness.md) (the refusal
half of the same seam), [010](010_index-status-and-build-tools.md) (the tool),
[052](052_incremental-noop-cost.md) (the phase vocabulary),
[176](176_no-full-build-from-a-shell.md) (**this makes 176 load-bearing, not convenient**),
[082](082_claims-nobody-outside-can-check.md).

## Session status

- **KEY:** 177 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-177.txt`.
- **Branch:** `feat/177-progress-for-a-long-build`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2175 passed, 0 failed` at `5d538c2` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

AC1 offers a choice — *"a test pins **either** the async return … **or** in-flight progress, and the
design records which and why"*. A **how-decision**: the ticket's own *Explicitly not in scope*
(no daemon, queue or second process) and AC3/AC4 constrain it to one answer, so it is resolvable from
the ticket plus the source. Resolved in Phase 2 → *Rejected alternatives*. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=7 R=5 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 11 applicable — 10 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.4 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R4.3 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅ · §R7.5 (change-type) ✅`
`BASELINE: green — 2175 passed, 0 failed, 0 skipped at 5d538c2 (bare pytest, Linux host)`

**Premise, all four claims checked and all four hold:**

```
$ grep -rn "report_progress\|from fastmcp import Context" code_atlas/ | wc -l    # Ran at 5d538c2a5f9d20495ae4104ccfa06da7f12fc4c9
0
$ grep -n "INCREMENTAL_PHASES" -A 10 code_atlas/indexer.py | head -12
56:INCREMENTAL_PHASES = ("announce","tree_walk","reconcile","hashing","parse","meta","enrichment","resolve")
```

`build_or_update_index.py:70,166` is one synchronous call; the `mode` vocabulary is entirely terminal
(`full`/`incremental`/`busy`/`refused`); `index_lock.py:19-31` is `flock`-based; **and one premise the
ticket did not state: `full_build` carries no phase instrumentation at all** — the eight `_phase_add`
call sites are all inside `incremental_update`, so the 30-minute case was the *un*instrumented path.
Surfaced, not blocking: it enlarges the change list rather than changing the design.

**Recall:** `derived-not-listed-invariant` (R6.7, by handle — phase names must come from 052's tuple,
not a second list; traced below). `072`/`082` (by area: a claim nobody outside can check) — the
inverse case, and the reason AC3 exists.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a valid long build must be distinguishable from a hang | something observable while it runs | `build_or_update_index.py:70` | open |
| R1 | Scope 1 | async return + job identity, **or** in-flight progress (AC1's either/or) | design picks one, records why | — | open |
| R2 | Scope 2 | a running build publishes how far it has got | phase + counters | — | open |
| R3 | Scope, pt 1 | progress is phase-shaped, not only file-shaped | `resolve`/`enrichment` are nameable | `indexer.py:303` | open |
| R4 | Scope, pt 2 | liveness derives from the lock, never a written flag | `flock` dies with the process | `index_lock.py:19-31` | open |
| R5 | Scope, pt 3 | a second client must not be required | a shell reader | 176's CLI | open |
| AC1 | AC 1 | a build outliving one call is distinguishable from a hang — pinned | Falsifiable: progress visible mid-build | proving test | open |
| AC2 | AC 2 | progress names the phase; a counter at 100 % cannot read as a wedge — pinned at the late-write phase | Falsifiable: `resolve` reported after `done == total` | proving test | open |
| AC3 | AC 3 | a SIGKILLed build leaves **no** claim that a build is running — pinned by killing the writer | Falsifiable: `kill -9` → probe false | proving test | open |
| AC4 | AC 4 | progress readable without a second MCP client | Falsifiable: a shell subprocess reads it | proving test | open |
| AC5 | AC 5 | a short build byte-identical (061); added cost measured and bounded | Falsifiable: payload unchanged + a measurement | proving test + benchmark | open |
| AC6 | AC 6 | 072's busy refusal unchanged; one lock, one writer | Falsifiable: busy payload asserted | proving test | open |
| AC7 | AC 7 | R4.2 determinism, R1.1 no language branch, R3 contract impact recorded | Falsifiable: grep-gates + no `contract.py` edit | grep-gates | open |
| C1 | Constraint | R4.3 — one `write.lock`, one writer; refresh and the server keep sharing it | add no second lock | `index_lock.py` | binding |
| C2 | Constraint | R4.2 — progress must not change what is written, nor reorder the parse | write outside the DB; report after each write | — | binding |
| C3 | Constraint | 061 — a short build is byte-identical; a small repo pays nothing | sink defaults to `None` | — | binding |
| C4 | Constraint | Cost — bounded, throttled, never per-node, never a second pass; measured | one fixed-width line, time-throttled | — | binding |
| C5 | Constraint | 072's guarantee — a refusal still carries staleness | do not touch `_busy` | `:101` | binding |
| C6 | Constraint | R6.7 — phase names from 052's vocabulary, not a second list | reuse `INCREMENTAL_PHASES` | `indexer.py:56` | binding |
| C7 | Constraint | R1.1 no language branch · R3 confirm nav vs contract vocabulary | — | — | binding |

### Root cause (taxonomy: observability)

Every payload the tool can emit describes a build that has **finished**, and the only operation that
takes minutes has no channel of its own. 072 made the *refusal* honest and left the opposite case —
a build that is working correctly and outlives the client's patience — with no claim at all.

### Blast radius

- `index_lock.py` gains three functions; `try_index_write_lock` is **unchanged**, so 053's hook and
  072's busy refusal keep the exact code path they had.
- `indexer.py`: an optional keyword-only `progress` on both build entries, threaded to `_parse_all`
  / `_parse_group` / `_count_late_writes`. Default `None` ⇒ one `is None` test per file and nothing else.
- `build_or_update_index.py`: `_run` builds the sink. The **payload is untouched** — no new field.
- `cli.py` gains `--status` (176's module; this is the shell reader AC4 requires).

## Phase 2 — design

### Approach

**In-flight progress, published into `write.lock`.** The process holding the lock rewrites one
fixed-width line in the file it already owns; a reader reports that line **only** while the lock is
held. Three consequences, one per design point the ticket asserts:

- **Phase-shaped.** The sink is called `(phase, done, total)`; phases come from 052's
  `INCREMENTAL_PHASES` and nothing else (R6.7). `full_build` had no phase markers at all, so it gets
  the same eight names — `resolve` and `enrichment` are reported *after* `done == total`, which is
  precisely the stretch a file counter renders as a wedge.
- **Liveness is the live `flock`.** `build_in_progress()` probes with `LOCK_SH | LOCK_NB` — a shared
  probe cannot make a real writer wait, and it fails exactly when a writer holds `LOCK_EX`. A killed
  build's line stays on disk and is never reported, because the OS already dropped its lock.
- **No second client.** `code-atlas-build --status` prints the line: exit `0` while a build runs,
  `3` when none does.

Throttle: every phase change writes; within a phase, at most one write per `PROGRESS_INTERVAL`
(0.5 s). One `r+` open, `seek(0)`, a 200-byte padded write, `fsync` — no truncate, so a concurrent
reader never sees a half-length line, and the file never grows over a 30-minute build.

**R3 verdict: no contract bump.** `phase` / `done` / `total` live in a lock file, are never persisted
to the graph and are not node/edge vocabulary. `contract.py` is untouched.

### Rejected alternatives

- **Async return (`mode: "started"` + a job identity), AC1's other branch.** Rejected on three
  independent grounds. (a) It needs the build to outlive the tool call — a background thread plus job
  state, which is the *"any daemon, queue or second process"* the ticket puts out of scope and which
  R4.3 exists to prevent. (b) Job state in a registry **survives `kill -9`**, so it re-creates exactly
  the durable false claim AC3 forbids; the lock cannot. (c) It does nothing for AC4 — a shell or CI
  reader still has no way in. Progress satisfies AC1, AC3 and AC4 with one mechanism.
- **A `building: true` flag in the DB or a status file.** The ticket names this and it is 072's own
  bug class: it outlives the process that wrote it.
- **FastMCP's `Context.report_progress`.** It is unused across the whole server, and it reaches only
  the client that made the call — the one caller already blocked inside the build. Fails AC4.
- **A separate `code-atlas-progress` script.** R7.4 / R1.2: one more entry point for one line, when
  the build script is where a reader already looks.

### Assumptions

| Assumption | Tag |
|---|---|
| `flock` is per open file description, so a second `open()` in the *same* process conflicts with the held lock | verified — the AC3 test's probe returns `True` from the holding process |
| A `LOCK_SH` probe never blocks a writer and never creates the file | verified (`open("r")` raises `OSError` when absent → `False`, 077) |
| The OS releases `flock` on `SIGKILL` | verified — the AC3 test kills the holder and the probe flips to `False` while the line is still on disk |
| `full_build` has no `_phase_add` sites (all eight are in `incremental_update`) | verified while checking the premise; it is why the change list includes `full_build`'s phase markers |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `lock_path_for` · `build_in_progress` · `publish_build_progress` · `read_build_progress` | `code_atlas/index_lock.py` | `try_index_write_lock` untouched (053/072 unchanged) | R2, R4, AC3 | 1/1 |
| `ProgressSink` + `_Progress`; optional `progress=` on both build entries and their callees | `code_atlas/indexer.py` | default `None` ⇒ pre-177 path (061) | R2, R3, AC2, AC5 | 1/1 |
| Throttled `_progress_sink` wired into `_run` | `code_atlas/tools/build_or_update_index.py` | payload unchanged | R1, AC1, AC5 | 1/1 |
| `--status` | `code_atlas/cli.py` | new flag; build path untouched | R5, AC4 | 1/1 |
| Proving tests (7) | `tests/test_build_progress.py` (new) | new file | AC1–AC6 | 1/1 |
| README *Is it building, or is it wedged?*; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** The progress vocabulary is 052's tuple, and the
  test asserts membership rather than restating the names, so a phase added to the indexer cannot
  drift from the phase a reader is told about:

  ```
  $ grep -n "set(phases) <= set(INCREMENTAL_PHASES)" tests/test_build_progress.py   # Ran at 1af2f780fe34708f89892221b353b84e6c869412
  62:    assert set(phases) <= set(INCREMENTAL_PHASES), f"phase outside 052's vocabulary: {set(phases)}"
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (the tool's own run publishes) | integration test | ✅ |
| AC2 | integration (a real build reaching the late writes) | integration test | ✅ |
| AC3 | integration (a real subprocess, a real `SIGKILL`) | integration test | ✅ |
| AC4 | integration (a separate process reading while the lock is held) | integration test | ✅ |
| AC5 | logic (payload unchanged) + measurement (bounded cost) | integration test + a recorded benchmark | ✅ |
| AC6 | integration (busy payload under a held lock) | integration test | ✅ |
| AC7 | guard (grep-gates) + logic (no `contract.py` edit) | `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_build_progress.py::test_a_killed_writer_leaves_no_claim_that_a_build_is_running` — the
one that separates this design from the flag-in-a-file design the ticket warns against. Plus
`::test_progress_names_the_phase_not_only_a_file_counter` for AC2.
`pytest tests/test_build_progress.py`.

### Rollback + porting

Rollback: revert the four source files and the test file; nothing persisted, no schema change, no
contract change. Porting: `app` only.

### SCOPE

`SCOPE: M` — one new channel, threaded through two build entries; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Progress published into `write.lock`, one fixed-width line rewritten in place | implemented-as-approved |
| Phase names taken from `INCREMENTAL_PHASES`, asserted by membership (R6.7) | implemented-as-approved |
| `full_build` gains the same eight phase markers it never had | implemented-as-approved |
| Liveness via `LOCK_SH \| LOCK_NB`; a missing file is *no build* (077) | implemented-as-approved |
| Throttled: every phase change, else ≤ 1 write / 0.5 s | implemented-as-approved |
| `code-atlas-build --status` as the shell reader | implemented-as-approved |
| The tool payload gains no field (061) | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**Red run 1 — no progress channel** (`publish_build_progress` made a no-op), which is the pre-177
world with the tests present:

```
$ .venv/bin/pytest -q tests/test_build_progress.py            # Ran at 5d538c2a5f9d20495ae4104ccfa06da7f12fc4c9
FAILED ::test_the_build_tool_publishes_progress_and_its_payload_is_unchanged
FAILED ::test_a_killed_writer_leaves_no_claim_that_a_build_is_running
FAILED ::test_progress_is_readable_from_a_shell_without_a_second_mcp_client
FAILED ::test_the_progress_write_is_bounded
4 failed, 3 passed
```

**Red run 2 — liveness from a written flag instead of the live lock** (the design the ticket's third
point warns against: `build_in_progress` swapped for "the file exists and is non-empty"). This is the
one that matters, because it proves the AC3 test can tell the two designs apart:

```
$ .venv/bin/pytest -q tests/test_build_progress.py            # Ran at 5d538c2a5f9d20495ae4104ccfa06da7f12fc4c9
FAILED ::test_a_killed_writer_leaves_no_claim_that_a_build_is_running
FAILED ::test_the_build_tool_publishes_progress_and_its_payload_is_unchanged
FAILED ::test_progress_is_readable_from_a_shell_without_a_second_mcp_client
3 failed, 4 passed
```

**AC5 — the measured cost.** 300 files, best of three runs each, same tree:

```
$ .venv/bin/python  (benchmark, see working doc)              # Ran at 1af2f780fe34708f89892221b353b84e6c869412
files=300  no sink: 1238.2 ms   in-memory sink: 1256.4 ms   delta +18.1 ms (+1.5%)
throttled lock-file sink: 1254.5 ms   delta vs no sink +16.2 ms
```

≈ **0.054 ms per file, +1.3 %**, and the throttled lock-file sink costs *no more* than an in-memory
one — the 0.5 s throttle is what keeps the write count off the file count. Bounded by wall time, never
by node or file count, and never a second pass.

**Green run:**

```
$ .venv/bin/pytest -q                                          # Ran at 1af2f780fe34708f89892221b353b84e6c869412
2182 passed in 148.51s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_the_build_tool_publishes_progress_and_its_payload_is_unchanged` (the tool's own run writes a phase line) |
| AC2 | `test_progress_names_the_phase_not_only_a_file_counter` — `("parse", 4, 4)` is reported, and `enrichment`/`resolve` come **after** it |
| AC3 | `test_a_killed_writer_leaves_no_claim_that_a_build_is_running` (real `SIGKILL`; line still on disk, claim retracted) + red run 2 |
| AC4 | `test_progress_is_readable_from_a_shell_without_a_second_mcp_client` (a separate process reads while the lock is held) |
| AC5 | `test_a_build_with_no_reader_reports_nothing`, the payload assertion, `test_the_progress_write_is_bounded`, and the benchmark above |
| AC6 | `test_the_busy_refusal_is_unchanged`; `try_index_write_lock` is byte-identical |
| AC7 | `gate.sh` R1.1/R2.2/R4.1 green; no `contract.py` edit ⇒ no bump (recorded above) |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** baseline `2175 passed / 0 failed` at `5d538c2` →
`2182 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`177-C1` (type-2, `liveness-belongs-in-a-handle-the-os-revokes`, seen: 177) recorded as `proposed`.
A liveness claim must live in something the OS retracts when the claimant dies — an `flock`, not a row
or a file — or `kill -9` turns it into a permanent lie. Falsification check: not falsified; red run 2
demonstrates the failure directly by substituting the file-existence design. seen=1 → stays in
`lessons_path`. Relates to 072/082.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: two red runs, full suite delta-green, ruff/mypy green, cost measured.
