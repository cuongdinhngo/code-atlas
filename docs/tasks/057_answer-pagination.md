---
id: 057
slug: answer-pagination
title: A large answer cannot be enumerated, so `total_count` cannot be audited
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [013, 014, 033]
---

## Goal
`find_implementations` returned `total_count: 143` with 10 rows. Its signature is
`find_implementations(qname, detail_level)` — **no `limit`, no `offset`, no cursor**. There is no
sequence of calls that yields rows 11–143. `search_symbol` takes `limit` but no `offset`, so it caps out
the same way. `find_callers` and `find_references` take neither.

`total_count` was added so an empty or short answer would stop reading as the whole truth (033). It
half-works: a field session was told it was missing 133 rows and given no way to get them. Asked to
cross-check the number against grep, it found 142 against atlas's 143 — **and could not reconcile the
one-row difference, because the answer cannot be listed.** Plausible explanations existed (the index
also covers the test tree; one of the 29 parse failures could cut the other way) and none could be
confirmed. A count that cannot be checked is not a count anyone can build on.

This is a recall problem, not a convenience one. Under the priority set on 2026-08-07 — correctness
gates, cost wins — an answer that is incomplete *by construction* and cannot be completed fails the
gate, however cheap it is.

## Scope / Deliverables
- **A consistent way to walk a large answer** across the nav and search tools. Decide the mechanism —
  `offset`, or an opaque cursor — and apply it uniformly; the current state, where one tool has `limit`,
  one has nothing, and none has `offset`, is itself part of the defect.
- **`limit` on `find_implementations`**, matching `search_symbol`'s. The asymmetry is undocumented and
  there is no reason for it.
- **Stable ordering is a precondition.** Paging over an unstable order silently skips and repeats rows.
  `_NODE_ORDER` / `_EDGE_ORDER` already end in `id`, so the ordering is total — assert that a paged walk
  visits every row exactly once (R4.2 makes this testable).
- **Say when a page is the last one**, so a caller stops without a speculative extra call.
- **Do not raise the default page size.** The fix is the ability to ask for more, not more by default —
  `max_results` exists because payloads are the cost centre.

## Constraints
- **Token cost of the common case must not move.** A first call that wants ten rows pays exactly what it
  pays today; paging is opt-in.
- **SQL stays in the store (R1.4)** — `LIMIT`/`OFFSET` belongs to `store.py`, not the tools.
- **Determinism (R4.2)** — the same index and the same page arguments return identical rows.
- **No contract or schema change (R3).**
- **Watch the reachability tools.** `reachable_from` / `find_orphans` are bounded by `impact_max_nodes`
  (default 500), not `max_results`, and a 500-row answer is already ~160 KB of JSON — an open BACKLOG
  observation. Decide whether they are in scope here or stay out; do not accidentally make them
  cheaper-to-ask-for and far more expensive to receive.

## Acceptance criteria
- Every result set larger than one page can be enumerated completely through a documented sequence of
  calls, asserted end to end on a fixture with more rows than the page size.
- A paged walk over a fixture visits each row exactly once, in a stable order, across two runs (R4.2).
- `find_implementations` accepts `limit`, bounded by `max_results` as `search_symbol` is.
- The last page is identifiable without an extra call.
- A default-arguments call returns a byte-identical payload to today's, asserted.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/tools/find_implementations.py` (no `limit`), `code_atlas/tools/search_symbol.py` (`limit`,
no `offset`), `code_atlas/tools/find_callers.py` / `find_references.py` (neither);
`code_atlas/tools/nav_result.py` (`total_count`, `truncated` — what exists today);
`code_atlas/store.py:112-113` (`_NODE_ORDER` / `_EDGE_ORDER`, both `id`-terminated, which is what makes
paging safe).
`total_count` origin: [033](033_nav-reason-codes.md). Reachability payload-size caveat:
[`BACKLOG.md`](../BACKLOG.md) open observations.
Origin: field retro round 2 §3b and §A.6 — the 143-vs-142 reconciliation that could not be done.
