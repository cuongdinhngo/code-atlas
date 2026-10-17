---
id: 388
slug: behind-refuses
title: 'With no build running, a behind index still refuses find_callers and find_references, and it is the most common reason an agent falls back to Grep'
phase: 2
milestone: Freshness
status: todo
depends_on: [257, 267, 274, 365]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17, 45 scored PRs, all
answered by 0.3.0, so 365 and 366 had shipped). In 6 PRs the agent fell back to Grep because the
index was `behind`, and at those moments no build held `write.lock`, so 365's unasked serve did
not apply.

- F1 (4 PRs): `find_callers` / `find_references` refused while the index was `behind`. The agent
  did not know about `serve_behind`, or read the refusal as final, and used Grep for the callers.
- F2 (1 PR): the index was `behind` because the main checkout had uncommitted deletions under a
  directory the change never touched. Nothing named those paths, so the agent could not tell that
  its own subject was unaffected.
- F3 (1 PR): `search_symbol` answered `index_stale` for one name inside a multi-query sweep. A
  name search has no inbound edge to vouch for.
- F4 (1 PR): a field had just been deleted in the working tree, so proving that nobody still reads
  it needed the *built* graph. `find_references` refused instead.

257 made `serve_behind` opt-in, and 365 narrowed that to "a build is writing". These six PRs are
the evidence that the opt-in itself is the cost: an agent rarely passes the flag.

## Scope

1. Measure first. On the anchor index, count over a window how often a behind answer refuses
   with no lock held, and check whether the refused subject's file is in `changed_indexed_files`.
2. Unchanged subject: serve by default, labelled `index_behind` with the built revision, never
   `ok`. Re-decide 257's default in PLAN §19 using this evidence.
3. Changed subject: keep the refusal, but name the route: the `serve_behind` call, ready to copy.
4. `search_symbol` never refuses on staleness. A row from a changed file carries `source_stale`.
5. `get_index_status` lists the uncommitted and changed paths that made the index `behind`
   (`behind_because`, capped), so "my subject is unaffected" can be read without another call (F2).
6. A symbol removed since the build is answered from the built graph as
   `index_behind_subject_removed`, so "who still uses what I deleted" works (F4).

## Acceptance criteria

- **AC1:** Index built at A, HEAD at B, no lock held, and the subject's file unchanged between A
  and B: `find_callers` answers `index_behind` with rows and the built revision.
- **AC2:** The same with the subject's file changed: a refusal whose `try_instead_hint` names the
  exact `serve_behind` call.
- **AC3:** `search_symbol` on a behind index never answers `index_stale`.
- **AC4:** A method deleted between A and B: `find_references` lists its built-graph references,
  labelled `index_behind_subject_removed`.
- **AC5:** On a current index, every answer is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 388 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/388-behind-refuses` off `main`. Contract `.mango/run-contract-388.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 0 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 20 unresolved surfaced | 5 want-decision asked | 15 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `find_callers`, `find_references`, `search_symbol`, `get_index_status`, `serve_behind`, `write.lock`
(`code_atlas/index_lock.py`), `changed_indexed_files` (`get_index_status.py:100`), `index_behind`, `index_stale`,
`try_instead_hint`, `source_stale`, PLAN §19 (257 entry, `docs/PLAN.md:855`), and tasks 257 / 267 / 274 / 365 resolve.
`behind_because` and `index_behind_subject_removed` are to-be-created. Ambiguous: "the anchor index" — not on this machine.

**Recall.** 365-C1 (area: the build lock vs a transaction probe) — the held-lock path (365) stays as it is.

