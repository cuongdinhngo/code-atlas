---
id: 224
slug: foreign-key-is-discarded-by-the-column-reader-so-no-table-relates-to-any-other
title: '`readColumnDef` returns null for every `FOREIGN KEY` entry and has no field to put an inline `REFERENCES` in, so a schema of 452 procedures and their tables carries not one relationship between two tables — while `REFERENCES` already sits in `EDGE_KINDS` and `FQN_EDGE_KINDS`'
phase: 1.5b
milestone: Comprehension
status: todo
depends_on: [022, 184, 144, 011]
---

## Why this exists

022 gave the graph `Table` and `Column` nodes and the `WRITES` edge, and the T-SQL adapter's own
comment states the budget it kept to: *"the vocabulary spend stays at Table + Column + WRITES"*
(`adapters/sql/src/scan.js:126`). The consequence was not spelled out anywhere: **nothing in the
graph relates one table to another.** A reader asking the first question anyone asks of a database —
*what joins to what* — gets nothing, and no honest-zero vocabulary covers it either, because the
relation is not modelled at all.

**Both spellings of a foreign key are structurally unrepresentable today, for two different
reasons.** Verified by reading the parser:

| Spelling | What happens | Where |
|---|---|---|
| `FOREIGN KEY (x) REFERENCES T(y)` as a table-level entry | `readColumnDef` reads the first identifier, finds `foreign` in `NOT_A_COLUMN`, and **returns `null`**; `readColumns` drops nulls. The entry is discarded whole. | `ddl.js:124`, `ddl.js:173-182` |
| `CONSTRAINT fk_x FOREIGN KEY …` | same path — first identifier is `constraint`, also in `NOT_A_COLUMN` | `ddl.js:9-11` |
| inline `x int REFERENCES T(y)` | `readColumnDef` reads name, then type, then calls `readDefault(rest)`. `references` is in `AFTER_DEFAULT`, so the token only **terminates a DEFAULT expression** and is never captured. The return shape is `{name, dataType, dflt}` — there is no field it could go in. | `ddl.js:17`, `ddl.js:121-139` |

**`NOT_A_COLUMN` is right and is not what this ticket disputes.** Its job is to stop a table-level
constraint being read as a column, and it does that correctly — the fix is a second reader for the
entries it rejects, not a change to the rejection.

**The cheap part, which is why this is worth doing now.** `REFERENCES` is **already** in
`EDGE_KINDS` and already in `FQN_EDGE_KINDS` (`contract.py:63`, `:74`), so the resolver looks it up
by FQN with no opt-in needed. A column qname is already `dbo.Trans::ChangeUser` — `Table` keeps its
native separator and `Column` joins on with `MEMBER_SEPARATOR`, exactly as a property does. **So a
Column → Column foreign-key edge needs no `CONTRACT_VERSION` bump and no schema change** (R3): it is
existing vocabulary reaching a pair of node kinds that already exist.

## Scope

1. **Read both FK spellings in the SQL adapter.** A table-level reader for the entries
   `readColumnDef` rejects, and a field on the column reader for the inline clause. Each yields
   `(from_table, from_columns, to_table, to_columns)` as written.
2. **Emit `REFERENCES` edges, Column → Column**, one per column pair, `RESOLVED` — the target is a
   declaration the parser read, not a string it guessed. A composite key is *n* edges, not one.
   Where the referenced column list is omitted (`REFERENCES T` naming the PK implicitly), the target
   is the **Table** at `HEURISTIC`, on the same reasoning `WRITES` already uses for a write that
   names no columns: the target kind carries what is known, and the tier says how sure the target is.
3. **Render an ER view from those edges** — `Table` boxes, `CONTAINS` columns, `REFERENCES` between
   them. The pattern to copy is `class_diagram.py`: a deterministic renderer plus a
   `validate_mermaid_*` guard, no LLM, no language branch. Mermaid's `erDiagram` is the target
   grammar; the artifact wiring is `artifact.py`'s existing diagram sections.
4. **Say what the view omits.** A capped or truncated diagram discloses it rather than reading as
   complete — 108/124 already set that rule for the layer diagram, and it binds here.

**Not in scope:** `READS` (`SELECT … FROM` / `JOIN` emit no edge; a separate ticket, and it is
inference over statements rather than a declaration the parser can read). Inferring a relationship
from a *naming convention* — `MemberID` in two tables is not evidence, and R5.2 forbids linking a
guess as `RESOLVED`. Any other adapter: this is T-SQL DDL.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A fixture carrying all three spellings — table-level
  `FOREIGN KEY`, `CONSTRAINT … FOREIGN KEY`, inline `REFERENCES` — asserts **zero** `REFERENCES`
  edges against today's adapter before the change. Without that row the ticket cannot show it fixed
  anything.
- **AC2** Each spelling produces the same edge set, because they declare the same fact. A composite
  key produces one edge per column pair; an implicit target produces one `HEURISTIC` Table edge.
- **AC3** `CONTRACT_VERSION` and `SCHEMA_VERSION` are **unchanged**, and the conformance suite is
  green. A proposal that needs either is wrong about what already exists (R3).
- **AC4** `readColumns` still returns exactly today's columns for every existing fixture — the
  table-level reader must not leak a constraint into the column list, which is what `NOT_A_COLUMN`
  was protecting. Pinned by the pre-change fixtures, byte-identical (R4.2).
- **AC5** The ER view renders from the graph alone, deterministically, and states its cap. Identical
  input yields byte-identical mermaid (R4.2).

## Exclusions

- **E1** The claim *"a real schema has no table relationships in the graph"* is measurable only on a
  corpus with a `CREATE TABLE` tree. On this checkout the artifact is the fixture proof of AC1 plus
  the recorded method; say so rather than quoting a corpus number that was never measured (the
  standing `real_corpus_path` gap, escalated at 209).
- **E2** The ER view's usefulness at scale is unproven here. A 400-table schema rendered whole is
  unreadable, so the cap and its disclosure are load-bearing, not a detail — but choosing the
  default cap needs a real schema, and E1 applies to it.

## Notes

**The gap this closes is stated in [`design/storage.md`](../design/storage.md)** under *What the
schema cannot express*, which is where a reader now learns the relation is missing.

**Why the ER view is the reason to do the edges, not a bonus.** Onboarding renders three diagram
kinds today — the layer flowchart (143), `classDiagram` (144) and the flows `flowchart LR` (197) —
and all three describe *code*. For a repository whose centre of gravity is a database, none of them
draws the thing the reader came for. The field report that produced 221-223 was written against
exactly that shape of project.

**Ordering against 222.** Independent — 222 links a PHP call site to a procedure; this links a
column to a column. They meet only in a later view that walks route → controller → procedure →
table, which is worth stating as the destination but is not a dependency in either direction.
