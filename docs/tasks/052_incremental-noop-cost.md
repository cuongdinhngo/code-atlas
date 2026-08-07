---
id: 052
slug: incremental-noop-cost
title: Where does a no-op incremental build spend 62 seconds?
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [016, 047]
---

## Goal
`build_or_update_index(full=false)` on an 18.9k-file index where **nothing had changed** returned
`files: 0, parsed: 0, removed: 0, nodes: 0, edges: 0, seconds: 62.296`. Field-measured, round 1 §5.
[047](047_staleness-scoped-to-indexed-files.md) removed the *trigger* — a docs-only edit no longer
flips `staleness` to `behind` — but it did not make the call cheaper, and an agent that follows
`next_tool_suggestions` still pays that minute whenever any indexed source file is dirty.

Nobody knows where the minute goes. That is the whole problem: it blocks two decisions at once.

- **Is it a defect at all?** 62 s to reconcile a 19k-file tree against a 1.78M-edge graph may simply
  be the price. "Slow" without a breakdown is not a finding.
- **Can freshness be automated?** [053](053_refresh-on-checkout-hook.md) wants to run this from a git
  `post-merge` hook. At 62 s that is unacceptable and at 2 s it is obvious. 053 is gated on this
  number.

**Leading hypothesis, and it is not the parsing.** On a no-op run `to_parse` is empty and `_parse_all`
is skipped outright (`indexer.py:189-193`), so the adapter never parses anything. But
`_count_late_writes` (`:201`) then calls **`resolve_edges(store, max_candidates=…)` with no
`file_path`** (`:216`) — the unscoped form, which builds the whole alias map (`resolver.py:32`) and
iterates the *entire* unresolved edge set in batches of 1000 (`:33-35`). On the anchor repo that is
~490k unlinked edges, walked on every incremental run, including one that parsed zero files.

The read-through path already has the narrow version: `reparse_file` passes `file_path` so a
query-time repair links only that file's edges (035, `resolver.py:23-24`). The incremental path does
not, **and that is deliberate** — a node added by a changed file can link an edge emitted by a file
that did not change, so scoping the resolve to changed files would leave those edges unlinked
forever. Any fix has to keep that property. This ticket does not assume the resolver is the answer;
it names it as the first thing to time.

Other fixed costs a no-op still pays, in call order:

- `_announce` (`:146`, `:430`) starts the PHP adapter subprocess purely to learn which suffixes it
  owns. Under the Docker runtime that is a container start.
- `collect` → `_walk` (`:149`, `:275`, `:472`) walks the **whole** tree through the ignore matcher.
- `store.file_paths()`, `qnames_in_files`, `file_paths_targeting` (`:160-171`) and `_reconcile`
  (`:172`, `:487`) reconcile the kept path set against every indexed row.
- `file_is_current` → `_digest` (`:180`, `:269`, `:661`) hashes each candidate — small on a no-op,
  large on a `git pull` that touched a thousand files.

## Scope / Deliverables
- **A profiler under `scripts/`** that times `incremental_update`'s phases against a repo already on
  disk, using its existing index in place. Follow the `--local` tier precedent from
  [045](045_tokens-to-answer-local-repo.md): an operator-supplied absolute `root`, no copy, no
  `git init`, no rebuild, and nothing about a private repo committed here.
- **Three scenarios, not one.** (a) true no-op, HEAD unmoved and tree clean; (b) one source file
  edited; (c) a realistic `git pull` — order 10² files changed. The third is the one 053 needs and the
  one that has never been measured at all.
- **A breakdown that names the phase**, not a total: adapter announce · tree walk · reconcile ·
  hashing · parse · enrichment · resolve · meta. Confirm or refute the unscoped-resolve hypothesis
  above and say which by how many seconds.
- **A recorded decision on whether this is a defect.** If the minute is dominated by one phase that
  can be narrowed without breaking the cross-file linking property, ticket the fix separately. If it
  is the honest price of reconciling a graph that size, write that down and close — 053 then has to
  run the hook out of band rather than in it.
- **Runbook note** in [`runbooks/onboarding-a-repo.md`](../runbooks/onboarding-a-repo.md): what an
  incremental costs on a repo-sized tree, so the next operator budgets for it instead of discovering
  it.

## Constraints
- **Measure before changing anything.** No optimisation lands in this ticket. Its deliverable is a
  number and a decision; a fix, if warranted, is its own ticket with its own acceptance criteria.
- **No permanent instrumentation on the strength of a guess (R1.2, R7.4).** Phase timings may be
  added to the `build_or_update_index` payload only if the measurement shows a phase worth surfacing
  to an agent — and never to `get_index_status`, whose cheapness is what the field retro said must not
  break.
- **Determinism holds (R4.2).** Timings vary; counts must not. Whatever the profiler runs must leave
  the index in the state a plain incremental would.
- **Nothing about a private repo enters this repository** — not the path, not the report. Default the
  report outside `artifacts/` paths that CI uploads, as 045 does.
- **SQL stays in the store (R1.4)**; no language branch in the core (R1.1).

## Acceptance criteria
- The profiler runs against a local repo's existing index and emits a per-phase breakdown for all
  three scenarios, with the phases summing to the wall clock within a stated tolerance.
- The unscoped `resolve_edges` call is timed explicitly and reported as confirmed or refuted.
- A `git pull`-shaped incremental has a measured cost, stated in seconds against a stated number of
  changed files.
- The ticket's Outcome records whether the 62 s is a defect, with the evidence.
- The runbook states the expected incremental cost on a repo-sized tree.
- Two runs over an unchanged index produce identical counts (R4.2); `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/indexer.py:128-204` (`incremental_update`), `:146` + `:430` (`_announce`), `:149` + `:275`
+ `:472` (`collect` / `_walk`), `:160-172` + `:487` (reconcile), `:180` + `:269` + `:661`
(`file_is_current` / `_digest`), `:189-193` (parse skipped when `to_parse` is empty), `:201` +
`:207-218` (`_count_late_writes`), `:216` (the unscoped resolve).
`code_atlas/resolver.py:18-35` (`resolve_edges`, the `file_path` scope and the batch loop), `:32`
(`alias_targets`).
`code_atlas/tools/build_or_update_index.py:70-79` (`_run`, full-vs-incremental selection and the
`seconds` field).
Local-tier precedent: [045](045_tokens-to-answer-local-repo.md) and
[`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) §local tier.
Origin: field retro round 1 §5, recorded in [`BACKLOG.md`](../BACKLOG.md) as an open observation since
2026-08-07. Gates [053](053_refresh-on-checkout-hook.md).
