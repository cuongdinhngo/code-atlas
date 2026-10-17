---
id: 389
slug: worktree-overlay
title: 'An agent in a worktree gets main''s spans and main''s staleness, and the per-worktree index is too expensive to be the route'
phase: 2
milestone: Trust
status: todo
depends_on: [366, 365, 268]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17, answered by 0.3.0).
366 made a worktree mismatch visible (`ref_mismatch`). The field still loses the answer itself.
5 PRs worked from a `.worktrees/` checkout, against a server rooted at main:

- F1 (2 PRs): `search_symbol` and `read_symbol` gave line numbers from main (a method at 892,
  where the worktree has it at 981). The agent re-read the worktree file with Grep.
- F2 (2 PRs): main was switched to another branch partway through the session. The answers
  followed main, and the agent saw only a metadata change, or nothing at all.
- F3 (1 PR): main had uncommitted changes, so the index was `behind`, and the worktree's queries
  were refused even though the worktree itself was clean (see 388 F2).

366's route is a per-worktree index (`CA_DB_PATH`). On the anchor repo that is a full build, about
550 s and 1.1 GB per worktree. Agents run 3–5 worktrees in parallel, so nobody takes that route.

## Scope

1. Measure whether Claude Code reports MCP `roots` to the server. If it does not, `ref_mismatch`
   never fires there. Record the result in the ticket, and record the client's `ref_check`.
2. **Worktree overlay.** When the caller's root is a worktree of the indexed repo, the files that
   differ between the built commit and the worktree (by `git diff --name-only`, plus untracked
   files) are parsed unstored, as 365's `parsed_unstored` already does. `read_symbol`,
   `file_outline` and `search_symbol` answer with the worktree's bodies and spans, labelled
   `overlay: worktree`. The store is untouched (R1.4).
3. Inbound tools (`find_callers`, `find_references`) answer from the built graph, plus the
   overlay's outbound edges at `HEURISTIC`. They are labelled, never `ok`.
4. If roots are not available, an opt-in `CA_CALLER_ROOT` (or a tool argument) names the
   worktree.

## Acceptance criteria

- **AC1:** Index built on main at A, worktree at B with a method moved 90 lines down:
  `read_symbol` from the worktree returns B's span and body, labelled `overlay: worktree`.
