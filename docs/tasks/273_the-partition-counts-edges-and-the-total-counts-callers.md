---
id: 273
slug: the-partition-counts-edges-and-the-total-counts-callers
title: '`production_count` + `test_count` counts edge rows while `total_count` counts the caller set, so a real answer reported 78 callers and 102 production ones — a partition that exceeds its whole is a number no reader can interpret, and the correct response to it is to ignore every count on the payload'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [262, 258]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §6)

One `find_callers` answer, quoted verbatim: `total_count: 78`, `production_count: 102`,
`test_count: 0`, `result_subtrees: {legacy: 42, src: 36}`. 42 + 36 = 78. The retro's verdict:

> *"I still do not know what the 102 counts. I ignored it, which is the correct response to a number
> you cannot interpret, but a number nobody can interpret is a number that should not ship."*

262 shipped the partition with the stated invariant *"`production_count` + `test_count` summing to the
hit set"*. Two things break it:

- `inbound_test_rows` (`store.py:1746–1776`) is `SELECT … COUNT(*) FROM edges JOIN nodes src …
  GROUP BY 1, 2` — it counts **edge rows**, so two calls from one caller count twice, while
  `outcome.total_count` is the size of the BFS hit set (one row per caller).
- That join is `src.qualified_name = edges.source_qname`, so a qname declared in more than one file
  multiplies every edge by its definition count — the same fan-out [258](258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md)
  names, arriving here as inflation rather than as rows.

The consequence is worse than a wrong number: a partition that can exceed its total teaches a reader
to discount `production_count`, which is the field [272](272_a-partition-that-is-all-tests-answers-ok.md)
needs them to act on.

## Scope / Deliverables

- **One census over one hit set.** The partition counts the same distinct sources the answer counts,
  so `production_count + test_count == total_count` holds by construction at depth 1 — not by
  a second query that happens to agree.
- **A test that pins the invariant**, not the two numbers: any fixture, any tier filter, any argument
  filter — the partition adds up or the test fails.
- **Multi-call and multi-definition fixtures**: one caller calling the subject three times, and a
  subject whose caller qname is declared in two files. Both are single callers.
- **`find_references` audited for the same shape** and fixed or pinned as already correct.

## Constraints

- R4.3: the count stays one grouped store read; no per-row Python counting over an unbounded pull.
- The partition must keep respecting `args_at` / `confidence_tier`, which today it does — the filter
  predicates are the part that is right.
- Above depth 1 the partition stays omitted (262's rule); this ticket does not widen it.
- 061: no new field; the fix is to the numbers already shipped.

## Acceptance criteria

- A property test over the existing caller fixtures: for every depth-1 answer, the partition sums to
  `total_count`.
- A fixture with one caller and three call sites reports `production_count: 1`.
- A fixture whose caller qname is declared in two files reports `production_count: 1`.
- `test_role_source` still names the deciding source on every partitioned payload.

## References
`code_atlas/store.py:1746–1776`, `code_atlas/tools/find_callers.py:579–599,519–523`,
field retro round 20 §6, [262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[258](258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md),
[272](272_a-partition-that-is-all-tests-answers-ok.md).
