---
id: 133
slug: agent-chain-is-one-tier
title: The always-binding read is ~66.5k tokens and most of it is reference — tier the agent chain and gate the tier
phase: 1.5b
milestone: Docs
status: done
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

---

# Working doc — 133

**Session status:** finalise · `work_doc_mode: embed` (plain local-file ticket) · branch
`docs/133-agent-chain-is-one-tier` · **SCOPE: M · TIER: full** · review **waived by the maintainer's
run args**; **CHALLENGER: OFF (waived)** — recorded as an argument, not improvised.

## Requirements matrix

| # | Kind | Source | Requirement | Met by | ✓ |
|---|---|---|---|---|---|
| G1 | Goal | *The measurable goal* | tier 1 < 25,000 tokens, by a committed instrument, held by a test | `scripts/agent_chain_cost.py` + `tests/test_agent_chain_budget.py` | ✅ |
| R1 | Scope 1 | Scope §1 | the instrument reports per-file **and per-tier** lines/tokens | `agent_chain_cost.py` prints both tiers | ✅ |
| R2 | Scope 2 | Scope §2 | the tier boundary stated where the chain states itself; CONVENTION §8.1 rows carry the tier | `AGENTS.md:20-31`, `CONVENTION.md:238-262` | ✅ |
| R3 | Scope 3 | Scope §3 | BACKLOG's token ledger leaves tier 1 | → `docs/TOKEN_LEDGER.md` | ✅ |
| R4 | Scope 4 | Scope §4 | PLAN §19 leaves tier 1 | PLAN listed consult-only (the option Scope §4 offers) | ✅ |
| R5 | Scope 5 | Scope §5 | a test pins the budget, shipped with a recorded red run | `tests/test_agent_chain_budget.py` + red run below | ✅ |
| AC1 | AC | ticket | instrument exists, read-only, uses `estimate_tokens`, deterministic | shipped in 134; extended here, still byte-identical across runs | ✅ |
| AC2 | AC | ticket | tier 1 **< 25,000**, reported with its commit | **22,457** — see *Outcome* | ✅ |
| AC3 | AC | ticket | no rule id left tier 1; enumeration shipped | 43 ids before (`b277f1a`, 7 files) → 43 after (6 files), **0 lost** | ✅ |
| AC4 | AC | ticket | the test fails when a consult-only doc returns to the binding list; red run recorded | **45,249 tokens, 1 failed** — below | ✅ |
| AC5 | AC | ticket | nothing deleted; a new doc carries its closed-set argument | nothing deleted (the ledger moved byte-for-byte); argument below | ✅ |
| AC6 | AC | ticket | `test_backlog_bookkeeping.py` passes, same assertions, new path | **272 passed**, only two paths changed | ✅ |
| C1 | Constraint | ticket | nothing binding leaves tier 1 | AC3 enumeration | ✅ |
| C2 | Constraint | ticket | no prose reworded in passing | the ledger moved verbatim; edits are pointer repairs only | ✅ |
| C3 | Constraint | Out of scope | `LESSONS.md` not shrunk — only made explicitly consult-only | listed on the tier-2 list, untouched (32,807) | ✅ |
| C4 | Constraint | R6.7 | one definition site: `estimate_tokens`; both tier sets derived, never listed | `chain()` / `consult_only()` read AGENTS.md's own lists | ✅ |
| C5 | Constraint | R6.5 | red run recorded, not asserted | below | ✅ |
| C6 | Constraint | R7.2/R7.6 | docs + status + spend row in the same change | R7.2, R7.6, README §Documentation, BACKLOG, this frontmatter, ledger row | ✅ |
| C7 | Constraint | Out of scope | no `docs/phase3-onboarding/` rename | untouched | ✅ |

## Decisions (HOW, self-resolved under the maintainer's standing approval)

