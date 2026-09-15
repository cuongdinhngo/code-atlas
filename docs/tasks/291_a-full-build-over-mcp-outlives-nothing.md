---
id: 291
slug: a-full-build-over-mcp-outlives-nothing
title: '201 built a `mode: refused` + route because a rebuild must not start "inside a call that cannot outlive its client", and gated it on `contract_rebuild_required` alone — so the one call that provably cannot finish, an explicit `build_or_update_index(full=true)` on a large repo, runs in-band to a client timeout that reports `failed` while the build keeps going, and a session that believes the report throws away an almost-complete index'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [201, 177, 072]
---

## Why this exists (field retro — the anchor repo, 2026-09-15)

Three full rebuilds over two days, none finished, and the retro names the transport as the reason the
loop repeated rather than the reason it was slow:

> *"The MCP client timeout is **5400 s (90 min)** and a cold full build here needs *more* than that, so
> a build launched through `build_or_update_index` **can never report success** — the client gives up
> mid-`resolve` and reports `failed`, even though the server-side build keeps running. Restarting on
> that 'failure' throws away a near-complete build. That is what happened repeatedly."*

It names the consequence as the costliest thing in the whole episode:
*"This is the single behaviour that wasted the most time."*

The reasoning the tool already carries is exactly right and is applied to the wrong case. Its docstring
(`build_or_update_index.py:96-101`) says a refusal exists *"rather than silently starting an hour-long
rebuild inside a call that cannot outlive its client"* — and the gate is
`if not (full or rebuilt_schema or allow_full_rebuild) and contract_rebuild_required(store)`
(`:213`). So the refusal fires for an **incremental** request that would secretly escalate, and never
for a caller who asks for the hour-long rebuild outright. `full=true` over MCP is the case the
sentence describes, and it is the one case excluded from it.

Two facts make this worse than a slow call. The build runs in the server process's worker thread, so
the client's timeout does **not** stop it — the work continues, unattributed, while the caller is told
`failed`. And a `failed` that is indistinguishable from a real failure invites the restart, which is
what discards the work. This is the empty-vs-unmeasured shape (272/238) moved from a query payload to a
build: a refusal an agent can act on is worth more than an answer it cannot trust.

AGENTS.md and the runbook already send a human to `code-atlas-build` for this. The tool does not.

## Scope / Deliverables

- **An explicit full build over MCP is answered, not attempted.** Return the existing `mode: refused`
  shape with a reason of its own and the route that can serve it (the shell CLI), so the caller is
  never handed a timeout as a verdict. `allow_full_rebuild=true` stays the opt-in that runs it anyway —
  that parameter is exactly this decision, and 201 already shipped it.
- **Decide the gate on evidence, not on a constant.** Whether the refusal is unconditional for
  `full=true` or conditional on measured scale (index size, file count, the last build's duration if
  recorded) is the design call. Do not hard-code a wall-clock guess at a client's timeout — no server
  knows it.
- **Name what a timed-out build leaves behind.** The caller must be told the build continues
  server-side, and how to observe it (`--status`, `last_commit`), so "failed" cannot be read as
  "stopped".

## Constraints

- 061: an incremental call is byte-identical to today; `allow_full_rebuild=true` behaviour is unchanged.
- R6.7: one refusal shape. Reuse `_refused`/`_contract_refused`'s structure rather than inventing a
  second vocabulary for the same event.
- Do not invent a timeout number. The server cannot see the client's deadline, so the refusal is
  argued from scale or from policy, never from an assumed 5400 s.
- 072's parallel-agent recipe (`docs/runbooks/parallel-agents.md`) still holds — this must not make a legitimate scripted full build
  unreachable.
- R4.2: refusing changes no stored row.

## Acceptance criteria

- `build_or_update_index(full=true)` on an index meeting the gate returns `mode: refused` with a reason
  and the CLI route, and writes nothing.
- The same call with `allow_full_rebuild=true` runs the build, exactly as today.
- `full=false` on a current index is byte-identical to today.
- The refused payload says the shell route and how to observe a build in flight.
- 201's `contract_rebuild_required` refusal still fires on its own case.

## References
`code_atlas/tools/build_or_update_index.py:82-113,199-225,329-397`, `code_atlas/cli.py:80-96`,
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md),
[072](072_busy-build-hides-staleness.md).
Origin: field retro "index rebuild never finishes", Rec 2 / Rec 3, 2026-09-15.
