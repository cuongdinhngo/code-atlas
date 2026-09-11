---
id: 258
slug: the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol
title: 'The build materialises the cartesian product of (unresolved call site × same-named symbol), alphabetically truncated at `max_results` — 1,016,207 rows on the anchor repo, 48.4 % of the whole graph, 3.35 per call site, 87.7 % of them linked and therefore returned as answers: one `->get()` inside a Zend library file is stored as eight callers of eight unrelated application classes'
phase: 2
milestone: Agent-trust
status: todo
depends_on: [251, 054, 066, 182]
---

## Why this exists (measured on the anchor index, 2026-09-11)

Eighteen field rounds have reported the same symptom in different words — *"~100 HEURISTIC false
positives from unrelated `build()` methods"* (round 18), *"`find_references(ModelConfig)` → 2, truth
20, `reason: ok`"* (round 8), *"`find_orphans` 99.2 % false orphans"* (round 11), *"ranked a JS
substring near-miss above six exact matches"* (round 12). They were filed as separate defects of
separate tools. **They are one storage decision.**

Read-only on the anchor index (`.code-atlas/graph.db`, 24,853 files):

```
total edges                    2,099,318
CALLS / HEURISTIC              1,016,207    48.4 % of the whole graph
  of those, linked             890,942      87.7 %  -> they are returned as answers
distinct call sites behind them  303,235
  fan-out                      3.35 stored edges per call site
sites with exactly 10 candidates  10,001    <- the max_results cap, visible in the data
sites with 11                        12
db size                        1.46 GB
```

**~713,000 rows — 34 % of the entire graph — are duplicate rows for a call site that appears once in
the source.** And the candidates they enumerate are chosen alphabetically:

```
Zend/Cache/Cache/Backend/Memcached.php:133   ->   'get'   (8 stored edges)
   \LedgerAPIController::get · \LedgerAPIModel::get · \AbsenceLeaveAPIController::get
   \AbsenceLeaveAPIModel::get · \AbstractRateDetail::get · \AccessGroupsAPIController::get
   \ActiveMembersAPIController::get · \AdditionalContactsAPIController::get
```

Every one of those eight is wrong. A cache backend in a vendored Zend tree has no relationship to an
Ledger API controller. The consequence runs both ways: the Zend file gains eight outbound call edges it
does not have, and **eight application classes each gain a caller they do not have** — which is
precisely the noise every round has been discarding by hand.

The eight are not the eight most likely candidates. They are the first eight in alphabetical order,
because the candidate set is capped by `max_results` and the cap takes a prefix of a name scan. The
anchor repo's own config records the bargain it was forced into:

> Measured on this repo: 491,741 heuristic call sites, 33,300 of them saturating a cap of 50. At 50
> the graph carries 4.8M heuristic edges (2.1 GB); at 10 it carries 2.6M.

A **retrieval** parameter is setting **graph content**. Lower it and the index shrinks by losing
candidates; raise it and the same query costs 2.1 GB. That trade exists only because the product is
materialised at build time.

## Root cause

An unresolved call carries a name, not a target. The builder answers "which symbols could this be?"
once, during the build, and writes one edge per answer. Everything downstream then treats those rows
as edges of equal standing with resolved ones: they are paged in `_EDGE_ORDER` (251), counted in
`total_count`, walked by `impact`, and subtracted by `find_orphans`.

The alternative is that the *site* is the fact and the *candidate set* is a query. The site is what
the parser observed; the candidate set is an inference that depends on how the caller wants to rank —
by proximity, by tier, by subtree — and is exactly the kind of thing a query decides and a build
should not freeze.

## Scope

Store the unresolved call **site** once; compute its candidates at query time.

This is a schema and resolver change (`schema_version` bump), not a contract change: adapters already
emit a call with a name and no target, and `contract.py` need not move. Phase 2 decides the mechanism;
the ticket binds the properties:

- **One row per unresolved call site**, carrying the name and its enclosing context.
- **Candidates are computed on demand**, so a caller can ask for them ranked by proximity, filtered by
  tier (this is 251's ask, made cheap), or counted honestly without paging a prefix.
- **`max_results` stops governing graph content.** It returns to being what its name says.
- **Recall improves rather than degrading.** Today a site with 47 same-named candidates stores ten
  alphabetical ones; the count of what was dropped is not recoverable from the graph. Query-time
  resolution can report the true candidate count even when it returns a page.

## Constraints

- **R5.6 — no silent narrowing.** Ranking candidates by proximity is allowed; dropping them silently
  is not. A query that returns three of forty says forty.
- **R4.2 — determinism.** Identical index and query, identical candidate order. Proximity ranking must
  be a total order, not a heuristic with ties broken by rowid.
- **R1.4** — `store.py` stays the only file touching SQLite; the resolver reads through it.
- **R1.1** — proximity is expressed over contract structure (namespace, file, subtree), never over a
  language's name syntax in the core.
- **Query cost is the risk and must be measured before the change is accepted.** This moves work from
  one build to every call. The pre-condition for phase 2 is a measurement: candidate resolution for a
  saturating name (`get`, `build`, `append`) against the name index, at the anchor repo's scale,
  compared with today's rowid seek. If it does not hold inside the tool budget, the ticket becomes
  build-time candidate *ranking* instead, and says so.
- **182's rule holds** — where the answer would be unreliable, refuse rather than return rows.

## Acceptance criteria

- **AC1** A call site that resolves to N same-named candidates is stored once, and the graph's edge
  count on the anchor repo falls by the measured duplicate share (~713,000 rows / 34 %).
- **AC2** `find_callers` on a saturating name returns candidates ranked by a stated, deterministic
  rule, and `total_count` reports the true candidate count — not a capped prefix.
- **AC3** The Zend/`get` case is the proving fixture: a call inside an unrelated subtree no longer
  makes eight application classes report a caller they do not have, **and the change is visible as a
  before/after on that exact site**.
- **AC4** `max_results` no longer changes what the build stores; a build at 10 and a build at 50
  produce identical graphs.
- **AC5** Query cost for a saturating name is measured and reported in the ticket, and stays inside
  the tool budget — or the ticket converts to build-time ranking and records why (the R6.5 discipline:
  the measurement decides, not the preference).

## References

- Measured: `.code-atlas/graph.db` on the anchor repo, read-only, 2026-09-11 (counts above).
- `code_atlas/store.py:170` (`_EDGE_ORDER`), `:1330` (`edges_by_target`); `code_atlas/config.py`
  (`max_results` / `clamp_limit`).
- [251](251_the-resolved-caller-can-be-off-the-page.md) — the query-side half. 251 can rank and filter
  what is stored; it cannot recover a candidate the build never wrote. Both are needed, and this one
  is why 251 alone is not enough.
- [054](054_bare-name-callers-silent-drop.md) — bare-name candidate capping, where the alphabetical prefix was introduced.
- [066](066_limit-clamped-silently.md) — `max_results` governing resolver fan-out, the coupling this removes.
- BACKLOG follow-up "`max_results` does two unrelated jobs" — this ticket is its root cause and closes
  it.
