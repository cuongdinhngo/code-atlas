---
id: 396
slug: rules-stale
title: 'An index built under other indirection rules answers as current, and a rules-only change waits for a full rebuild'
phase: 2
milestone: Freshness
status: todo
depends_on: [040, 080, 385]
---

## Why this exists

This comes from the anchor project (2026-10-17). The anchor drafted three more rule blocks
(`keyed_calls` table writes, a `routes` TSV) and stopped before committing them: no session could
tell whether its index had been built under them, so a rule-fed answer was unverifiable.

- F1: `load_indirection_rules` computes `RulesPayload.digest` (`enrichment.py:87-116`), and nothing
  stores or compares it. An index built before a rule edit, or with the knob off, still reports
  `current`. `find_view_data`, the rule-fed writers in `find_references` and a route lookup answer
  from the old rules with no label.
- F2: a true no-op incremental skips enrichment and the resolve (`indexer.py:598-619`, task 080).
  A rule edit with no source change is applied only by the next build that parses a file, or by
  `--full` (~550 s on the anchor). The anchor's setup doc has to say "a rule change applies only on
  `--full`", and the background refresh hooks never apply one.
- F3: a `routes` TSV is digested with its rule file, so the same gap covers a regenerated table.

Each session builds at a different time and from different rules, so a rule is only as
trustworthy as the least-recently-built index that answers with it.

## Scope

1. The build stores the rules digest in meta (empty when the knob is off).
2. `get_index_status` recomputes the digest from the rule files on disk and reports
   `rules_stale: true` with both digests when they differ; the summary names the build that
   clears it.
3. A rule-fed answer on a `rules_stale` index is labelled (`rules_stale`, never `ok`) and keeps its
   rows; an answer that reads no rule edge is unchanged.
4. An incremental build whose digest moved re-runs enrichment, `publish_routes` and the resolve
   scoped to the rules bookmark, even when nothing was parsed. Rules turned off clear the rows the
   same way.

## Acceptance criteria

- **AC1:** Build with a `view_data` rule, then edit the rule file: `get_index_status` reports
  `rules_stale: true`, and `find_view_data` answers labelled `rules_stale`.
- **AC2:** Then an incremental build with no source change: the new rule's edges are present, the
  build is not reported as a no-op, `rules_stale` is gone, and no file was re-parsed.
- **AC3:** Remove `indirection_rules`, incremental build: every rule-derived edge and the route
  table are gone.
- **AC4:** A routes TSV edited, nothing else: AC1 and AC2 hold for a route lookup.
- **AC5:** Digest unchanged: a no-op stays a no-op (same timing class as 080), and every answer is
  byte-identical.

- **AC-field:** on the anchor index, a rule edit followed by the background refresh answers
  `find_view_data` and a table's writers from the new rule with no `--full`; record the build time
  in the working doc.
