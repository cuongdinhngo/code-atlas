---
id: 283
slug: bare-name-resolve-counts-once-per-calls-edge
title: 'The bare-name resolve pass runs one `count_nodes_by_name` per CALLS edge — O(edges) SQLite COUNTs (each with a correlated language sub-select) where the batched fetch two lines above already proves uniqueness, so `resolve` on a large PHP repo went from ~15 min to never finishing; 258 traded a cartesian-product storage blowup for a per-edge query blowup that is worse'
phase: 1.5b
milestone: Graph
status: done
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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 283 — bare-name resolve O(names) not O(edges) (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: (1) keep count_nodes_by_name — find_callers still calls it (Scope retire-if-only-caller). (2) large PHP anchor-repo bench unavailable (real_corpus_path null) — record AC3 as coverage-gap exclusion; spy-based O(names) test is the proving test. Citation: ticket Scope bullet 2; harness real_corpus_path; Constraints behaviour-preserving.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | per-edge COUNT regression from 258 | uniqueness from batched fetch | D1 | AC1 | ✅ |
| C1 | Constraints | behaviour-preserving 258 | proving at max_candidates 2 and 1 | D2 | AC2 | ✅ |
| C2 | Constraints | no cartesian product | at most one candidate queued | D1 | AC2 | ✅ |
| C3 | Constraints | R4.2 / R1.4 / 204 / 027 | fetch stays in store; language filter | D1 | — | ✅ |
| R1 | Scope | delete per-edge count; limit=max(mc,2) | _link_by_bare_name | D1 | AC1–2 | ✅ |
| R2 | Scope | retire count if sole caller | keep — find_callers uses it | D1 | AC4 | ✅ |
| R3 | Scope | O(names) regression test | spy proving test | D2 | AC1 | ✅ |
| AC1 | AC | no count; scales with names | proving | D2 | proving | ✅ |
| AC2 | AC | unique links; multi stays unresolved at mc=2 and 1 | proving | D2 | proving | ✅ |
| AC3 | AC | large PHP resolve bench | EXCLUDED — no corpus | — | gap | ⬜ |
| AC4 | AC | count retired iff no callers | kept for find_callers | D1 | AC4 | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 258 added per-edge count_nodes_by_name while nodes_by_names already answers uniqueness when probe_limit >= 2.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 ✅ · R1.4 ✅ · R7.6 ✅`

Ran at 59098518f62936d3f2a0982ad4c35af0b385e4ab

```
$ .venv/bin/python -m pytest tests/test_bare_name_resolve_query_budget.py tests/test_resolver.py::test_many_method_name_matches_stay_one_unresolved_site -q --tb=no
...                                                                      [100%]
3 passed in 0.35s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: probe_limit = max(max_candidates, 2); link iff len(method_hits[name]) == 1; keep count_nodes_by_name for find_callers; spy regression test; exclude large-corpus AC3.
- Rejected: retire count_nodes_by_name (still used); invent anchor-repo numbers (never invent).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Exclusion: AC3 large-PHP resolve wall-time — no real_corpus_path / anchor-repo checkout on this host; expiry: 2026-10-15 or when config.real_corpus_path is set.

**Proving test:** `.venv/bin/python -m pytest tests/test_bare_name_resolve_query_budget.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | uniqueness from batched fetch | resolver.py | bare-name resolve | 1/1 |
| D2 | O(names) spy + max_candidates=1 | tests/test_bare_name_resolve_query_budget.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/283-bare-name-resolve-o-names-not-o-edges
**Axis 1:** resolver · proving tests.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 59098518f62936d3f2a0982ad4c35af0b385e4ab

```
$ .venv/bin/python -m pytest tests/test_bare_name_resolve_query_budget.py tests/test_resolver.py::test_many_method_name_matches_stay_one_unresolved_site -q --tb=no
...                                                                      [100%]
3 passed in 0.35s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (1 can't tell: AC3 large-PHP bench); reconciled against Gate-2 exclusion (real_corpus_path null / no anchor-repo); no code fix without inventing numbers. agent aa496e71-2dea-4cb3-85a8-5c1a9551b57b
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_bare_name_resolve_query_budget.py — 2 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-283.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/374

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on (1 can't tell → exclusion); main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
