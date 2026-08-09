---
id: 068
slug: rules-bookmark-counted-as-source-file
title: 'The rules bookmark is counted as an indexed, successfully parsed source file'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [040, 062, 064]
---

## Goal
Enabling `indirection_rules` adds a synthetic `files` row and a synthetic `File` node for
`.code-atlas/indirection-rules`, written with `parsed_ok=True`. `get_index_status` counts the `files`
table, so turning the rules channel on **raises `files` and `parsed` by one** with no file having been
read. A field evaluator caught the drift from the outside and could not explain it. Stop counting a
bookmark as source.

## Evidence (anchor repo, 2026-08-09)
- Round-3 retro §0 flagged it blind: the build report said **18,876 collected / 18,847 parsed**, and
  `get_index_status` in the same session said **18,877 / 18,848**, failures matching exactly at 29.
  The evaluator wrote: *"the index I was handed is not quite the index the evaluation describes"* —
  the drift class that quietly invalidates a benchmark.
- Confirmed directly against the database:
  ```
  files rows: 18877
    file: ('.code-atlas/indirection-rules', parsed_ok=1)
    node: ('.code-atlas/indirection-rules', 'File', '.code-atlas/indirection-rules')
  ```
- Source: `enrichment.py:142` — `store.upsert_file(INDIRECTION_FILE, loaded.digest, _RULES_LANGUAGE,
  parsed_ok=True)`, then `replace_file_rows`. `store.counts()` (`store.py:397`) is
  `SELECT COUNT(*) FROM files` and `COUNT(*) … WHERE parsed_ok = 1`, so both totals absorb it.
  `BuildReport.files` is `len(kept)` (`indexer.py:137`) and does not — hence exactly the +1/+1 split.
- **This also answers the open question in [064](064_build-without-adapter-silent.md):** the
  adapter-less build reported `nodes: 1` with `parsed: 0` because rules were configured, and the
  bookmark node is that node. 064's "account for `nodes: 1`" item resolves here.
- The bookmark is already special-cased elsewhere, so the concept of "not a real file" exists:
  `is_rule_edge_path` suppresses `file` on hits and sets `rule: true` (`nav_result.py`);
  `_reconcile` excludes it from removal (`indexer.py:190, 539`); `_view_data_edges` skips it as a
  call-site source (`enrichment.py:176`). Only the **counters** treat it as source.

Scale note: the distortion is one row. That is precisely why it must be fixed rather than tolerated —
it is small enough to be invisible and load-bearing enough to make two honest numbers disagree.

## Scope / Deliverables
- **Exclude the bookmark from source-file counters.** `files`, `parsed`, and anything derived
  (`parsed_ok` ratios, staleness denominators, `dirty_indexed_files`) count on-disk source only.
- **Make `BuildReport` and `get_index_status` agree by construction**, not by coincidence — a test
  asserting equality with the rules channel *on* is the deliverable that keeps them together.
- **Pick one representation and apply it everywhere.** Either the bookmark stops living in `files`,
  or it carries a marker every counter honours. The current state — a real row that most call sites
  remember to skip — is the defect.
- **Check the neighbours.** `nodes` totals, `find_orphans`, `reachable_from`, `search_symbol`, and
  `file_outline` each need a verdict on whether the bookmark can surface; state each explicitly
  rather than fixing only the two counters that were caught.
- **Close 064's open item** by reference, and update that ticket.

## Constraints
- R1.1 / R2 — the bookmark is core vocabulary, not a language or repo artifact.
- R4 — with the rules channel off, every number is byte-identical to today's.
- 040 / 062 — the bookmark's role as the anchor for rule-derived edges does not change; only what
  the counters say about it.

## Acceptance criteria
- With `indirection_rules` set, `get_index_status.files` / `parsed` equal `BuildReport.files` / `parsed`
  and equal the count of real source files; a test pins the equality with the channel on and off.
- The rules bookmark never appears as a result in a tool whose subject is a source file.
- Rule-derived edges still resolve, and `find_view_data` output is unchanged.
- 064's `nodes: 1` question is answered in that ticket with a pointer here.

