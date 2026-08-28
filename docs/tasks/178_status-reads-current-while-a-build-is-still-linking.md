---
id: 178
slug: status-reads-current-while-a-build-is-still-linking
title: '`get_index_status` reads `staleness: "current"` while a build is still linking — and if that build dies, the index keeps saying so'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [072, 077, 010, 177]
---

## Why this exists (field episode, 2026-08-27 — the seventh finding)

Mid-build, the maintainer asked the index how it was doing:

```
get_index_status  →  staleness: "current",  built_at: "…15:47:16Z",
                     dirty_indexed_files: 0
                     (no field naming a build in flight)
```

…while roughly **7.6 %** of the graph's edges had been linked.

> *"Không có field nào nói 'đang có build chạy dở, số liệu này chưa ổn định'. Chỉ
> `build_or_update_index` mới lộ ra `mode: busy`. Một người đọc status lúc này sẽ kết luận index đã sẵn
> sàng … và tin rằng đó là sự thật cuối cùng — chính xác là cái bẫy em vừa rơi vào."*

**072 is the precedent and it only did half the job.** It made the *build tool's refusal* honest — a
`mode: "busy"` returning in 0.0 s no longer reads like success — on the reasoning that *"an agent whose
opening move is 'refresh the index, then investigate' reads it as done and proceeds against an index it
never refreshed."* That is this defect verbatim, one tool over: **the reader who never called the build
gets no signal at all, and `get_index_status` is the tool an agent actually opens first.**

## Root cause — three layers, and only the first is the missing field

- **No lock probe.** `code_atlas/tools/get_index_status.py` has no reference to `write.lock`; its only
  mention of the busy path is a comment at `:41` pointing at 072's shared staleness vocabulary. The
  liveness signal exists on disk (`index_lock.py:19-31`, `flock`-based) and this tool never looks.
- **Meta is stamped before the graph is linked, in both build paths.** `indexer.py:140-142` —
  `full_build` calls `_record_meta(...)` and *then* `_count_late_writes(...)`, which is where
  `resolve_edges` links every bare edge. `update()` has the same order (`:239` then `:247`). So
  `built_at` and `last_commit` are written **when parsing ends**, and the whole link phase runs against
  an index already advertising completion. The observed `built_at` was not a stale read; it was a
  premature stamp.
- **`staleness` has no completeness axis.** `staleness.py:78` computes
  `staleness_of(last_commit, head, dirty=dirty)` — a pure **revision** comparison. A graph that is at
  the right commit and only 7.6 % linked is `current` by that definition, and the definition is not
  wrong; it is being read as *"is this index usable"*, which nothing answers.

**The consequence layers 2 and 3 add, which the missing field alone does not cover:** a build killed
during the link phase leaves `built_at` set, `last_commit` at HEAD and `staleness: "current"` on an
under-linked graph — **permanently**. `flock` releases on process death, so a `build_in_progress` probe
correctly reports *false* the moment the writer dies, and the index goes on lying. This is 082's class
("a claim nobody outside can check") with the claim now durable.

## Scope

1. `get_index_status` carries `build_in_progress: true` when a writer holds `write.lock`, read with a
   **non-blocking, read-only** probe. One definition site, shared with
   [177](177_a-long-build-is-indistinguishable-from-a-hang.md) (R6.7).
2. A **completeness** axis, so an index whose link phase never finished says so — and so the durable
   case above cannot pass as `current`. Design picks the mechanism (stamp completion after the late
   writes rather than before; a phase marker cleared on success; a bare-edge count already in
   `edge_health`) and records the rejected alternatives.
3. **`staleness` keeps meaning revision identity.** The maintainer's proposal was that `staleness` not
   read `current` during a build; this ticket deliberately does not do that, because `staleness_of` is
   shared vocabulary with 072's busy refusal and 077, where its job is to tell a caller *which
   revision* they are about to query. Overloading it would make that answer ambiguous exactly where 072
   made it unambiguous. The build state and the completeness state get their own names. **If design
   disagrees, it must record why.**

### Explicitly not in scope

- Progress or async for the build's own caller — [177](177_a-long-build-is-indistinguishable-from-a-hang.md).
  This ticket is for the reader who did **not** start the build.
