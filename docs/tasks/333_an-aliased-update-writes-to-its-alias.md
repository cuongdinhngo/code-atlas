---
id: 333
slug: an-aliased-update-writes-to-its-alias
title: "UPDATE c SET … FROM dbo.T c emits WRITES onto the alias c, not dbo.T — the table's writer list and check_column_defaults lose every aliased update"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [278, 328]
---

## Why this exists (review of #451, 2026-09-25)

T-SQL's joined-update form names the **alias** after `UPDATE` and the table in the `FROM` clause.
`readUpdate` (`adapters/sql/src/ddl.js:497-520`) takes the first qualified name after `UPDATE` as the
table, so the statement below emits `WRITES` onto `c::ParentId` at `RESOLVED`:

```sql
UPDATE c SET ParentId = 1 FROM dbo.Child c JOIN dbo.Parent p ON p.Id = c.ParentId;
```

Probed on `main` after #452: `dbo.Alias_Upd c::ParentId 3 RESOLVED`; the plain form
`UPDATE dbo.Child SET …` emits `dbo.Child::ParentId` correctly. The aliased site is missing from
`find_references dbo.Child` and from `check_column_defaults`, and the edge claims `RESOLVED` for
a name that is not an object.

#451 fixed the same shape for `DELETE c FROM dbo.T c` with `deleteAliasTable` (`ddl.js`); the
UPDATE path was left out of that PR's scope.

## Goal

An aliased UPDATE writes to the table its alias names.

## Scope / Deliverables

1. **`readUpdate` resolves an alias** through the statement's `FROM` / `JOIN` sources, sharing one
   helper with `readDelete` (R6.7) — no second alias parser.
2. **Unresolvable alias** (no matching source) keeps today's target — never a guessed table.

## Constraints

- **R2.1** — T-SQL grammar only; no repo's table or procedure names.
- **R6.7** — one alias resolver for DELETE and UPDATE.
- **061** — a non-aliased UPDATE answers byte-identically.
- **R4.2** — identical input, identical rows.

## Acceptance criteria

- **AC1** `UPDATE c SET X = 1 FROM dbo.T c JOIN …` → `WRITES` onto `dbo.T::X`; red-arm on today's code.
- **AC2** `UPDATE t SET X = 1 FROM dbo.T AS t` (explicit `AS`) → the same.
- **AC3** `UPDATE dbo.T SET X = 1 WHERE …` is byte-identical (regression).

## Out of scope

- The loose statement classifier (`INSERT_RE` / `UPDATE_RE` match anywhere on a line) — a separate
  finding if a probe shows a false edge.

## References
`adapters/sql/src/ddl.js:497-520` (`readUpdate`), `deleteAliasTable` (328); `adapters/sql/src/scan.js`
statement flush; tickets 278, 328.
