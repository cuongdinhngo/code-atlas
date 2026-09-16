---
id: 293
slug: the-dot-spelling-is-a-near-miss-in-every-language-that-is-not-php
title: '287 banded `Class::method` as a direct hit because it is the spelling every stack trace uses, but it keyed the band on `MEMBER_SEPARATOR in query` — so `Class.method`, the spelling every TypeScript, Python and Java stack trace uses, still falls to the substring band, and 249''s separator repair cannot reach it because that repair is gated on `no_matches`, the gate 287 already found unreachable'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [287, 249, 253]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

287 is right about the finding and half-right about the population. The argument it shipped on — *an
agent pastes the spelling its stack trace, its ticket and its code review use* — is not a PHP fact.
PHP writes that spelling `Class::method`; TypeScript, Python and Java write it `Class.method`. The
guard added at `code_atlas/store.py:395` is `contract.MEMBER_SEPARATOR.casefold() not in q: return
False`, so only the PHP spelling reaches the boundary-suffix band.

Measured against the shipped predicate:

```
is_direct_match('Class::method', 'method', 'App\Svc\Class::method')      -> True
is_direct_match('Class.method',  'method', 'src/svc.ts::Class::method')  -> False
is_direct_match('Class.method',  'method', 'pkg/mod.py::Class::method')  -> False
```

The three qnames are the same shape; the three queries are the same *intent*. Two of them answer
`reason: substring_match` and rank below every trigram neighbour, which is the payload 287 exists to
stop an agent reading as "not really this one".

249's `member_separator_variant` already knows the variant spellings (`contract.py:288-302`) and
`search_symbol` calls it — but only in the `no_matches` branch (`tools/search_symbol.py:283`). A
`Class.method` query on a TS repo *has* hits; it is the substring band that is wrong, not the count.
That is the same reasoning 287 recorded for `::`, applied to the adapters that shipped after it.

## Scope / Deliverables

- **One definition site, extended** (R6.7): `is_direct_match` tries `contract.member_separator_variant`
  on a query that carries no `MEMBER_SEPARATOR`, and bands a boundary-suffix variant exactly as 287
  bands the direct spelling. `search_symbol`'s `reason` and the ordering band stay one decision.
- **No language branch** (R1.1): the variant alphabet is contract data (`_CONTAINER_SEPARATORS`, `member_separator_variant`), never
  a per-language rule and never a lookup of the subject's language.
- **The payload says which spelling matched.** A hit reached through a variant keeps 249's near-miss
  vocabulary in `reason`; banding must not silently claim the query was spelled as stored.

## Constraints

- **Byte-identical where nothing changes** (061 / R5.6): a query with no separator of any kind, and a
  query already carrying `::`, produce the same rows in the same order as today.
- **287's boundary rule is reused, not re-derived** — the character before the suffix must be a
  namespace/path separator, so `Foo_EntityPlan.getItem` is not a direct match for
  `EntityPlan::getItem`. `_` is an identifier character.
- The predicate runs as a SQLite UDF per candidate row; the variant is computed once per query, never
  per row.

## Acceptance criteria

- `is_direct_match('Class.method', 'method', 'src/svc.ts::Class::method')` is `True`, and the same for
  the `pkg/mod.py::Class::method` and PHP forms above.
- A TS fixture search for `UserService.getUser` returns the method in the direct band with a `reason`
  that names the separator variant, not `substring_match`.
- The underscore case stays `False`, pinned by its own test.
- A search that matched nothing before still matches nothing, and the 249 `no_matches` repair path is
  unchanged.

## References
`code_atlas/store.py:380-400`, `code_atlas/contract.py:288-302`,
`code_atlas/tools/search_symbol.py:283-295`,
[287](287_the-spelling-every-stack-trace-uses-is-a-near-miss.md),
[249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md).
