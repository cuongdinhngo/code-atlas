---
id: 317
slug: nav-results-do-not-name-the-ref-they-answered-about
title: "Only get_index_status and behind-labelled reads name the ref they answered about, so a find_callers on a worktree can silently describe main and the caller never knows"
phase: 1.5b
milestone: Agent-trust
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 317 — answered_about_ref on nav results (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 071, 077 (done)
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/317-answered-about-ref`
- **work_doc_mode:** embed

## Session status
- **Current phase:** finalise

## Phase 0
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`
| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Where to attach | Single `attach_answered_about_ref` in shared envelope builders | ticket Scope §1; R6.7 |
| 2 | Which ref value | Reuse 077 `last_ref_for_payload` via `answered_about_ref_for` | staleness.py; Constraints 071/077 |
| 3 | read_symbol (own builders) | Stamp via shared helper; wrappers + `_stamp` on helper returns | nav_result attach site; AC2 |
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=3 R=2 G=1 AC=4`
`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ · R6.7 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

| ID | Source | Interpretation | Status |
|----|--------|----------------|--------|
| C1 | 071/077 reuse | last_ref_for_payload only | ✅ |
| C2 | 061 add field | field present; null when unknown | ✅ |
| C3 | R4.2 | identical index → identical ref | ✅ |
| R1 | shared envelopes | empty_nav/nav_result/list_result/batch_* | ✅ |
| R2 | four named tools + inherit | AC1 + AC2 | ✅ |
| G1 | name the index ref | AC1 | ✅ |
| AC1-AC4 | proving tests | ✅ | ✅ |

## AC validation
| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1 | Y | four tools assert field == last_ref |
| AC2 | Y | single ANSWERED_ABOUT_REF_FIELD] writer |
| AC3 | Y | equals get_index_status last_ref |
| AC4 | Y | no twin behind*ref key |

## Phase 2 — Design
**Approach:** `attach_answered_about_ref` + `answered_about_ref_for` in `nav_result.py`; thread `about_ref` from open store in find_callers/find_references/search_symbol; read_symbol stamps via shared helper.
**Rejected:** (a) per-tool field assign — fails AC2/R6.7; (b) reading caller worktree ref — out of scope.
`HANDLES: 0 recalled | 0 traced | 0 does not apply | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**APPROVED CHANGE LIST:**
1. `code_atlas/tools/nav_result.py` — attach site + answered_about_ref_for; kwargs on envelopes
2. nav tools (`find_callers`/`find_references`/`search_symbol`/`read_symbol`/`find_implementations`/`find_view_data`/`impact`/`include_graph`/`subtree_dependencies`/`find_orphans`/`reachable_from`/`reach_shared`/`file_outline`) — thread about_ref
3. `tests/test_answered_about_ref.py` — proving AC1–AC4
4. frozen-key / weight tests (`test_nav_tools`, `test_answer_pagination`, `test_try_instead_*`, `test_index_root`)
5. working doc / BACKLOG / TOKEN_LEDGER
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_answered_about_ref.py -q`
**TREE_PATHS:** `code_atlas/tools/nav_result.py code_atlas/tools/find_callers.py code_atlas/tools/find_references.py code_atlas/tools/search_symbol.py code_atlas/tools/read_symbol.py code_atlas/tools/find_implementations.py code_atlas/tools/find_view_data.py code_atlas/tools/impact.py code_atlas/tools/include_graph.py code_atlas/tools/subtree_dependencies.py code_atlas/tools/find_orphans.py code_atlas/tools/reachable_from.py code_atlas/tools/reach_shared.py code_atlas/tools/file_outline.py tests/test_answered_about_ref.py tests/test_nav_tools.py tests/test_answer_pagination.py tests/test_try_instead_is_a_callable_tool_name.py tests/test_index_root.py tests/test_batched_subject_sweep.py tests/test_file_outline_pagination.py tests/test_untracked_files_are_invisible.py tests/test_payload_weight.py docs/tasks/317_nav-results-do-not-name-the-ref-they-answered-about.md docs/BACKLOG.md docs/TOKEN_LEDGER.md`
**Gate 2 status:** cleared (autorun)

## Phase 3 — Execute
Implemented. Proving green.
`PROVING TEST:` `.venv/bin/python -m pytest tests/test_answered_about_ref.py -q` → 6 passed.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 NOT CLEAN (read_symbol typo + other nav null); round2 NOT CLEAN (reach refuse/no_roots); round3 CLEAN (agent 35809031). Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
