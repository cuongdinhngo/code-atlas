---
id: 212
slug: an-incremental-update-escalates-on-correctness-but-never-on-cost
title: "`incremental_update` escalates to a full build only when a delta would be *wrong*, never when it would be slower than one — and no change is ever classified as too small to re-parse"
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [030, 052, 080, 096, 172, 202]
---

## Why this exists

`incremental_update` (`code_atlas/indexer.py:254`) has exactly three routes to `full_build`, and all
three are correctness arguments:

| trigger | line | why |
|---|---|---|
| `build_incomplete(store)` | 275 | a graph left mid-write cannot be extended (202) |
| `contract_rebuild_required(store)` | 275 | vocabulary era changed; a delta would mix eras (030) |
| `_ScopeChanged` | 373-380 | a suffix entered scope the git diff cannot name (172) |

Each is right. Together they are the complete list, and **cost is not on it.** The decision is
binary — this delta, or everything — with nothing in between and no floor beneath it:

- **No upper tier.** A branch touching 5,000 files runs as a delta: re-parse, re-link, reconcile,
  per changed file. Whether that is cheaper than one full build is never asked, and past some
  fraction of the repo it certainly is not.
- **No lower tier.** A commit that reformats whitespace, edits comments, or changes only string
  literals re-parses every touched file, because nothing compares *what changed inside* a file
  against what the graph stores. The no-op skip at the end of the function
  (`if to_parse or removed:`) catches a delta that turned out empty **after** the parse, not one
  that could have been predicted empty before it.

The consequence is the one the anchor's operator hit: a full rebuild takes about an hour, and the
only alternative on offer is a delta whose cost nobody can predict either. Neither number is
knowable before committing to one.

### Why this is not the rebuild-speed ticket

Making a full build faster and doing fewer full builds are different work. A ticket for the first
(the parallelism ceiling in a full rebuild) was drafted for this repo and **is not in the tree** —
`docs/tasks/` has 200, 201, 202, 204 and nothing at 203. This ticket does not replace it and does
not depend on it: even at half the wall-clock, choosing the cheaper of two routes and skipping work
that cannot move the graph are still wins, and they are wins that arrive without touching the
parallelism model.

### Prior art, and the part that transfers

The reference implementation surveyed in the user's notes classifies each update before acting —
roughly *skip* (cosmetic), *partial*, *architecture-level* (directories added or removed), *full*
(beyond a fraction of the repo) — and hashes each file's declarations so a cosmetic edit is
provably cosmetic. The tiering and the declaration fingerprint transfer directly. Its thresholds do
not: they are that project's constants, and **R2.3** says sample repos drive targets, never
behaviour. Measure this repo's crossover point instead of importing a number.

## Scope

1. **Measure the crossover first.** On the anchor, time `incremental_update` against `full_build`
   across a range of delta sizes and find where the delta stops being cheaper. Everything below
   depends on this number existing; without it a threshold is a guess.
2. **An upper tier.** Above the measured crossover, escalate to `full_build` for cost, recorded in
   the `scope` dict beside the three correctness escalations so the report can name why — the
   pattern 172 established.
3. **A lower tier: a change that cannot move the graph is not parsed.** A per-file fingerprint over
   the declarations the graph stores — symbols, signatures, imports, call targets — lets a file whose
   fingerprint is unchanged be skipped. Whitespace and comment edits are the case that pays for it.
4. **The route is always reported.** Every build says which tier it took and why. A cost escalation
   must never look like a correctness one, and a skipped file must never look like an indexed one.
5. **Never skip on a correctness route.** The three existing escalations outrank any cost tier; a
   contract-era change re-parses everything regardless of fingerprints.

### Explicitly not in scope

- **Full-build parallelism.** The absent ticket's subject; independent of this one.
- **Changing what a delta indexes** when it does run. Same collect, same link, same reconcile.
- **Cross-run caching of parse results.** A fingerprint decides whether to parse; it does not store
  what the parse produced.

## Constraints

- **R2.3** — thresholds come from measuring this repo, never from the reference implementation's
  constants.
- **R5.5 — a reported value is sourced from the computation that owns the whole fact.** The tier is
  decided in one place and reported from it, not re-derived by the reporter.
- **R4.2** — the resulting graph is identical whichever route was taken. This is the ticket's central
  risk: a fingerprint that misses a construct silently under-indexes, and the index still reports
  current. Guard it directly (AC5).
- **R6.5** — the fingerprint guard ships only once observed failing: construct a file whose text
  changes, whose declarations do not, and prove the graph is identical either way; then one whose
  declarations do change, and prove it is not skipped.
- **R5.3** — a fingerprint that cannot be computed fails loud into "parse it", never into "skip it".
- **202's lesson applies verbatim:** a build that did less work must not leave an index that reports
  as though it did more.

## Acceptance criteria

1. The crossover measurement exists, is recorded with its method, and the upper-tier threshold cites
   it.
2. A delta above the threshold escalates to a full build and the report names cost — distinguishable
   from the three correctness routes.
3. A file whose declarations are unchanged is not re-parsed, and the graph is byte-identical to a
   run that did re-parse it.
4. A file whose declarations changed is never skipped, proven by a fixture that fails without the
   guard.
5. A fingerprint that cannot be computed results in a parse, and a test exhibits that path.
6. Every build reports its tier; no tier is inferable only from timing.
7. The three existing correctness escalations are unchanged and still take precedence, pinned by a
   test.

## References

[030](030_alias-indirection-edges.md) (the escalation the code cites at indexer.py:275), [052](052_incremental-noop-cost.md)
(the phase-timing the code cites for `phase_times`, and Scope 1's measuring surface), [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the no-op floor
and the 6,071-edge finding — the closest prior work), [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (why a
delta-scoped resolve is equivalent only under a fixed alias map),
[172](172_incremental-is-blind-to-a-scope-change.md) (the `scope` reporting pattern this reuses),
[202](202_a-killed-build-leaves-an-index-that-reports-current.md) (an index that reports current
after doing less work).
