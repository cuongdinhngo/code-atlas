---
id: 133
slug: agent-chain-is-one-tier
title: The always-binding read is ~66.5k tokens and most of it is reference — tier the agent chain and gate the tier
phase: 1.5b
milestone: Docs
status: in-progress
depends_on: [132]
---

## Why this exists (measured in 132, on commit `1f85f9a`)

Pillar 1 says the caller is an agent and the value is *"a token cost low enough that an agent can
afford to ask"*. The doc set charges that same caller **~66,500 tokens across 7 files** before it has
seen everything `AGENTS.md` says governs every session — and **82 % of that is two files that are
reference material, not rules**:

| Tier | Files | Lines | Tokens |
|---|---|---|---|
| 1 — *"Read these before non-trivial work (they govern every session)"* | 7 | 2,344 | **~66,500** |
| 2 — pointed to as binding from tier 1 (`LESSONS.md`, `SKILL_GAP_CANDIDATES.md`) | 2 | 1,916 | ~34,100 |
| closure | 9 | 4,260 | ~100,700 |

`BACKLOG.md` is ~27,500 of tier 1 and `PLAN.md` is ~26,900. Neither is read to learn a rule.
`BACKLOG.md`'s weight is its **token ledger** — 118 rows of per-ticket retrospective, several of them
600+ words, which an agent starting a ticket has no use for. `PLAN.md`'s is **§19**, a 385-line
decision log that is consulted when a decision is questioned, not read at the top of a session.

**This is not a tidiness ticket.** Every session pays this, the same way every `find_callers` call
pays its payload. 132 made the boundaries stateable and deliberately did not act on this number,
because moving either body is a structural change that needs its own measurement.

## The measurable goal

**Tier 1 — what an agent must read before it knows what binds it — comes in under 25,000 tokens,
measured by a committed instrument, and stays there under a test.**

The number is a budget, not a diet: nothing is deleted, and nothing binding moves out of tier 1.
What moves is what was never binding — reference bodies get their own tier, reachable by a pointer an
agent follows when it needs them.

## Scope

**The instrument comes first.** A claim about the chain's cost that cannot be re-run is the kind of
number this repo does not ship.

1. **`scripts/agent_chain_cost.py`** — walks the chain from `CLAUDE.md`, follows only the pointers
   the chain marks as binding, and prints per-file and per-tier lines/tokens plus the tier-1 total.
   It must use `code_atlas.tokens.estimate_tokens` — the one definition site (R6.7); a second
   4-chars-per-token proxy in a script is exactly the drift that rule exists to stop. Read-only, no
   network, no index required.
2. **The tier boundary, stated where the chain states itself.** `AGENTS.md`'s "Read these before
   non-trivial work" list is the definition of tier 1, so the split is expressed there: a binding
   list, and a separate *consult when you need it* list. `CONVENTION.md` §8.1's role table gains the
   tier in each row, so a future document lands in a tier on purpose.
3. **`BACKLOG.md`'s token ledger leaves tier 1.** It is one `## Token usage` section, already
   bounded, already parsed by its own guard, and cited by exactly one rule (R7.2). Candidate
   destinations to decide in design, not here: a sibling `docs/TOKEN_LEDGER.md` (needs the closed-set
   argument, CONVENTION §8.1), or `docs/tasks/NNN_slug.work.md` ledgers as the only home with a
   generated summary table. Whichever wins, `tests/test_backlog_bookkeeping.py` follows it — the
   guard reads the ledger by heading now (132), so it moves with a path change and no reparse.
4. **`PLAN.md` §19 leaves tier 1.** The decision log is the project's memory and must stay one
   coherent document; the question is only whether tier 1 needs it inline. Design decides between a
   pointer with §19 in its own file and leaving it in place with the chain listing PLAN as
   consult-only below §18.
5. **A test pins the budget.** `tests/test_agent_chain_budget.py` asserts the tier-1 total is under
   the number, and — R6.5 — is shipped with a recorded red run: made to fail by putting a
   consult-only file back on the binding list.

## AC1 landed in 134 — the rest is untouched

`scripts/agent_chain_cost.py` shipped with [134](134_standing-docs-grow-and-nothing-prunes-them.md),
because that ticket's per-file ceilings were constants chosen from a session run, which is R6.3's own
falsifier. It derives the chain from `CLAUDE.md`'s `@import` and the bullet list `AGENTS.md` itself
labels *read before non-trivial work* — the set is never listed in the script (R6.7) — and its
output is byte-identical across runs.

It confirms both numbers this ticket was written on: the same 7 files, and **66,500 → 49,153 tokens**
after 134's prune. **AC2's < 25,000 is still 24,153 tokens away, and none of AC2–AC6 has started.**
The remaining gap is almost entirely the two bodies this ticket exists to move: `PLAN.md` §19 and
`BACKLOG.md`'s token ledger.

## Acceptance criteria

- **AC1** ✅ *(shipped in 134)* `scripts/agent_chain_cost.py` exists, is read-only, uses
  `estimate_tokens`, and reports the chain's files/lines/tokens. Two runs on one tree are
  byte-identical (R4.2).
- **AC2** The measured tier-1 total is **< 25,000 tokens**, reported in this ticket's Outcome with
  the commit it was measured at (P4).
- **AC3** Nothing binding left tier 1: every rule id (`R*`, `P*`) reachable from the chain before the
  change is still reachable from tier 1 after it. Asserted, not asserted-by-eye — the ticket ships
  the enumeration.
- **AC4** `tests/test_agent_chain_budget.py` fails when a consult-only document is returned to the
  binding list. The red run is recorded.
- **AC5** No standing document is deleted, and any new one carries its closed-set argument in this
  ticket (CONVENTION §8.1).
- **AC6** `tests/test_backlog_bookkeeping.py` passes wherever the ledger ends up, with no change to
  what it asserts — only to where it reads.

## Out of scope

- **Shrinking `LESSONS.md` (tier 2, ~31,800 tokens).** Its size is its function: a claim corpus whose
  `seen:` counts are promotion's only gate (P1). It is already consult-only in substance; this ticket
  only makes that explicit in the list.
- **Rewriting any prose.** Same constraint as 132: content moves or is cut, never reworded in
  passing.
- **The `docs/phase3-onboarding/` directory rename**, deferred from 132 C6 with its own collision to
  decide (`docs/onboarding/` is `generate_onboarding`'s output).