## References
Field retro round 3 §0 (the +1 drift, found from outside). `code_atlas/enrichment.py:22,99-143`
(`INDIRECTION_FILE`, `upsert_file(..., parsed_ok=True)`); `code_atlas/store.py:394-400` (`counts`);
`code_atlas/indexer.py:137,190,539`; `code_atlas/tools/nav_result.py` (`is_rule_edge_path`).
Related: [040](040_framework-indirection-data.md) (the rules channel),
[062](062_view-databag-producer.md) (what the bookmark anchors),
[064](064_build-without-adapter-silent.md) (the `nodes: 1` question this closes),
[028](028_index-health-metrics.md) (the counters), [051](051_build-report-edge-undercount.md)
(precedent: a build number that did not match the graph it described).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 068 — working doc (mango)

## Session status

- **Phase:** execute complete; review skipped; finalise pending
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full (review skipped)
- **BASELINE:** green — 1016 passed
- **work_doc_mode:** embed
- **working-doc path:** this file below separator
- **Branch:** `fix/068-rules-bookmark-counted-as-source-file`

## Phase 0 — Refine

`REFINE: 5 want ASSUMED (blanket) | HOW cited | exposure-checker 8 findings folded | skip: no`

| # | Want | Chosen (ratified) |
|---|------|-------------------|
| W1 | representation | Drop `files` row + File node; keep edges on `INDIRECTION_FILE` |
| W2 | schema bump | No — edges have no FK |
| W3 | legacy purge | Always `remove_file` before apply |
| W4 | neighbours | No search/outline/orphan/reachable_from subject; dirty/failed/stubs N/A |
| W5 | review | Skip this run |

## Requirements matrix

`SECTIONS: 5 | ROWS: C=3 R=5 G=1 AC=4` — all ✅ under Ph3

| ID | Interpretation | Status |
|----|----------------|--------|
| G1 | stop counting bookmark as source | ✅ |
| R1 | exclude from files/parsed counters | ✅ by construction |
| R2 | BuildReport ↔ status agree with rules on | ✅ proving test |
| R3 | one representation everywhere | ✅ edges-only |
| R4 | neighbour verdicts | ✅ |
| R5 | close 064 | ✅ |
| AC1–4 | equality + no surface + view_data + 064 | ✅ |

## Design (Gate 2 — approved)

**Approach:** `apply_indirection_rules` always purges the bookmark path, then writes edges only via `replace_file_rows(..., [], edges)` — never `upsert_file` / File node.

**Change list:**
1. `code_atlas/enrichment.py` — edges-only apply + purge
2. Flip 051 disagreement test → equality; legacy purge + tool-subject tests
3. Docs: PLAN, LESSONS, 064, BACKLOG, task 068

**Proving test:** `test_rules_bookmark_does_not_inflate_source_file_counts`

## Post-PR review (main loop, 0 dispatch) — two findings, both fixed on the branch

**1. R3 ("one representation everywhere") was not met — the exemptions outlived the row.**
`indexer.py:192` and `:550` still subtracted `{INDIRECTION_FILE}` from sets built out of
`store.file_paths()`. Post-068 the bookmark has no `files` row, so neither subtraction can ever
match: they are the "real row that most call sites remember to skip" pattern this ticket exists to
delete, kept alive after the row was gone (R7.4). Both removed, with the import.

Safe because of ordering, which is now pinned rather than assumed: `_reconcile` runs at
`indexer.py:126` (full) / `:196` (incremental), and `_count_late_writes` → `apply_indirection_rules`
always runs after it, on both paths, with no early return between. So on a **pre-068** index the
reconcile pass performs the purge and enrichment re-inserts the edges in the same run — the end state
is identical, and `removed` counts the one row that really was removed.
`test_legacy_bookmark_is_purged_by_an_incremental_run_without_losing_rule_edges` covers the
incremental path the branch had only tested through `full_build`, and asserts the rule edges survive.

**2. The neighbour verdict (R4/W4) was proven vacuously, and missed `reachable_from`.**
`test_rules_bookmark_is_not_a_source_file_tool_subject` called `find_orphans` on a config with no
entry points, so it returned `status: no_roots_configured` with **zero rows** — every "the bookmark
is absent" assertion passed over an empty list. `reachable_from`, named in the ticket's own neighbour
list, was not checked at all. The test now sets `CA_ENTRY_POINTS`, asserts each payload is `ok` with
non-empty results *before* asserting absence, and covers both tools (3 orphans / 2 reachable rows on
the fixture).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | explore | 1 | unmeasured (blocking retrieval) |
| refine | exposure-checker challenger | 1 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-09 | edges-only representation; purge legacy; skip review |

## Reviewed at

skipped (user instruction)
