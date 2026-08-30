# T-SQL adapter (tier 1a)

Parses Transact-SQL into the code-atlas contract vocabulary. Self-contained: its runtime lives here
and never reaches the Python core (R8.1). Task 184.

## Runtime

- **Node.js ≥ 18.** That is the whole runtime — the scanner has **zero production dependencies**.
  `typescript` and `@types/node` are dev-only, for the R6.6 analyser.

Parsing is a **streaming DDL/`EXEC` scanner**, not a parser building a syntax tree. `fs.readSync`
fills a fixed 64 KB buffer and lines are handed off as they complete, so peak memory is flat in file
bytes. That is a requirement, not an optimisation: the anchor's normal shape is one ~240k-line file,
and building a whole-file tree over it is the failure mode the PHP adapter already has.

## What tier 1a emits

| Construct | Emitted as |
|---|---|
| `CREATE`/`ALTER`/`CREATE OR ALTER` `PROC`/`PROCEDURE` | `Function` node |
| `CREATE`/`ALTER`/`CREATE OR ALTER` `FUNCTION` | `Function` node |
| `EXEC` / `EXECUTE <name>` | bare `CALLS` edge at `RESOLVED` |
| `EXEC (@sql)`, `EXEC @var`, `sp_executesql` | `CALLS` edge at **`DYNAMIC`**, target `(dynamic)` |

**Nothing else.** `CREATE VIEW`, `CREATE TRIGGER`, `CREATE TABLE` and the PHP↔SQL crossing are out of
scope — see the task for the tier split and why each waits.

A dynamic call site is **emitted, never dropped and never `RESOLVED`**: the call happened, and what
an unlinkable edge means is the core's decision, not the adapter's (R3.3).

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
