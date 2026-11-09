---
id: 448
slug: exec-target-casefold
title: "An `EXEC` target links case-insensitively, and its misses are counted"
phase: 2
milestone: "Round-3 field gaps"
status: todo
depends_on: [386]
---

## Why this exists

The follow-up 386 left: a host-string or T-SQL `EXEC` matches its procedure case-sensitively, so
`exec insert_order` misses `Insert_Order`, and the miss is never counted. Round-3 field feedback hit
it in the last week: `find_callers` on a procedure answered `no_matches` while one T-SQL caller
spelled it lowercase with no schema. T-SQL resolves routine names case-insensitively under the
default collation, so this is the language standard, not one repo's habit (R2).

`resolver.py` already has a casefold pass for writes and column reads (`_link_writes_casefold`);
`_link_by_unique_function` (bare `EXEC`) does an exact match only.

## Scope

1. A bare or schema-qualified `EXEC` target from SQL, or from a host string the SQL literal scanner
   reads, that misses exactly falls back to a casefold match against `Function` nodes of the SQL
   language. One distinct qname links at the incoming tier; two or more stays unlinked.
2. An `EXEC` naming a procedure in a schema other than `dbo` resolves in that schema first, then
   casefold, as today's `dbo` default does.
3. Unlinked `EXEC` targets are counted per build (`exec_unresolved`) in the build report and
   `get_index_status`, beside the existing `routes_unresolved`.

## Out of scope

A Python `dbo.py` module's function named like a procedure stays an exact match (386); casefold is
for SQL targets only.

## Acceptance

- Fixture: `exec insert_order` from T-SQL and from a PHP string both link to `dbo.Insert_Order`.
- Fixture: `Insert_Order` in two schemas, called bare → unlinked, counted, no guess.
- `find_callers dbo.Insert_Order` lists both callers; contract unchanged (resolver only), so no
  rebuild is forced — say so in the CHANGELOG.
