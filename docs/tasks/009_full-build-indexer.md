---
id: 009
slug: full-build-indexer
title: Full build indexer + workers (M1)
phase: 1
milestone: M1
status: todo
depends_on: [004, 005, 007]
---

## Goal
Index a whole repo end-to-end into SQLite (§8.1).

## Scope / Deliverables
- `indexer.full_build`: collect files (`git ls-files` per adapter extensions, minus ignores; walk fallback); reconcile vanished paths.
- Fan paths across N adapter processes (`min(cpu-2, 8)`); hash bytes; upsert `files`, replace `nodes`+bare `edges`. Single SQLite writer.
- Store `meta.last_commit`, `contract_version`, `built_at`; build `nodes_fts`.
- **Deadline for a hung adapter** (deferred here from task 005, Q5). A live-but-silent adapter blocks the driver's blocking read forever, at **`start()`** (waiting for the handshake) as well as at `parse()` — task 005 ships no protection either way. This task owns the fan-out, so it can bound a worker and kill it outright rather than paying for a per-request reader thread (`select` does not work on Windows pipes).

## Acceptance criteria
- Builds a small PHP repo to a queryable DB; re-run is idempotent.
- Single writer (no SQLite lock contention); worker count honors `CA_WORKERS`.
- A result rejected by `contract.validate()` sets `files.parsed_ok=0` and never breaks the stream (R5.1) — this closes the R5 integration-proof exclusion deferred from task 002.
- An adapter that never answers is killed and its files recorded as unparsed, rather than wedging the build — proven for **both** a silent boot and a silent reply. This closes task 005's recorded hung-adapter exclusion.
- The `busy_timeout` / two-writer contention proof deferred from task 004 lands here, where a real fan-out exists to contend.

## References
Plan §8.1, §4.1 (the wire rules and the deferred hang), §15 (M1). Carried exclusions: task 005 (hung adapter, both call sites), task 004 (`busy_timeout` contention).
