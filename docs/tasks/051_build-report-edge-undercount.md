---
id: 051
slug: build-report-edge-undercount
title: '`BuildReport.edges` counts what the adapters emitted, not what the build wrote'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [009, 011, 028]
---

## Goal
On the anchor repo, a full build reports **949,808 edges**. Counting the table straight afterwards
returns **1,775,812**. Calling `get_index_status` at that moment reports 1,775,812 too, because it
counts rows in SQL (`store.counts()`, `store.py:393-407`). So the two tools disagree by **87%** about
the same graph with no build in between, and the smaller number is the one an agent is handed at the
one moment it is deciding whether the index is worth using.

The cause is ordering, not arithmetic. `_parse_all` accumulates its tally while writing adapter output
(`indexer.py:492`), and `full_build` returns a report built from that tally (`indexer.py:120`) —
*after* two later steps have inserted more rows:

- `resolve_edges` (`indexer.py:119`) turns a call site with N candidate declarations into one linked
  parent plus N−1 sibling rows, inserted by `store.apply_resolution` (`resolver.py:87`,
  `store.py:602-603`). None of them is in the tally.
- `apply_indirection_rules` (`indexer.py:118`) inserts a synthetic `File` node plus ALIASES/CALLS rows
  when `indirection_rules` is configured (`enrichment.py:89-110`). Also not in the tally.

`incremental_update` has the identical shape (`indexer.py:195-199`).

**The siblings are where the missing 826k rows are, and that is measured, not assumed.** Counting
distinct `(source_qname, kind, target_raw, file_path, line)` in the anchor repo's index gives
**920,939** — close to the 949,808 the adapters emitted and nowhere near the 1,775,812 stored. The
extra rows are alternative candidates for call sites that were already counted once, so they are the
resolver's, not the adapter's. The anchor repo configures no `indirection_rules`, so enrichment
contributes nothing there — its share of the hole is **unmeasured, not proven zero**.

**Same family as [048](048_edge-health-resolved-ambiguity.md).** That ticket removed a payload where
the wrong reading was the easy one; this is a payload where the only reading available is wrong. An
agent that builds and reads `edges: 949,808` has no way to discover it is holding a number 46% below
the graph it just created — nothing in the payload hints that a later step wrote more rows.

## Scope / Deliverables
- **Decide what `edges` means, and write down why.** Two defensible definitions, and the current
  number matches neither:
  - *rows in the graph now* — what `get_index_status` reports, and the reading a full build invites;
  - *rows this run wrote* — what the other `BuildReport` fields already mean (`parsed`, `failed`,
    `removed` are per-run deltas), and the only reading that survives `incremental_update`.
  Pick one. If the delta reading wins, the fields must be named so a total cannot be read out of them.
- **Count after every writer has run**, whichever definition is chosen — the report is assembled at
  `indexer.py:120` / `:195-199`, so resolver siblings and enrichment rows are already on disk by then.
  The cost is one `COUNT(*)` per build, against a build that already took minutes.
- **`nodes` gets the same treatment.** Enrichment's synthetic `File` node is outside the tally too.
  It is one row, but "small" is not "counted".
- **Make the two tools agree, in a test.** A full build followed immediately by `get_index_status`
  must report the same `edges` — on a fixture that actually contains a multi-candidate call site, or
  the assertion passes vacuously against a graph with no siblings to miss.
- **Recheck the plausibility gate.** `scripts/cross_repo_validate.py:64` fails a sample when
  `report.edges < min_edges`, and the thresholds in `scripts/cross_repo_samples.json` were calibrated
  against the understated number. A correct count only moves them upward, but they must be re-derived
  rather than left to pass by luck.

## Constraints
- **SQL stays in the store (R1.4).** Any new count is a `GraphStore` method; the indexer does not
  learn to query.
- **No contract or schema change (R3), no new column.** This is a reporting fix.
- **Determinism (R4.2)** — the same repo state must still produce the same report.
- **Cost stays proportionate.** One aggregate query at the end of a build is fine; per-file counting
  inside the write loop is not.
- **The incremental path keeps whatever meaning is chosen**, and says so in a test — a full build and
  an incremental run must not quietly report on different scales.

## Acceptance criteria
- On a fixture whose resolver produces at least one sibling row (asserted non-zero, so the guard
  cannot pass vacuously), `build_or_update_index` and a following `get_index_status` report the same
  `edges`.
- The same fixture with `indirection_rules` configured: enrichment's inserted rows and node are
  included in the report.
- `incremental_update` reports on the chosen scale, with a test that would fail on the other one.
- `scripts/cross_repo_samples.json` thresholds re-derived against the corrected count.
- The chosen definition and its rationale are recorded in the working doc and reflected in PLAN §8.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/indexer.py:492` (the tally), `:118-120` (enrichment → resolve → report, in that order),
`:195-199` (the same shape in `incremental_update`), `:71-81` (`BuildReport`);
`code_atlas/resolver.py:87` and `code_atlas/store.py:588-603` (`apply_resolution`, which inserts the
sibling rows); `code_atlas/enrichment.py:89-110`; `code_atlas/store.py:393-407` (`counts()`, the
number `get_index_status` reports); `scripts/cross_repo_validate.py:53-64` and
`scripts/cross_repo_samples.json` (the `min_edges` gate).
Measured on the anchor repo's index at schema/contract v3, 2026-08-07: report 949,808 · table
1,775,812 · distinct call-site 5-tuples 920,939 · nodes 185,882.
Sibling expansion is [046](046_resolver-qname-candidate-dedupe.md)'s deliberate design, not a bug —
this ticket is about the count that omits it. Payload-honesty precedent:
[048](048_edge-health-resolved-ambiguity.md).
