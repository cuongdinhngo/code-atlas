---
id: 027
slug: resolver-batched-lookups
title: Batch resolver candidate lookups (N+1 read path)
phase: 1
milestone: M4
status: todo
depends_on: [011, 015]
---

## Goal
Make the resolver's read path batched like its write path, so the M4 scale baseline measures the
shape we intend to ship (§8.2, Plan §6.1).

## Scope / Deliverables
- `resolver.resolve_edges` pulls unresolved edges 1000 at a time (`_RESOLVE_BATCH`), then issues one
  `nodes_by_qualified_name` per edge — plus a `nodes_by_name(kind="Method")` fallback for
  HEURISTIC `CALLS` — so a full batch costs up to ~2000 SELECTs. `apply_resolution` is already
  batched; only the reads are not.
- Add a batched store lookup (`nodes_by_qualified_names` / `nodes_by_names`) taking a set of keys and
  returning `key → rows`, capped at `max_candidates` **per key**.
- Rewrite `_resolve_include` / `_resolve_symbol` to two passes per edge batch: (1) one batched lookup
  for FQN targets plus one kind-scoped lookup for `INCLUDES` paths, (2) one batched `Method` lookup
  for the `CALLS` edges that pass 1 left unmatched.
- No behavior change: same links, same siblings, same tiers, same candidate order.

## Constraints
- **Per-key top-N, not a global LIMIT.** `WHERE qualified_name IN (...) LIMIT n` breaks the
  `max_candidates` cap — it truncates across keys, changing which candidate becomes the edge's target
  and which become siblings. Use `ROW_NUMBER() OVER (PARTITION BY qualified_name ORDER BY …)`
  (SQLite ≥ 3.25) or an equivalent per-key partition.
- **Candidate order must be byte-identical to today's.** `_NODE_ORDER` is
  `qualified_name, file_path, line_start, id` (`store.py:101`), so partitioning by `qualified_name`
  and ordering by `file_path, line_start, id` reproduces the current per-key sequence exactly (R4).
- Store owns the SQL; the resolver never opens a cursor (R1.4). No language branches (R1.1).

## Acceptance criteria
- Resolving a fixture with multi-candidate targets produces byte-identical `edges` rows (target,
  tier, sibling set and order) before and after — a golden assertion, not just a count.
- A batch of N unresolved edges issues O(1) node SELECTs per batch, not O(N) — asserted by counting
  queries against a real store, not by inspecting the SQL string.
- `max_candidates` still caps candidates per target qname when several qnames in one batch each
  exceed the cap.
- Existing resolver and nav-tool tests pass unchanged.

## References
Plan §8.2, §6.1; [PR #25](https://github.com/cuongdinhngo/code-atlas/pull/25) review (write path
batched, read path not); `code_atlas/resolver.py`; `code_atlas/store.py` `_nodes` / `_NODE_ORDER`.
Ordering note: land this **before** the 015 AC2 timing artifact (BACKLOG follow-up / task 018), or
that baseline measures the read path this task removes.
