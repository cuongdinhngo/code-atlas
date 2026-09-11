---
id: 247
slug: the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key
title: 'The SQL column reader keeps a column''s type and DEFAULT and discards its nullability, IDENTITY and PRIMARY KEY — so the first question anyone asks of a schema has no answer at any price'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [022, 228, 239]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 17)

A consuming agent graded the round **6.5/10** and named one dimension as the whole of the gap:
symbol questions were answered well and honestly, schema questions were not answered at all. The
single most-repeated question of the review — *"what type is this column, and does this table have a
single-column integer primary key?"* — was asked about ten tables, roughly six times, and code-atlas
answered it **zero times**. All of it went by `grep` over DDL.

The retro's reading of why was that the data is in the index and no tool opens a door to it. That is
half right, and the half that is wrong is this ticket. **Type is captured. Nullability, IDENTITY and
PRIMARY KEY are never parsed**, so no read path could surface them however it were written.

Measured on the anchor index (read-only) — 20,808 `Column` nodes, 20,000 sampled:

```
extra keys across 20,000 Column nodes:
  data_type  19,979
  type       19,979
  default     6,975
  (nothing else)
```

Three keys. No `nullable`, no `identity`, no `primary_key`, no ordinal.

**A verification pass on 2026-09-11 found two more losses in the same reader**, both of which remove
the fallbacks a consumer would otherwise use to recover declaration order:

```
tables whose columns ALL share one line_start:  1348 / 1548
  dbo.ContractAssets   585 cols, 1 distinct line (13)
  dbo.AwardStructure     173 cols, 1 distinct line (13)
  dbo.Member_Site       316 cols, 8 distinct lines    <- multi-statement ALTER, not per-column
```

Every column of a `CREATE TABLE` is emitted at the line of the `CREATE` statement itself, so a
`Column` node's position is its table's position. And `_NODE_ORDER` is
`qualified_name, file_path, line_start, id` (`store.py:169`), so `file_outline` returns a table's
columns **alphabetically** — correct and R4.2-deterministic, but it means neither the line nor the
row order carries the DDL's column order. A consuming agent confirmed both in the field: *"the order
returned is alphabetical, not declaration order — I have no way to know the real column order. And
all 7 columns report line_start: 13, the same line as the Table node, so the position is meaningless
too."* Declaration order is currently **unrecoverable from the index at any price**, which also makes
a primary-key ordinal unverifiable against it.

## Root cause

`readColumnDef` (`adapters/sql/src/ddl.js:140`) reads exactly four things out of a column
definition: the name, the data type (with its size parens), the `DEFAULT` expression, and an inline
`REFERENCES` clause. Everything else in the T-SQL `column_definition` grammar — `NULL` / `NOT NULL`,
`IDENTITY(seed, increment)`, an inline `PRIMARY KEY`, `UNIQUE`, `ROWGUIDCOL` — is read only as a
boundary marker for the `DEFAULT` expression (`AFTER_DEFAULT`, `ddl.js:22-26`) and then dropped.

The table-level declaration is worse than unmodelled: it is **deliberately discarded**. `NOT_A_COLUMN`
(`ddl.js:10-12`) makes `readColumnDef` return `null` for any entry whose first word is `primary`,
`unique`, `foreign`, `constraint`, `key` or `index`. That guard is correct — those entries are not
columns — but nothing else reads them, so `PRIMARY KEY ([ID] ASC)` is parsed, recognised, and thrown
away. The composite/single distinction the retro asked for lives entirely in the list that guard
drops.

`scan.js:517` is the second loss: `for (const col of ddl.readColumns(body.body)) column(qname, col, line)`
passes **one** `line` — the `CREATE` statement's — for every column in the body. `readColumns`
(`ddl.js:295`) splits the body on top-level commas and never tracks an offset, so the per-column line
is not available to pass.

This is not a `get_index_status` honesty defect. The `sql` stamp declares `declared_types: true`,
which is true — `data_type` is captured. There is no flag claiming the other three, so nothing
lied; the capability simply does not exist.

## Scope

Extend the T-SQL DDL reader to capture, on each `Column` node's `extra`:

1. **`nullable`** — from an explicit `NULL` / `NOT NULL` in the column definition. Absent when the
   definition states neither: SQL Server's default nullability depends on session settings
   (`ANSI_NULL_DFLT_ON`) that no static reader can know, so an omitted clause must stay **omitted**,
   never defaulted to `true` (R5.6 — an unmeasured thing is not a value).
