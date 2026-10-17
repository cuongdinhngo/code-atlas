---
id: 392
slug: bare-table-name
title: 'find_references refuses a bare table name that check_column_defaults resolves'
phase: 2
milestone: Retrieval
status: done
depends_on: [320]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). F1 (1 PR):
`find_references RefType` (a bare table name) answered `name_not_qualified`, so the agent switched to
`git grep`. `check_column_defaults` already resolves a bare table name "to its one
schema-qualified table, or refuses with the candidates" (320). The same name in the same index
gets two different contracts, depending on the tool.

## Scope

1. `find_references` and `impact` resolve a bare name that matches exactly one `Table` or
   `Procedure`, and `find_callers` one `Procedure`, by the same rule as 320, and report `resolved_from: "bare"`.
2. More than one match: refuse with the candidates, as 320 does.

## Acceptance criteria

- **AC1:** A fixture with one `dbo.Items`: `find_references Items` answers as
  `find_references dbo.Items` does, plus `resolved_from`.
- **AC2:** `dbo.Items` and `audit.Items`: the refusal lists both.
- **AC3:** Qualified names are byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 392 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W4, runs E1, then merges after #79. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/392-bare-table-name`, **stacked on `feat/395-js-in-php-views`**. Contract `.mango/run-contract-392.txt`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 4 want-decision asked | 8 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `find_references`, `find_callers`, `impact`, 320's `_resolve_bare_table` and `classify_missing_subject`
resolve. "Procedure" names no contract kind: a SQL procedure is a `Function` (`adapters/sql/README.md`). Ambiguous:
"the anchor index".

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 53,329 tokens) raised ten. Its key finding set H3: a
unique bare name already re-points (`classify_missing_subject`), so F1 was a kind-blind count — a table and a column
of the same name.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | "Procedure" | how | kind-only: `Table` or `Function` (`find_callers`: `Function`) — never a language or `object_type` (R1.1) |
| H2 | where it runs | how | the exact miss the suffix classifier calls ambiguous, nowhere else — a hit pays nothing, an unambiguous miss is unchanged |
| H3 | what may share the name | how | only a table's own parts (`Column`, `ForeignKey`); a class or method namesake keeps today's answer (R5.6) |
| H4 | the refusal | how | when a `Table` is among the candidates, with each site, 320's shape (challenger M1 narrowed it) |
| H5 | a capped scan | how | falls through unchanged — a cap cannot prove nothing else answers to the name |
| H6 | `resolved_from` | how | on the new path only, beside `resolved_qname` (AC3) |
| H7 | one helper | how | `bare_subject` in `nav_result`, beside the classifier; 320 keeps its own — its tool takes tables only |
| H8 | `impact_modules` | how | in scope: it shares `impact`'s seed plan (R6.7) |
| W1 | AC-field (anchor) | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | `impact`'s `resolved_from` with several subjects | want | **ASSUMED (awaiting ratification):** one flag for the call |
| W3 | two schemas' routines (`dbo.P`, `audit.P`) | want | **ASSUMED (awaiting ratification):** stay `name_not_qualified` — only a table pair refuses with sites |
| W4 | the refusal's routing fields | want | **ASSUMED (awaiting ratification):** `candidate_count` / `try_instead` dropped, matching 320 |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

`TIER: full` despite `SCOPE: S`: three public tools' miss answers move.

### BASELINE

Stacked on 395. `main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 bare table | a table and a same-named column count two: `name_not_qualified` | the table, `resolved_from: "bare"` |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "two different contracts, depending on the tool" | one rule for the four tools | ⏳ |
| C1 | AC3 | "Qualified names are byte-identical" | H2 | ⏳ |
| R1 | Scope 1 | "resolve a bare name that matches exactly one" | H1–H3, H5–H8 | ⏳ |
| R2 | Scope 2 | "refuse with the candidates, as 320 does" | H4 | ⏳ |
| AC1 | AC | `find_references Items` as `dbo.Items`, plus `resolved_from` | | ⏳ |
| AC2 | AC | the refusal lists both | | ⏳ |
| AC3 | AC | qualified byte-identical | | ⏳ |
| AC4 | AC-field | anchor | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — equal rows, the flag | |
| AC2 | yes — both qnames | |
| AC3 | yes — the 1,867 resolution-suite tests unchanged | |
| AC4 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ kinds only, no language · §R1.8 (change-type) ✅ one helper for three tools · §R5.6 (change-type) ✅ a namesake of another kind keeps the refusal · §R6.5 (change-type) ✅ seen red on 395's tip · §R6.7 (change-type) ✅ impact_modules shares the seed plan`

