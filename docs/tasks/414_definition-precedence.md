---
id: 414
slug: definition-precedence
title: "A table defined in a schema project and again in migrations answers `subject_ambiguous` to `read_symbol` and `impact`"
phase: 2
milestone: Retrieval
status: todo
depends_on: [403, 407]
---

## Why this exists

A consumer's survey, 2026-10-25. One central table had 8 definitions: a schema project plus several
migration files. Every table question came back `subject_ambiguous`, so the agent could not read the
table or its blast radius in one call. This was already a BACKLOG follow-up: *"`impact` on a table
defined in several files walks nothing … 403's fix covers `read_symbol` on routines"*.

403 resolves the case where every definition is a *versioned migration* redefinition: the highest
version answers (`symbol_pointers.py:131-166`). A schema project beside migrations is not ordered by
any standard, so only the project can say which definition is authoritative (R2).

## Scope

1. A project-declared definition precedence: an ordered list of path globs. Design picks where it
   lives, either the indirection rules file or the project config.
2. With it, `read_symbol` and `impact` answer from the preferred definition, and list the others as
   `other_definitions` (path and line). This mirrors 394 and 403's lists.
3. References, readers and writers are aggregated across every definition of the object. First
   measure whether they already are: edges that target the qname may need no change.
4. Without the setting, behaviour does not change. 403's migration ordering still applies.
5. Update the user docs.

## Acceptance criteria

- **AC1:** A fixture table is defined in `schema/t.sql` and `migrations/V2__t.sql`, with precedence
  `["schema/**"]`. `read_symbol` returns the schema definition plus one `other_definitions` entry.
- **AC2:** `impact` on that table walks its readers and writers. `find_references` lists writers found
  against either definition.
- **AC3:** Without the precedence, the answer is `subject_ambiguous`, as today.
