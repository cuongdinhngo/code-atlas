---
id: 073
slug: freshness-cannot-find-what-is-not-indexed
title: 'Read-through freshness repairs only rows it already found — a new symbol is confidently reported absent'
phase: 1.5b
milestone: Agent-trust
status: todo
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

**The field write-up attributed this to the FTS index not being refreshed. That is not the mechanism**
and the distinction matters, because the FTS explanation would make this a narrow `search_symbol` bug
when it is in fact general:

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
  (path-named, qname-named, query-named) and pins each answer.
- 035's documented guarantee matches the code.

## References
Memory/concurrency field run 2026-08-09 §5 (the two-tool disagreement), §6 (the probe transcript that
shows the call ordering), §10.2 (the protocol gap that surfaced it).
`code_atlas/tools/search_symbol.py:72-83` (fetch-then-ensure), `code_atlas/tools/freshness.py`
(`ensure_paths`, `ensure_qname`, `READ_THROUGH_CAP`), `code_atlas/store.py:80-97` (the FTS triggers
that rule out the first-guess mechanism). Related: [035](035_read-through-freshness.md) (the
guarantee), [065](065_empty-answer-cannot-explain-itself.md) (the channel this should reuse),
[033](033_nav-reason-codes.md) (`index_stale` and the reason vocabulary).
