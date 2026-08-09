---
id: 073
slug: freshness-cannot-find-what-is-not-indexed
title: 'Read-through freshness repairs only rows it already found — a new symbol is confidently reported absent'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [035, 065, 033]
---

## Goal
Read-through freshness is **result-driven**: it takes the paths of the rows a query already matched
and repairs those. A symbol added to a drifted file matches nothing, so there are no paths to repair,
no reparse is attempted, and the caller receives `reason: "no_matches"` — a confident proof of absence
for a symbol that is on disk. During an edit-heavy fan-out, that is every symbol an agent just wrote.

## Evidence (memory/concurrency field run, 2026-08-09, anchor repo)
Two tools in the same server disagreed about the same file:

```
search_symbol(atlasProbeMainAb3)          -> {"results":[],"reason":"no_matches","total_count":0}
file_outline(src/System/RegionManager.php) -> names=[…, 'atlasProbeMainAb3', …]
```

`atlasProbeMainAb3` had just been written into that file on disk. `file_outline` names a path, so its
guard repaired that path and the symbol appeared. `search_symbol` names only a query, so it had
nothing to repair.

### Reproduced in this repo, and the FTS explanation is ruled out
A three-file PHP fixture, built full, then a method appended to `src/Widget.php` on disk with no
rebuild. Same server, three calls in this order:

```
A. search_symbol("atlasProbeZq7")   -> {"results":[], "reason":"no_matches", "total_count":0}
B. file_outline("src/Widget.php")   -> [..., '\App\Widget::atlasProbeZq7']
C. search_symbol("atlasProbeZq7")   -> {"results":[{...line 4}], "reason":"ok", "total_count":1}
```

**C is the decisive cell.** If the FTS table were the stale component, C would still fail — the same
FTS is queried in A and C, and nothing between them rebuilt it. C succeeds because B's *path-named*
call performed the reparse that A never attempted, and the insert triggers carried the row into FTS
correctly on the way.

**Consequence for the fix: "refresh FTS as part of `reparse_file`" is a no-op** and would leave the
defect in place. FTS is already refreshed by every reparse. What is missing is the reparse.

### Why the FTS reading is wrong
The distinction matters because the FTS explanation would make this a narrow `search_symbol` bug when
it is in fact general:

- `nodes_fts` is an external-content fts5 table kept current by triggers on every insert, delete and
  update of `nodes` (`store.py:80-97`). A reparse that writes a node **does** update FTS.
- The real path is `search_symbol.py:74-83`: rows are fetched first, then
  `guard.ensure_paths(hit_paths)` is called on the paths **of those rows**, and the re-query fires only
  `if status == "repaired" or (status == "stale" and guard.used > 0)`. With zero hits, `hit_paths` is
  empty, `ensure_paths([])` returns `ok`, and no adapter ever runs.
- The same blind spot sits in `FreshnessGuard.ensure_qname` (`freshness.py`): `if not rows: return
  "ok"`. Every tool that resolves a subject by qname — `find_callers`, `find_references`,
  `find_implementations`, `find_view_data`, `read_symbol` — reports a brand-new symbol as absent
  without attempting a reparse, and calls that state `ok`.

So the honest statement of 035's guarantee today is: *freshness repairs what the index already knows
about; it cannot discover what the index has not yet seen.* That is a defensible design — it is also
undocumented, and the payload asserts the opposite by returning a clean empty answer.

Confirming it is not a contention artifact: under 3-way write contention with 452 drift events the
run recorded **zero** `index_stale` soft-fails and zero `SQLITE_BUSY` reaching a caller. This defect
appears at N=1, on a single quiet server, the moment a file changes.

## Scope / Deliverables
- **Decide what an empty result owes a drifted tree, and record the decision.** Three candidates, and
  the ticket must choose explicitly rather than drift into one: (a) leave behaviour as is and make the
  limit legible in the payload — the [065](065_empty-answer-cannot-explain-itself.md) channel, since
  this is the same family: an empty answer that cannot say why it is empty; (b) when a query would
  return zero results, spend the call's one reparse budget on the dirty files that could plausibly
  contain the subject, then re-query; (c) reject (b) on cost and say so with numbers.
- **Bound any repair by the existing budget.** `READ_THROUGH_CAP = 1` exists so one tool call spawns at
  most one adapter. A zero-result query has no natural single path to repair, so option (b) needs a
  rule for *which* file — "all dirty files" is a full incremental build wearing a read tool's name and
  must be ruled out on measurement, not on instinct.
- **Make the asymmetry visible either way.** A path-named tool (`file_outline`) and a query-named tool
  (`search_symbol`) currently give different answers about the same file at the same moment. Whatever
  is chosen, a caller must be able to tell that the query-scoped answer carries a weaker guarantee.
- **Correct the record in 035's documentation.** Its docstrings and task doc should state the
  result-driven boundary in the terms above, so the next reader does not have to rediscover it from a
  probe.
