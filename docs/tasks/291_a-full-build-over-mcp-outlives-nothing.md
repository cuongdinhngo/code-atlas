---
id: 291
slug: a-full-build-over-mcp-outlives-nothing
title: '201 built a `mode: refused` + route because a rebuild must not start "inside a call that cannot outlive its client", and gated it on `contract_rebuild_required` alone — so the one call that provably cannot finish, an explicit `build_or_update_index(full=true)` on a large repo, runs in-band to a client timeout that reports `failed` while the build keeps going, and a session that believes the report throws away an almost-complete index'
phase: 1.5b
milestone: Agent-trust
status: done
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


## Decision — gate (HOW, cited)

**Refuse `full=true` over MCP when the index already has `last_commit`**, unless
`allow_full_rebuild=true` or a schema-older rebuild is already in flight. First builds (no
`last_commit`) and the shell route (`allow_full_rebuild=True` always) stay reachable (072).
Policy, not a wall-clock guess at the client's timeout (Constraints: "Do not invent a timeout
number" / Scope bullet 2).

## References
`code_atlas/tools/build_or_update_index.py:82-113,199-225,329-397`, `code_atlas/cli.py:80-96`,
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md),
[072](072_busy-build-hides-staleness.md).
Origin: field retro "index rebuild never finishes", Rec 2 / Rec 3, 2026-09-15.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 291 — refuse full over MCP (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket
- **Current phase:** finalise
- **Session status:** autorun — reviewer off; challenger CLEAN

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: refuse full=true when last_commit is set unless allow_full_rebuild or schema rebuild — cites Scope bullet 1–2 and Constraints (no invented timeout; 072 shell still opts in).

## Requirements matrix

`SECTIONS: 6 found (Why · Scope · Constraints · Acceptance · Decision · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | full over MCP times out | refuse with shell route | D1 | AC1 | ✅ |
| C1 | Constraints | 061 incremental | full=false unchanged | D1 | AC3 | ✅ |
| C2 | Constraints | R6.7 one refusal shape | reuse refused fields | D1 | AC1 | ✅ |
| C3 | Constraints | no timeout number | policy on last_commit | D1 | AC1 | ✅ |
| C4 | Constraints | 072 shell reachable | allow_full_rebuild / CLI | D1 | AC2 | ✅ |
| R1 | Scope | answer not attempt | _full_mcp_refused | D1 | AC1 | ✅ |
| R2 | Scope | decide gate | Decision section | D3 | AC1 | ✅ |
| R3 | Scope | name continues + observe | hint + --status | D1 | AC4 | ✅ |
| AC1 | AC | refused + route + no write | proving | D2 | proving | ✅ |
| AC2 | AC | allow_full_rebuild runs | proving | D2 | proving | ✅ |
| AC3 | AC | incremental identical | proving | D2 | proving | ✅ |
| AC4 | AC | shell + observe named | proving | D2 | proving | ✅ |
| AC5 | AC | 201 still fires | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: refusal gated only on secret escalation; explicit full=true excluded.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — 061 ✅ · R6.7 ✅`

Ran at ba1c70489fa9febb61f5fa0733d93d3f785f3e90

```
$ .venv/bin/python -m pytest tests/test_contract_rebuild_refusal.py -q --tb=no
..........                                                               [100%]
10 passed in 3.00s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: refuse full+last_commit without allow_full_rebuild; same refused shape + hint.
- Rejected: unconditional refuse (breaks first-build seeds); invent 5400s threshold.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_full_mcp_rebuild_refusal.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | refuse gate + payload | build_or_update_index.py, indexer.py | MCP full | 1/1 |
| D2 | proving | tests/test_full_mcp_rebuild_refusal.py | — | 1/1 |
| D3 | Decision record | docs/tasks/291_*.md | ticket | 1/1 |

## Phase 3 — Execute

**Branch:** feat/291-refuse-full-rebuild-over-mcp
**Axis 1:** build tool · proving · decision.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at ba1c70489fa9febb61f5fa0733d93d3f785f3e90

```
$ .venv/bin/python -m pytest tests/test_full_mcp_rebuild_refusal.py tests/test_contract_rebuild_refusal.py -q --tb=no
..............                                                           [100%]
14 passed in 4.49s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (hint omitted last_commit); fixed; round-2 CLEAN. agents ce6e1a36 / 69cd81c2-56a7-4538-96e2-548a4dbc509b

Ran at ba1c70489fa9febb61f5fa0733d93d3f785f3e90

```
$ .venv/bin/python -m pytest tests/test_full_mcp_rebuild_refusal.py -q --tb=no
....                                                                     [100%]
4 passed in 2.41s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_full_mcp_rebuild_refusal.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN
PR: https://github.com/cuongdinhngo/code-atlas/pull/385

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