## Phase 2 — design

### Approach

1. `contract.BARE_SUBJECT_KINDS` / `TABLE_PART_KINDS` — named subsets, no vocabulary change.
2. `nav_result.bare_subject` (H1–H5) and `shape_bare_ambiguous`.
3. `find_references` / `find_callers`: the ambiguous-miss path tries it; `impact`'s `resolve_seeds` does too, a
   refused seed joining the ambiguous-site disclosure.
4. Docs: TOOLS.md inbound row, CHANGELOG `Unreleased`.

### Rejected alternatives

- **Re-point on any kind count of one** — a PHP class namesake would be answered as a table (R5.6).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| F1 was a table and a same-named column | novel-untested | the exposure-checker's reading; E1 confirms |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | kind subsets | `code_atlas/contract.py` | none | R1 | 1/1 |
| 2 | the helper | `code_atlas/tools/nav_result.py` | miss path only | R1, R2 | 1/1 |
| 3 | the tools | `find_references.py`, `find_callers.py`, `impact.py` | ambiguous misses; `impact_modules` via the plan | R1, R2, C1 | 3/3 |
| 4 | proving test | `tests/test_bare_table_name.py` (new) | — | AC1–AC3 | 1/1 |
| 5 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL adapter + build + tools | real build | authored | ✅ |
| AC2 | integration | two schemas | authored | ✅ |
| AC3 | integration | the resolution suites | existing | ✅ |
| AC4 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, `find_references RefType` before/after,
and what else ends with `RefType` · `expiry: when the anchor index is available to a maintainer run` ·
`seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 392`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_bare_table_name.py` — red on 395's tip (`3 failed`), green after.

### Rollback

`git revert`; nothing stored moves. Merge after #79 (stacked).

## Phase 3 — execute

Commit `dd51b5b0`.

**Red first.** The proving test with the base's `code_atlas` (f5fcb709): `3 failed in 2.23s`.

**Green after.** `3 passed in 2.01s`; every test file naming the three tools or the classifier: `1867 passed in
433.88s`; `ruff`, `mypy` clean. Ran at dd51b5b0.

**Axis 1.** Change-list rows 1–4, plus one deviation the gate's suite caught: `tests/test_sql_tier2_vocabulary_is_opt_in.py` lists the two new subsets as joined by design — they act only past a Table or Column row, so a repo with no `.sql` answers identically (a P5 miss at design). **Axis 2.** Approach bullets 1–3 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff f5fcb709..HEAD` without this file; 1 dispatch, 62,162 tokens):
7 met · 0 not met · 1 can't tell (E1). One Major, four Minor:

| # | Finding | Resolution |
|---|---|---|
| M1 | two PHP functions `run` moved from `name_not_qualified` to the new refusal | only a table pair refuses with sites (H4, aa2ec7c0) |
| m1 | a table and a PHP function of one name refuse listing both | kept: safe, never a wrong re-point |
| m2 | the refusal drops `candidate_count` / `try_instead` | W4: 320's shape |
| m3 | a capped scan could miss a blocking namesake | a capped scan falls through (H5, aa2ec7c0) |
| m4 | a bare table on `find_callers` is not re-pointed | the ticket: `find_callers` takes procedures |

**Red first.** The challenger tests against the base's `code_atlas`: `1 failed, 4 passed in 1.95s`. **Green after:**
`5 passed in 2.85s`; `ruff`, `mypy` clean. Ran at aa2ec7c0.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R1 / AC1 | `test_ac1_…`, `test_a_bare_procedure_…` | 2/2 |
| R2 / AC2 | `test_ac2_…`, `test_challenger_a_mixed_impact_…` | 2/2 |
| C1 / AC3 | `test_challenger_two_functions_…`; the resolution suites | 2/2 |
| AC4 | E1 | 0/1 (excluded) |

Reviewed at aa2ec7c0 — files: change-list rows 1–5. Working doc: `docs/tasks/392_bare-table-name.md`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after aa2ec7c0 only this file, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md` change. Not stale.

### Outward actions

Under the handover: push `feat/392-bare-table-name`; open the PR against `main` (stacked on #79).
Deferred: ratify W2–W4; E1; merge after #79.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 53,329 |
| 4 review | `challenger` (ticket-blind) | 1 | 62,162 |

`LEDGER TOTAL: 115,491 · top cost driver: challenger`
