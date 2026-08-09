---
id: 072
slug: busy-build-hides-staleness
title: '`mode: "busy"` returns in 0.0 s and reads like success — the caller then queries a stale index'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [053, 033]
---

## Goal
Two clients called `build_or_update_index` at once. The lock did its job: one built, one was refused,
nothing corrupted. But the refusal returns in **0.0 seconds** carrying no staleness information, so an
agent whose opening move is *"refresh the index, then investigate"* reads it as done and proceeds
against an index it never refreshed. Make the refusal say what the caller is about to query.

## Evidence (memory/concurrency field run, 2026-08-09, anchor repo)
Two clients released simultaneously through a barrier, both calling `build_or_update_index(full=false)`:

```
--- client 0: 0.0s
    {"mode": "busy", "requested_full": false, "reason": "another_build_running",
     "db_path": "…/.code-atlas/graph.db", "seconds": 0.0}
--- client 1: 83.2s
    {"mode": "incremental", "wrote": {"files": 107, …},
     "graph": {"files": 18878, "nodes": 185966, "edges": 1782725}, "seconds": 83.21}
# errors: none; afterwards staleness "current"
```

The mechanism is correct and stays: `try_index_write_lock` (`index_lock.py:19`) gives real mutual
exclusion via `write.lock`, and the busy branch returns **without opening the DB**
(`build_or_update_index.py:53-62`) — a deliberate property worth keeping.

What the loser cannot tell from that payload:
- whether the index it is about to read is **current or behind** — `get_index_status` in the same run
  reported `"staleness": "behind"` with `last_commit` ≠ `head_commit`, a field the refusal never
  carries;
- whether the winner's build will finish **soon or in 83 seconds**;
- that the correct next move is to wait and re-check rather than proceed.

The 0.0 s latency is what makes it read as success. A refusal that takes no time and returns no
warning is indistinguishable, to a caller skimming for "did the refresh happen", from a no-op
"already current" — and the tool has no such response today, so nothing teaches the caller otherwise.

This is one of exactly two API shapes in the whole run that can mislead a caller under concurrency;
the other is [071](071_answers-do-not-name-their-tree.md). Both produce a **confident answer rather
than an error**. The rest of the concurrency path was honest: 452 drift events under 3-way contention
produced zero soft-fails and zero `SQLITE_BUSY` reaching a caller.

## Scope / Deliverables
- **Attach the staleness of the index the caller is about to query** to the busy payload —
  `staleness`, `last_commit` and `head_commit` in the shapes `get_index_status` already uses, so a
  caller has one vocabulary, not two.
- **Preserve the no-DB-open property, or justify losing it.** The busy branch currently answers without
  touching the database, which is why it costs 0.0 s under contention. Reading staleness may require
  opening it. Measure the cost under N-way contention and record the decision; if the cost is real,
  a cheaper signal (e.g. reporting only that the answer is unverified) is acceptable and must be
  stated as such rather than silently substituted.
- **Say the request was not performed, in the reason vocabulary.** `reason: "another_build_running"`
  states the cause; nothing states the consequence. Whatever channel [033](033_nav-reason-codes.md)
  established for "this is not the answer you asked for" applies here too.
- **Decide whether busy should ever wait.** A bounded wait-and-retry inside the tool is one option;
  returning immediately with enough information for the caller to decide is the other. Pick one and
  record why. Do not do both.
- **State the operational rule in the docs.** The measured recipe is: refresh the index **once before
  dispatching a fan-out, never from inside an agent**. That is a docs deliverable of this ticket, not
  a code one.

## Constraints
- R4 — deterministic: the same lock state and the same index produce the same payload.
- R5.3 — busy is not a config error; it stays a normal, non-raising outcome. This ticket adds
  information to it, it does not turn it into a failure.
- 053 — lock semantics do not change. Exactly one writer, no corruption, no lock upgrade.
- 061 — the added fields land only on the busy payload, which is rare by construction.

## Acceptance criteria
- A busy refusal carries enough for the caller to distinguish "the index is current, proceeding is
  safe" from "the index is behind and a build is in flight".
- The successful build payload is unchanged.
- A test drives two concurrent builds and asserts the loser's payload contains the staleness signal
  and that exactly one build ran.
- The busy-branch latency under contention is measured and recorded before and after.
- `docs/` states the before-dispatch refresh rule for parallel agents.

## References
Memory/concurrency field run 2026-08-09 §5 ("concurrent rebuild — the deliberate separate trial"),
§9 fix #2 and the configuration table. `code_atlas/tools/build_or_update_index.py:53-62` (the busy
branch), `code_atlas/index_lock.py:19` (`try_index_write_lock`),
`code_atlas/tools/get_index_status.py` (the staleness vocabulary to reuse),
`code_atlas/hooks/refresh.py:49` (an existing consumer that already branches on `mode == "busy"`).
Related: [053](053_refresh-on-checkout-hook.md) (the lock), [033](033_nav-reason-codes.md),
[071](071_answers-do-not-name-their-tree.md) (the run's other silent-wrong-answer shape).
