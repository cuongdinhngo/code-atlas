---
id: 228
slug: the-sql-adapter-owns-every-sql-file-but-reads-one-dialect-and-says-nothing
title: 'The adapter announces `name: "sql"` and claims every `.sql` file but reads only T-SQL spellings, so on a PostgreSQL schema it reports `parsed_ok` for 36/36 files while publishing a table called `IF`, a column called `COLUMN`, and 48 of the repo''s 52 tables not at all — `readQualified` takes the token after `CREATE TABLE` as the name and nothing refuses a reserved word'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [022, 184, 224]
---

## Why this exists

A field build over a 1,209-file AWS Lambda repo with an Aurora **PostgreSQL** schema returned
`parsed_ok` for all 36 `.sql` files and 127 `Table` nodes. The repo declares **52** tables. The
graph is not incomplete — it is **wrong**, in three separate places, and every one of them is
`RESOLVED` tier.

Reproduced whole in six lines through `adapters/sql/index.js --file`:

```sql
CREATE TABLE IF NOT EXISTS m_tenants (
    tenant_id UUID PRIMARY KEY,
    tenant_code VARCHAR(20) NOT NULL
);
ALTER TABLE m_tenants ADD COLUMN nickname VARCHAR(50);
CREATE OR REPLACE FUNCTION gen_uuidv7() RETURNS uuid AS $$ BEGIN RETURN NULL; END; $$ LANGUAGE plpgsql;
```
```
NODE  Table  'IF'                   line 1
NODE  Table  'm_tenants'            line 5     <- the ALTER, not the CREATE
NODE  Column 'm_tenants::COLUMN'    line 5
```

| Spelling | What happens | Where |
|---|---|---|
| `CREATE TABLE IF NOT EXISTS t (…)` | `TABLE_RE` matches, then `readQualified` reads the **next identifier** — `IF`. `readParens` then looks for `(` after `IF`, finds `NOT`, returns null, so **every column is lost**. All 48 baseline tables collapse onto one node named `IF`. | `scan.js:269-271`, `scan.js:279-280` |
| `ALTER TABLE t ADD COLUMN c type` | the `add` arm calls `readColumnDef("COLUMN c type")`; `column` is not in `NOT_A_COLUMN`, so the **keyword becomes the column name** and `c` becomes its data type. | `scan.js:284-288`, `ddl.js:9-11`, `ddl.js:121-124` |
| `CREATE OR REPLACE FUNCTION f()` | `CREATE_RE` spells the alternation `(?:or\s+alter\s+)?`, so `OR REPLACE` does not match and **no node is emitted**. | `scan.js:116-117` |

**The tables that do appear are attributed to the wrong statement.** `m_tenants` is defined at
`001_baseline_schema.sql:38` and the graph places it at `:1005` — the `ALTER TABLE m_tenants DROP
CONSTRAINT …` that runs 967 lines later. `read_symbol` on that table opens a foreign-key statement.

**Two of the three spellings are the majority spelling, not an exotic one.** `IF NOT EXISTS` and
`ADD COLUMN` are accepted by PostgreSQL, MySQL, MariaDB and SQLite; T-SQL is the outlier that omits
both. So this is not "add a dialect" — it is a reader that assumes one engine's phrasing of three
very common statements while its handshake claims all of them.

**Nothing in any payload discloses the dialect.** `index.js:11-15` announces `name: "sql"`,
`extensions: [".sql"]`; only `adapters/sql/README.md:1` says *"T-SQL adapter"*, and a reader of the
index never sees it. `emitted_kinds_by_language` for this build reads `{"sql": ["CONTAINS",
"WRITES"]}` — no `CALLS`, no `Function` — which is the shape of an adapter that read nothing, stated
in a field no answer carries.

## Scope

1. **Refuse a reserved word as an object name.** A `Table` or `Column` whose name is `if`, `not`,
   `exists`, `column`, `constraint`, `table` or `key` is never a real name in any dialect. Emit
   nothing rather than a wrong node (R5.2 — absence is honest, a wrong `RESOLVED` node is not).
   `NOT_A_COLUMN` (`ddl.js:9-11`) is the existing seam for exactly this and needs `column` added.
2. **Skip the optional clauses before the name.** `IF NOT EXISTS` after `CREATE TABLE`, and the
   `COLUMN` keyword after `ADD` — two token skips in the readers that already run, no new reader.
3. **Accept `CREATE OR REPLACE`** alongside `CREATE OR ALTER` in `CREATE_RE` and `TRIGGER_RE`.
4. **Prefer the defining statement for a table's site.** A `CREATE TABLE` must win over an
   `ALTER TABLE` for `line_start`, whichever the scanner reaches first. Today `table()`
   (`scan.js:183-191`) keeps the first sighting unconditionally.
5. **Say which dialect was read.** The adapter knows what it does and does not parse; the index does
   not. Publish it — a `dialect` (or equivalent) note the index can carry, so a PostgreSQL or MySQL
   repo learns from the payload rather than from a README it never opens. **The shape is this
   ticket's to decide and justify**; what is not optional is that the claim stops being silent.

**Not in scope:** full PostgreSQL support — `CREATE POLICY` (105 in this repo), `CREATE INDEX` (94),
`$$`-quoted function bodies, `plpgsql` and MySQL backtick quoting are each their own decision. This
ticket makes the reader stop publishing falsehoods and stop hiding what it skipped; it does not
promise a second dialect.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** The six-line fixture above, as a test, asserts
  today's output: `Table IF`, `Column m_tenants::COLUMN`, no function node, `m_tenants` at the ALTER
  line. Without the red row nothing shows the change did anything.
- **AC2** After the change that fixture yields `Table m_tenants` at **line 1** with columns
  `tenant_id`, `tenant_code` and `nickname`, and a `Function gen_uuidv7`.
- **AC3** No node is emitted whose name is a reserved word, on any input — proven on a fixture that
  the readers cannot parse at all, where the correct output is *nothing*, not a guess.
- **AC4** Every existing T-SQL fixture is byte-identical (R4.2). The T-SQL spellings 022/184 shipped
  are the regression surface and none of them moves.
- **AC5** The dialect claim reaches a payload a working reader sees, and a `.sql` file the adapter
  cannot read no longer reports success indistinguishable from a file it read completely.

## Exclusions

- **E1** The 36-file / 127-node measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture, which reproduces all three
  defects on six lines of standard PostgreSQL. `cross_repo_samples.json` pins no non-T-SQL sample.

## Notes

**224 is a no-op on this corpus until this lands.** 224 adds `REFERENCES` between columns from
`FOREIGN KEY` clauses; on a schema whose 48 `CREATE TABLE` statements produce zero columns there is
nothing for it to relate. The two are independent changes to the same file and 228 is the
prerequisite for 224 being measurable outside T-SQL.

**Why `parsed_ok` is the sharpest part.** 221 exists because a zero and an unmeasured were
indistinguishable in an *answer*. This is the same failure one layer earlier, in the *build*: a file
the adapter structurally could not read is reported exactly like one it read completely, and the
resulting graph then answers confidently from it. An operator has no signal at any point in the
chain.
