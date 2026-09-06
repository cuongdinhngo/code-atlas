---
id: 219
slug: a-full-rebuild-pays-the-populated-db-tax-nobody-chose
title: 'A full rebuild over an existing index costs 76 minutes against the same build''s 29 minutes into an empty one — 203 measured the 2.6x, named truncate-first and defer-FTS as the candidates, and stopped because choosing between them is an architecture decision an unattended run may not take'
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [203, 201, 052]
---

## Why this exists

[203](203_a-rebuild-is-gil-bound-and-its-operating-knowledge-is-unroutable.md) ran the same full
build twice over the 24.6k-file anchor. The **only** difference was whether the target database
already held the graph; both runs wrote identical output — 24,569 files, 262,899 nodes, 2,077,473
edges (R4.2).

| | wall | files/s | target DB at start |
|---|---|---|---|
| **populated** | **4,545 s · 75.8 min** | **5.41** | 1.16 GiB, 262,899 nodes / 2.08 M edges |
| **fresh** | **1,751 s · 29.2 min** | **14.03** | empty |
| | **2.60× · 46.6 min** | | |

[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md) measured the field rebuild worse still:
**5,470 s / 4.49 files/s** against a 2.2 GiB index.

**203 decomposed the gap and closed its own AC1, then deliberately stopped.** Sampling the live lock
during the fresh run separated two effects the single wall figure hid:

1. **An index-size term, present in both runs.** On an empty database the rate falls **43.2 → 9.7
   files/s** as rows accumulate — nothing about the source files changed; the per-file write got
   dearer as `nodes`/`edges` and the `nodes_fts` trigram index grew. The populated run is **flat at
   5.41 from its first file**, because it starts at the far end of that curve.
2. **A pre-existing-rows term, in the populated run only.** At comparable index size the fresh run
   still sustains ~9.7 files/s against 5.41 — a further **~1.8×**. `replace_file_rows`
   (`store.py:481`) wraps `_delete_rows(path)` plus both inserts in one transaction, and on an empty
   database that delete matches nothing.

203's own conclusion, and the reason this is a separate ticket: **"the wall is dominated by what the
write path does per file as the index grows"**, *not* the GIL hypothesis it was named for — so
moving `json.loads` off the writer's thread cannot touch either term. Its A6 row records that
choosing between the remaining candidates "is an architecture decision, and an unattended run is the
wrong place for it".

## Scope

1. **Decide and implement one of the two candidates 203 made visible**, against its measured pair:
   - **Truncate before a full build.** A full rebuild rewrites every row anyway, so the per-path
     `_delete_rows` is provably redundant work. Removing it should recover the ~1.8× term outright.
   - **Defer the FTS index.** Build `nodes_fts` once at the end rather than maintaining the trigram
     index per insert, targeting the 43.2 → 9.7 decay.
   They are not exclusive; the ticket may take one and record why the other waits.
2. **Bound the claim before building.** 203 already states the ceiling: the best case for any fix is
   bounded by the ~29 minutes a fresh build already costs. A proposal whose projected win exceeds
   that is wrong about its own mechanism.
3. **Only the full-build path.** Incremental is out of scope and measured healthy — 63.8 s for a
   3-file edit, 5.5 s no-op — and `hashing` is already scoped to `(changed_set | dependents)`.

**Not in scope:** a process pool or adapter-side decode (203 measured them as unable to touch either
term); `workers` as a throughput knob (1.07×, settled); any change to `incremental_update`.

## Acceptance criteria

- **AC1** A full rebuild over a populated index of comparable size is measurably faster than
  4,545 s on the anchor, reported as a **pair against a fresh build on the same tree**, the way 203
  reported it — one wall figure alone cannot separate the two terms.
- **AC2** Output is **byte-identical** to the pre-change build on the same tree: same files, nodes
  and edges (R4.2). This is the gate the whole ticket turns on — a faster build that writes a
  different graph has not sped anything up.
- **AC3** If truncate-first is taken, a **killed** truncating build must not leave an index that
  reports `current`. 202 already made that an escalation path; state whether this widens it, and pin
  whichever answer ships.
- **AC4** The single-writer rule (R4.3) and 072's busy-payload behaviour are unchanged, pinned.
- **AC5** The candidate **not** taken is recorded with the reason, so the next reader does not
  re-derive the comparison.

## Exclusions

- **E1** The anchor measurement needs `real_corpus_path`, which is null on this checkout — the same
  standing gap escalated at 209. Fixture-scale proof plus the recorded method is the artifact if the
  anchor is unavailable; say so rather than reporting an unmeasured win.

## Notes

`AGENTS.md` carried **"rebuild ~10 min"** until 2026-09-06 — wrong by ~8× against 203's own numbers,
and it is the figure that decides whether a caller starts a rebuild at all. Corrected in the same
session that filed this ticket; the lesson is that a measured number reached a ticket and never
reached the orientation doc a session actually reads.
