---
id: 321
slug: dynamic-ddl-in-migrations-leaves-no-trace
title: "A migration that alters a table through sp_executesql leaves no trace on that table, so \"has this object already been migrated?\" is unanswerable and duplicate migrations ship"
phase: 2
milestone: Coverage
status: done
depends_on: [022, 184, 296]
---

## Why this exists (field retro, 2026-09-22 — FIELD-1426/1013/1598 batch; second sighting)

An agent fixing FIELD-1013 searched `dbo.UserNotes`, got the `Table` and its `Column`s — including
`ChangeUser` / `ModifiedUser` — read the proc, confirmed the live DEFAULTs, and wrote migration
**V187** re-pointing them at `SESSION_CONTEXT('app_user')`. A human reviewer then found
`V128__field962_usernotes_author_session_context.sql`: **the byte-identical fix, merged 2026-09-14.**
V187 was deleted. The retro names `FIELD-1371/1438` as a prior instance of the same class, and calls
duplicate migrations "the most expensive DB mistake here".

**The graph could not have prevented it.** V128 re-points the DEFAULT with `ALTER TABLE … ` handed
to `sp_executesql` inside a cursor. The adapter reads that as a dynamic call — `CALLS` at `DYNAMIC`
onto `(dynamic)`, with `unmodelled_resolution: ["dynamic_sql"]` stamped on the File
(`adapters/sql/src/scan.js:255`, `:781`) — and the table name exists **only inside a string
literal**, so no edge reaches `dbo.UserNotes`. `search_symbol("UserNotes")` therefore shows the
table and its columns but not the migration that changes them. The static spelling is already
modelled (`ddl.js:523` reads `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr) FOR col`); it is the
dynamic one — *"the one a migration usually takes"*, as that function's own docstring says — that
vanishes.

**This is a relation, not a location**, which is the surviving product claim after the 2026-08-08
measurement ([PLAN §19](../PLAN.md#19-project-context--decision-log): *"What survives is
relationships, not locations"*). "Which migrations have altered this object" is not a grep for a
count — the honest answer needs the object resolved to its node and the alteration attributed to a
file, which is what the graph is for. The retro's own mitigation ("grep `database/migrations/`
before writing any migration") is a process workaround for a missing edge.

## Goal

From a `Table` / `Function` node, name the migration files that alter it through dynamic DDL —
low-confidence and marked as such — so "has this object already been migrated?" is a graph question
instead of a discipline question.

## Scope / Deliverables

1. **A new edge kind, not an overload of `WRITES`.** `WRITES` means *a routine assigns a column*
   (`contract.py:74`), and `check_column_defaults` counts exactly those edges as the table's
   **writers** (`check_column_defaults.py:58`). Emitting DDL as `WRITES` would enrol every migration
   as a writer that omits every column it does not name, corrupting 022's whole ratio. Add
   `ALTERS` to `EDGE_KINDS`, joined to `FQN_EDGE_KINDS` so the resolver looks the target up by FQN.
2. **Bump `CONTRACT_VERSION` 10 → 11 and extend `tests/contract/`** — a new word in the vocabulary
   is exactly what R3 gates. Adapters that never emit `ALTERS` stay conformant.
3. **Emit it from the SQL adapter, at `DYNAMIC` only.** Inside an `EXEC` / `sp_executesql` string
   argument, match `ALTER TABLE` / `DROP CONSTRAINT` / `ADD CONSTRAINT` / `CREATE OR ALTER` followed
   by an identifier, and emit `ALTERS` from the File to that name at `confidence_tier: DYNAMIC`. No
   control flow, no string concatenation resolution, no attempt at the column: a name-in-string
   match is the whole claim, and the tier says so.
4. **Read it back on the object.** A `Table` / `Function` answer that has inbound `ALTERS` discloses
   them — the file and line — under a field that names the tier, never mixed into a resolved list.
   The `search_symbol` hit is the natural site; the tool decision is the ticket's, not this file's.
5. **Static DDL joins the same relation.** `ALTER TABLE` read literally (`ddl.js:523` and the
   `ALTER … ADD` path at `scan.js:523`) emits `ALTERS` at `RESOLVED`, so the reader gets one
   question with two tiers rather than two half-answers.

## Constraints

- **R2 standard over sample** — the scan keys on T-SQL DDL keywords and `sp_executesql`, never on
  Flyway's `V<n>__` naming, a `database/migrations/` path, or any repo's layout. A migration corpus
  is where this pays off; it must not be what the adapter recognises.
- **R5.6** — a name found inside a string literal is never signed like a resolved edge; `DYNAMIC` is
  load-bearing and the reader must be able to separate the two.
- **R3** — vocabulary change ⇒ version bump ⇒ conformance tests, in the same commit.
- **R1.1 / R1.4** — the core reads `ALTERS` as one more contract kind; no language branch, no SQL
  outside `store.py`.
- Flat memory: the scanner is streaming with a fixed 64 KB buffer and a `PENDING_CAP`; the string
  match must not require buffering a whole statement (`scan.js:497`).
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** A fixture reproducing V128's shape — `ALTER TABLE … DEFAULT … FOR …` built into a variable
  and run through `sp_executesql` inside a cursor — yields an `ALTERS` edge from that file to
  `dbo.UserNotes` at `DYNAMIC`.
- **AC2** Asking about `dbo.UserNotes` names that file, marked as a dynamic-DDL claim, distinct
  from any resolved relation in the same payload.
- **AC3** A literal `ALTER TABLE dbo.X ADD …` yields `ALTERS` at `RESOLVED` onto the same node.
- **AC4** `check_column_defaults`' `writers_total` / `omitted_count` are unchanged by the presence of
  `ALTERS` edges — a red-arm test pins that DDL never counts as a writer.
- **AC5** `CONTRACT_VERSION` is 11, `tests/contract/` covers the new kind, and every existing adapter
  still passes conformance unchanged.
- **AC6** A string mentioning a table without a DDL verb (`'SELECT * FROM UserNotes'` in an `EXEC`)
  emits **no** `ALTERS` — the claim is "altered by", not "mentioned near".

## Out of scope

- Resolving what the dynamic DDL actually *does* (which column, which expression) — the value is
  "this file alters that object", and inventing the rest would be worse than an honest name (R5.6).
- Any Flyway-, migration-path- or version-ordering awareness; "has it already shipped" is the
  reader's inference from the files named, not the graph's claim.
- A `find_object_migrations` tool. The surface is 24 tools and count-pinned; this is an edge on
  existing tools, and a new verb needs its own evidence (R1.2).
- Dynamic DML (`INSERT`/`UPDATE` built in a string) — `WRITES` at `DYNAMIC` already covers the
  truncated case (`scan.js:503`); widening it is a separate question.

## References
`adapters/sql/src/scan.js:255` (`DYNAMIC_PROCS`), `:497-509` (`flush`, `PENDING_CAP`), `:523`
(`ALTER … ADD`), `:781` (`unmodelled_resolution`); `adapters/sql/src/ddl.js:523`
(`readNamedDefault`); `code_atlas/contract.py:29` (`CONTRACT_VERSION`), `:62-77` (`EDGE_KINDS`),
`:81` (`FQN_EDGE_KINDS`); `code_atlas/tools/check_column_defaults.py:58` (`_sources`);
[PLAN §19](../PLAN.md#19-project-context--decision-log) (2026-08-08 measurement);
[320](320_column-defaults-dead-ends-on-an-unqualified-table.md); ADAPTER_PLAYBOOK §1.
