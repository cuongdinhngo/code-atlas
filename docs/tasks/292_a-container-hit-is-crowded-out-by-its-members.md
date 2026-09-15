---
id: 292
slug: a-container-hit-is-crowded-out-by-its-members
title: 'An exact-name hit on a container and a substring hit on the members it contains sit in the same ranking bands, so searching a stored procedure or a table by name returns its own definitions first and then forty of its columns — and on a subject with more members than the page holds, the real answers are truncated away by rows the caller did not ask for'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [265, 277, 245]
---

## Why this exists (field retros — the anchor repo, rounds 16 and 22, 2026-09-15 / 2026-09-14)

Two rounds, two languages, one shape.

Round 16 searched a stored-procedure name: 86 hits, **truncated at the page limit**, and the page was
*"dominated by `#UpdateRecursiveUntilTemp::<column>` rows"*. The procedure's real definitions — the
function node, the file node, the `_beta` twin, three migration copies — were there, and then roughly
forty temp-table **columns** sharing the substring pushed the answer past the page. The retro's verdict:

> *"A `search_symbol` for a procedure name should not return 40 temp-table columns ahead of the
> procedure's own definitions, and should not truncate the real answers at a page limit because of
> them."*

Round 22 §5 logged the same thing on a Table and generalised it: *"When a Table matches exactly, its
columns are rarely what the caller wants."*

The ordering is working as designed and the design has a blind spot. `is_direct_match`
(`store.py:379-391`) bands exact-and-prefix ahead of near-misses over the whole result set (180/167),
and relevance breaks ties inside a band. A column's qname contains its container's name, so
`Container::col_1 … col_40` are all legitimate substring hits — and where the container name is also a
*prefix* of them, they land in the **same** band as the container's own definitions, ranked on
relevance alone. Nothing in the order knows that a column is a *member of the thing asked for* rather
than a competing answer to it.

This is 277's argument applied to containment instead of mirroring: the graph already holds the
relation that decides the order (`CONTAINS`), and the ranking does not read it. It is also 245's
failure mode with the sign flipped — there a truncated near-miss answer had no route; here a truncated
answer is *caused* by rows the caller did not ask for, so a route is not the fix, the order is.

Out of scope, deliberately: a query that is a bare **class** name wanting one of its methods
(round 26 §3). That is a correct near-miss with a correct route — the payload already says
`try_instead: file_outline` — and widening this ticket to cover it would change a working answer.

## Scope / Deliverables

- **A container's own definitions outrank its members** for a query that names the container, using
  the stored `CONTAINS` relation rather than a name-shape heuristic. Members stay in the answer; they
  stop displacing it.
- **Truncation must not be caused by members.** A page that had to drop real hits to make room for
  contained rows is the failure; whether that is fixed by order alone or needs the count reported
  separately is the design call.
- **Decide the scope by kind, once.** Table/Column is the clearest case and Procedure/Function the one
  the field hit; pick the rule from contract vocabulary (R1.1), never per language.

## Constraints

- R1.1: the rule keys on node kinds and `CONTAINS`, never on a language or a naming convention.
- R6.7 / 167: the exactness band stays one predicate. This ticket adds an ordering input, it does not
  fork the band definition.
- 061: a query whose hits contain no container/member pair is byte-identical to today, `reason`
  included.
- R4.2: deterministic order; ties resolve as they do now.
- Do not drop members from the result — the round-22 note is that they are *rarely* wanted, not never.
- Leave 277's mirror ordering and 265's tier-first default intact; this composes with them.

## Acceptance criteria

- An exact-name query on a Table returns the Table before its columns.
- The same query on a Procedure/Function returns its definitions (and its indexed twins) before rows
  merely contained by a same-named object.
- A subject whose members exceed the page no longer truncates a real definition away.
- A query with no container/member relation among its hits is byte-identical to today.
- 277's mirror-order and 265's ordering tests still pass.

## References
`code_atlas/store.py:379-396`, `code_atlas/tools/search_symbol.py:116-128`,
`code_atlas/contract.py:98-104` (`CLASS_MEMBER_KINDS`, `CONTAINS`),
[265](265_the-default-page-order-is-the-alphabet.md),
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).
Origin: field retro round 16 §1.2 / §3, 2026-09-15, and round 22 §5, 2026-09-14 — two rounds, same shape.
