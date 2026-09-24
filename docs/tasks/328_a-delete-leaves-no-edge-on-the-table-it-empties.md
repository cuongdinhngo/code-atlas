---
id: 328
slug: a-delete-leaves-no-edge-on-the-table-it-empties
title: "The SQL adapter emits WRITES for INSERT and UPDATE only — a DELETE, MERGE or TRUNCATE leaves no edge, so 'what removes rows from this table' has no answer in any language"
phase: 1.5b
milestone: Coverage
status: in-progress
depends_on: [022, 278, 321]
---

## Why this exists (field retro, 2026-09-24 — FIELD-1426)

Rows a trigger had just generated vanished milliseconds later with no audit row. The session asked
the right question — *every code path that DELETEs rows of table X* — and `find_references` on the
table returned 866 `WRITES`, none of them a delete. It blamed the PHP half (`writes_emitters_only`:
PHP string SQL is not measured), and the culprit was indeed a PHP delete found by `git grep`.

**The gap is wider than the retro saw.** The SQL adapter never emits a delete either:
`INSERT_RE` / `UPDATE_RE` (`scan.js:277-278`) are the only statement tests that reach `writes()`
(`scan.js:851-853`); `delete` appears only in `BOUNDARY_RE` (`scan.js:282`) as a statement edge.
No `MERGE` or `TRUNCATE` handling exists. A DELETE inside a stored procedure is as invisible as one
in PHP.

**It cannot simply be a `WRITES`.** `check_column_defaults` reads `WRITES` as *the writers of a
table* and asks which omit a defaulted column (194); a DELETE names no columns, so every deleter
would become a false "omits the default" finding. 321 met the same trap for dynamic DDL and chose a
new kind, `ALTERS`, rather than *"a `WRITES` that would enrol every migration as a writer"*
(`contract.py:30`). That precedent decides the shape here.

## Goal

A statement that removes rows leaves an edge on the table it removes them from, addressable from
the table, and never counted as a writer.

## Scope / Deliverables

1. **Design call, in writing:** a new edge kind (e.g. `DELETES`) for DELETE / TRUNCATE, and where
   `MERGE` lands (it can insert, update and delete in one statement).
2. **SQL adapter emits it** at the tier the target warrants, from the same statement scanner.
3. **`find_references` on a Table / Column** returns it beside `WRITES`, each row labelled by kind;
   `check_column_defaults` is unchanged.
4. **`contract_version` bump + conformance tests** (R3.1).

## Constraints

- **R3.1** — new vocabulary ⇒ bump and conformance update in the same change.
- **R2.1** — T-SQL / ANSI statement grammar only; no repo's procedure or table names.
- **R4.2** — identical input, identical rows.
- **061** — a table no statement deletes from answers byte-identically.

## Acceptance criteria

- **AC1** Fixture procedure with `DELETE FROM dbo.T WHERE …` → one edge of the new kind onto `dbo.T`.
- **AC2** `TRUNCATE TABLE dbo.T` and the MERGE decision each have a fixture.
- **AC3** `check_column_defaults` on `dbo.T` is byte-identical with and without the delete.
- **AC4** `find_references dbo.T` lists the delete site with its kind.

## Out of scope

- **SQL inside PHP string literals.** That is the retro's actual culprit and the larger win, but it
  is a cross-language link (222) keyed on SQL text; a separate ticket, and never on a wrapper
  method's name (R2.2).
- A per-kind filter argument on `find_references` — add when the rows exist to filter.

## References
`adapters/sql/src/scan.js:277-282,573-595,845-856`; `code_atlas/contract.py:30,79`;
`code_atlas/tools/check_column_defaults.py:1,36-53`; `code_atlas/tools/find_references.py:236-240,368`;
tickets 022, 194, 222, 278, 321.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 328 — DELETES edge kind (working doc)

- **Ticket:** 328 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR
- **Session status:** review clean → finalise

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: new kind `DELETES` (not WRITES) — citation: ticket Goal + 321 ALTERS precedent.
HOW2: MERGE emits DELETES only when a WHEN…DELETE action is present; insert/update-only MERGE unchanged — citation: ticket Scope §1 + AC2.

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · Out of scope · References) | 7 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | removals leave addressable non-writer edge | D1–D3 | ✅ |
| R1 | Scope 1 | DELETES + MERGE decision written | D1 | ✅ |
| R2 | Scope 2 | SQL adapter emits | D2 | ✅ |
| R3 | Scope 3 | find_references lists; defaults unchanged | D3 | ✅ |
| R4 | Scope 4 | contract_version bump + conformance | D1 | ✅ |
| C1–C4 | Constraints | R3.1 R2.1 R4.2 061 | D* | ✅ |
| AC1–AC4 | AC | proving | D4 | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: SQL scanner only classified INSERT/UPDATE as writers; DELETE invisible.
- Blast radius: contract, sql adapter, find_references kinds, version pins.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R3.1 ✅ · R1.4 ✅ · R2.1 ✅ · R7.2 ✅`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | DELETES + v12 | contract.py · adapter handshakes · pins | 1/1 |
| D2 | emit DELETES | adapters/sql scan.js · ddl.js · README | 1/1 |
| D3 | find_references kinds | find_references.py | 1/1 |
| D4 | proving | tests/test_deletes_edge_kind.py | 1/1 |
| D5 | bookkeeping | docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1–4 | integration | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_deletes_edge_kind.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/328-deletes-edge-kind

Ran at PLACEHOLDER

```
$ .venv/bin/python -m pytest tests/test_deletes_edge_kind.py -q
5 passed
```

## Phase 4 — Review

REVIEWER: OFF · CHALLENGER: ON — CLEAN 12/0/0.

## Phase 5 — Finalise (learning loop)

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger round 1`