2. **`identity`** — presence, plus seed and increment when the DDL gives them.
3. **Primary-key membership and ordinal** — from *both* spellings: the inline `PRIMARY KEY` on a
   column definition, and the table-level `PRIMARY KEY (c1, c2, …)` / `CONSTRAINT x PRIMARY KEY (…)`
   entry that `NOT_A_COLUMN` currently drops. The ordinal is what makes a single-column key
   distinguishable from the first column of a composite one.
4. **A declaration ordinal**, and a real `line_start` per column. The ordinal is the durable answer
   (it survives reformatting and is what a PK ordinal is checked against); the line is what makes
   `read_symbol` on a column able to point at the column. `readColumns` must track an offset through
   the body split to produce either.
5. The same for `ALTER TABLE … ADD CONSTRAINT … PRIMARY KEY (…)`, which is how a large share of real
   schemas declare the key — `scan.js:529` already routes `ALTER` through `readColumnDef`.

## Constraints

- **R2 — standard over sample.** Encode the T-SQL `column_definition` and `table_constraint` grammar,
  not the shape of any one repo's tables. The anchor index is the measurement, never the spec.
- **No `CONTRACT_VERSION` bump.** These are `extra` keys, and `extra` is the free-form seam 236 used
  for the same reason (`contract.py`: the FK's child/referenced tables ride `extra` "since
  NODE_FIELDS is frozen"). No kind moves and no qname changes, so R3.1's trigger does not fire.
  A full rebuild is still needed to populate the new keys on an existing index — state that in the
  ticket's close-out rather than letting a reader assume incremental pickup.
- **Dialect honesty (228).** The SQL adapter owns every `.sql` file and reads one dialect. A MySQL
  or Postgres `AUTO_INCREMENT` / `GENERATED … AS IDENTITY` is not T-SQL `IDENTITY`; capture what the
  reader actually understands and leave the rest absent rather than guessing a cross-dialect mapping.
- **Omit-when-absent (061).** A column whose DDL declares none of these carries none of these keys.
  No `nullable: null`, no `identity: false` on every column in the graph.

## Acceptance criteria

- **AC1** A `CREATE TABLE` with `[ID] int IDENTITY(1,1) NOT NULL PRIMARY KEY` yields one `Column`
  node carrying nullability, identity (seed 1, increment 1) and a primary-key ordinal of 1.
- **AC2** A table-level `CONSTRAINT PK_x PRIMARY KEY ([A] ASC, [B] ASC)` marks exactly `A` and `B`
  with ordinals 1 and 2, and marks no other column. The `NOT_A_COLUMN` guard still emits no `Column`
  node for the constraint entry itself.
- **AC3** `ALTER TABLE … ADD CONSTRAINT … PRIMARY KEY` reaches the same nodes as AC2, including when
  the `ALTER` is in a different file from the `CREATE`.
- **AC4** A column definition stating neither `NULL` nor `NOT NULL` carries **no** `nullable` key.
- **AC5** Each column of a multi-column `CREATE TABLE` carries its own `line_start` — pointing at its
  own definition, not the `CREATE` line — and a declaration ordinal that reproduces the DDL order
  independently of the alphabetical `_NODE_ORDER`.
- **AC6** Every existing `Column` assertion in `tests/contract/` and the SQL adapter suite still
  passes unchanged — this adds keys, it moves none.
- **AC7** A repo with no SQL adapter sees byte-identical rows from every tool (the 022 AC3 shape).

## References

- `adapters/sql/src/ddl.js:10-12` (`NOT_A_COLUMN`), `:22-26` (`AFTER_DEFAULT`), `:140-165`
  (`readColumnDef`).
- `adapters/sql/src/scan.js:415-431` (`Column` node emission), `:517` (one `line` for every column
  in a body), `:529` (`ALTER` path); `ddl.js:295` (`readColumns`, no offset tracking).
- `code_atlas/store.py:169` (`_NODE_ORDER`) — why row order cannot stand in for declaration order.
- [239](239_a-column-row-cannot-name-what-it-points-at.md) — the same shape one step earlier: the
  fact was in the graph and the row could not carry it. Here the fact is not in the graph at all.
- [228](228_the-sql-adapter-owns-every-sql-file-but-reads-one-dialect-and-says-nothing.md) — the
  dialect boundary this must not quietly cross.
- [248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md) — the read path that
  consumes these facts. Useless without this ticket for three of the four.
