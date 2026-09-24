---
id: 329
slug: a-table-writer-list-repeats-each-statement-per-column
title: "find_references on a Table unions its columns' WRITES, so one INSERT naming eight columns is eight rows — six statements filled a 50-row page and read as duplicates"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [278]
---

## Why this exists (field retro, 2026-09-24 — FIELD-1426)

`find_references` on a hot table returned **866 `WRITES`, capped at 50**. Page 1 was *"the same six
`INSERT` lines … repeated ~8 times"*; `path_prefix` narrowed it to 368 rows, page 1 still "all
duplicates". The session rated the tool 3/10 for the question and asked for dedupe.

**They are not duplicates.** Since 278 a Table subject unions the writers of the table with the
writers of each `CONTAINS` column (`find_references.py:236-240,368`), and the SQL adapter emits one
`WRITES` per named column onto `T::col` (`scan.js:590-595`). An INSERT naming eight columns is eight
correct rows at one `(file, line)`. The answer is right; its unit is wrong for the question a Table
subject asks — *which statements write this table* — and it buries the statement list.

## Goal

A Table subject answers one row per writing statement, with the columns it names folded into that
row; a Column subject is unchanged.

## Scope / Deliverables

1. **Group Table-subject rows by `(source, file, line)`**, carrying the named columns as a list
   on the row. Counts (`total_count`, test/production census) count statements.
2. **Paging walks statements**, so page 1 of a 50-cap is 50 statements.
3. **Column subjects and the writer set `check_column_defaults` reads are untouched** (278 shares
   the set; only this tool's rendering changes).

## Constraints

- **061** — Column subjects and non-Table subjects are byte-identical.
- **R4.2** — deterministic column order within a row.
- **R1.4** — grouping is a `GraphStore` query, not a Python pass over an unbounded fetch.

## Acceptance criteria

- **AC1** Fixture: two INSERTs naming 3 and 2 columns + one column-less write → 3 rows, not 6.
- **AC2** `total_count` is 3; a `limit=2` page returns 2 statements and `truncated: true`.
- **AC3** `find_references T::col` is byte-identical to today.

## References
`code_atlas/tools/find_references.py:88,155,236-240,368`; `adapters/sql/src/scan.js:573-595`;
ticket 278.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 329 — Table writer statements (working doc)

- **Ticket:** 329 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions.

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=3 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | one row per writing statement; columns folded; Column unchanged | store group + Table-only path | D1 D2 | AC1 AC3 | ✅ |
| R1 | Scope 1 | Group by (source, file, line); columns list; counts are statements | write_statements_* | D1 | AC1 AC2 | ✅ |
| R2 | Scope 2 | Paging walks statements | limit/offset on grouped query | D1 | AC2 | ✅ |
| R3 | Scope 3 | Column + check_column_defaults untouched | Table-only branch | D2 | AC3 | ✅ |
| C1 | Constraints | 061 Column/non-Table byte-identical | Column path unchanged | D2 | AC3 + 278 | ✅ |
| C2 | Constraints | R4.2 deterministic column order | sorted() | D1 | AC1 | ✅ |
| C3 | Constraints | R1.4 grouping is GraphStore query | store methods | D1 | review | ✅ |
| AC1 | AC | 3+2+0 cols → 3 rows not 6 | proving | D1 | proving | ✅ |
| AC2 | AC | total=3; limit=2 truncated | proving | D1 | proving | ✅ |
| AC3 | AC | Column byte-identical | proving | D2 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause (bug, `data`/`logic`): Table unions column WRITES; adapter emits one WRITES per named column → one INSERT = N rows at same (file,line). Unit wrong for Table question.
- Blast radius: find_references Table arm; store; 278 tests; check_column_defaults untouched.

`TRACK: backend — 0/3 touched files under UI paths`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.4 (change-type) ✅ store query · R4.2 (change-type) ✅ sorted columns · R7.2 (change-type) ✅ ledger`

`BASELINE: green`

## Phase 2 — Design

- Approach: GraphStore `count_write_statements_by_targets` / `write_statements_by_targets` / statement census; Table arm only; Column keeps `edges_by_targets`.
- Rejected: Python post-group over unbounded fetch (R1.4); changing adapter emission (out of scope — unit is the tool answer).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | grouped store queries | code_atlas/store.py | find_references | R1 R2 C2 C3 | 1/1 |
| D2 | Table arm uses statements | code_atlas/tools/find_references.py | 278 | G1 R3 C1 | 1/1 |
| D3 | proving AC1–3 | tests/test_table_writer_statements.py | — | AC* | 1/1 |
| D4 | bookkeeping | docs/tasks/329_… · BACKLOG · TOKEN_LEDGER | — | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest | authored | ✅ |
| AC2 | integration | pytest | authored | ✅ |
| AC3 | integration | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_table_writer_statements.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/329-table-writer-statements

Ran at d9f99d8df066f167e8728ead4dbe53d40d299702

```
$ .venv/bin/python -m pytest tests/test_table_writer_statements.py tests/test_table_writer_set_via_find_references.py -q
9 passed in 1.14s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN, 9 met / 0 not met / 0 can't tell.

Verdict: `clean (challenger only — REVIEWER: OFF)`

Ran at d9f99d8df066f167e8728ead4dbe53d40d299702

```
$ .venv/bin/python -m pytest tests/test_table_writer_statements.py tests/test_table_writer_set_via_find_references.py -q
9 passed in 1.14s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at d9f99d8df066f167e8728ead4dbe53d40d299702`

## Phase 5 — Finalise

Outward: push feat/329-table-writer-statements, open PR. Never merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger round 1`