**Reproduced on a fixture before deciding** (scratch script, `main` at daa6baa0): an unchanged subject on a behind index
answered `ok` unlabelled; the refusal arises only when the changed subject's re-read fails, with a generic hint; a
deleted method's references answered `ok`; `get_index_status` listed callers/references under `behind_refuses` though
they served — a status that tells an agent to Grep.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 46,743 tokens) raised nine; H13–H18 and W3 came from it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | unchanged subject on a behind index | how | `index_behind` + `last_commit` + per-row `index_revision` by default, both inbound tools (ticket Scope 2). **Tripwire:** reverses 257's opt-in; the ticket orders it and PLAN §19 records it |
| H2 | `serve_behind` | how | stays; it now governs only a changed subject that could not be re-read (Scope 3, `freshness.py:222`) |
| H3 | a changed subject whose re-read succeeds | how | keeps `ok` + `subject_refreshed_only` (257's rule, `freshness.py:268`); only an unrepairable one refuses (Scope 3) |
| H4 | the refusal's route | how | `try_instead_hint` ends with the call: tool, the caller's non-default args (`claim.call_args`, `claim.py:120`), `serve_behind=true`, JSON values; `serve_behind` is a param, so no `try_instead` (R5.4) |
| H5 | an unnameable miss amid several drifted files | how | answered, not refused: no `serve_behind` call could serve it (`unrepaired_subject_served` needs a nameable file), so a hint naming one would fail R5.4(c); the miss carries `other_indexed_files_drifted` |
| H6 | `search_symbol` hit page with drift past the budget | how | the normal reason ladder; each row whose file drifted carries `source_stale: true` (Scope 4) |
| H7 | `search_symbol` zero-hit miss nothing vouched for | how | `index_behind`, empty, `other_indexed_files_drifted`, keeps `try_instead=file_outline` (073's route) |
| H8 | `index_stale` anywhere in `search_symbol` | how | none (AC3), the separator retry included |
| H9 | `behind_because` shape | how | `[{path, change: deleted · uncommitted · committed}]`, sorted, at `standard`+ beside `changed_indexed_files` (274 keeps git off `minimal`) |
| H10 | `behind_serves` / `behind_refuses` | how | `behind_serves` lists all four; `behind_refuses` goes (nothing refuses by family); `serve_behind_opt_in` stays except while held (365) |
| H11 | detecting "removed" | how | an exact `nodes_by_qualified_name` row at entry that the re-read file no longer declares, or whose file is gone — a typo never had a row (exposure #6) |
| H12 | removed applies to | how | both inbound tools: one shared preamble (R1.8); F4 is a find_references question and "who calls what I deleted" the same one |
| H13 | caller rows from drifted files (exposure #2) | how | answer-level label only: Scope 2 labels the answer with the built revision; per-row `index_revision` already says which graph each row came from |
| H14 | 365's held path (exposure #3) | how | unchanged: under the lock a changed subject is served unasked; the opt-in field is omitted there |
| H15 | contract version | how | none: reason codes are a tool payload, not the adapter contract (R3.1) |
| W1 | Scope 1 + AC-field (anchor replay) | want | **asked, settled by the maintainer (2026-10-17):** defer to the maintainer as an escalated exclusion (third sighting of the class, 378 · 384) with the replay command |
| W2 | ship on fixtures while the PLAN §19 re-decision rests on the ticket's six-PR evidence (exposure #1) | want | **asked, settled with W1:** yes — the ticket states the evidence; the replay confirms or reverts |
| W3 | `index_stale_subjects` keeps its name but now keys on unvouched subjects (exposure #7) | want | **ASSUMED (awaiting ratification):** keep the field, widen its predicate; a rename breaks consumers for no reader gain |
| W4 | `behind_because` cap (exposure #4, #5) | want | **ASSUMED (awaiting ratification):** 20 paths by count, `behind_because_truncated: true` past it, total in `changed_indexed_files` |
| W5 | per-call staleness cost (exposure #8) | want | **ASSUMED (awaiting ratification):** acceptable; measured below, no cache |

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 0 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=6 G=1 AC=6`
`CLARIFICATION: 20 raised | 20 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

The 20 are Phase 0's H1–H15 and W1–W5: W1–W2 answered by the maintainer, W3–W5 handed back by the handover and carried
as `ASSUMED`. `SCOPE: L` — six source modules, a shared preamble, a new reason code and a status field.

### BASELINE

`.venv/bin/pytest -q -p no:cacheprovider` on the untouched checkout: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`.
Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 unchanged subject served | `ok` unlabelled (`find_callers.py:655` labels only under `serve_behind`); status says `behind_refuses` (`get_index_status.py:313`) | `index_behind` + revision by default; status lists all four as serving |
| F1 changed subject routed | refusal hint `pass serve_behind=true …` (`nav_result.py:277`) | the exact call, ready to copy |
| F2 changed paths named | a count only (`get_index_status.py:322`) | `behind_because` paths + how each changed |
| F3 search never refuses | `index_stale` on hits past the budget and on an unvouched miss (`search_symbol.py:371`) | `source_stale` rows; `index_behind` miss |
| F4 removed subject | after the re-read, `ok` with the built edges (reproduced) | `index_behind_subject_removed` |

Blast radius: the two inbound tools' freshness preamble (duplicated today, `find_callers.py:266-298`,
`find_references.py:351-380`), `search_symbol._search_one` / `_single_payload` / `_batch_answer`, the status routes and
summary, the reason vocabulary (`NAV_REASONS`, count-pinned by `tests/test_nav_reason_codes.py:173`), the agent brief
line (`scripts/gen_skill.py:357`). One repo.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the opt-in itself is the cost" | a behind index answers without an opt-in | ⏳ |
| C1 | Scope 2 | "never `ok`" | a served behind answer never reads `ok` | ⏳ |
| R1 | Scope 1 | "Measure first. On the anchor index" | W1: maintainer replay (exclusion E1) | ⏳ |
| R2 | Scope 2 | "Unchanged subject: serve by default … Re-decide 257's default in PLAN §19" | H1, H13; PLAN §19 entry rewritten | ⏳ |
| R3 | Scope 3 | "Changed subject: keep the refusal, but name the route" | H2–H5 | ⏳ |
| R4 | Scope 4 | "`search_symbol` never refuses on staleness … `source_stale`" | H6–H8, W3 | ⏳ |
| R5 | Scope 5 | "`get_index_status` lists … (`behind_because`, capped)" | H9, H10, W4 | ⏳ |
| R6 | Scope 6 | "answered from the built graph as `index_behind_subject_removed`" | H11, H12 | ⏳ |
| AC1 | AC | `find_callers` answers `index_behind` with rows and the built revision | | ⏳ |
| AC2 | AC | a refusal whose `try_instead_hint` names the exact `serve_behind` call | | ⏳ |
| AC3 | AC | `search_symbol` never answers `index_stale` | | ⏳ |
| AC4 | AC | a deleted method's built-graph references, `index_behind_subject_removed` | | ⏳ |
| AC5 | AC | on a current index every answer is byte-identical | | ⏳ |
| AC6 | AC-field | the F-cases replayed on the anchor index answer without Grep | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `reason == index_behind`, `last_commit == A`, each row's `index_revision == A[:7]` | both inbound tools |
| AC2 | yes — the hint ends with `find_callers(qname=…, …, serve_behind=true)`, and that call answers | |
| AC3 | yes — no `reason == index_stale` on a single call, a miss or a sweep over two drifted files | |
| AC4 | yes — the deleting method's caller listed, reason `index_behind_subject_removed` | method deleted, and file deleted |
| AC5 | yes — no `last_commit` / `index_revision` / `source_stale` / `behind_because` anywhere in four answers and no behind field on status, on a current index | non-regression: green before and after |
| AC6 | no — needs the anchor index | manual-check exclusion E1 (design) |

### Rule sections

`RULE SECTIONS: 12 applicable — 12 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no language branch: removal and drift are read from rows and file hashes · §R1.8 (change-type) ✅ the two inbound tools' duplicated freshness preamble becomes one read_subject · §R3.1 (change-type) N/A because the reason codes are a tool payload, not node/edge vocabulary · §R4.2 (change-type) ✅ behind_because is sorted by path, capped by count · §R5.4 (change-type) ✅ the serve_behind call is a hint, never try_instead; an unnameable miss gets no hint a serve_behind call could not answer · §R5.6 (change-type) ✅ removed vs typo, vouched vs source_stale rows, each driven by a test · §R6.5 (change-type) ✅ the proving test is seen red on main · §R6.9 (change-type) ✅ tests read the tool payloads, the consumer · §R7.2 (change-type) ✅ ledger rows in this file and TOKEN_LEDGER · §R7.5 (change-type) ✅ every added comment ≤ 3 lines · §R7.6 (change-type) ✅ the PLAN decision-log 257 entry is rewritten, not appended to; behind_refuses leaves every doc that named it · §R7.7 (change-type) ✅ ruff format hunks outside the edit reverted`

## Phase 2 — design

### Approach

1. `freshness.read_subject` — the one preamble both inbound tools call (R1.8): staleness, the drifted set when behind,
   the read-through repair, 365's held flip, and the verdict `refuse | unrepaired | removed`. Removed = an exact row
   at entry that the re-read file no longer declares, or whose file is gone. Refuse = a named subject whose changed
   file could not be re-read, without `serve_behind`; an unnameable miss is answered with its residue.
2. `freshness.label_behind` (was `label_serve_behind`) labels every behind answer, no opt-in: removed → `…_removed`,
   unrepaired → `…_changed`, repaired → untouched, `ok` → `index_behind`; a current index is never touched (AC5).
3. `nav_result`: reason `index_behind_subject_removed`; the refusal hint ends with `serve_behind_call(tool, call)`.
4. `search_symbol`: drift past the budget marks rows `source_stale` instead of `index_stale`; an unvouched empty miss
   is `index_behind` with `other_indexed_files_drifted`; a sweep's `retry_as` and envelope key on unvouched subjects.
5. `get_index_status`: `behind_serves` = all four, `behind_refuses` gone, `behind_because` (20, `{path, change}`,
   truncated flag) at `standard`+; the not-held summary says the built graph answers.
6. Docs: TOOLS.md, CONVENTION.md, the onboarding runbook, PLAN §19's 257 entry rewritten, the brief line
   (`gen_skill.py`, regenerated), CHANGELOG `Unreleased`.

### Rejected alternatives

- **Keep the opt-in, improve the refusal text only** — the ticket's evidence is that agents do not pass the flag;
  a better refusal is still a refusal (Scope 2).
- **Label every row from a drifted file in the inbound tools too** — the answer-level label plus per-row
  `index_revision` already names the graph each row came from (H13); a per-row hash check per caller is a cost the
  ticket does not ask for.
- **A new `index_unvouched` reason for the empty search miss** — `index_behind` already means "the built graph
  answered"; a second word for one state is vocabulary drift.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| after a successful re-read the built edges onto a removed subject remain | verified | reproduced: `find_references('\App\Drift::gone')` after deleting the method answered `\App\User::go` (scratch run, main daa6baa0) |
| a subject file deleted from disk makes `ensure` answer `stale` without a re-read | verified | `freshness.py:117` (`is_file()` check) |
| the extra git reads cost little | verified | `compute_staleness` 5.7 ms, `dirty_indexed_paths` 3.5 ms per call on this repo (718 files, 20-call mean) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `read_subject`, `label_behind`, `drifted`, unnameable residue | `code_atlas/tools/freshness.py` | both inbound tools, search, `test_actionable_stale_warnings` (the renamed labeller) | R2, R3, R6, C1 | 1/1 |
| 2 | removed reason; exact-call hint | `code_atlas/tools/nav_result.py` | `NAV_REASONS` count-pin (`test_nav_reason_codes.py:173`, P5); the hint text (`test_behind_status_routes`) | R3, R6 | 1/1 |
| 3 | shared preamble + label | `code_atlas/tools/find_callers.py`, `code_atlas/tools/find_references.py` | every behind-fixture inbound test; the no-git stamp guard that stubbed `find_references.compute_staleness` | R2, R3, R6 | 2/2 |
| 4 | `source_stale`, unvouched miss, sweep keys | `code_atlas/tools/search_symbol.py` | the search-staleness tests below | R4 | 1/1 |
| 5 | all-serve routes, `behind_because`, summary | `code_atlas/tools/get_index_status.py` | status/summary tests | R5 | 1/1 |
| 6 | proving test | `tests/test_behind_index_serves.py` (new) | — | AC1–AC5 | 1/1 |
| 7 | proof collateral: tests encoding the superseded opt-in / refusal | `tests/test_actionable_stale_warnings.py`, `test_batched_subject_sweep.py`, `test_behind_status_routes.py`, `test_ensure_miss_subject_not_count.py`, `test_freshness_cannot_find_what_is_not_indexed.py`, `test_index_status_summary.py`, `test_mixed_sweep_budget_envelope.py`, `test_nav_reason_codes.py`, `test_read_through_freshness.py`, `test_reads_during_a_refresh.py`, `test_separator_spelling_near_miss.py`, `test_serve_behind_labelled_reads.py`, `test_server_build_on_payloads.py` | each asserts the new contract, and the superseded form absent (P3) | R2–R6 | 13/13 |
| 8 | docs | `docs/TOOLS.md`, `docs/CONVENTION.md`, `docs/PLAN.md`, `docs/runbooks/onboarding-a-repo.md`, `scripts/gen_skill.py`, `contrib/agent-brief.md`, `CHANGELOG.md` | doc budgets, `test_skill_drift` | G1, R2 | 7/7 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

Trace — mechanical, not a name grep: the full suite on the drafted change (scratch worktree,
`PYTHONPATH=<worktree> pytest -q`) → `20 failed, 4553 passed, 4 skipped, 1 xfailed in 597.07s`. 17 encode the
superseded contract (row 7); 2 were doc budgets and 1 drift guard edited mid-run (row 8, green on re-run); 1
(`test_setup_script::test_a_pipless_interpreter_still_writes_the_config`) is an artifact of the `PYTHONPATH`
override — `5 passed` without it.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build + git + tool | a real PHP build, HEAD moved, both tools | authored | ✅ |
| AC2 | integration | a real build, the re-read forced to fail (`CA_PHP_CMD=false`), then the hint's call | authored | ✅ |
| AC3 | integration | two drifted files against the one-file budget: hit page, miss, sweep | authored | ✅ |
| AC4 | integration | a method deleted, and a file deleted | authored | ✅ |
| AC5 | integration | a current index, four answers and status | authored | ✅ |
| AC6 | runtime — the anchor's agent sessions | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC6 and Scope 1 · risk: medium — the default flip rests on the ticket's
six-PR evidence, unreplayed · why: the anchor index is not on this machine · third sighting of the class (`seen: 378,
384, 388`), so it was **escalated, not re-recorded**: the maintainer answered on 2026-10-17 "defer to me" · follow-up:
on the anchor, after the build, replay F1–F4's shapes (`find_callers` / `find_references` on an unchanged subject
with HEAD moved, a sweep with a drifted name, `get_index_status` with uncommitted deletions, `find_references` on a
deleted field) and record before/after Grep fallbacks here · `expiry: when the anchor index is available to a
maintainer run` · `seen: 378, 384, 388`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_behind_index_serves.py` — red on `main` (7 failed, AC5 green as a
non-regression guard), green after.

### Rollback

`git revert` the branch's commits; nothing persisted changes shape — no schema, contract or meta key. `SCOPE: L`
holds: six modules, as declared at analysis.
