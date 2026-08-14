---
id: 096
slug: edit-then-ask-tax-two-files-cost-a-minute
title: 'A 2-file incremental costs 59 s while a no-op costs 2 s — the tax that keeps the graph out of the work'
phase: 1.5b
milestone: Cost
status: todo
depends_on: [080, 052, 016]
---

## Goal
[080](080_noop-incremental-cost-and-uninterpretable-writes.md) landed and the field confirms it
exactly: a no-op incremental went from 56.1 s to **2.113 s** (~26×), `wrote.edges` from 6,071 to
**0**, two consecutive no-ops byte-identical. 080 named the general small-delta case as an explicit
follow-up. This is that follow-up, and round 5 measured its shape:

| files changed | seconds |
|---|---|
| 0 | 2.113 / 2.106 |
| 2 | **59.25** |
| 14 | 61.6 |

**The cliff is entirely between zero and one**, and above one the size of the delta barely matters.
080 removed the idle-poll tax and left the edit-then-ask tax untouched — and the edit-then-ask tax is
the one an agent actually pays, because it is levied exactly when the agent has just written code and
wants to ask about it.

## Why this is a behaviour ticket, not a performance ticket
Round 5 is the first round to show cost changing *what the agent asked*, not just what it paid:

- 16 code-atlas calls in a ~5 hour session: **8 in the opening analysis, 7 in the closing review, 1
  build in between** (§6). Across roughly three hours of actual porting the graph was asked nothing.
- The evaluator's own explanation: *"I batched my questions into two clusters because each refresh
  cost a minute, and batching is why I asked the graph nothing during the three hours when I was
  actually writing the code it could have checked."*
- One of the things it could have checked in that window was the closure count it was deriving by
  hand — the miscount that shipped into a committed comment and cost a second commit on an open PR
  (§8, §11.3).
- In-work build time: **181.7 s for 35 changed files** — roughly two orders of magnitude more wall
  clock than the session's entire code-atlas token cost (~3,050 tokens, well under 1 %).

Retro §11.7: *"If the goal is for the graph to be consulted during work rather than around it, the
sub-minute incremental for small deltas is the enabling change, not a nice-to-have."*

## Scope / Deliverables
- **Profile a small nonempty delta on a large index** and name the dominant phase, the way 052 did
  for the no-op. 080's analysis already points at full-graph `resolve_edges` / enrichment running
  regardless of delta size — confirm or refute with a phase breakdown before designing anything.
- **Scope the late writers to the delta.** 080's rejected alternative ("delta-scope `resolve_edges`
  for all incrementals, persist resolved state") is this ticket's likely core. It needs **new schema
  or persisted resolver state** — treat the schema decision as the ticket's main design question, not
  an implementation detail.
- **Set a target and state it as a target, not a hope.** Design must name the seconds a 1–5 file
  delta should cost on the anchor scale and what phase floor makes that achievable.
- **Prove correctness, not just speed.** A delta-scoped resolve must produce a graph
  byte-identical to the full-resolve path for the same tree (R4) — that equivalence is the proving
  test, and it is worth more than the timing.
- **Re-measure in the field.** Anchor-repo before/after seconds for 0 / 2 / 14 / ~273-file deltas,
  recorded here. 080's precedent applies: the operator's anchor numbers are a **confirming follow-up,
  not a merge gate** (ASSUMED-A) — the fixture proof ships with the fix.

## Constraints
- R4 — determinism is the gate: identical input must produce identical rows whichever path computed
  them. A delta-scoped resolver that drifts from the full resolver is worse than a slow one.
- R3 / schema — a persisted-resolver-state schema bump needs the mismatch-recovery path (050) to
  handle it, and the migration verdict must be written down.
- R1.1 — no language branch; resolution scoping is core mechanics.
- Full builds stay untouched (080's boundary).
- Do not absorb 080's no-op guard — it landed, it works, and this ticket must not regress it. A no-op
  must still cost ~2 s and report `wrote.edges: 0` after this change.

## Acceptance criteria
- A phase profile of a small nonempty delta on a large synthetic index is recorded in this ticket.
- A fixture test proves the delta-scoped path and the full path produce identical graph rows for the
  same tree.
- A no-op incremental still short-circuits: `wrote.edges: 0`, two runs identical (080's ACs re-run
  green).
- Anchor before/after seconds for 0 / 2 / 14 / large deltas are recorded as the confirming follow-up.
- If the schema route is rejected in design, the ticket records the rejected alternative and what the
  achievable floor is without it.

## References
Field retro round 5 §6 (required 080 measurement table), §11.7, §1 (call distribution); candidate 5.
Related: [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the no-op fix; this is its
named follow-up — see its ASSUMED-B and rejected alternatives),
[052](052_incremental-noop-cost.md) (the original profile + `scripts/profile_incremental.py`),
[053](053_refresh-on-checkout-hook.md) (inherits any floor), [016](016_incremental-git.md),
[061](061_payload-weight.md) (the standing rule that cost is a win, correctness a gate — this ticket
is the case where cost *became* a correctness cost).
