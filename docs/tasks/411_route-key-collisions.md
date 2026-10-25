---
id: 411
slug: route-key-collisions
title: "Two declared routes that canonicalise to one key keep the first silently, so a URL traces to an unrelated handler"
phase: 2
milestone: Trust
status: todo
depends_on: [385, 397]
---

## Why this exists

A consumer's survey of real questions, 2026-10-25, on a legacy PHP monolith (about 12.9k files and
177k symbols). 154 declared routes of the form `/endpoint.php?cmd=X` canonicalised to a single key,
because `cmd` was not in the block's `significant` set. Every such URL traced to the same, wrong,
handler, and nothing said so. Of 1,029 declared rows, 834 were stored. The consumer could account for
153 of the 195 missing rows (the collapsed ones) but not for the other 42.

On `main`, `routes.resolve` skips a key it has already seen with no count (`routes.py:236-238`).
Rows whose target names nothing are counted as `routes_unresolved`, but only in the build report
(`enrichment.py:261`), never in `get_index_status`. A consumer that reads status cannot balance the
table.

`significant` is already per block (`routes.py:92`), so a path can get its own keys through a
separate `routes` block. The gap is that a collision is never reported, and a JSON or TSV census is
one block with one key set.

## Scope

1. At build, two declared rows that canonicalise to one key with **different** targets are a
   collision. Store them, and report them in `get_index_status` as a count plus the first N examples.
   Two rows with the same key and the same target are a duplicate, not a collision.
2. Every declared row that is not stored is counted by reason: unresolved, short-name tie (397),
   collision, duplicate. Report the counts in `get_index_status`, with examples.
3. `trace_capability(route=…)` on a colliding key answers with every candidate and an ambiguity flag.
   It never answers one handler. `impact(routes=…)` behaves the same way.
4. Let a census set its significant keys per path, as well as per block. Design picks the smallest
   form: a per-path map in the block, or a per-row column.
5. Update the user docs for the routes rule.

Out of scope: several handlers on one key *by design* (415 builds that on top of this).

## Acceptance criteria

- **AC1:** A fixture declares `/x.php?cmd=a` → `A::a` and `/x.php?cmd=b` → `B::b`, with `significant`
  excluding `cmd`. Status reports one collision, and tracing `/x.php?cmd=b` does not answer `A::a`
  alone. It answers both candidates, flagged ambiguous.
- **AC2:** With `cmd` significant for `/x.php`, both URLs resolve to their own handler and no collision
  is reported.
- **AC3:** For every fixture, declared = stored + Σ dropped-by-reason.
- **AC4:** A routes rule with no collisions answers exactly as before. Status only gains the new
  counts.
