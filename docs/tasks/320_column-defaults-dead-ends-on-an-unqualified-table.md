---
id: 320
slug: column-defaults-dead-ends-on-an-unqualified-table
title: "check_column_defaults answers a bare table name with a dead-end no_such_symbol — the exact-qname partition 165-C1 already ruled on, and the one tool where the bare name is what a caller types"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [194, 022]
---

## Why this exists (field retro, 2026-09-22 — FIELD-891/1583/1611 batch)

A field session asked `check_column_defaults` whether `FormInstance.Status` / `ModifiedDate`
declared a DEFAULT. It answered **`no_such_symbol`, empty** — and the agent concluded the tool
"can't reach the schema because the DDL lives in migration `.sql`", rated it **3/10**, and answered
the question with raw `sys.columns` / `sys.default_constraints` queries instead. The defaults
existed (`DEFAULT((1))` / `DEFAULT(getdate())`).

**That diagnosis was wrong, and the payload is why it was reachable.** The SQL adapter does index
this DDL: `CREATE TABLE` and `ALTER TABLE … ADD` emit `Table` + `Column` on `CONTAINS`, and both
DEFAULT spellings are parsed — the inline clause and `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr)
FOR col` (`adapters/sql/src/ddl.js:424`, `:523`). What failed is the **lookup**: the tool does one
exact `nodes_by_qualified_name(table, kind="Table")` (`check_column_defaults.py:198`), and a SQL
qname is schema-qualified and file-independent by CONVENTION §3 — so the bare `FormInstance`
can never match the stored `dbo.FormInstance`.

**The repo has already ruled on this shape.** Claim `165-C1` (`LESSONS.md:807`,
`disclose-a-partition-as-a-partition`): *"a tool answer scoped to one qname is a partition when the
subject shares its identity slot with definitions under other qnames; disclose the siblings and mark
the answer `authoritative: false` rather than presenting the partition as the whole."* It was closed
in `find_callers` by adding a `nodes_by_name` sibling query beside the exact one
(`nav_result.attach_sibling_definitions:929`). `check_column_defaults` never received the same
treatment, and its envelope (`:139-157`) carries **no** `try_instead`, no candidate list, no hint
that the name wants a schema — unlike `search_symbol`, which routes a near-miss to `file_outline`,
and `read_symbol`, which refuses ambiguity with `ambiguous_definitions` (070/078). This is the
second sighting of `165-C1`, which is the promotion gate (P1).

It matters disproportionately here because this is the one tool whose subject a caller types from a
**database** mental model, where the bare table name is the name — not from a symbol the index
already handed them.

## Goal

A bare, unqualified table name reaches the table it plainly names, or is refused with the qualified
candidates that would reach it — never a bare `no_such_symbol` that reads as "this table does not
exist".

## Scope / Deliverables

1. **A name fallback beside the exact lookup** in `check_column_defaults.create` — when
   `nodes_by_qualified_name(table, kind="Table")` misses, query `nodes_by_names(table,
   kind="Table")`. Contract-kind branch only; no language branch (R1.1).
2. **One candidate → answer about it, and say so.** Report the resolved `qualified_name` in the
   envelope (the subject the answer is about is not the string that was passed), so a reader never
   has to assume which table was measured. The `column` argument composes against the **resolved**
   qname, not the raw one (`f"{table}::{column}"` at `:208`).
3. **Two or more candidates → refuse and list them**, following `read_symbol`'s 078 precedent: no
   rows, and `ambiguous_definitions` naming each qualified candidate — one schema's table must not
   be measured while the others go unmentioned.
4. **Zero candidates → keep `no_such_symbol`, but stop the dead end.** Attach `try_instead`
   pointing at `search_symbol(kind="Table")`, the way a `substring_match` page already routes to
   `file_outline` (245/093).

## Constraints

- **061** — a call that already resolves exactly stays byte-identical; the new fields ride only the
  fallback, ambiguous and empty arms.
- **R5.6** — a resolved-by-fallback answer must be distinguishable from an exact hit; do not sign
  them alike.
- **R1.1** — the fallback keys on `kind="Table"`, never on a language or a schema-name convention.
- **R1.4** — the name query goes through `GraphStore`; no SQL in the tool.
- **R4.2** — candidate order is deterministic.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** `check_column_defaults(table="FormInstance")` against a fixture holding
  `dbo.FormInstance` returns that table's defaulted columns, and the envelope names the
  resolved qualified subject.
- **AC2** With the same bare name held by two schemas, the call returns **no rows** and lists both
  qualified candidates — a red-arm test proves one schema's answer is never returned alone.
- **AC3** A genuinely absent table still answers `no_such_symbol`, now carrying `try_instead`.
- **AC4** Regression: an exactly-qualified call's payload is byte-identical to today's (061).
- **AC5** `LESSONS.md` claim `165-C1` gains this incident on its `seen:` line — the gate P1 reads.

## Out of scope

- Indexing anything new; the DDL is already indexed and this ticket touches no adapter.
- Dynamic DDL inside `EXEC` / `sp_executesql` — that is genuinely unreadable here and is
  [321](321_dynamic-ddl-in-migrations-leaves-no-trace.md).
- Extending the fallback to other tools; do it when a second tool is sighted, not before (R1.2).

## References
`code_atlas/tools/check_column_defaults.py:198` (exact lookup), `:139-157` (envelope), `:208`
(column composition); `code_atlas/store.py:1671` (`nodes_by_qualified_name`), `:1677`
(`nodes_by_names`); `code_atlas/tools/nav_result.py:929` (`attach_sibling_definitions`);
`adapters/sql/src/ddl.js:424`, `:523`; `docs/LESSONS.md:807` (claim `165-C1`);
`tests/test_check_column_defaults.py`; CONVENTION §3; AGENT_BRIEF P1.
