---
id: 057
slug: answer-pagination
title: A large answer cannot be enumerated, so `total_count` cannot be audited
phase: 1.5b
milestone: Agent-trust
status: in-progress
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

## Outcome

**Mechanism:** `limit` + `offset` (not cursor). Store owns `LIMIT`/`OFFSET` on edge and search reads.

**Tools:** `search_symbol`, `find_implementations`, `find_callers`, `find_references`. Reachability,
`file_outline`, and `include_graph` stay out. Last page ⇒ `truncated: false`. Default page size
unchanged. **AC1 scope:** complete enumeration for store-backed pages (incl. `find_callers` depth=1);
depth>1 pages the BFS hit stream and may still hit a count floor (W4).

**Proving:** `tests/test_answer_pagination.py::test_paged_walk_visits_each_row_once_stable`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 057 — answer-pagination (working doc)

- **Ticket:** 057 · local `docs/tasks/057_answer-pagination.md`
- **Type:** bug / enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full
- **BASELINE:** green — `911 passed` (2026-08-08, untouched main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 4 unresolved | 0 asked (standing→ASSUMED) | 3 HOW | 4 ASSUMED | skip: no`

**INPUT KIND:** ticket

**HOW (cited):**

| # | Decision | Resolution | Citation |
|---|----------|------------|----------|
| H1 | Last-page signal | Reuse `truncated: false` (no new payload field); last page ⇒ not truncated | ticket L37; `nav_result.py` `truncated` |
| H2 | `limit` on find_implementations | Same shape as `search_symbol` (`None` → `max_results`) | ticket L32–33 |
| H3 | SQL LIMIT/OFFSET in store | `_edges` / search reads take `offset` | ticket C R1.4 |

**ASSUMED (standing — confirm at Gate 1):**

| # | Choice | Why |
|---|--------|-----|
| W1 | **`offset`** (not opaque cursor) | Store SQL; stable `_EDGE_ORDER`/`_NODE_ORDER`+`id`; opt-in; no server state |
| W2 | Reachability (`reachable_from` / `find_orphans`) **out of scope** | Ticket caveat; different cap (`impact_max_nodes`) |
| W3 | Tool set = **four named only** (`search_symbol`, `find_implementations`, `find_callers`, `find_references`) | Ticket names them; outline/include stay as today |
| W4 | `find_callers` **depth=1** fully enumerable via store OFFSET; **depth>1** supports `limit`/`offset` on the BFS hit stream but complete enumeration only guaranteed at depth=1 (exact `total_count`) | Exposure-checker; BFS is not one store ORDER BY |

**Exposure-checker:** [Challenger](2eff6265-4c08-4dc1-86fa-dbd0fd06eadd) — surfaced W3/W4 (folded into ASSUMED).

## Requirements matrix

`SECTIONS: 4 found | 4 decomposed | ROWS: C=5 R=5 G=2 AC=6`

| ID | Interpretation | Status |
|----|----------------|--------|
| G1 | Incomplete-by-construction answers must be completable | ✅ |
| G2 | `total_count` must be auditable via listing | ✅ |
| R1 | Uniform walk (`offset`) across four tools | ✅ |
| R2 | `limit` on find_implementations | ✅ |
| R3 | Stable order; paged walk visits each row once | ✅ |
| R4 | Last page identifiable (`truncated=false`) | ✅ |
| R5 | Do not raise default page size | ✅ |
| C1 | Common-case token cost unchanged (defaults) | ✅ |
| C2 | SQL LIMIT/OFFSET in store | ✅ |
| C3 | R4.2 determinism | ✅ |
| C4 | No contract/schema change | ✅ |
| C5 | Reachability out (W2) | ✅ |
| AC1 | Enumerate larger-than-page via documented calls | ✅ |
| AC2 | Paged walk unique+stable across two runs | ✅ |
| AC3 | find_implementations accepts limit | ✅ |
| AC4 | Last page identifiable without extra call | ✅ |
| AC5 | Default-args payload byte-identical to today | ✅ |
| AC6 | pytest/ruff/mypy green | ✅ |

`CLARIFICATION: 4 ASSUMED (W1–W4) | j=0` (Gate 1 ratify)

**Cause:** validation/data UX — page cap without resume; tools inconsistent.

**Blast radius:** `store.py` `_edges`/`search_nodes`; four tools; tests; docs Outcome.

`RULE SECTIONS: R1.4 ✅ | R3 N/A (no vocab change) | R4.2 ✅ | R6.1 ✅ | R1.1 N/A`

`SCOPE: M` · `TIER: full`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass process gates; push/PR need per-action OK |
| 2026-08-08 | Gate 1 cleared (standing) — W1–W4 ratified as ASSUMED |

## Session status

- **Phase:** analysis → design (Gate 1 standing-cleared)


## Phase 2 — Design

**Approach**
1. Add `offset: int = 0` to store `_edges` / `edges_by_*` and `search_nodes` (+ short path); SQL `LIMIT ? OFFSET ?` after existing `ORDER BY`.
2. Four tools: optional `limit` (None → `max_results`, capped) + `offset` (default 0). Reject `offset < 0` / `limit < 1` loud.
3. `truncated = (offset + len(results)) < total_count` (equiv. to today when offset=0).
4. `find_callers` depth=1: store offset. depth>1: skip `offset` BFS hits then take `limit` (enumeration guaranteed only at depth=1).
5. Defaults → same page as today (AC5). No default size raise.

**Rejected:** opaque cursor (server state / more surface); paging reachability (W2); raising `max_results`.

**Assumptions:** SQLite OFFSET stable under `_EDGE_ORDER`/`_SEARCH_ORDER` ending in `id` — **verified** by existing order constants + proving walk test.

**Change list**

| # | Change | Path | Rows |
|---|--------|------|------|
| 1 | `offset` on edge/search reads | `code_atlas/store.py` | C2,R3,AC1–2 |
| 2 | `limit`+`offset` on four tools | `find_implementations.py`, `find_references.py`, `find_callers.py`, `search_symbol.py` | R1–2,R4–5,AC3–5 |
| 3 | Proving + byte-identical + last-page tests | `tests/test_answer_pagination.py` | AC1–6 |
| 4 | Outcome + BACKLOG status | docs | AC |

**Proving test:** `test_paged_walk_visits_each_row_once_stable` — max_results=2, N>2 edges, walk offsets, two runs identical.

**SCOPE:** M unchanged.

## Decision log (cont.)

| When | Decision |
|------|----------|
| 2026-08-08 | Gate 2 cleared (standing) — offset approach |


## Phase 3 — Execute

- **Branch:** `fix/057-answer-pagination`
- **Sweep axis 1:** diff ⊆ change list ✅
- **Sweep axis 2:** approach implemented-as-approved ✅
- **Proving:** `test_paged_walk_visits_each_row_once_stable` green
- **Suite:** 918 passed

## Session status

- **Phase:** execute → review

