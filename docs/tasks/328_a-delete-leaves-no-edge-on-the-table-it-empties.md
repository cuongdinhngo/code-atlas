---
id: 328
slug: a-delete-leaves-no-edge-on-the-table-it-empties
title: "The SQL adapter emits WRITES for INSERT and UPDATE only — a DELETE, MERGE or TRUNCATE leaves no edge, so 'what removes rows from this table' has no answer in any language"
phase: 1.5b
milestone: Coverage
status: todo
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
