# T-SQL adapter (tier 1a + tier 2)

Parses Transact-SQL into the code-atlas contract vocabulary. Self-contained: its runtime lives here
and never reaches the Python core (R8.1). Tasks 184 (tier 1a) and 022 (tier 2). Every `File` node
carries `extra.dialect = "tsql"` so a reader of the index sees which dialect was read (task 228) —
`META_FIELDS` is frozen, so the handshake stays `name: "sql"`.

Reserved words are refused as object names only when written **bare**: delimiting is SQL's own way
to name an object after a keyword, so `CREATE TABLE [dbo].[Key]` is a real table and `readIdent`
carries a `delimited` flag for the refusal to read.

## Runtime

- **Node.js ≥ 18.** That is the whole runtime — the scanner has **zero production dependencies**.
  `typescript` and `@types/node` are dev-only, for the R6.6 analyser.

Parsing is a **streaming DDL/`EXEC` scanner**, not a parser building a syntax tree. `fs.readSync`
fills a fixed 64 KB buffer and lines are handed off as they complete, so peak memory is flat in file
bytes. That is a requirement, not an optimisation: the anchor's normal shape is one ~240k-line file,
and building a whole-file tree over it is the failure mode the PHP adapter already has.

## What it emits

| Construct | Emitted as | Tier |
|---|---|---|
| `CREATE`/`ALTER`/`CREATE OR ALTER` `PROC`/`PROCEDURE`, `FUNCTION` | `Function` node | 1a |
| `EXEC` / `EXECUTE <name>` | bare `CALLS` edge at `RESOLVED` | 1a |
| `EXEC (@sql)`, `EXEC @var`, `sp_executesql` | `CALLS` edge at **`DYNAMIC`**, target `(dynamic)` | 1a |
| `CREATE TABLE`, `ALTER TABLE … ADD <col>` | `Table` + `Column` nodes on `CONTAINS` | 2 |
| a column's `DEFAULT`, either spelling | `Column.extra.default` | 2 |
| `INSERT` / `UPDATE` naming columns | `WRITES` edge per column | 2 |
| `INSERT` / `UPDATE` naming none | one `WRITES` edge onto the **`Table`** | 2 |
| `DELETE` / `TRUNCATE` / `MERGE…DELETE` | one `DELETES` edge onto the **`Table`** | 2 |
| `UPDATE c …` / `DELETE c …` `FROM dbo.T c` (an alias) | the edge lands on the top-level `FROM` / `JOIN` source `dbo.T`; a subquery's own `c` never shadows it (328, 333) | 2 |
| `CREATE`/`ALTER`/`CREATE OR ALTER` `TRIGGER` | `Function` node, `extra.object_type = "trigger"` | 2 |
| literal `ALTER TABLE` | `ALTERS` edge from the file onto the `Table` at `RESOLVED` (321) | 2 |
| `ALTER TABLE` or `(CREATE OR) ALTER PROC`/`FUNCTION`/`TRIGGER` inside a string an `EXEC` / `sp_executesql` runs | `ALTERS` edge at **`DYNAMIC`** — a name read from a string, a claim, never a fact (321) | 2 |
| standalone `ALTER TABLE … ADD … FOREIGN KEY` | `ForeignKey` node, `CONTAINS`-owned by its table (`extra`: `parent_table`, `referenced_table`, `columns`) | 2 |

A foreign key declared **inside a `CREATE TABLE` body** stays a `REFERENCES` edge (task 224); a
**standalone `ALTER … ADD … FOREIGN KEY`** (the `_fk_constraints.sql` shape) is a `ForeignKey` node
(task 236), so a table's DDL site and a constraint on it never collide as two `Table` rows.

**Nothing else.** `CREATE VIEW`, `MERGE`, and the PHP↔SQL crossing are out of scope — see the task
for the tier split and why each waits. A `MERGE` writes nothing the graph records; it is a feature
bound, deliberately not a silent partial answer.

A dynamic call site is **emitted, never dropped and never `RESOLVED`**: the call happened, and what
an unlinkable edge means is the core's decision, not the adapter's (R3.3).

### Two things tier 2 records rather than guesses

- **A writer that names no columns** — `INSERT INTO t SELECT …` — writes the `Table`, not each of
  its columns. The **target kind** carries that distinction, so *"which writers omit column C"* can
  separate an omitter from a writer it simply cannot measure (R5.6). The confidence tier is left to
  say what it is for: how sure the adapter is of the target.
- **A `DEFAULT` holding a string literal.** The scanner drops literal bodies so a keyword inside one
  is never read as code; a dropped body leaves `'…'`, so `DEFAULT ''` (a genuinely empty default)
  and `DEFAULT 'N'` (elided) stay distinguishable.

Both `DEFAULT` spellings reach the same `Column`: inline (`ChangeUser varchar(50) DEFAULT
(user_name())`) and the named constraint a migration usually writes (`ALTER TABLE t ADD CONSTRAINT
DF_x DEFAULT (…) FOR ChangeUser`) — one column node, filled in by whichever arrives.

## Qualified names

A SQL object's qname is **schema-qualified and file-independent** — `dbo.Insert_AC_Trans_v1` — because
the database, not the file, is its container (CONVENTION §3). That is what lets an `EXEC` in one file
link to a procedure declared in another. Delimiters are dropped, so `[dbo].[My Proc]`, `"dbo"."My Proc"`
and `dbo.[My Proc]` are one name. An unqualified `EXEC Foo` stays `Foo`: the default schema is a server
setting, not a fact in the file, and inventing `dbo.` would be a guess.

## Static analysis (R6.6)

`npm run check` runs `tsc --checkJs` at **full `strict`, `noImplicitAny` included**. Unlike the TS
adapter (task 150), this source carries JSDoc types from its first commit, so there is no untyped
legacy to defer and no flag held off. No baseline, no `@ts-nocheck`, no suppression.

## Protocol

`node index.js --server` announces the adapter once, then answers one `\n`-framed JSON request per
line (§4.1). `node index.js --file <path>` answers once and exits — the one-shot mode the conformance
suite drives.
