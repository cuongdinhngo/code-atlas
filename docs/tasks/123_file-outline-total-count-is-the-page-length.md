---
id: 123
slug: file-outline-total-count-is-the-page-length
title: '`file_outline` omitted the symbol under repair, reported `total_count: 10` for a 12-symbol file, and has no page 2'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [014, 057, 066, 067]
---

## Why this exists (field retro round 6, 2026-08-21, anchor monorepo, `max_results` = 10)

`file_outline`'s own description says: *"Call this before you read or port a large file — it is the
symbol map."* On a **225-line file holding 12 symbols** it returned:

```
results: 10 rows · truncated: true · total_count: 10
```

The two symbols it dropped included **the defect site of the ticket being worked**. Ordering is
alphabetical, the cut is at `max_results`, and the missing method was the 8th of 9. Cross-checked with
`impact` on the same file, which returned all 13 nodes.

Two independent defects in that one payload:

1. **`total_count` means the page length, not the total.** `file_outline.py`:
   `total_count=len(results)`. On `search_symbol` the same field is the real total
   (`search_symbol.py:179`, `store.count_search_nodes`), and on `find_references` /
   `find_implementations` it is the real edge count. So one field name carries two meanings across the
   surface, and on `file_outline` **the true count is not recoverable from the payload at all**.
   Independently reproduced: a 118-function utility file also reports `total_count: 10`.
2. **A truncated outline is terminal.** The signature is `{path, detail_level}` — no `limit`, no
   `offset`. There is no page 2 from this tool at any call site.

**Round 5 recorded `file_outline` as its most expensive *miss* — the tool it never called. Round 6
called it and it was wrong.** That is a strictly worse outcome: not calling a tool leaves you knowingly
ignorant, calling one that under-reports leaves you confidently wrong. The same tool has now failed two
evaluators in opposite directions.

## The exclusion was deliberate, and that is the finding

This is not an oversight to be embarrassed about — it is a recorded decision meeting its first field
evidence. Both prior paging tickets ruled `file_outline` out **on purpose**:

- [057](057_answer-pagination.md): *"**Tools:** `search_symbol`, `find_implementations`,
  `find_callers`, `find_references`. Reachability, `file_outline`, and `include_graph` stay out."*
- [066](066_limit-clamped-silently.md): *"Out of scope (no user `limit` param → nothing to clamp):
  `file_outline` … it reports `truncated` but never reduces a caller's request."* — with a
  forward-looking clause: *"AC3's enumerating test must be built so that if either later grows a
  `limit` param, it is forced into the clamp-signal contract."*
- [067](067_first-page-not-representative.md) gave `search_symbol` `result_subtrees` so page 1 cannot
  hide the rest of the tree. It never reached `file_outline` — the tool most likely to be asked about a
  large file.

The exclusions were reasonable when made and are cheap to close now: **nine tools already carry
`offset: int = 0`** (`search_symbol`, `find_references`, `find_callers`, `find_implementations`,
`find_view_data`, `get_index_status`, `architecture_overview`, `guided_tour`, `file_outline`
(123), `find_orphans` (124)). `include_graph` is the remaining list-returning tool without paging.

## Why raising `max_results` is not the fix

`max_results` is configurable and `get_index_status` reports it (`governs: [returned_rows,
resolver_candidate_fanout]`), so a wider page is available. But the `total_count` inconsistency is a
bug at **any** page size, and "the symbol map cannot be paged" is a shape gap, not a tuning problem.
Raising the knob also widens resolver candidate fan-out, which is a separate cost.

## Scope

- **Make `total_count` mean on `file_outline` what it means on `search_symbol`** — the real number of
  symbols in the file, from a store-side count (R1.4: the SQL lives in `store.py`; `nodes_by_file` has
  no counterpart count method today).
- **Add `limit` / `offset`**, following 057's mechanism and store ordering exactly, and fold the new
  `limit` into 066's clamp contract — which 066's AC3 test already anticipates.
- **Bring 067's spread disclosure to a truncated outline**, so a capped symbol map says what kind of
  symbols it is not showing rather than presenting itself as complete.
- **Fix the description.** A tool that calls itself "the symbol map" while capable of returning a
  partial one must say so in its own docstring; the reader's trust came from that sentence.

### Supporting context — truncation is not a neutral trade

Round 6's single most valuable result arrived from a `search_symbol` page holding 9 rows of
`total_count: 20`, where **4 of the 9 were one test class**. The row that corrected already-shipped
work fitted on page 1 by luck; a slightly different ranking and it would have been invisible.
`search_symbol` itself needs no fix here — it reports an honest total and takes an `offset`, so the
reader can see there is a page 2 and go there. That is exactly the affordance `file_outline` lacks, and
it is the argument for this ticket rather than a separate one.

## Acceptance criteria

1. **AC1.** On a file whose symbol count exceeds the page size, `total_count` equals the true symbol
   count and `truncated: true`; the two fields can no longer contradict each other.
2. **AC2.** A cross-tool test asserts `total_count` has one meaning — the true total — on every tool
   that emits it, with the tool list as the denominator (`guided_tour` and `architecture_overview`
   included, or explicitly excepted with the reason recorded).
3. **AC3.** Paging a file's outline with `limit`/`offset` visits every symbol exactly once and the last
   page reports `truncated: false` — 057's `test_paged_walk_visits_each_row_once_stable` shape, reused.
4. **AC4.** `file_outline`'s new `limit` is inside 066's clamp contract: an over-ceiling request reports
   `limit_capped_to`, proven by the enumerating test 066 built for this purpose.
5. **AC5.** The round-6 case is a regression test: a file with more symbols than the page size never
   omits a symbol without the payload disclosing both the true count and the route to the rest.
6. **AC6.** The default payload for a file that fits in one page is byte-identical to today (R4.2).
7. **AC7.** 057's and 066's recorded exclusions are updated in those tickets to say the exclusion was
   closed by field evidence — a deliberate scope boundary that later cost an answer should read as
   revisited, not as forgotten.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 123 — file_outline total_count is the page length (working doc)

- **Ticket:** 123 · `docs/tasks/123_file-outline-total-count-is-the-page-length.md`
- **Type:** bug
- **SCOPE:** M · **TIER:** full
- **CHALLENGER:** OFF · **Review:** SKIPPED (solve args)
- **BASELINE:** 1692 passed (main, 2026-08-22)

## Execute summary

- `store.count_nodes_by_file`, `node_kinds_by_file`, `nodes_by_file` + `offset`
- `file_outline`: honest `total_count`, `limit`/`offset`, `result_kinds`, clamp contract
- Tests: `test_file_outline_pagination.py`, `test_total_count_semantics.py`; 066 denominator → 6
- Delta-green: **1692 → 1709 passed** (+17)

## Session status

- **Current phase:** complete (shipped)
- **work_doc_mode:** embed
- **Next action:** commit, push, open PR

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens |
|-------|---------------------|-------|--------|
| — | no subagent dispatched | — | unmeasured (host does not surface usage) |

**LEDGER TOTAL:** 0 dispatch · main-loop only
