# Design — observing fit locally (task 260)

> Part of code-atlas's **design record**. Read this **before** quoting any number from the local
> fit counter. The founding benchmark figure in [PLAN §19](../PLAN.md#19-project-context--decision-log)
> is a different measurement; do not treat the two as interchangeable.

## What fit means here

**Fit** is the share of *relationship* questions that reached the graph, against a search/grep
proxy — **not** “every tool call, divided”.

| Bucket | Tools counted in the ratio |
|---|---|
| Relationship (numerator) | `find_callers`, `impact`, `impact_modules`, `explain_path` |
| Search/grep proxy (denominator peer) | `search_symbol` (in-server). External `grep` is not visible to a local counter. |

Every registered tool except `get_index_status` increments a local meta row of shape
`(tool, reason, authoritative, truncated)` — counts only, no qname/path/argument values (R4).
The **ratio** for product decisions uses only the buckets above.

Two shapes to expect when reading the rows: a tool with no `reason` field (a build, a report)
counts under the **empty** reason rather than an invented one; and `get_index_status` never
appears, because the tool that *reports* the counter must not move it between two identical
calls (R4.2). It is in neither bucket above, so the ratio is unaffected.

## What this counter does *not* support

PLAN §19's founding figure — the agent reached for the index in **22 of 117 tool calls (19%)** —
aggregates *all* calls in one mixed session ([PLAN §19](../PLAN.md#19-project-context--decision-log)).
A counter that aggregates relationship-vs-proxy produces a number that **cannot be compared** to
that 19%. Use the local ratio to watch relationship demand vs search proxy over time; use a fresh
all-calls benchmark if you need a figure comparable to 19%.

## Where to read and reset

- **Read:** `get_index_status(detail_level="verbose")` → `fit_counts` (omitted on minimal/standard).
- **Reset:** `get_index_status(reset_fit_counts=true)` (works at any detail level; clears `fit:` meta rows).

Local counts live in `graph.db` meta. They are not telemetry (no network). They must not enter
determinism-compared nav payloads and must not feed retrieval ranking.
