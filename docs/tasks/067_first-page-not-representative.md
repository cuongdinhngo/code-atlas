---
id: 067
slug: first-page-not-representative
title: 'Page 1 of `find_callers` was 100% of the tree the agent must not touch, 0% of the tree it had to change'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [057, 013]
---

## Goal
`find_callers` was **correct** — 23 of 23, hand-verified — and still a **net loss** on the one
question the round-3 session asked it, because the visible page pointed away from the answer. Result
ordering is a correctness surface when the caller reads one page and stops.

## Evidence (anchor repo, index built 2026-08-09, reproduced against the DB)
`find_callers("\getActiveStatus")` → `total_count: 23`. Rows are ordered by
`_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"` (`store.py:114`). The first 10
rows under that ordering:

```
\getIconMemberInfo            legacy/alpha/web/ajax.php:821
\getIconMemberInfo            legacy/beta/web/ajax.php:548
legacy/alpha/…/detail_screen.php  legacy/alpha/…/detail_screen.php:323
legacy/alpha/…/member_screen.php  legacy/alpha/…/member_screen.php:1343
legacy/alpha/…/tabs.php             legacy/alpha/…/tabs.php:26
legacy/alpha/…/major_change.php     legacy/alpha/…/major_change.php:121
legacy/alpha/…/movement_list.php    legacy/alpha/…/movement_list.php:1233
legacy/alpha/…/reviewOnly.php       legacy/alpha/…/reviewOnly.php:77
legacy/beta/…/ledger_screen.php       legacy/beta/…/ledger_screen.php:37
legacy/beta/…/detail_screen.php   legacy/beta/…/detail_screen.php:284
```

**All 10 are `legacy/`. All 8 `src/` callers sit on pages 2–3.** File-scope call sites carry the file
path as `source_qname`, and `\g…` < `legacy/…` < `src/…`, so the sort is effectively lexical by path.
In this repo `legacy/` is a **read-only, being-deleted tree the agent is forbidden to edit**.

The session's own words: it "briefly read that page as *no `src/` callers*" before `grep` contradicted
it, and recorded the call as the single question where the graph was a net loss versus `grep` — at
roughly twice the tokens. The payload was honest (`truncated: true`, `total_count: 23` both correct);
**the sample was not representative**, which no honesty field can repair.

This compounds with [066](066_limit-clamped-silently.md): the session asked for `limit: 30` — enough
to see all 23 — and silently received the 10 that were least useful.

## Scope / Deliverables
- **Measure before designing.** Across the fixture corpus and the anchor repo, quantify how often
  page 1 of a `find_callers` / `find_references` result is drawn from a single directory subtree
  while later pages hold others. If skew is rare, this ticket shrinks to documentation. The count is
  the kill gate.
- **Pick an ordering that is defensible for a first page**, and write down the reasoning against
  at least: confidence tier first (RESOLVED before HEURISTIC), interleaving by top-level directory,
  and keeping the current lexical order. The current order is not the product of a decision — it is
  `_EDGE_ORDER`, a storage-layer sort reused for presentation.
- **Determinism is non-negotiable (R4).** Whatever ordering is chosen must be total and stable —
  `id` stays the final tiebreak. No sampling, no randomisation, no host-dependent ordering.
- **Consider telling the caller about the skew** rather than reordering: e.g. the distinct
  top-level directories present in the *full* result set, so a caller reading page 1 knows another
  subtree exists. Cheaper than reordering and possibly sufficient — evaluate both.
- **No language or repo knowledge.** `legacy/` vs `src/` is this repo's convention. Nothing in the
  core may learn those names (R2); the mechanism must be structural.

## Constraints
- R2 absolute — no repo-specific path names anywhere in `code_atlas/`.
- R4 — identical index + identical query ⇒ identical row order.
- 057 — `offset` paging must remain coherent: a stable total order, no row appearing on two pages or
  on none.
- Reordering changes every paged tool's output; the contract-conformance suite and any golden
  payloads move with it in the same change.

## Acceptance criteria
- The skew measurement lands in the working doc before any ordering change, with the proceed/kill
  call recorded.
- If ordering changes: a fixture where callers span two top-level directories yields a first page
  containing both, and full enumeration by paging still returns every row exactly once.
- If the answer is a signal instead: a caller reading only page 1 can tell from the payload that
  results exist in a subtree not shown.
- `find_callers("\getActiveStatus")`-shaped case documented as a regression test at fixture scale.
- Ordering is deterministic across repeated runs and across a rebuild of the same tree.

## References
Field retro round 3 §4 ("biased page 1"), §8 (net loss), §11b ("correctness and usefulness came
apart"). `code_atlas/store.py:114` (`_EDGE_ORDER`), `code_atlas/store.py:485-530`
(`edges_by_source` / `edges_by_target`). Related: [057](057_answer-pagination.md) (paging),
[066](066_limit-clamped-silently.md) (the clamp that kept the page at 10),
[013](013_nav-tools.md) (nav tool surface).
