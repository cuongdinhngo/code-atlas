---
id: 390
slug: table-readers
title: 'A table lists its writers but never its readers, and a trigger that writes a column is not among them'
phase: 2
milestone: Coverage
status: done
depends_on: [278, 328, 364, 371]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). The schema
questions that still went to Grep:

- F1 (1 PR): "who reads `dbo.X`" before a reference-data change. `find_references` returns
  `WRITES` and `DELETES` only, so the reader sweep over the PHP and SQL trees was Grep.
- F2 (1 PR): the writer of a status column `T.Flag` was an `AFTER` trigger. Asking which SQL writes
  a column inside a trigger was not a one-call question.
- F3 (2 PRs): a column written by an `UPDATE` inside a PHP string, and a T-SQL function
  (`USER_NAME()`) compared inside PHP SQL strings. 371 reads a string that *begins* a write.
  These were mid-string fragments, or strings built across several concatenations.

## Scope

1. Measure first: on the anchor index, count the trigger bodies whose `INSERT`, `UPDATE` and
   `DELETE` statements emit `WRITES` today. Fix the trigger case here only if it is a gap in
   the SQL adapter. Otherwise record the cause.
2. A `READS` edge from a `SELECT … FROM` / `JOIN` table reference: in T-SQL bodies at
   `RESOLVED`, and in host strings at `HEURISTIC` (the same reader as 371). This is a contract
   change (a new edge kind), so it is decided in design against R1.2 and PLAN §19.