- Making the build faster or scope-aware — [172](172_incremental-is-blind-to-a-scope-change.md).
- `dirty_indexed_files: 0`, which is correct as defined (working-tree signal, 166's recorded verdict).

## Constraints

- **Read-only, and it must stay that way.** `try_index_write_lock` (`index_lock.py:20-24`) does
  `mkdir(parents=True, exist_ok=True)` and opens the file `"a+"` — it **creates** the lock file and
  takes `LOCK_EX`. A status probe must do neither: no create, no exclusive lock, no blocking, and no
  answer that depends on the probe succeeding.
- **072 unchanged** — the busy refusal still carries the staleness of the index the loser is about to
  query, and one mutex still governs writes (R4.3).
- **077** — an unbuilt or wedged reply must not block or spawn git; a missing lock file is *not* a
  build in progress.
- **061** — a quiet server with no build running is byte-identical to today.
- **Cost** — one `stat`/`flock` test per status call, measured; never per row.
- **R4.2** determinism · **R1.1** no language branch · **R3** confirm whether the new fields are nav or
  contract vocabulary.

## Acceptance criteria

1. `get_index_status` called while a writer holds `write.lock` reports `build_in_progress: true` —
   pinned by a test that holds the lock from another process/thread.
2. The probe creates no file, takes no exclusive lock and never blocks; a repo with no `.code-atlas/`
   still answers (077), and the absence of a lock file reads as *no build*, not as unknown.
3. An index whose link phase did not complete does **not** present as a finished, current index —
   pinned by a test that interrupts between the parse and the late writes.
4. `staleness` still answers revision identity only, and 072's busy payload is byte-identical — both
   pinned. Any deviation from scope item 3 is recorded with its reason.
5. A quiet server is byte-identical to today (061); the probe's cost is measured.
6. The lock probe has one definition site, reused by 177 (R6.7).
7. Determinism (R4.2), no language branch (R1.1), contract impact confirmed and recorded (R3).

## References

Field episode 2026-08-27, finding (7). Root causes 2 and 3 were found while verifying it, not observed
in the field. `code_atlas/tools/get_index_status.py:41`; `code_atlas/tools/staleness.py:63-86`;
`code_atlas/indexer.py:140-142,239,247`; `code_atlas/index_lock.py:19-31`. Related:
[072](072_busy-build-hides-staleness.md) (**the same rule, applied to the other tool**),
[077](077_index-cannot-name-the-revision-it-describes.md) (the revision axis this must not overload),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md) (the caller's half; shares the probe),
[082](082_claims-nobody-outside-can-check.md), [166](166_read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol.md)
(`dirty_indexed_files`' recorded verdict).

## Session status

- **KEY:** 178 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-178.txt`.
- **Branch:** `feat/178-status-during-a-build`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2182 passed, 0 failed` at `f1c80a2` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 2 leaves the completeness mechanism open — *"stamp completion after the late writes rather than
before; a phase marker cleared on success; a bare-edge count already in `edge_health`"* — and says
design picks and records the rejected alternatives. A **how-decision**: the ticket's own root-cause
analysis plus 072's stated bug class settle it. Resolved in Phase 2. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=3 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R4.3 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2182 passed, 0 failed, 0 skipped at f1c80a2 (bare pytest, Linux host)`

**Premise — every referenced source resolves, and all three root-cause layers reproduce.** Layer 1:
`get_index_status.py` had no reference to `write.lock`. Layer 2: `_record_meta` ran *before*
`_count_late_writes` in both paths. Layer 3: `staleness_of` is a pure revision comparison. The
durable case reproduces exactly as the ticket predicts — see *Empirical outputs*.

**Recall:** `derived-not-listed-invariant` (R6.7, by handle — the probe must be 177's, not a second
one; traced below). `072`/`082` (by area: a claim nobody outside can check) — this ticket is 082's
class with the claim made *durable*, which is what fixes the mechanism choice.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | status must not read `current` while a build runs, nor after one died mid-link | two new axes; `staleness` untouched | field episode | open |
| R1 | Scope 1 | `build_in_progress: true` when a writer holds the lock, read-only probe, one definition site shared with 177 | reuse `index_lock.build_in_progress` | `index_lock.py` (177) | open |
| R2 | Scope 2 | a completeness axis, so the durable case cannot pass as `current` | design picks the mechanism | `indexer.py:140-142,239,247` | open |
| R3 | Scope 3 | `staleness` keeps meaning revision identity; deviation must be recorded | do not touch `staleness_of` | `staleness.py:78` | open |
| AC1 | AC 1 | `build_in_progress: true` under a held lock — pinned from another process/thread | Falsifiable: lock held → field present | proving test | open |
| AC2 | AC 2 | probe creates no file, takes no exclusive lock, never blocks; no `.code-atlas/` still answers; absent lock = no build | Falsifiable: 4 assertions | proving test | open |
| AC3 | AC 3 | an index whose link phase did not complete does not present as finished/current — pinned by interrupting between parse and late writes | Falsifiable: red→green at that seam | proving test | open |
| AC4 | AC 4 | `staleness` still revision-only; 072's busy payload byte-identical | Falsifiable: compare during vs quiet | proving test | open |
| AC5 | AC 5 | quiet server byte-identical (061); probe cost measured | Falsifiable: fields omitted; per-call timing | proving test | open |
| AC6 | AC 6 | the probe has one definition site, reused by 177 (R6.7) | Falsifiable: `get_index_status` imports it, defines nothing | source | open |
| AC7 | AC 7 | R4.2, R1.1, R3 recorded | Falsifiable: grep-gates; no `contract.py` edit | `gate.sh` | open |
| C1 | Constraint | read-only: no create, no exclusive lock, no blocking, no dependence on the probe succeeding | `LOCK_SH \| LOCK_NB` on an `open("r")` | 177's probe | binding |
| C2 | Constraint | 072 unchanged — busy still carries staleness; one mutex (R4.3) | do not touch `_busy` / `try_index_write_lock` | — | binding |
| C3 | Constraint | 077 — unbuilt/wedged must not block or spawn git; a missing lock file is *not* a build | probe returns `False` on `OSError` | — | binding |
| C4 | Constraint | 061 — a quiet server is byte-identical | omit both fields when there is nothing to say | — | binding |
| C5 | Constraint | Cost — one `stat`/`flock` per status call, measured; never per row | one probe in `_attach_build_state` | — | binding |
| C6 | Constraint | R4.2 determinism · R1.1 no language branch · R3 nav vs contract | — | — | binding |

### Root cause (taxonomy: observability / ordering)

All three layers confirmed. The one that makes the defect **durable** is layer 2: because the stamp
came first, a build killed during the link phase left `built_at` set and `last_commit` at HEAD on an
under-linked graph — permanently, because `flock` releases on death and the in-flight probe correctly
goes false. The index then goes on lying with nothing running to contradict it.

### Blast radius

- `store.py`: one new meta key + two constants. No schema change (meta is a key/value table).
- `indexer.py`: `_record_meta` moves after `_count_late_writes` in **both** paths; a `0` stamp at the
  start of each. `_record_meta` itself gains the `1` stamp — it now runs last, so it is the completion
  point as well as the revision point.
- `get_index_status.py`: one helper, called on the built and the unbuilt paths. Both fields omitted
  when silent, so every existing payload assertion holds.
- **Not touched:** `staleness.py`, `_busy`, `try_index_write_lock`, `contract.py`.

## Phase 2 — design

### Approach

Three axes with three different lifetimes, each in the carrier whose failure mode matches it:

| Axis | Question | Carrier | Why that carrier |
|---|---|---|---|
| `staleness` | which revision? | meta (`last_commit`) | unchanged; 072/077 read it this way |
| `build_in_progress` | is one running **now**? | the live `flock` | must die with the writer — a surviving *positive* claim is a lie |
| `index_complete` | did the last build finish linking? | meta (`build_complete`) | must **survive** the writer — a surviving *negative* claim is the truth |

That inversion is the whole design. 177 refused to put liveness in the DB for exactly the reason this
ticket puts completeness there: `kill -9` leaves the row behind, and "a build is running" then becomes
permanently false while "the last build did not finish" becomes permanently **true**.

Plus the ordering fix: `_record_meta` after `_count_late_writes` in both paths, so `built_at` /
`last_commit` are written only once the graph is linked. This alone removes the observed
`staleness: "current"`; the completeness axis names *why* rather than leaving the reader to infer it
from a missing stamp.

Absent `build_complete` (an index built before this key existed) is **unknowable**, so the field is
omitted rather than guessed — R5.6, never attest past what the payload can distinguish.

### Rejected alternatives

- **Make `staleness` not read `current` during a build** — the maintainer's original proposal, which
  the ticket itself declines. `staleness_of` is shared vocabulary with 072's busy refusal and 077,
  where its job is to tell a caller *which revision* they are about to query. Overloading it makes
  that answer ambiguous exactly where 072 made it unambiguous. **No deviation from Scope 3 was
  needed**; both new facts got their own names.
- **A phase marker cleared on success.** Equivalent in effect to `build_complete`, but it stores the
  *phase* — a second, richer thing to keep in step with 052's vocabulary and with 177's line, for no
  extra answer at the status layer. `build_complete` is one bit and cannot drift.
- **Infer completeness from `edge_health`'s bare-edge count** (the ticket's third option). Rejected:
  it cannot separate *"the link phase never ran"* from *"this repo genuinely has unlinkable edges"* —
  R5.2 says unresolvable-but-static references are legitimately `HEURISTIC`, and a repo can sit at a
  high unlinked count while perfectly built. It would also cost a query per status call (C5).
- **Leave the stamp where it was and rely on the new field alone.** Rejected: it leaves `built_at`
  and `last_commit` lying about a graph they were written ahead of, and every consumer of `staleness`
  keeps reading `current`. Fixing the ordering is the root cause; the field is the name.

### Assumptions

| Assumption | Tag |
|---|---|
| Nothing inside `_count_late_writes` reads the meta `_record_meta` writes | verified — full suite green with the order swapped, incl. `test_incremental`, `test_profile_incremental`, resolver and enrichment suites |
| Meta is a key/value table, so a new key is not a schema change | verified — `schema_version` untouched, no migration test fires |
| 177's probe satisfies every C1/C3 constraint already | verified — `open("r")` (no create), `LOCK_SH \| LOCK_NB` (no block, not exclusive), `OSError` ⇒ `False` |
| A no-op incremental still rewrites `indexed_suffixes` | verified, and deliberately **left alone** — that is 173's defect, and this ticket must not pre-empt its design |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `BUILD_COMPLETE_KEY` + the two values | `code_atlas/store.py` | one meta key; no schema change | R2, AC3 | 1/1 |
| `_record_meta` after the late writes in both paths; `0` at start, `1` inside `_record_meta` | `code_atlas/indexer.py` | both build paths | R2, AC3 | 1/1 |
| `_attach_build_state` on the built and unbuilt paths | `code_atlas/tools/get_index_status.py` | omit-when-silent ⇒ existing payloads unchanged | R1, R3, AC1, AC2, AC4, AC5, AC6 | 1/1 |
| Proving tests (8) | `tests/test_status_during_a_build.py` (new) | new file | AC1–AC5 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** `get_index_status` imports the probe and defines
  nothing of its own, so 177 and 178 cannot drift apart:

  ```
  $ grep -n "build_in_progress" code_atlas/tools/get_index_status.py   # Ran at 27ee90510589d4fec3dca687da4ae9c6eab9aa46
  20:from code_atlas.index_lock import build_in_progress
  53:BUILD_IN_PROGRESS = "build_in_progress"
  118:    if build_in_progress(config.db_path):
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a real held lock; and a real `SIGKILL` for the negative) | integration test ×2 | ✅ |
| AC2 | integration (no `.code-atlas/` on disk, timed) | integration test | ✅ |
| AC3 | integration (a build interrupted at the parse/late-write seam) | integration test + red run | ✅ |
| AC4 | logic (compare the same payload during a build and quiet) | integration test ×2 | ✅ |
| AC5 | logic (fields absent) + measurement (200 calls timed) | integration test | ✅ |
| AC6 | logic (one import, no second definition) | source, traced above | ✅ |
| AC7 | guard (grep-gates) + logic (no `contract.py` edit) | `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_status_during_a_build.py::test_an_unfinished_link_phase_does_not_present_as_a_finished_index`
— the durable case, interrupted exactly at the seam the ticket names.
`pytest tests/test_status_during_a_build.py`.

### Rollback + porting

Rollback: revert the three source files and the test file. The meta key is additive and ignored by an
older reader; no migration. Porting: `app` only.

### SCOPE

`SCOPE: M` — one ordering fix, one meta key, one status helper; branch `feat` matches (two new
reported axes, not only a correctness repair).

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `build_in_progress` from 177's probe, one definition site (R6.7) | implemented-as-approved |
| `build_complete` meta: `0` before the graph is touched, `1` after linking returns | implemented-as-approved |
| `_record_meta` after `_count_late_writes` in **both** build paths | implemented-as-approved |
| `staleness_of` untouched; no deviation from Scope 3 | implemented-as-approved |
| Both fields omitted when silent; absent key ⇒ say nothing (R5.6) | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**The field observation, reproduced under the pre-178 ordering** — a build interrupted between the
parse and the late writes:

```
$ .venv/bin/python  (reproduction, pre-178 ordering restored)   # Ran at f1c80a2b18603ebe8a92a17d011796a4c39c2638
  indexed: True     files: 1     nodes: 1     edges: 0
  staleness: 'current'
  built_at: '2026-08-28T01:09:15+00:00'
  last_commit: 'cf9d4e76198332d5e6ed04ba8b2fac46e2303a58'
  edge_health: {'by_tier': {'RESOLVED': 0, 'HEURISTIC': 0, 'DYNAMIC': 0}, 'linked': 0, 'unlinked': 0}
```

`staleness: "current"` and a `built_at` on a graph with **zero linked edges** — the ticket's
`~7.6 %` case, at the limit. The same interruption after the fix:

```
$ .venv/bin/python  (same script, current tree)                 # Ran at 27ee90510589d4fec3dca687da4ae9c6eab9aa46
  indexed: True     files: 1
  staleness: 'unknown'
  built_at: None
  last_commit: None
  index_complete: False
  build_in_progress: <omitted>
```

**Red run A — the two axes removed** (`_attach_build_state` calls deleted):

```
$ .venv/bin/pytest -q tests/test_status_during_a_build.py       # Ran at f1c80a2b18603ebe8a92a17d011796a4c39c2638
FAILED ::test_status_names_a_build_in_flight
FAILED ::test_an_unfinished_link_phase_does_not_present_as_a_finished_index
FAILED ::test_staleness_still_answers_revision_identity_only
FAILED ::test_a_killed_build_stops_claiming_to_be_running
4 failed, 4 passed
```

**Red run B — the premature stamp restored** (`_record_meta` back before `_count_late_writes`):

```
$ .venv/bin/pytest -q tests/test_status_during_a_build.py       # Ran at f1c80a2b18603ebe8a92a17d011796a4c39c2638
>           assert store.get_meta(BUILD_COMPLETE_KEY) == "0"
E           AssertionError: assert '1' == '0'
FAILED ::test_an_unfinished_link_phase_does_not_present_as_a_finished_index
1 failed, 7 passed
```

A build that died mid-link stamps itself **complete**. That is the durable lie, pinned.

**Green run:**

```
$ .venv/bin/pytest -q                                            # Ran at 27ee90510589d4fec3dca687da4ae9c6eab9aa46
2190 passed in 146.90s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_status_names_a_build_in_flight` (lock held) + `test_a_killed_build_stops_claiming_to_be_running` (real `SIGKILL`) |
| AC2 | `test_the_probe_creates_nothing_and_never_blocks` — no `.code-atlas/` created, answers unbuilt, absent lock ⇒ field omitted, timed |
| AC3 | `test_an_unfinished_link_phase_does_not_present_as_a_finished_index` + red run B + the reproduction above |
| AC4 | `test_staleness_still_answers_revision_identity_only`, `test_the_busy_refusal_payload_is_unchanged`; `staleness.py` untouched. **No deviation from Scope 3 to record.** |
| AC5 | `test_a_completed_build_says_nothing_extra` (061) and `test_the_probe_costs_one_lock_test_per_call` (200 calls, < 0.05 ms/call budget) |
| AC6 | the R6.7 trace above — one import, no second definition |
| AC7 | `gate.sh` R1.1/R2.2/R4.1 green; no `contract.py` edit ⇒ no bump (nav vocabulary, recorded) |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2182 passed / 0 failed` at `f1c80a2` →
`2190 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`178-C1` (type-2, `match-the-carrier-to-the-claims-failure-mode`, seen: 177, 178) — **recurring**, and
it is the same class as `177-C1` seen from the other side: a claim that must not outlive its subject
goes in something the OS revokes; a claim that must outlive it goes in the store. Both tickets in this
batch turned on it. **Cannot promote yet:** recurrence is 2 within one batch by one author, and
`/mango:promote` is the cross-ticket path — this is a note for it, not a rule. seen=2, routed nowhere.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: the field observation reproduced then fixed, two red runs, full suite
delta-green, ruff/mypy green.
