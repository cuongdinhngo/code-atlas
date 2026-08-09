---
id: 068
slug: rules-bookmark-counted-as-source-file
title: 'The rules bookmark is counted as an indexed, successfully parsed source file'
phase: 1.5b
milestone: Agent-trust
status: todo
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
