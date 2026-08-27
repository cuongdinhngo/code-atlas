---
id: 178
slug: status-reads-current-while-a-build-is-still-linking
title: '`get_index_status` reads `staleness: "current"` while a build is still linking — and if that build dies, the index keeps saying so'
phase: 1.5b
milestone: Agent-trust
status: todo
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
