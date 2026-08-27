---
id: 177
slug: a-long-build-is-indistinguishable-from-a-hang
title: '`build_or_update_index` is silent for 30 minutes on a large repo — a valid long build is indistinguishable from a hang, and 072 covered only the refusal'
phase: 1.5b
milestone: Agent-trust
status: todo
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

1. **Async.** The tool returns promptly with `mode: "started"` and a job identity; `get_index_status`
   reports the running build. Design records where job state lives.
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
