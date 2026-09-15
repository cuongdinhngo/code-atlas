---
id: 285
slug: a-class-hit-omits-the-one-fact-that-decides-whether-its-callers-typecheck
title: '`read_symbol` stamps `params` on a callable and `columns` on a Table, but a `Class` hit carries neither its declared `implements`/`extends` nor a route to `find_implementations` — so on a repo of partial ports, "the port took the methods and dropped the interface" is invisible at the one call an agent makes before trusting the class, and shipped as a production `TypeError`'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [242, 248, 158]
---

## Why this exists (field retro — the anchor repo, round 26 §6 / §9, 2026-09-15)

A ported class kept its static helper and lost its `implements` clause. Its consumer's constructor is
typed on the interface, so the call raised a `TypeError` at runtime — behind an early return, and
therefore invisible until an unrelated fix made the path reachable. Every gate was green.

The retro does not blame the tool; it blames the prompt it never wrote:

> *"`read_symbol` on the class would have shown `class ServiceViewFile {` with no `implements`.
> `find_implementations` on the interface — a tool in the roster I did not call once all session —
> would have listed the views and omitted this one. I never asked."*

The asymmetry is what makes this a payload ticket rather than a habit ticket. `read_symbol` already
stamps the adjacent structural fact for two other kinds — `params` on a callable (242) and a paged
`columns` list on a Table (248), each with an honest "not captured" spelling rather than an empty list
(`read_symbol.py:63-77`). A `Class` gets the body and nothing else, although the graph holds
`EXTENDS`/`IMPLEMENTS` as contract vocabulary (`contract.py:100`, `IMPL_KINDS`) and `find_implementations`
already walks them (`find_implementations.py:39-48`).

Round 25 §3 recorded why the adjacent field is worth more than the lookup it replaces: `params`
changed a fix *because it was next to what the session came for*, not because it was faster than
reading the signature. The same argument applies here, on a repo shape this project has indexed twice.

`attach_next_tools` (`nav_result.py:599-607`) is the second half: it is keyed on node kind and a
non-callable kind earns no field by design (158 / 061), so a `Class` read names no next step at all.

## Scope / Deliverables

- **A found `Class` at `standard` carries its declared supertypes** — the `EXTENDS`/`IMPLEMENTS`
  targets stored for that node, resolved qname where linked and the raw declared name where not, so an
  unresolved base is visible rather than dropped.
- **An honest negative, never an empty list.** A class that declares nothing says so; a language whose
  adapter does not emit `IMPL_KINDS` gets the `params_not_captured_by_adapter` treatment (242 / R5.6),
  not a list that reads as "implements nothing".
- **Route the follow-up.** Extend `attach_next_tools` so a `Class`/`Interface` hit names
  `find_implementations`, closing the loop the retro walked past.

## Constraints

- R1.1: keyed on contract node kinds and `IMPL_KINDS`, never on language.
- 061: `minimal` and every other kind stay byte-identical; no field where nothing is declared.
- R5.6: supertypes are stored edges, never re-parsed from the returned source at read time.
- R4.2: same index, same list, same order (declaration order, as `columns` is DDL order).

## Acceptance criteria

- A class declaring an interface and a base class lists both at `standard`; `minimal` omits them.
- A class declaring neither carries no field (061), and this is distinguishable from an adapter that
  does not emit `IMPL_KINDS`.
- A declared supertype the resolver could not link is still named, marked unresolved.
- A `Class` hit's `next_tool_suggestions` names `find_implementations`; a callable's is unchanged.
- A Table and a callable read byte-identically to today.

## References
`code_atlas/tools/read_symbol.py:63-77`, `code_atlas/contract.py:100` (`IMPL_KINDS`),
`code_atlas/tools/find_implementations.py:39-48`, `code_atlas/tools/nav_result.py:209,599-607`,
[242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md),
[248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md),
[158](158_routing-suggestions-fire-on-index-state-not-on-the-question.md).
Origin: field retro round 26 §6 / §9, 2026-09-15 — the round's single concrete ask.
