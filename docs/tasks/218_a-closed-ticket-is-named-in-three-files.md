---
id: 218
slug: a-closed-ticket-is-named-in-three-files
title: A closed ticket is named in three files and every session pays for all three
phase: 2
milestone: —
status: done
depends_on: [133, 134, 205]
---

## Goal
`BACKLOG.md` measured **8,797 tokens against a ceiling of 8,800**, and tier 1 as a whole **25,899
against 25,900** — one token of headroom, so no ticket could be filed at all. 208 of its 214 rows
were `done`: a third naming of what `tasks/NNN_*.md` and the ticket's `TOKEN_LEDGER.md` spend row
already hold. That is the copy R7.6 forbids, and every session pays for it.

## Scope / Deliverables
- Remove every `done` row from `BACKLOG.md`; keep the open rows, the section prose, Follow-ups and
  Conventions.
- Narrow the bookkeeping guard: an **open** task needs a row that agrees with its frontmatter; a
  **done** task needs a ledger row and must **not** have a row; no task falls through both.
- Add the prune's own falsifier — a `done` row surviving in BACKLOG fails.
- Update R7.2's text, which said status updates *both* places for every task.
- Lower `BACKLOG.md`'s ceiling and `TIER1_BUDGET` to the measured size plus headroom.

## Acceptance criteria
- AC1 — `tests/test_backlog_bookkeeping.py` green on the narrowed invariant, and red when any of the
  208 removed rows is restored.
- AC2 — `tests/test_doc_size_budget.py` and `tests/test_agent_chain_budget.py` green with ceilings
  that still bite (within 25 % of measured).
- AC3 — every open task still reachable: `set(open task files) == set(BACKLOG rows)`.

## References
R7.2, R7.6 (`docs/ENGINEERING_RULES.md`). Prior prunes: 133 (ledger out of tier 1), 134, 205.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 218 · **work_doc_mode:** embed · **Current phase:** closed — merged as `fde7403` (PR #269).
- **Next action:** none.
- **Blocked on:** nothing.
- Branch: `docs/218-prune-the-closed-rows-out-of-backlog` (merged).

## Phase 0–2 — refine · analysis · design (2026-09-05, compressed)

This ticket was *found by* 217's refine, not filed from a raw request: the budget constraint it
records (tier 1 at 25,899/25,900) is what blocks 217 and every other new ticket. The maintainer chose
the direction — **collapse the `done` rows** rather than raise the ceiling a fifth time since
2026-08-30 — so there was no want-decision left to expose.

**One thing the design got wrong and execute corrected.** Refine recorded the prune as "a count plus
a git-history pointer", a BACKLOG-only edit. `tests/test_backlog_bookkeeping.py:117` then asserted
`set(BACKLOG rows) == set(task files)` — so removing a row makes a task *untracked* by that guard's
reading, and the prune could not be a docs-only change. The change list grew by two files, both
required: the guard's invariant and R7.2's text, which is the rule the guard enforces.

**Rejected: raise the ceiling again.** It has moved four times since 2026-08-30 (25,150 → 25,900).
Each raise is charged to every future session, and the thing being paid for here is a copy, not
content.

### Approved change list

| File | Change |
|---|---|
| `docs/BACKLOG.md` | 208 `done` rows removed; three landed Phase sections collapsed to one; header and Conventions restated |
| `tests/test_backlog_bookkeeping.py` | equality invariant → open-task row + done-task ledger row + no-orphan; new `test_a_closed_ticket_leaves_the_backlog` |
| `docs/ENGINEERING_RULES.md` | R7.2 carve-out for a closing ticket, with the new falsifier |
| `tests/test_doc_size_budget.py` | `BACKLOG.md` ceiling lowered to the measured size |
| `tests/test_agent_chain_budget.py` | `TIER1_BUDGET` lowered by what the prune freed |

**Proving test:** `tests/test_backlog_bookkeeping.py::test_a_closed_ticket_leaves_the_backlog` —
fails on restoring any one of the 208 removed rows.

## Phase 3 — execute

`BACKLOG.md` 8,797 → 1,826 tokens (−6,971). Tier 1 25,899 → 18,990. `scripts/gate.sh` GATE GREEN
19/19 on a Linux host; `gh pr checks 269` 4/4. Red run recorded: restoring 020's row fails
`test_a_closed_ticket_leaves_the_backlog` by id.

## Cost ledger

| Item | Spend |
|---|---|
| refine (217, which surfaced this) | 67,519 tokens — 1 challenger dispatch |
| this ticket | fresh session, no dispatch |
