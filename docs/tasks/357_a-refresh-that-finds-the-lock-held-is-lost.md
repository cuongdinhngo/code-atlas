---
id: 357
slug: a-refresh-that-finds-the-lock-held-is-lost
title: 'A refresh that finds the write lock held is dropped, so the index can stop short of HEAD'
phase: 2
milestone: Freshness
status: todo
depends_on: [053, 355]
---

## Why this exists

`code-atlas-refresh` skips cleanly when another writer holds `write.lock` (053, R4.3). The skip is
right for the writer, but the request is lost: nothing re-runs once the holder is done. An
incremental costs about a minute on a large index (052), so a second request inside that window is
common:

- `git rebase` of N commits: `post-commit` fires per pick and `post-rewrite rebase` once at the end
  (355's spike). The first pick's refresh holds the lock; the rest, the final one included, skip.
  The index stops at a pick's HEAD.
- Two commits a minute apart, or a `git pull` (`post-merge`) right after a commit.

Answers stay honest — the state line says `behind`, and 035's read-through repairs the files a query
touches — but the index the hooks were installed to keep current is not current until the next
refresh. `contrib/git/README.md` documents the gap (355).

## Scope

1. A refresh that finds the lock held leaves a "pending" marker beside the lock instead of only
   skipping. The holder, before it releases the lock, re-runs an incremental while a marker is
   pending — so the last request always lands, with no waiting and no extra process.
2. Applies to every writer that shares the lock (`code-atlas-refresh` and `build_or_update_index`),
   not only the git hooks — it is the lock's contract, not a hook's.
3. A full rebuild in progress is not repeated: a marker left during one is served by one
   incremental after it publishes.
4. **No lost wake-up.** A marker written after the holder's last check but before its unlock must
   still land. So the holder releases, re-checks the marker, and if it is set tries the lock again,
   looping until the marker is clear. Checking only before release leaves a window AC1 can fail in.
5. The marker is a stateless "dirty" flag (one overwritable file, no PID, no owner). Nothing has to
   be reclaimed when a holder dies: the next writer reads it, clears it and runs (AC3, 177).

## Acceptance criteria

- **AC1 (proving test):** a real `git rebase` of two picks with the hooks installed and a real
  index ends with the index's `last_commit` equal to HEAD.
- **AC2:** two refreshes requested while one runs cost exactly one extra incremental, not two.
- **AC3:** a holder killed with a marker pending leaves no claim that outlives it (177): the next
  writer starts clean and the marker is consumed or ignored, never a permanent "pending".
- **AC4:** `contrib/git/README.md`'s rebase row no longer carries the gap.
- **AC5:** a unit test drives two writers deterministically through the window between the
  holder's last check and its unlock, and the late request still runs. AC1's real rebase is slow
  and timing-dependent, so it cannot be the only proof of Scope 4.