1. **PLAN.md goes consult-only whole, rather than §19 being extracted.** Scope §4 offers both. The
   arithmetic decides it: §19 is 7,022 tokens and the ledger 4,773, so extracting only those two
   leaves tier 1 at **37,777** — AC2 fails by 12,777. PLAN defines **no** `R*`/`P*` of its own
   (AC3's enumeration), so demoting it costs no rule reachability, and `AGENTS.md` already described
   it as the thing `§`-refs point *into*.
2. **The ledger goes to `docs/TOKEN_LEDGER.md`**, the first candidate Scope §3 names. *Closed-set
   argument (CONVENTION §8.1):* the set grows by one file and loses a section; the new file answers
   exactly one question no other standing doc may answer (*what did ticket NNN cost*), it is the
   destination R7.2 already required a home for, and its boundary is stated in its own header and in
   the §8.1 row. It is the only standing doc with **no** size ceiling, because R7.2 makes it
   append-only — a ceiling there would force pruning evidence.
3. **`PLAN.md` keeps its per-file ceiling although it is tier 2.** A `§`-ref pulls it into a session
   anyway, so R7.6 still applies to it; only the *sum* it is charged to changed.

## Change list (as approved at Gate 2, and what landed)

| # | File | Change |
|---|---|---|
| 1 | `docs/TOKEN_LEDGER.md` | **new** — the `## Token usage` section moved verbatim, under a boundary header |
| 2 | `docs/BACKLOG.md` | ledger section removed; head + `## Conventions` repointed |
| 3 | `AGENTS.md` | the one list becomes two: tier 1 binding, tier 2 consult-only; R7.2 pointer repaired |
| 4 | `docs/CONVENTION.md` | §8.1 gains a `Tier` column + its definition + the `TOKEN_LEDGER.md` row; BACKLOG row loses cost |
| 5 | `docs/ENGINEERING_RULES.md` | R7.2 destination repointed; R7.6 restated in tier terms + the new total cap |
| 6 | `README.md` | doc map: six → seven docs, cost split out |
| 7 | `scripts/agent_chain_cost.py` | `_binding_list` → `_bulleted_links`; adds `consult_only()`; prints both tiers |
| 8 | `tests/test_agent_chain_budget.py` | **new** — the 25,000 total cap, the partition, and the teeth |
| 9 | `tests/test_doc_size_budget.py` | budgets re-baselined (BACKLOG 14,000→9,500; CONVENTION 6,100→6,300; AGENTS 2,700→2,800) |
| 10 | `tests/test_backlog_bookkeeping.py` | reads the ledger from its new file; status reader no longer partitions on the ledger heading |
| 11 | this file, `docs/BACKLOG.md` row, `docs/TOKEN_LEDGER.md` row | R7.2 bookkeeping |

## Outcome (AC2)

Measured on this branch by `scripts/agent_chain_cost.py`:

| Tier | Files | Lines | Tokens |
|---|---|---|---|
| **1 — binding** | 6 | 1,007 | **22,457** |
| 2 — consult | 4 | 3,130 | 62,853 |

**66,500 → 49,153 (134) → 22,457 (here)**, against a budget of 25,000 — **2,543 tokens of headroom**.
Two runs on the tree are byte-identical (R4.2).

## Recorded red run (AC4 · R6.5)

`docs/PLAN.md` moved back onto `AGENTS.md`'s binding list, nothing else changed:

```
tier 1 — binding … 7 files  2003  45,249
E  AssertionError: tier 1 is 45,249 tokens against a budget of 25,000. Every session pays it.
1 failed, 11 passed
```

Reverted; `tests/test_agent_chain_budget.py` green (3 passed). Not every consult-only file is
individually large enough to breach — the smallest is 2,291 tokens — so the third test asserts the
claim about the largest, and the docstring says so rather than implying more.

## Verification

- `scripts/gate.sh` → **GATE GREEN — all 12 checks passed** (Linux host, PHP on PATH).
- Full suite: **1821 passed, 0 skipped** in 108 s, same host. Delta-green.
- `tests/test_backlog_bookkeeping.py` → 272 passed (AC6, no assertion changed).