- **Every guard consumer, not just `search_symbol`.** `ensure_qname`'s `if not rows: return "ok"` is
  the same defect on five more tools and must move with it.

## Constraints
- R4 — deterministic. Any repair rule must produce the same answer for the same tree state; "repair
  whichever file we noticed first" is not a rule.
- 035 — the per-call reparse cap is the whole point of read-through freshness. Raising it silently to
  make this work is out of scope; changing it is a decision to be argued and measured.
- 061 — if the answer is a signal rather than a repair, it is one field.
- R5.2's spirit — never claim the stronger tier. `ok` is the strongest freshness claim the vocabulary
  has, and it is currently emitted in exactly the case where nothing was checked.

## Acceptance criteria
- A symbol written to an already-indexed file and then queried by name is either found, or reported
  with a signal distinguishing it from a genuine absence — the choice recorded with its reasoning.
- `file_outline` and `search_symbol` asked about the same freshly-edited file no longer make
  contradictory claims without any indication of which is weaker.
- The `ensure_qname` no-rows path behaves consistently with the `ensure_paths` empty path across all
  six consuming tools; a test enumerates them.
- A fixture-scale regression test writes a new symbol into an indexed file, queries it three ways
  (path-named, qname-named, query-named) and pins each answer. The A/B/C sequence above is that test;
  it must include cell C, which is what distinguishes this defect from a stale-FTS one.
- 035's documented guarantee matches the code.

## References
Memory/concurrency field run 2026-08-09 §5 (the two-tool disagreement), §6 (the probe transcript that
shows the call ordering), §10.2 (the protocol gap that surfaced it).
`code_atlas/tools/search_symbol.py:72-83` (fetch-then-ensure), `code_atlas/tools/freshness.py`
(`ensure_paths`, `ensure_qname`, `READ_THROUGH_CAP`), `code_atlas/store.py:80-97` (the FTS triggers
that rule out the first-guess mechanism). Related: [035](035_read-through-freshness.md) (the
guarantee), [065](065_empty-answer-cannot-explain-itself.md) (the channel this should reuse),
[033](033_nav-reason-codes.md) (`index_stale` and the reason vocabulary).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 073 — freshness-cannot-find-what-is-not-indexed (working doc)

- **Ticket:** 073 · local file
- **Type:** bug / agent-trust
- **SCOPE:** M · **TRACK:** backend · **TIER:** full (review skipped)
- **BASELINE:** green (pre-change main suite)
- **work_doc_mode:** embed

## Phase 0 — Refine

`REFINE: hybrid ratified under blanket approval | skip: no`

**Settled wants:** hybrid of (b)+(a) — sole dirty indexed file → miss-repair under CAP=1; multi-dirty → `index_stale` + `try_instead=file_outline`; post-repair miss → genuine empty; candidate set = git dirty ∩ indexed suffixes.

**Exposure-checker:** [challenger](58f7b485-d6f9-4825-bcb9-30cb672ef065) — gaps A1–A4 ratified as above.

## Matrix (summary)

`SECTIONS: 5 | ROWS: G1 R1–5 C1–4 AC1–5` — all ✅ via miss-repair + tests + 035 doc note.

## Design

Approach: `FreshnessGuard.ensure_miss` + `ensure_qname` no-rows → miss; `search_symbol` zero-hit → miss; multi-dirty stale + hint; document 035 boundary.

Rejected: always reparse all dirty (cap violation); pure signal-only (leaves single-edit case broken); raise CAP.

Proving: `tests/test_freshness_cannot_find_what_is_not_indexed.py`

## Execute

Branch `fix/073-freshness-cannot-find-what-is-not-indexed`. Suite **1007 passed**. Review skipped.

**Post-PR review (main loop, 0 dispatch) — one defect, fixed on the branch.** The `search_symbol`
miss-repair keyed off an empty *page*, not an empty answer, so it also fired when `offset` walked past
the end (057). Measured on a two-node fixture, query `Thing`, `limit=1`, two dirty indexed files:
`offset=0 → reason ok, total_count 2` but `offset=9 → reason index_stale, total_count 2, no
try_instead` — the freshness verdict flipped with pagination on an answer that was never empty, and
with a single dirty file the same path spent the `READ_THROUGH_CAP` reparse on a query that already
had hits. Fix: gate the miss on `offset == 0`; pinned by
`test_empty_page_past_the_end_is_not_a_miss`, which also asserts the cap is unspent. The nav tools are
unaffected — `ensure_qname` keys off the subject qname, not the page.

## Cost ledger

| Phase | Dispatch | Tokens |
|-------|----------|--------|
| refine | explore | unmeasured (blocking retrieval) |
| refine | exposure-checker | unmeasured (blocking retrieval) |

## Session status

finalise → ship (user pre-approved commit/push/PR)

