---
id: 296
slug: the-sql-adapter-names-the-dynamic-procs-and-stamps-nothing
title: 'The T-SQL adapter already holds the set of procedures that execute a string as SQL, and uses it to mark the call `DYNAMIC` — the exact evidence 279 asks for, one level below the claim it protects — but it never stamps `unmodelled_resolution`, so a schema whose dispatch goes through `sp_executesql` still yields a confident orphan population'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [279, 184, 255, 299]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

**Blocked on [299](299_a-confident-hit-list-does-not-say-the-index-never-saw-this-extension.md).**
This stamp cannot see an extension the adapter never parsed. Run 299 first.

Of the three ports in this group this is the cheapest, because the detection already exists.
`DYNAMIC_PROCS` at `adapters/sql/src/scan.js:255` names `sp_executesql` and its siblings, and the
`EXEC` scan marks a call dynamic when the target is a variable or a parenthesised expression
(`scan.js:711`, `:720-723`). The adapter therefore already knows, per file, that some execution in it
resolves at runtime — and does nothing with the fact above the edge.

279's mechanism is language-agnostic and waiting: `File.extra.unmodelled_resolution` unioned per
language (`store.py:1252`), stamped into `meta` (`indexer.py:1273`), read by `find_orphans`
(`tools/find_orphans.py:82-95`). Only `adapters/php/src/Visitor.php:1341` sets it.

A dynamic-SQL schema is the strongest case of the three: a procedure called only by name assembled at
runtime has *no* inbound edge anywhere in the graph, so it is not merely under-linked, it is
indistinguishable from dead code. That is the shape 279's Why argues an agent must never be handed as
a bare population.

## Scope / Deliverables

- **A strategy token in `contract.py`** naming string-executed SQL (`dynamic_sql`), beside
  `RESOLUTION_AUTOLOAD`.
- **The stamp, from evidence the scan already produces** — the existing `DYNAMIC_PROCS` hit and the
  variable/parenthesised `EXEC` target. No new parsing, no new regex, no procedure-name list beyond
  the T-SQL standard set already there.
- **The File-node `extra` merge** in the SQL adapter's node emission, sorted and de-duplicated.
- **A gate-1 fixture** with an `EXEC(@sql)` and an `sp_executesql` call, and one without.

## Constraints

- R5.6: the stamp says the population is unmeasured; it never claims a target.
- R1.1: core change limited to the token constant.
- 061: a schema with no dynamic execution is byte-identical, including the `meta` stamp being absent.
- The per-edge `DYNAMIC` confidence tier stays exactly as it is — this adds a file-level fact, it does
  not reinterpret an edge.

## Acceptance criteria

- A T-SQL fixture executing `@sql` stamps `unmodelled_resolution: ["dynamic_sql"]`; a static fixture
  stamps nothing.
- `find_orphans` over the stamped fixture answers `status=resolution_unmodelled`; over the static one
  its payload is unchanged.
- No edge kind, confidence tier or node kind changes.

## References
`adapters/sql/src/scan.js:255`, `:711`, `:720-723`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[184](184_tsql-source-adapter-tier-1a.md).
