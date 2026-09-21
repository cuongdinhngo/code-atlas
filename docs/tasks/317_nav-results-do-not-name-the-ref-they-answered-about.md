---
id: 317
slug: nav-results-do-not-name-the-ref-they-answered-about
title: "Only get_index_status and behind-labelled reads name the ref they answered about, so a find_callers on a worktree can silently describe main and the caller never knows"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [071, 077]
---

## Why this exists (field-retro 2026-09-20, the worktree trap)

A reviewer subagent ran `find_callers` from a feature-branch checkout and got an **empty** result;
the main-branch run of the same query returned 9. The index answered about `main`, the caller was on a
branch, and nothing in the nav payload said which ref the answer described — the empty read was
indistinguishable from "no callers." The retro's ask: *"an `answered_about_ref` field on every query
result, not just get_index_status, so the worktree-staleness trap can't be missed silently."*

The pieces exist but stop short of every nav result. `index_root` rides every payload (071);
`head_ref`/`last_ref` were added to `get_index_status`/`build_or_update_index` (077); `serve_behind`
labels a *behind* nav read with its revision (`nav_result.py:53-55`). But a **current** nav answer
carries no ref, and the envelopes are not unified: `search_symbol` uses `list_result`/`subject_answer`
/`batch_result` while `find_callers`/`find_references` use `nav_result` (all in
`code_atlas/tools/nav_result.py:284-396`), so the ref has to be added in one shared place to reach
every tool.

## Goal

Name the ref every nav answer was computed against, on every nav result, current or behind, so a
worktree/branch mismatch is visible rather than silent.

## Scope / Deliverables

1. **An `answered_about_ref` field** (the index's `head_ref`/`last_ref`, from `compute_staleness`
   `staleness.py:78-102`) attached in the shared envelope builders (`nav_result.py`), so it appears on
   `search_symbol`, `read_symbol`, `find_callers`, `find_references`, and the other nav tools — not
   just status/build.
2. **Consistent with 077's vocabulary** — same ref names, no new field where `serve_behind` already
   states the revision; this fills the *current*-answer gap, it does not duplicate the behind label.

## Constraints

- 071/077: reuse the existing provenance plumbing; do not open a second revision source.
- 061 / R4.2: the field is deterministic for a given index state; identical state → identical value.
- It names the ref the index holds — it does not attempt to read the caller's working tree (the server
  cannot see it; naming its own ref is what lets the caller detect the mismatch).

## Acceptance criteria

- **AC1** `find_callers`, `find_references`, `search_symbol` and `read_symbol` results each carry
  `answered_about_ref` naming the index's ref, on both a current and a behind answer.
- **AC2** The field is single-sourced in the shared envelope — a test asserts one attach site covers
  every nav tool, so a new nav tool inherits it (R6.7-style anti-drift).
- **AC3** It agrees with `get_index_status`'s `head_ref`/`last_ref` for the same index state.
- **AC4** No duplication of the `serve_behind` revision label on a behind read.

## Out of scope

- Detecting the caller's own checkout ref — out of a static server's reach; this ticket makes the
  mismatch *detectable* by naming the index's ref, not automatic.
- Any change to `get_index_status`/`build_or_update_index`, which already carry the refs (077).

## References
`code_atlas/tools/nav_result.py:53-55`, `:284-396`, `code_atlas/staleness.py:78-102`,
[071](071_answers-do-not-name-their-tree.md),
[077](077_index-cannot-name-the-revision-it-describes.md), ENGINEERING_RULES R4.2, R6.7.