- **AC2:** A new file in the worktree is found by `search_symbol` without a build.
- **AC3:** Main switched to another branch after the build: the worktree's answers do not change
  (the overlay is keyed on the worktree, not on main's HEAD).
- **AC4:** No roots and no `CA_CALLER_ROOT`: answers are byte-identical to today.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 389 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/389-worktree-overlay`, **stacked on `feat/388-behind-refuses`** (both rewrite the inbound tools'
  freshness preamble; 384's precedent, "stacked on #67"). Contract `.mango/run-contract-389.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run (written after the draft began — DISCLOSURE).

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 22 unresolved surfaced | 4 want-decision asked | 18 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `ref_mismatch` / `ref_check` (`code_atlas/ref_check.py`), `parsed_unstored` (`read_symbol.py:338`),
`CA_DB_PATH`, `read_symbol`, `file_outline`, `search_symbol`, `find_callers`, `find_references`, R1.4, tasks 365 /
366 / 268 resolve. `CA_CALLER_ROOT` and the overlay are to-be-created. Ambiguous: "the anchor index".

**Recall.** 366-C1 (area: FastMCP middleware never sees `roots/list_changed`) — roots are asked per call, kept.
`widen-every-query-that-shares-the-page` (362-C1, class index) — the overlay swaps page rows, so every figure
computed over the built rows is a sibling query; answered in HANDLES.

**Scope 1, measured.** In this Claude Code session the server answered `get_index_status(detail_level="minimal")`
with no `ref_check` field (`server_version 0.3.0`, 2026-10-17): `attach_ref_check` writes that field only when the
roots read failed or was never declared (`ref_check.py:178-181`), so Claude Code declares `roots` and listed one —
the index root, this session's cwd. `ref_mismatch` and the overlay therefore fire for an agent whose session starts
in a worktree, not for one that starts in main and `cd`s into it.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 45,436 tokens) raised ten; H13–H18 and W3–W4 came
from it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the caller's worktree | how | the first client root that checks out this repository (same git common dir, another top level) — 366 X2's rule, now one `other_checkout` both callers share (R1.8, `ref_check.py`) |
| H2 | which files overlay | how | `git diff --name-only <built commit>` in the worktree plus untracked (`--exclude-standard`), through `indexable` — the index's own ignore rules (`indexer.py:921`) |
| H3 | parse | how | `parse_file` with `config.root` replaced; adapters run with `cwd` = root (`indexer.py:1104`); nothing is written (R1.4) |
| H4 | tools | how | read, outline, search (Scope 2) and the inbound pair (Scope 3); every other tool keeps `ref_mismatch` (366) |
| H5 | inbound matching | how | a worktree edge counts when `target_raw` equals the stored qname; added at `HEURISTIC` (Scope 3); built rows from changed files dropped |
| H6 | depth > 1 | how | only the first hop is the worktree's; deeper hops are the built graph's |
| H7 | `CA_CALLER_ROOT` | how | a knob (`KNOB_KEYS`), query-only (out of the config identity, like `page_limit`); read only when the client reports no roots — Scope 4 "If roots are not available"; a server-wide variable cannot name 3–5 parallel worktrees, so it never overrides a client that names its own |
| H8 | a tool argument instead | how | rejected: five signatures widen for what roots and one knob already carry (R7.1) |
| H9 | `ref_mismatch` on an overlay answer | how | never: the caller's own checkout answered (`attach_ref_check` skips `overlay: worktree`) |
| H10 | main's drift under an overlay | how | the guard trusts the built rows and never repairs from main (AC3; F3) |
| H11 | search merge | how | rows from changed files swap for the worktree's symbols, direct matches first (180's band), `total_count` moved by the page's swap |
| H12 | built partitions | how | `production_count` / `test_count` / `test_role_source` / `tier_census` are dropped when rows swap (R5.5) |
| H13 | a root that is not this repo, or main itself (exposure #1) | how | no overlay, no git beyond 366's: AC4 holds (`other_checkout` returns None) |
| H14 | several roots (exposure #2) | how | the first root in the repo decides (366 X2) |
| H15 | main behind or dirty (exposure #4) | how | the overlay is keyed on the built commit; main's state never enters (H10) |
| H16 | deleted / renamed files (exposure #6) | how | `git diff` lists a deletion, so the file overlays to no symbols: search drops its rows, read answers `no_such_symbol`; a rename is a deletion plus an addition |
| H17 | an unreadable worktree file (exposure #5) | how | never read as absence: `index_stale`, labelled (R5.6) |
| H18 | reason vocabulary (exposure #8) | how | `worktree_overlay` is a tool payload reason, not the adapter contract (R3.1) |
| W1 | Scope 1 + AC-field (anchor) | want | **asked, settled by the maintainer (2026-10-17):** defer to the maintainer as escalated exclusion E1 |
| W2 | per-call parse cap (exposure #5) | want | **ASSUMED (awaiting ratification):** 25 files; past it the answer carries `overlay_truncated` and an absence becomes `index_stale` |
| W3 | exact-qname matching only (exposure #10) | want | **ASSUMED (awaiting ratification):** precision over recall; calls on untyped receivers are counted in `overlay_unlinked_same_name`, never linked |
| W4 | search `total_count` under an overlay | want | **ASSUMED (awaiting ratification):** moved by what the page swapped — exact on a single page, a floor past it |

## Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=5`
`CLARIFICATION: 22 raised | 22 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/18 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

The branch point is 388's tip; its gate (`scripts/gate.sh`, `pytest -q` among 21 checks) is quoted in 388's PR.
`main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 worktree spans | read/search answer main's rows; `ref_mismatch` relabels (`ref_check.py:183`) | worktree's spans and bodies, `overlay: worktree` |
| F2 main switched | answers follow main's repair of its own drift (`freshness.py:117`) | keyed on the worktree and the built commit |
| F3 main dirty | refusals (fixed in 388) and repairs from main | the overlay ignores main |
| Scope 4 | no knob | `CA_CALLER_ROOT` |

Blast radius: `ref_check.find_mismatch` (366's two consumers), `Config` (a defaulted field: every `replace` and hand
built Config unaffected), the four read/search/outline/inbound tools, the guard. One repo.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the per-worktree index is too expensive to be the route" | a worktree is answered with no build | ⏳ |
| C1 | Scope 2 | "The store is untouched (R1.4)" | the overlay writes nothing | ⏳ |
| R1 | Scope 1 | "Measure whether Claude Code reports MCP roots" | measured above | ⏳ |
| R2 | Scope 2 | "Worktree overlay … `read_symbol`, `file_outline` and `search_symbol` …" | H1–H3, H11 | ⏳ |
| R3 | Scope 3 | "Inbound tools … plus the overlay's outbound edges at HEURISTIC … never ok" | H5, H6, H12 | ⏳ |
| R4 | Scope 4 | "an opt-in `CA_CALLER_ROOT`" | H7 | ⏳ |
| AC1 | AC | moved method: B's span and body, labelled | | ⏳ |
| AC2 | AC | a new worktree file found by `search_symbol` | | ⏳ |
| AC3 | AC | main switched: answers unchanged | | ⏳ |
| AC4 | AC | no roots, no knob: byte-identical | | ⏳ |
| AC5 | AC-field | anchor replay | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `line_start` = built + 90, body from B, `overlay == "worktree"` | |
| AC2 | yes — exact `results` qname list | also `file_outline` |
| AC3 | yes — the payload before == after main's switch and edit | |
| AC4 | yes — payload with no knob == payload with the knob at the index root; no overlay key | three tools |
| AC5 | no — needs the anchor | E1 |

### Rule sections

`RULE SECTIONS: 10 applicable — 10 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the overlay reads paths and adapter rows, no language name · §R1.4 (change-type) ✅ parse_file only, nothing written · §R1.8 (change-type) ✅ other_checkout serves the mismatch and the overlay; overlay_inbound serves both inbound tools · §R3.1 (change-type) N/A because a payload reason is not node/edge vocabulary · §R5.3 (change-type) ✅ CA_CALLER_ROOT parses through the path resolver, loud on a bad value · §R5.5 (change-type) ✅ built partitions dropped when rows swap · §R5.6 (change-type) ✅ unread is index_stale, never absence; untyped calls counted · §R6.5 (change-type) ✅ the proving test is seen red before the overlay · §R7.6 (change-type) ✅ the runbook's share-main row rewritten, PLAN's 366 line replaced · §R7.7 (change-type) ✅ formatter hunks outside the edit reverted`

## Phase 2 — design

### Approach

1. `ref_check.other_checkout` — 366's scan, shared: the first root that is another checkout of this repo, with its
   HEAD. `find_mismatch` and the new `caller_checkout` (roots, else `CA_CALLER_ROOT`) both call it (R1.8).
2. `code_atlas/overlay.py` — `active_overlay(config, store)`: the changed set against the built commit, an `Overlay`
   that parses a file once per call through `parse_file` on a root-replaced config, finds a qname, and labels an
   answer (`overlay`, `overlay_root`, `overlay_truncated`, `answered_about_ref: null`). `overlay_inbound` swaps
   this page's rows from changed files for the worktree's edges onto the subject at `HEURISTIC`, counts the
   untyped same-name calls, drops the built partitions, and sets `worktree_overlay`.
3. `FreshnessGuard(trust_built=…)`: under an overlay, never repair from the index checkout.
4. `read_symbol`, `file_outline`, `search_symbol`: the overlay path before the built path; `find_callers`,
   `find_references`: `overlay_inbound` instead of 388's behind label.
5. `attach_ref_check` skips an overlay answer; `Config.caller_root` / `CA_CALLER_ROOT` (query-only knob).
6. Docs: TOOLS.md, CONVENTION.md, PLAN §19's 366 line, the parallel-agents runbook, tool docstrings, CHANGELOG.

### Rejected alternatives

- **Build a per-worktree index on demand** — 366's route, ~550 s and 1.1 GB per worktree on the anchor (ticket).
- **Write the worktree's rows into a side table of the shared store** — the ticket rules the store untouched
  (R1.4), and two worktrees would race one writer (R4.3).
- **Link worktree calls by bare member name** — guesses a receiver the adapter could not type; counted instead (W3).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| adapters read paths relative to `config.root` | verified | `SubprocessAdapter` starts with `cwd=config.root` (`indexer.py:1104`, `adapter.py:165`) |
| a worktree shares the object store, so `git diff <built>` answers inside it | verified | AC1/AC3 tests run `git worktree add` and diff against the main-built commit |
| Claude Code reports roots | verified | Scope 1 measurement above |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `other_checkout` (shared), `caller_checkout`; overlay answers skip the relabel | `code_atlas/ref_check.py` | 366's `find_mismatch` callers, `test_ref_mismatch` | R1, R4, H9 | 1/1 |
| 2 | `caller_root` knob | `code_atlas/config.py` | `KNOB_KEYS` count- and order-pins (`test_config.py`, P5); config identity (query-only, unmoved) | R4 | 1/1 |
| 3 | the overlay module (new) | `code_atlas/overlay.py` | core-module count pins (`test_core_is_language_agnostic.py:54`, `test_sql_confinement.py:39`, P5) | R2, R3, C1 | 1/1 |
| 4 | `trust_built`; `read_subject` passes it | `code_atlas/tools/freshness.py` | every guard consumer (default off) | R2, AC3 | 1/1 |
| 5 | overlay paths | `code_atlas/tools/read_symbol.py`, `file_outline.py`, `search_symbol.py`, `find_callers.py`, `find_references.py` | the evidence-kinds guard (`test_honesty_predicate_derived_mapping.py:217`: `find_references` must not name `UNLINKED_EVIDENCE_KINDS`, so `kinds=None` resolves inside the overlay) | R2, R3 | 5/5 |
| 6 | reason `worktree_overlay` | `code_atlas/tools/nav_result.py` | `NAV_REASONS` pin (P5) | R3 | 1/1 |
| 7 | proving test | `tests/test_worktree_overlay.py` (new) | — | AC1–AC4 | 1/1 |
| 8 | proof collateral | `tests/test_config.py`, `test_core_is_language_agnostic.py`, `test_sql_confinement.py`, `test_nav_reason_codes.py`, `test_ref_mismatch.py` | assert the overlay where 366 asserted `ref_mismatch` for the five overlaid tools; `impact` keeps it | R2–R4 | 5/5 |
| 9 | docs | `docs/TOOLS.md`, `docs/PLAN.md`, `docs/runbooks/parallel-agents.md`, `CHANGELOG.md` | doc budgets | G1 | 4/4 |
| 10 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

Trace — the full suite on the drafted change (scratch worktree): `19 failed, 4564 passed, 4 skipped, 1 xfailed in
752.27s`. 11 are pins or 366's tests (rows 2, 3, 5, 6, 8); 2 doc budgets (row 9); 6 status-payload weight tests
pass on re-run (`111 passed` — they weigh `server_build`'s `+dirty`, which moved while the run's files were edited);
1 is the `PYTHONPATH` artifact seen in 388 (`test_setup_script`, green without it).

| Handle | Answer |
|---|---|
| `widen-every-query-that-shares-the-page` | traced: `grep -n '"production_count"\|"test_count"\|"tier_census"\|"test_role_source"' code_atlas/tools/find_callers.py code_atlas/tools/find_references.py` → the four partitions the inbound pair compute over the built rows; `overlay_inbound` drops all four when it swaps a row (`_BUILT_PARTITIONS`), and `total_count` moves by the swap; asserted in `test_scope3_…` |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — git worktree + adapter + tool | a real `git worktree`, a PHP build on main | authored | ✅ |
| AC2 | integration | a new file in the worktree; search and outline | authored | ✅ |
| AC3 | integration | main checks out another branch and edits the subject's file | authored | ✅ |
| AC4 | integration | no knob vs the knob at the index root, three tools | authored | ✅ |
| AC5 | runtime — the anchor's agents | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: medium — 5 field PRs, unreplayed · why: the anchor index
is not on this machine · the class's sighting after 388 (`seen: 378, 384, 388, 389`), escalated and answered by the
maintainer on 2026-10-17 ("defer to me") · follow-up: on the anchor, from a `.worktrees/` checkout, replay F1
(`read_symbol` / `search_symbol` on a moved method), F2 (switch main mid-session, re-ask) and F3 (main dirty), and
record the Grep fallbacks before/after · `expiry: when the anchor index is available to a maintainer run` ·
`seen: 378, 384, 388, 389`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_worktree_overlay.py` — red on 388's tip (`5 failed, 1 passed`; AC4 is the
non-regression guard), green after.

### Rollback

`git revert` the branch's commits; nothing is stored, so no index changes shape. Merge after #72 (stacked).
