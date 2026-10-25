---
id: 412
slug: records-direct-first
title: "`impact` records reached through a hub file drown the records about the subject itself"
phase: 2
milestone: Trust
status: todo
depends_on: [407]
---

## Why this exists

A consumer's survey, 2026-10-25. `impact` on one save controller answered `records_total: 179`. All of
them came `via` the front-controller file, a hub that dispatches hundreds of routes. Only about 11
records named the controller's own symbols, and records about unrelated screens came first.

On `main`, `impact` builds its carriers in this order: walk seeds, the radius in walk order, then
files (`impact.py:286-293`). `records.attached` keeps each record under its first carrier and then
truncates at `page_limit` (`impact.py:294-297`). A record on a *member* of the seed sits wherever that
member falls in the radius, so a hub reached early can fill the page before it.

## Scope

1. Every record row carries `distance` (hops from the seed) and `direct: true|false`, beside the
   existing `via`. *Direct* means the record is attached to the seed, to a symbol the seed contains,
   or to the seed's own file. Design confirms that definition.
2. Rows are ordered direct first, then by distance, then as today.
3. Two new parameters on the tools that return records: `records: "direct" | "radius"` (default
   `radius`) and `records_limit`.
4. A `stop_at` list of globs in the `records` block. A file it matches carries no records into an
   answer whose seed is somewhere else. Its own `impact` still lists them.
5. Update the user docs for the records rule and the tools affected.

Out of scope: auto-flagging hubs by record fan-in. Revisit only if `stop_at` proves insufficient.

## Acceptance criteria

- **AC1:** In a fixture, a hub file carries 50 records and a leaf it reaches carries 2. `impact(leaf)`
  lists the 2 first, each `direct: true`.
- **AC2:** With `stop_at` covering the hub, none of the hub's 50 records is in that answer.
- **AC3:** With `records: "direct"`, exactly the 2 are returned.
- **AC4:** A caller passing neither parameter gets the same *set* of records as before, with the added
  fields.
