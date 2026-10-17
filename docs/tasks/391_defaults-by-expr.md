---
id: 391
slug: defaults-by-expr
title: 'check_column_defaults takes one table, so "every column that defaults to user_name(), and its writers" is a Grep over the schema'
phase: 2
milestone: Coverage
status: done
depends_on: [320]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). F1 (1 PR, from a
ticket family of five): audit columns declared `DEFAULT (user_name())` record the SQL login
instead of the app user, unless a writer sets them. Each fix starts with the same question: which
tables carry that default, and which of their writers leave it to the default. The tables came from
`git grep` over the schema baseline, and then the tool ran once per table.

TOOLS.md §"one table" rejects a *list of tables* (N independent scans, with no shared
arithmetic). This is a different subject: a default expression, which the index already stores per
column.

## Scope

1. `check_column_defaults(default_expr=…)` as an alternative subject to `table`: the columns whose
   stored `DEFAULT` matches the expression (normalised for case, brackets and whitespace), each
   with the omitter / total count that today's answer gives.
2. Page it like the other tools. Unmeasured writers stay unmeasured.

## Acceptance criteria

- **AC1:** Two fixture tables with `DEFAULT (user_name())` and one with `DEFAULT (getdate())`:
  `default_expr="user_name()"` lists the first two, with their omitters.
