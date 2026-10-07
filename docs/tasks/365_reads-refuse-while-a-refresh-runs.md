---
id: 365
slug: reads-refuse-while-a-refresh-runs
title: 'While a background refresh runs, read_symbol and find_references answer index_stale, so the agent drops to Grep'
phase: 2
milestone: Adoption
status: todo
depends_on: [356, 357, 274]
---

## Why this exists

356 keeps a full rebuild behind a shadow index. The anchor project's field retro shows that the
incremental path still refuses. This is the most frequent reason the agent fell back to Grep (the
7 PRs below), and it still happens after 356 landed.

- F1 (2 PRs, 2026-10-07): `find_references` on a table → `index_stale` "during the background
  build".
- F2 (1 PR): index `behind`, and `read_symbol` on a controller class → `index_stale`.
- F3 (3 PRs): `read_symbol` → `index_stale` while a build ran.
- F4 (1 PR): `read_symbol` on a table → `subject_ambiguous` mid-rebuild.

**Reproduced (2026-10-07, real PHP adapter, scratch repo).** Build, commit an edit to `A.php`, then
hold `write.lock` and a SQLite write transaction the way an incremental refresh does:

| Call while the lock is held | Answer | Wall |
|---|---|---|
| `read_symbol` / `find_callers` / `find_references`, subject **unchanged** | `ok` | 0.0 s |
| `read_symbol A::m`, subject **changed** | `index_stale`, no route | 5.0 s |
| `find_callers A::m`, subject changed | `index_stale` | 5.0 s |
| `find_callers` / `find_references A::m`, `serve_behind=true` | `index_behind_subject_changed`, 1 hit | 5.0 s |
| Any of the above, lock released | `ok` | 0.0 s |

So an unchanged subject already answers. The refusal hits only the subject the commit just changed,
which is exactly the file an agent asks about next. Read-through repair (035) calls
`reparse_file`, which writes to the live DB, waits out `busy_timeout=5000` behind the refresh's
transaction, fails, and the guard answers `index_stale`. The caller cannot cure that refusal: the
cure, a refresh, is already running. `read_symbol` has no `serve_behind` and no route at all.

**Decision.** Treat a held lock as "repair is in progress", not as a repair failure. This narrows
257's opt-in (PLAN §19) to one condition instead of reversing it, so it needs a one-line §19 entry.

- *Rejected: serve unchanged subjects labelled.* The table shows they already answer `ok`, so this
  would change nothing.
- *Rejected: flip the `serve_behind` default.* It changes every behind answer to fix one condition.
- *Rejected: wait for the refresh.* An incremental costs about a minute on a large index (052, 357).

## Scope

1. Read-through repair probes `write.lock` without blocking (`index_lock.try_index_write_lock`)
   before it writes. When the lock is held, skip the write and the 5 s wait.
2. With the lock held, `find_callers`, `find_references` and `impact` on a changed subject answer
   from the built graph as 267's `index_behind_subject_changed`, with the built revision, without
   `serve_behind`. Add `refresh_in_progress: true`. Inbound edges come from other files, which a
   per-file staleness check vouches for.
3. With the lock held, `read_symbol` on a changed subject parses the file *without writing*. Split
   `reparse_file` into a parse half and a write half; the store is untouched (R1.4). It serves the
   current bytes and span, labelled as read through this call. If the parse fails, it refuses as
   today, but with a route and with `refresh_in_progress`.
4. `get_index_status` says that a refresh is running and the served graph is usable.
5. Out of reach of this repro, and still to reproduce: F1 ran during a 356 *full* rebuild, which
   writes the shadow and leaves the live DB unlocked. F4 is `subject_ambiguous`.
   Fix them here only if they share this cause; otherwise file them.

## Acceptance criteria

- **AC1:** With the lock held, `find_callers` and `find_references` on a subject changed since the
  build answer `index_behind_subject_changed` with the built revision and `refresh_in_progress`,
  in under 1 s.
- **AC2:** With the lock held, `read_symbol` on that subject returns its current source, in under
  1 s, and the store is byte-identical afterwards.
- **AC3:** Unchanged subjects, and every call with no lock held, are byte-identical to today.