3. `find_references` on a Table takes `kinds` (default: today's writers). `READS` is opt-in, so
   today's answers stay byte-identical.

## Acceptance criteria

- **AC1:** An `AFTER UPDATE` trigger that sets `T.C` is listed by `find_references T::C`, labelled
  with the trigger as its writer — or, if scope 1 finds the gap outside the SQL adapter, the
  measured cause is recorded and AC1 moves to the ticket that owns it.
- **AC2:** With `kinds=["READS"]`, a proc that selects from `T` and a PHP string
  `"SELECT … FROM dbo.T"` are both listed, with their tiers.
- **AC3:** Without `kinds`, `find_references` on a table is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 390 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W6, pushes the `v0.4.0` tag after merge, runs E1, then merges after #74. **Revert path:** `git revert` the branch's commits (a contract bump: an index built at 15 needs a full rebuild after a revert).
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/390-table-readers`, **stacked on `feat/394-stub-or-alias`**. Contract `.mango/run-contract-390.txt`.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 17 unresolved surfaced | 6 want-decision asked | 11 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Premise.** `find_references`, `WRITES` / `DELETES`, the SQL adapter's trigger handling (`adapters/sql/src/scan.js:278`),
371's host-string reader (`SqlLiteral.php`, `sqlLiteral.js`, `sql_literal.py`), R1.2, PLAN §19, tasks 278 / 328 / 364 /
371 resolve. `READS` and `kinds` are to-be-created. Ambiguous: "the anchor index".

**Scope 1 probed on a fixture** (`main`-equivalent tree, scratch run): an `AFTER UPDATE` trigger's `UPDATE dbo.T SET
Flag = 1 …` and `UPDATE t SET t.C = 2 FROM dbo.T t JOIN inserted …` both already emit `WRITES` from the trigger —
`dbo.trg_T_upd → dbo.T::Flag`. The F2 cause is therefore not the SQL adapter's trigger case as fixtured; what the
anchor's trigger is is E1's to measure.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,709 tokens) raised six; H9–H11 and W3–W5 came from it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | AC1 | how | met by today's adapter (probe above); AC1's test names the trigger as the column's writer |
| H2 | the reader relation | how | a new edge kind `READS` (Scope 2: "a contract change … decided in design"): contract 15, `FQN_EDGE_KINDS`, every adapter's handshake 15 (R3.1) |
| H3 | SQL bodies | how | `READS` for every `FROM` / `JOIN` source of `SELECT`, `INSERT … SELECT`, `UPDATE … FROM`, `DELETE … FROM`, subqueries included, `RESOLVED`, once per table per statement, on its keyword's line; never the write target, `inserted` / `deleted`, `#temp` / `@table`, a CTE name or a table-valued function |
| H4 | host strings | how | 371's head-of-literal reader gains `SELECT … FROM <name>` → `READS` at `HEURISTIC` (Scope 2: "the same reader as 371"); an unqualified name needs a clause or the literal's end, so prose reads as nothing; the three ports share `sql_literal_cases.json` |
| H5 | `kinds` | how | `find_references(kinds=[…])` on a Table / Column (Scope 3), default `["WRITES", "DELETES"]`; an unknown kind raises (R5.3) |
| H6 | AC3 | how | the default call equals the explicit default; the existing writer tests run unchanged |
| H7 | P8 | how | `cross_repo_validate.py --public-only` re-run; floors re-measured if moved (AGENT_BRIEF P8) |
| H8 | F3 mid-string fragments, `USER_NAME()` comparisons | how | out: Scope 2 names 371's head-of-literal reader, not a fragment parser |
| H9 | an empty reader answer (exposure #2) | how | `reads_emitters_only` when a covered language emitted no `READS` — R5.6, as 281 did for writers |
| H10 | other consumers of the new kind (exposure #3) | how | every inbound walk that reads all kinds now sees `READS` — a proc reading a table is in its impact; P8's counts show the move |
| H11 | `kinds` on another subject (exposure) | how | ignored and said so: `kinds_ignored` |
| W1 | Scope 1's anchor count + AC-field | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | cut 0.4.0 in this PR | want | **ASSUMED (awaiting ratification):** a contract bump cuts a release (R3.1); the version and heading ship, the `v0.4.0` tag is the maintainer's (381 E3's xfail moved to 0.4.0) |
| W3 | `READS` is table-level (exposure #1) | want | **ASSUMED (awaiting ratification):** a `SELECT`'s source is a table; a column subject's readers are not modelled |
| W4 | host strings read the first `FROM` only | want | **ASSUMED (awaiting ratification):** `JOIN`s inside a host string are not read |
| W5 | AC3 proof strength (exposure) | want | **ASSUMED (awaiting ratification):** internal equality plus the unchanged writer suite, not a byte golden |
| W6 | F3's fragments stay out (exposure) | want | **ASSUMED (awaiting ratification):** follows H8; a fragment reader is a ticket of its own |

## Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 17 raised | 17 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/30 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

Stacked on 394's tip, whose gate is green (PR #74). `main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in
522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 readers | `find_references` on a Table: `WRITES` + `DELETES` only (`find_references.py:385`) | `kinds=["READS"]` |
| F2 trigger writer | already emitted (probe) | proven by test; anchor cause → E1 |
| F3 host reads | 371 reads a string that begins a write | also one that begins `SELECT … FROM` |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the reader sweep … was Grep" | a table names its readers | ⏳ |
| C1 | Scope 3 | "today's answers stay byte-identical" | `READS` opt-in | ⏳ |
| R1 | Scope 1 | "Fix the trigger case here only if it is a gap in the SQL adapter" | H1 | ⏳ |
| R2 | Scope 2 | "A `READS` edge … RESOLVED … HEURISTIC" | H2–H4 | ⏳ |
| R3 | Scope 3 | "`find_references` on a Table takes `kinds`" | H5, H11 | ⏳ |
| AC1 | AC | the trigger listed as `T::C`'s writer | | ⏳ |
| AC2 | AC | proc + PHP string listed with tiers | | ⏳ |
| AC3 | AC | without `kinds`, byte-identical | | ⏳ |
| AC4 | AC-field | anchor replay | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `[(dbo.trg_T_upd, WRITES)]` exactly | |
| AC2 | yes — exact `(qname, kind, tier)` set | |
| AC3 | yes — plain == explicit default; writer suites unchanged | W5 |
| AC4 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 10 applicable — 10 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ READS read from SQL grammar in adapters, none in the core · §R1.2 (change-type) ✅ no registry: one edge kind on the existing seam · §R2.1 (change-type) ✅ T-SQL statement grammar only · §R3.1 (change-type) ✅ contract 15, conformance case select-sources, 0.4.0 heading flagging rebuild and adapter update · §R3.3 (change-type) ✅ bare targets, the resolver links them · §R5.6 (change-type) ✅ reads_emitters_only separates no readers from unmeasured · §R6.2 (change-type) ✅ the construct named in SQL_R62_CASES before its fixture · §R6.6 (change-type) ✅ phpstan max, tsc strict, mypy strict green · §R7.6 (change-type) ✅ PLAN's SQL line extended, narrative trimmed · §R7.7 (change-type) ✅ formatter hunks outside the edit reverted`

## Phase 2 — design

### Approach

1. `contract.py`: `READS`, contract 15, `FQN_EDGE_KINDS`; every adapter's handshake 15.
2. SQL adapter: `ddl.readSources`; the scanner's `select` statement kind and a `reads()` on every reading statement.
3. Host-string readers (PHP, TS, Python): a `select` verb reading the first `FROM` name; shared cases.
4. `find_references(kinds=)` on Table / Column; `reads_emitters_only`; `kinds_ignored` elsewhere.
5. Release: `pyproject` 0.4.0, CHANGELOG `0.4.0 — 2026-10-17 · contract 15 · schema 7` with both upgrade flags, the
   tag xfail moved to 0.4.0, generated hook tables regenerated.
6. Docs: TOOLS.md, CONVENTION.md, PLAN, the four adapter READMEs.

### Rejected alternatives

- **`REFERENCES` from a routine to a table** — no contract bump, but `REFERENCES` onto a table already means a
  column-list-omitted FK, so `kinds=["REFERENCES"]` would blend readers with constraints (R5.6).
- **Readers in the default answer** — Scope 3 makes `READS` opt-in; a writer question would grow a page of readers.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the three host adapters emit whatever kind the reader returns | verified | `Visitor.php:355`, `parse.js:584`, `parse.py:1101` pass `kind` through |
| the release guard accepts an untagged release under a strict xfail | verified | 381 E3's marker, moved to 0.4.0; `test_release_discipline` `19 passed, 1 xfailed` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `READS`, contract 15 | `code_atlas/contract.py` | 16 `CONTRACT_VERSION == 14` pins; the two edge-kind pins in `tests/contract/test_contract_schema.py` (P5) | R2 | 1/1 |
| 2 | handshake 15 | `adapters/{php/index.php,typescript/index.js,sql/index.js,python/index.py}` | every adapter launch | R2 | 4/4 |
| 3 | body reads | `adapters/sql/src/ddl.js`, `adapters/sql/src/scan.js` | SQL conformance (`insert-without-column-list` now reads its source) | R2 | 2/2 |
| 4 | host-string reads | `adapters/php/src/SqlLiteral.php`, `adapters/typescript/src/sqlLiteral.js`, `adapters/python/src/sql_literal.py` | the shared cases, `test_sql_literal_agreement` (its kind filter) | R2 | 3/3 |
| 5 | `kinds`, caveat | `code_atlas/tools/find_references.py`, `code_atlas/tools/nav_result.py` | Table/Column answers (default unchanged) | R3, C1 | 2/2 |
| 6 | release | `pyproject.toml`, `CHANGELOG.md`, `tests/test_release_discipline.py`, the generated hook / plugin files | `test_release_discipline`, `test_skill_drift` | R2 | 1/1 |
| 7 | proving test + conformance | `tests/test_table_readers.py` (new), `tests/contract/adapter_registry.py`, `tests/fixtures/sql/select_sources.sql` (new), `tests/contract/sql_literal_cases.json` | — | AC1–AC3 | 4/4 |
| 8 | proof collateral | the 16 version-pin tests, `test_contract_schema.py`, `test_sql_literal_agreement.py` | P5 | R2 | 18/18 |
| 9 | docs | `docs/TOOLS.md`, `docs/CONVENTION.md`, `docs/PLAN.md`, four adapter READMEs | doc budgets | G1 | 7/7 |
| 10 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

Trace: `grep -rl "CONTRACT_VERSION == 14" tests` → 16 files (row 8); the conformance suite (`353 passed` after rows
1–8); the cross-repo run (H7).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL adapter + build + tool | a real build with a trigger | authored | ✅ |
| AC2 | integration — two adapters | real SQL + PHP builds | authored | ✅ |
| AC3 | integration | default == explicit default; the writer suites | authored | ✅ |
| AC4 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** Scope 1's count and AC-field · risk: medium (F2's real cause unknown) ·
why: the anchor index is not on this machine · escalated, answered by the maintainer 2026-10-17 · follow-up: on the
anchor, count triggers whose body emits `WRITES` (`SELECT count(DISTINCT source_qname) FROM edges e JOIN nodes n ON
n.qualified_name = e.source_qname WHERE e.kind = 'WRITES' AND n.extra LIKE '%"trigger"%'`) against the trigger count,
and replay F1–F3 · `expiry: when the anchor index is available to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_table_readers.py` — red on 394's tip (`3 failed, 1 passed`; AC1 holds
there), green after.

### Rollback

`git revert`; an index built at contract 15 then reports `rebuild required` — run `code-atlas-build --full`.

## Phase 3 — execute

Commits `ef229ca7` (contract 15, adapters, `kinds`, proof collateral), `1200f14b` (0.4.0 + docs), `decfc536`
(`reads_emitters_only`), `0f6ff76c` (challenger fixes).

**Red first.** The proving test against 394's tip (`0d1757fc`, a scratch copy): `3 failed, 1 passed in 2.92s` — AC1
holds there (the adapter already wrote from the trigger). The challenger-fix test's input on the pre-fix adapter
(`e11639db`): one of four reads (`[('dbo.Q', 'dbo.A')]`).

**Green after.** `tests/test_table_readers.py`: `6 passed`; the agreement, conformance and proving suites:
`85 passed`; adapters: `tsc` (TS, SQL) clean, `phpstan` `[OK] No errors`, Python adapter `mypy --strict` and `ruff`
clean. Ran at 0f6ff76c.

**P8.** `scripts/cross_repo_validate.py --public-only --skip-clone`: `"public_ok": 11, "public_failed": 0` — every
floor holds; `READS` only adds edges, so no floor moved and none is re-measured. Ran at e11639db (adapter
emission unchanged since but for the three challenger fixes, which only add reads).

**Axis 1.** Change-list rows 1–10, plus one deviation: `scripts/gen_skill.py` and the regenerated `contrib/agent-brief.md` — `test_agent_brief_usage_completeness` requires every `find_references` parameter taught or waived, and `kinds` is taught (a P5 miss at design, caught by the gate's suite). **Axis 2.** Approach bullets 1–6 implemented as approved; the caveat (H9) and
the fixes below sit inside rows 3–5.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff feat/394-stub-or-alias..feat/390-table-readers` without this
file; 1 dispatch, 64,894 tokens): 0 not met · 2 can't tell (E1) · 1 met with gaps.

| # | Finding | Resolution |
|---|---|---|
| D1 Major | a view's reads are the file's; a one-line inline function read nothing | the function fixed (`0f6ff76c`); views are not nodes in this adapter (README: out of scope) — documented in its emission table |
| D2 | a comma join read its first table only | every listed source (`0f6ff76c`) |
| D3 | `INSERT INTO t SELECT … FROM t` lost the self-read | an INSERT keeps it (`0f6ff76c`) |
| D4 | `UPDATE t … FROM dbo.T t` records no read of its target | kept: that FROM names the write target |
| D5 | prose ending in "as" passed the host-string guard | `as` dropped from all three ports; shared case added |
| D6 | AC3 proven by internal equality | W5 |

Verify-only round, main loop: `6 passed` (proving test, the new fix test red on the pre-fix adapter) and `85 passed`
(agreement, conformance, proving). Ran at 0f6ff76c.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R2 | `test_ac2_…`, conformance `select-sources`, `test_challenger_…` | 3/3 |
| C1 / AC3 | `test_ac3_…`; the writer suites unchanged | 2/2 |
| R1 / AC1 | `test_ac1_…` | 1/1 |
| R3 | `test_kinds_must_name_an_inbound_edge_kind`, `test_a_language_that_emits_no_reads_…` | 2/2 |
| AC4 | E1 | 0/1 (excluded) |

Reviewed at 0f6ff76c — files: change-list rows 1–9. Working doc: `docs/tasks/390_table-readers.md`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim: the contract-bump path (version in core and four adapters, conformance, a
release heading with both flags, the tag left to the maintainer) followed 328 and 381 E3 as written.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after 0f6ff76c only this file, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md` change. Not stale.

### Outward actions

Under the handover: push `feat/390-table-readers`; open the PR against `main` (stacked on #74).
Deferred: ratify W2–W6; push `v0.4.0` after merge (a release tag — stop-and-confirm); E1; merge after #74.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 44,709 |
| 4 review | `challenger` (ticket-blind) | 1 | 64,894 |

`LEDGER TOTAL: 109,603 · top cost driver: challenger`
