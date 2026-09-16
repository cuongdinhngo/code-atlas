---
id: 297
slug: the-member-demote-is-keyed-to-one-kind-so-a-class-still-buries-itself
title: '292 stopped a Table being crowded off page one by its own Columns by demoting, inside the band, any hit whose CONTAINS parent is also a hit — but the SQL it shipped tests `nodes.kind = COLUMN_KIND`, and the crowding is not a Column fact: a qualified query puts a Class and every one of its Methods in the same direct band, so the container an agent asked for still ranks behind its own members in php, typescript and python'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [292, 265, 245]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

292's mechanism is right and its key is narrow. `_search_contains_demote` (`code_atlas/store.py:410`)
builds an `ORDER BY` term reading `CASE WHEN nodes.kind = '{contract.COLUMN_KIND}' AND EXISTS (…
CONTAINS parent that is itself a direct match …)`, so it fires for Columns and for nothing else.

The band collision it fixes is a qname fact, not a Column fact. A member's qname is its container's
qname plus `MEMBER_SEPARATOR` plus its own name, so any query spelled as the container is a *prefix*
of every member's qname, and the prefix arm of `is_direct_match` puts them all in the direct band
together. Measured against the shipped predicate:

```
is_direct_match('App\UserService',          'getUser', 'App\UserService::getUser')          -> True
is_direct_match('src/user.ts::UserService', 'getUser', 'src/user.ts::UserService::getUser')  -> True
```

Both are the `dbo.Trans` / `dbo.Trans::ChangeUser` shape 292 was filed for, in the two adapters 292
does not cover. On a class with forty methods the class declaration is one row among forty-one in the
same band, ordered by whatever `_SEARCH_ORDER` decides — which is 265's tier order, not "the thing
that was asked for first". The cost is 245's shape: the agent pages, or re-asks with a narrower
query it had no reason to think it needed.

## Scope / Deliverables

- **Generalise the demote to containment, not kind:** any hit whose `CONTAINS` parent satisfies the
  same query, kind and namespace filters ranks after non-members within its band. The `COLUMN_KIND`
  literal goes; the parent-side filter parity 292 established stays exactly as it is.
- **One definition site** (R6.7) — the same ORDER BY term serves every kind, so Table/Column and
  Class/Method cannot drift apart.
- **No language branch** (R1.1): `CONTAINS` is contract vocabulary, and the fix must read no kind
  name that belongs to one adapter.

## Constraints

- **061 / byte-identical:** a hit set with no container/member pair in it produces the same order as
  today, and every SQL result 292 pinned stays pinned.
- The parent sub-select already costs one EXISTS per candidate row; generalising must not widen it —
  same index path, same filters, no second join.
- Band, mirror order and tier order (265 / 277) keep their precedence; this is a within-band tiebreak
  and stays one.

## Acceptance criteria

- A PHP fixture searching the qualified class name returns the `Class` row above its `Method` rows, and
  the same for a TypeScript and a Python fixture.
- 292's SQL tests pass unchanged, and a fixture with no container/member pair returns a byte-identical
  page.
- No `COLUMN_KIND` (or any other single kind) literal remains in the demote term.

## References
`code_atlas/store.py:407-445`, `:2514-2540`, `code_atlas/contract.py:243`,
[292](292_a-container-hit-is-crowded-out-by-its-members.md),
[265](265_the-default-page-order-is-the-alphabet.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).
