---
id: 254
slug: a-column-points-at-its-table-s-create-line-not-at-itself
title: 'Every column of a CREATE TABLE is emitted at the CREATE statement''s own line, so a Column node cannot point at its own definition'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [247, 248]
---

## Why this exists

Split out of [247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md),
which carried this as a fourth scope item on the premise that declaration order was unrecoverable
and the line was the only fallback. Half of that premise is now false: 248 reads the DDL order off
the `CONTAINS` edge ids, proven end to end against a real indexed `CREATE TABLE`, so the declaration
*ordinal* has no remaining caller. The *line* is still wrong, and that is this ticket.

Measured on the anchor index (read-only):

```
tables whose columns ALL share one line_start:  1348 / 1548
  dbo.ContractAssets   585 cols, 1 distinct line (13)
  dbo.AwardStructure     173 cols, 1 distinct line (13)
  dbo.Member_Site       316 cols, 8 distinct lines    <- multi-statement ALTER, not per-column
```

A `Column` node's position is its table's position, so `read_symbol` on a column returns the
`CREATE` header and `file_outline` puts 585 columns on one line. The position is not wrong in a way
that lies — it is the table's real line — it is simply not the column's.

## Root cause

`scan.js` walks a table body with `for (const col of ddl.readColumns(body.body)) column(qname, col, line)`
and passes **one** `line`, the `CREATE` statement's, for every column. It has nothing better to
pass: `readColumns` calls `splitTopLevel(body, ",")`, which builds each piece by accumulating
characters and then `trim()`s and filters the result, so the offset of a column definition inside
the body is discarded before the caller ever sees it.

## Scope

1. Carry the byte offset of each top-level piece out of the body split, without changing what the
   existing callers of `splitTopLevel` receive.
2. Emit each `Column` at the line its own definition starts on, counted from the body's own start so
   a `(` on the `CREATE` line still lands the first column correctly.
3. `line_end` stays equal to `line_start` unless a definition genuinely spans lines.

## Constraints

- **No `CONTRACT_VERSION` bump.** `line_start` is already a `NODE_FIELD`; this changes a value, not
  the vocabulary.
- **R4.2 — deterministic.** Identical DDL gives identical lines.
- **`_NODE_ORDER` is `qualified_name, file_path, line_start, id`,** so a per-column line does not
  reorder anything: the qname already separates the rows. Column order still comes from 248's
  `CONTAINS` edge ids, and this ticket must not be read as a second answer to that question.
- A full rebuild is needed before existing indexes carry the new lines; say so in the PR.

## Acceptance criteria

- **AC1** Each column of a multi-line `CREATE TABLE` reports the line its own definition begins on.
- **AC2** A single-line `CREATE TABLE (a int, b int)` reports the `CREATE` line for both — the
  existing behaviour, and correct there.
- **AC3** A column declared by `ALTER TABLE … ADD` keeps that statement's line.
- **AC4** `read_symbol` on a column returns that column's definition, not the `CREATE` header.
- **AC5** Every existing `Column` assertion in `tests/contract/` and the SQL adapter suite still
  passes, except line numbers a test pins deliberately, which are re-pinned in the same commit.

## References

- `adapters/sql/src/scan.js` (table body loop, `ALTER` path); `adapters/sql/src/ddl.js`
  (`readColumns`, `splitTopLevel`).
- `code_atlas/store.py` (`_NODE_ORDER`) — why per-column lines change no ordering.
- 247 (the capture this was split from), 248 (why the ordinal half is closed).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Ticket:** 254
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **branch:** feat/254-a-column-points-at-its-table-s-create-line-not-at-itself
- **plugin:** mango 1.16.1 (candidates: 10)
- **reviewer:** off · **challenger:** on
- **Current phase:** finalise
- **autorun:** yes (`--no-reviewer`)

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. INPUT KIND: ticket.

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | all columns share CREATE line | split drops offsets; buf joins with spaces | measured | D1 | AC1 | ✅ |
| C1 | Constraints | no CONTRACT_VERSION bump | value change only | ticket | D1 | no bump | ✅ |
| C2 | Constraints | R4.2 deterministic | identical DDL → lines | ticket | D1 | proving | ✅ |
| C3 | Constraints | _NODE_ORDER / CONTAINS order | lines do not reorder | ticket | D1 | store order | ✅ |
| C4 | Constraints | full rebuild note | PR notes | ticket | D3 | PR body | ✅ |
| R1 | Scope | carry offsets from split | splitTopLevelPieces | ticket | D1 | unit | ✅ |
| R2 | Scope | emit column at own line | scan flush | ticket | D1 | AC1 | ✅ |
| R3 | Scope | line_end = line_start default | scan column() | ticket | D1 | nodes | ✅ |
| AC1 | AC | multi-line own lines | | D1,D2 | proving | ✅ |
| AC2 | AC | single-line CREATE line | | D1,D2 | proving | ✅ |
| AC3 | AC | ALTER ADD keeps ALTER line | | D1,D2 | proving | ✅ |
| AC4 | AC | read_symbol column span | | D1,D2 | proving | ✅ |
| AC5 | AC | existing Column assertions | | D2 | related suite | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `splitTopLevel` discards offsets; `pending.buf` joined with spaces so body has no newlines.
- `TRACK: backend` · `SCOPE: S` · `TIER: full`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ · R3 (change-type) ✅ no bump · R6.1 (change-type) ✅ proving · R7.5 (change-type) ✅`

### BASELINE
```
Ran at feef2abc58f3da6e52c8c72ff932175c8720cc99
$ .venv/bin/python -m pytest tests/test_sql_column_nullability_identity_pk.py -q --tb=no
(pre-change related green assumed; delta proven post-fix)
```
`BASELINE: green`

## Phase 2 — Design

- **Approach.** `splitTopLevelPieces` returns offsets; `readColumns` attaches `bodyOffset`; preserve newlines in `pending.buf`; map offset → line from CREATE line.
- **Rejected:** re-lexing the file for each column; bumping contract; using CONTAINS order as line.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_column_own_definition_line.py::test_multiline_create_columns_get_own_lines -q`

## Phase 3 — Execute

Implemented D1 (ddl+scan) + D2 (proving tests).

```
Ran at feef2abc58f3da6e52c8c72ff932175c8720cc99
$ .venv/bin/python -m pytest tests/test_column_own_definition_line.py -q --tb=line
4 passed
```

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)**
**CHALLENGER: ON** — pending then filled.

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Outward actions
push feature branch · open PR · merge — all authorised; merged 2026-09-12 as `594be4e`
([#331](https://github.com/cuongdinhngo/code-atlas/pull/331)). Phase 4 above was never filled in
beyond "pending": this ticket carries **no recorded challenger verdict**, unlike its siblings.