- **AC2:** `[USER_NAME]()` and `user_name ( )` match the same columns.
- **AC3:** A `table=` call is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 391 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W4, runs E1, then merges after #75. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/391-defaults-by-expr`, **stacked on `feat/390-table-readers`**. Contract `.mango/run-contract-391.txt`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 4 want-decision asked | 11 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `check_column_defaults` (`code_atlas/tools/check_column_defaults.py`), its `table` subject, `Column.extra.default`,
TOOLS.md's "one table" row resolve. `default_expr` is to-be-created. Ambiguous: "the anchor".

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 47,135 tokens) raised six; H7–H11 and W3–W4 came from it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the subject | how | `default_expr` as an alternative to `table`, exactly one (Scope 1); `column` narrows a table only — both refusals raise (R5.3) |
| H2 | normalisation | how | case, `[ ]` and whitespace dropped outside quoted literals (Scope 1), then balanced outer parentheses (the DDL stores `(user_name())`) |
| H3 | the arithmetic | how | each matched column measured against its own table's writers by the table mode's arithmetic, one shared `_measure` (R1.8) |
| H4 | rows | how | ordered by table then column, each naming its `table` (the full qname); `limit` / `offset` page them (Scope 2) |
| H5 | no match | how | `reason: no_matches`, empty |
| H6 | unmeasured writers | how | stay `unmeasured` per row (Scope 2) |
| H7 | quoted literals (exposure #1) | how | kept as written, so `'N'` ≠ `'n'` — folding them would merge distinct defaults on an audit tool (R5.6) |
| H8 | a capped column scan (exposure #3) | how | `columns_scan_capped` when the schema exceeds the scan; the arithmetic runs once per table |
| H9 | what matched (exposure #4) | how | `default_expr_normalised` echoes the compared form |
| H10 | a matched column whose table has no writers (exposure #5) | how | listed, `status: table_has_no_writers`, no `omitted_by` — the table mode's row |
| H11 | `writers_partial` (exposure #4) | how | per row, since each table has its own writers |
| W1 | AC-field (anchor) | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | outer-parenthesis stripping | want | **ASSUMED (awaiting ratification):** counts as normalisation beyond the ticket's three |
| W3 | match strictness (exposure #2) | want | **ASSUMED (awaiting ratification):** exact after normalisation — `dbo.user_name()` and `isnull(user_name(), …)` do not match `user_name()` |
| W4 | no envelope-level `writers_partial` | want | **ASSUMED (awaiting ratification):** per-row only |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=4`
`CLARIFICATION: 15 raised | 15 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

`TIER: full` despite `SCOPE: S`: a second subject on a public tool reshapes its signature (quick's single-row bar fails).

### BASELINE

Stacked on 390's tip. `main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 default-expression sweep | `table` required (`check_column_defaults.py:175`); the tables came from `git grep` | `default_expr` |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Each fix starts with the same question" | one call answers it | ⏳ |
| C1 | AC3 | "A `table=` call is byte-identical" | table mode untouched | ⏳ |
| R1 | Scope 1 | "`default_expr=…` as an alternative subject" | H1–H3, H7 | ⏳ |
| R2 | Scope 2 | "Page it … Unmeasured writers stay unmeasured" | H4, H6 | ⏳ |
| AC1 | AC | two `user_name()` tables listed with omitters | | ⏳ |
| AC2 | AC | spellings match the same columns | | ⏳ |
| AC3 | AC | `table=` byte-identical | | ⏳ |
| AC4 | AC-field | anchor | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — exact column list, `omitted_by`, `named_by` | |
| AC2 | yes — four spellings, one column set | |
| AC3 | yes — the table-mode suites unchanged; no `default_expr` / row `table` keys | |
| AC4 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.8 (change-type) ✅ _measure shared by both subjects · §R5.3 (change-type) ✅ the subject pair and column refusals raise · §R5.6 (change-type) ✅ quoted literals kept, capped scan flagged · §R6.5 (change-type) ✅ seen red on 390's tip · §R7.6 (change-type) ✅ TOOLS one-table row rewritten · §R7.7 (change-type) ✅ formatter hunks outside the edit reverted`

## Phase 2 — design

### Approach

1. `_measure` — the table mode's arithmetic, extracted; both subjects call it.
2. `normalise_default` — the comparable form; `_by_expression` scans `Column` rows, groups matches by table, measures
   each table once, pages the rows.
3. The signature: `table` optional, `default_expr` new; refusals for both-or-neither and for `column` with an expression.
4. Docs: TOOLS.md (tool row, the one-subject row), CHANGELOG `Unreleased`.

### Rejected alternatives

- **A `tables=[…]` list** — TOOLS.md's own row: N scans with no shared arithmetic.
- **Matching inside expressions (`isnull(user_name(),…)`)** — a fuzzy match on an audit tool; W3.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| both DEFAULT spellings reach `Column.extra.default` | verified | the proving test's named constraint (`ALTER … ADD CONSTRAINT … DEFAULT ([USER_NAME]()) FOR …`) matches |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the expression subject | `code_atlas/tools/check_column_defaults.py` | the tool's MCP signature (`table` no longer required); its two suites | R1, R2, C1 | 1/1 |
| 2 | proving test | `tests/test_defaults_by_expression.py` (new) | — | AC1–AC3 | 1/1 |
| 3 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 4 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL adapter + build + tool | real build, three tables | authored | ✅ |
| AC2 | integration | four spellings | authored | ✅ |
| AC3 | integration | the table-mode suites + key absence | authored | ✅ |
| AC4 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, `check_column_defaults(default_expr=
"user_name()")` against the ticket family's five tables · `expiry: when the anchor index is available to a maintainer
run` · `seen: 378, 384, 388, 389, 394, 390, 391`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_defaults_by_expression.py` — red on 390's tip (`3 failed`), green after.

### Rollback

`git revert`; nothing stored moves. Merge after #75 (stacked).

## Phase 3 — execute

Commits `2156565c` (the subject), `d02f413d` (docs), `ac40226e` (challenger minors).

**Red first.** The proving test against 390's tip (`71bd1c81`, a scratch copy): `3 failed in 2.40s`.

**Green after.** `tests/test_defaults_by_expression.py` plus both table-mode suites: `20 passed in 4.99s`; `ruff`,
`mypy` clean. Ran at ac40226e.

**Axis 1.** Change-list rows 1–4. **Axis 2.** Approach bullets 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff feat/390-table-readers..feat/391-defaults-by-expr` without this
file; 1 dispatch, 56,342 tokens): 8 met · 0 not met · 1 can't tell (E1). Six Minor findings:

| # | Finding | Resolution |
|---|---|---|
| m1 | a parenthesis inside a literal blocked outer stripping | literals skipped in `_balanced` (ac40226e) |
| m2 | a matching Column no table contains was dropped silently | counted in `columns_without_table` (ac40226e) |
| m3 | the partial-writers hint never rode the expression answer | attached once when any row is partial (ac40226e) |
| m4 | a blank subject answered `no_matches` | refused (ac40226e) |
| m5 | the unbuilt envelope lacks `default_expr_normalised`; every call scans the columns | kept: nothing to normalise against unbuilt; a schema-sized scan per call (H8) |
| m6 | no paging test | `test_an_expression_answer_pages` (ac40226e) |

Verify-only round, main loop: `20 passed`. Ran at ac40226e.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R1 / AC1 | `test_ac1_…` | 1/1 |
| AC2 | `test_ac2_…`, `test_a_quoted_literal_…`, `test_a_parenthesis_inside_a_literal_…` | 3/3 |
| C1 / AC3 | `test_ac3_…`; both table-mode suites unchanged | 2/2 |
| R2 | `test_an_expression_answer_pages` | 1/1 |
| AC4 | E1 | 0/1 (excluded) |

Reviewed at ac40226e — files: change-list rows 1–3. Working doc: `docs/tasks/391_defaults-by-expr.md`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after ac40226e only this file, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md` change. Not stale.

### Outward actions

Under the handover: push `feat/391-defaults-by-expr`; open the PR against `main` (stacked on #75).
Deferred: ratify W2–W4; E1; merge after #75.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 47,135 |
| 4 review | `challenger` (ticket-blind) | 1 | 56,342 |

`LEDGER TOTAL: 103,477 · top cost driver: challenger`
