---
id: 385
slug: route-table-as-data
title: 'A URL a tester reports cannot be asked about: a dispatcher route resolved at runtime has no subject in the graph'
phase: 2
milestone: Coverage
status: deferred
depends_on: []
---

**Deferred 2026-10-10 — evidence gate:** the motivating consumer already resolves URLs with its own measured route table, outside the graph, at no measured cost. Reopen when a consumer shows that a route subject is needed *inside* a graph answer (`impact` or `trace_capability`), not only as a lookup.

## Why this exists

Bug reports and test docs name **what the user did**: a URL (`index.php?module=orders&action=edit`),
a CLI command, a message type. A front-controller dispatcher maps that key to a handler at runtime
from request input, so the graph has no edge and no subject for it: `trace_capability` takes a
`qname`, a `path` or a `module`, never a route.

`keyed_calls` with `key_pattern` (361, `docs/TOOLS.md` §"Indirection rule files") covers a route
**spelled as a literal inside the code**. It cannot cover a route that only exists in the request,
which is the common case for front controllers (`$_GET['action']`, `argv[1]`, a queue message's
type field).

Many repos already hold the mapping as data — a route census measured by crawling the running app,
a framework's route dump. The anchor repo keeps one as a TSV and resolves URLs through its own
script, re-implementing outside the graph what a route subject would answer inside it. The table
stays in the consuming repo; code-atlas only reads it through the rule file the repo points at.

## Scope

1. A new indirection rule kind, data not adapter code (PLAN §1 non-goals): `routes`, a list of
   `{key, target}` where `key` is a route string or pattern (query-string keys order-insensitive)
   and `target` is a stored qname or a File. Loadable from JSON, and from a TSV via a named column
   map so a measured route census can be used as is.
2. Each route becomes an `Entry` subject with a `HEURISTIC` `ROUTES_TO` edge to its target (it is
   declared, not resolved) carrying `rule: true`.
3. `trace_capability` and `impact` accept `route` as a subject; `search_symbol` finds routes by
   key. An unmatched URL answers `no_such_symbol` with the nearest declared keys, not an empty list.
4. Build report counts `routes_unresolved` (a target naming no indexed symbol), like
   `rule_keys_unresolved`.

## Assumptions to prove at design

- Whether a route is a node or only a lookup table in front of existing subjects; a node makes it
  show up in `impact` answers ("which routes does this change reach"), which is the stronger case.
- Matching rule for query strings: which keys are significant (`module`, `action`) and which are
  noise (paging flags, ids) must be declared in the rule, not guessed.

## Acceptance criteria

- **AC1:** a fixture front controller with a two-row route TSV answers `trace_capability(route=...)`
  with a path starting at the declared target, tier `HEURISTIC`, `rule: true`.
- **AC2:** `impact` on the target's file lists the route among what it reaches.
- **AC3:** a route naming a missing target is counted in `routes_unresolved` and produces no edge.
- **AC4:** with no `routes` rule configured, `trace_capability(route=...)` answers
  `capability_not_configured`, not an empty result.
