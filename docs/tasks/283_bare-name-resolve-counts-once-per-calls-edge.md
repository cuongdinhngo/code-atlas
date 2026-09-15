---
id: 283
slug: bare-name-resolve-counts-once-per-calls-edge
title: 'The bare-name resolve pass runs one `count_nodes_by_name` per CALLS edge — O(edges) SQLite COUNTs (each with a correlated language sub-select) where the batched fetch two lines above already proves uniqueness, so `resolve` on a large PHP repo went from ~15 min to never finishing; 258 traded a cartesian-product storage blowup for a per-edge query blowup that is worse'
phase: 1.5b
milestone: Graph
status: todo
depends_on: [258, 214, 027]
---

## Why this exists

`resolver.py::_link_by_bare_name` (`code_atlas/resolver.py:336-356`) issues **one**
`store.count_nodes_by_name` **per bare-name CALLS edge**:

```python
for language, pairs in grouped.items():
    method_hits = store.nodes_by_names(               # BATCHED: one query for all distinct names
        [name for _, name in pairs], kind=_BARE_NAME_KIND, limit=max_candidates, language=language,
    )
    for edge, name in pairs:                          # iterates EVERY edge (~10^6 on anchor-repo)
        total = store.count_nodes_by_name(            # ONE SQLite COUNT PER EDGE
            name, kind=_BARE_NAME_KIND, language=language
        )
        if total != 1:
            continue
        methods = method_hits.get(name, [])
        if methods:
            _queue_candidates(edge, methods, "HEURISTIC", links, siblings)
```

Cost is **O(edges)**, not O(distinct names). On `anchor-repo` (PHP monorepo, ~23k files, ~1.1M unlinked +
~255k HEURISTIC edges) that is on the order of **10⁶ COUNT queries in one phase**, each carrying a
correlated language sub-select (`count_nodes_by_name`, `code_atlas/store.py:2165-2180`):

```python
# clauses: name = ?  AND kind = ?  AND file_path IN (SELECT path FROM files WHERE language = ?)
```

It is **not a missing index** — `idx_nodes_name` exists and is used. The pathology is the *number* of
queries × the per-call sub-select. Measured effect (native Windows, py-spy, retro 2026-09-15): `resolve`
CPU-bound the whole time in exactly this frame, three full rebuilds over two days, **none finished**;
even the last build that did finish (2026-09-14) took **128 min**, up from a pre-258 `resolve` of
**~15 min** on the same repo/host.

**This is a regression from 258** (`feat(258)`, commit `9949e9a`, 2026-09-12), confirmed by
`git log -S count_nodes_by_name -- code_atlas/resolver.py`. Before 258, a multi-match bare name
materialised N HEURISTIC sibling edges (a storage blowup, ~5.4M edges) but issued no per-edge count.
258 correctly stopped materialising the cartesian product (one unresolved site instead — a real win)
but paid for uniqueness with a per-edge COUNT, trading a storage blowup for a worse query blowup.

**The count is redundant — the batched fetch already answers it.** `nodes_by_names`
(`store.py:1599` → `_nodes_batched:3689`) returns up to `limit` rows *per name* via
`ROW_NUMBER() … WHERE rn <= limit` over a real `JOIN files` (not a correlated sub-select). So for any
name, a fetch that returns **fewer than `limit`** rows *is* the exact total. The sibling one function
up — `_link_by_unique_function` (`resolver.py:276-313`) — already decides uniqueness this way:
`nodes_by_names(..., limit=2)` then `len(candidates) == 1`, **no count query**. `_link_by_bare_name` is
the lone holdout.

**Correctness footgun to respect:** `max_candidates` has a floor of **1** (`config.py:413`; default 50,
`config.py:65`). A length test is only sound if the probe fetches with `limit >= 2`, so that a single
row back always proves `total == 1` and a max-results prefix can never masquerade as unique (the exact
concern 258 raised). `_link_by_unique_function` hard-codes `limit=2` for this reason.

## Scope / Deliverables

- **Delete the per-edge count from `_link_by_bare_name`.** Decide uniqueness from the batched fetch:
  link (queue HEURISTIC) iff `len(method_hits[name]) == 1`, skip otherwise — mirroring
  `_link_by_unique_function`. Fetch with `limit=max(max_candidates, 2)` so the length test is exact
  even when `max_candidates == 1`. This removes ~10⁶ queries → 0 (the fetch is already O(languages)
  per batch) and takes the correlated language sub-select out of the hot path with it.
- **Retire `count_nodes_by_name` if `_link_by_bare_name` was its only caller** (verify with a
  repo-wide search); leaving a dead per-edge-count primitive invites the same regression back (R7.6).
- **Regression test:** assert the bare-name pass issues **O(distinct names)** store queries, not
  O(edges) — e.g. a resolver run over an index with many call sites of a few names, counting real
  store calls (spy/counter), proving the count does not scale with edge count.
- **Before/after benchmark** on a large PHP index (full-build wall time + `resolve` CPU): record the
  drop in the ticket's working-doc ledger and one row in `TOKEN_LEDGER.md` (R7.2). Expectation:
  `resolve` returns from *hours / never* to *minutes*.

## Constraints

- **Behaviour-preserving.** 258's observable contract is unchanged: a multi-match bare Method CALLS
  stays one unresolved site (`target_qname IS NULL`, HEURISTIC), a unique match links HEURISTIC. Verify
  against `tests/test_resolver.py::test_many_method_name_matches_stay_one_unresolved_site` (uses
  `max_candidates=2`) and the `max_candidates=1` degenerate case.
- **Do not reintroduce the cartesian product** 258 removed — this ticket changes *how uniqueness is
  decided*, never *what is stored*. Queued output is still at most one candidate per site.
- R4.2: identical input → identical rows (the fetch order `_NODE_ORDER` already fixes tie-breaks).
- R1.4: `resolver.py` parses/decides, `store.py` owns SQLite — the batched primitive stays in store.
- 204: the bare-name pass keeps its call-site-language restriction; no widening.
- 027: an all-HEURISTIC batch's store budget stays O(1) per batch, not O(edges).

## Acceptance criteria

- `_link_by_bare_name` issues no `count_nodes_by_name` (and none per edge); a resolver run's store-query
  count scales with distinct names, not edge count (new regression test).
- A single unique same-language Method still links HEURISTIC; two-or-more matches stay one unresolved
  site — unchanged from 258, verified at `max_candidates` both `2` and `1`.
- A benchmark row shows `resolve` on a large PHP index dropping from the pre-fix time to minutes, with
  identical resolved/unlinked edge counts (proving behaviour, not just speed, held).
- If removed, `count_nodes_by_name` has no remaining callers and its tests go with it.
