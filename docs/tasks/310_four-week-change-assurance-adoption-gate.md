---
id: 310
slug: four-week-change-assurance-adoption-gate
title: "Change Assurance value gate — closed unmeasured, never ran"
phase: 3
milestone: Change-Assurance
status: done
depends_on: [260, 300, 303, 305, 306, 307, 309, 312]
---

## What this was for

The only end-to-end evidence [304](304_change-assurance-makes-every-important-change-carry-evidence.md)
would ever have had: does the evidence bundle surface what an ordinary review misses?

Its first form — a four-week cohort running Change Assurance on a real team — died with
[300](300_the-index-is-registered-permitted-and-never-chosen.md) (*full availability, zero uptake*,
n = 3), which put half the cause outside this repo. Its second form was a blind two-arm study:
one arm reads the diff, one reads the diff plus the bundle, marginal recall scored against the
upstream authors' own test edits, the 0.50 / 0.20 thresholds ratified before any machinery existed.

**Closed 2026-09-20 and off the backlog.** `done` here means the ticket is finished with, not
that it delivered: the verdict below is `not_measured`. From here it is carried by its
[TOKEN_LEDGER](../TOKEN_LEDGER.md) row alone (R7.6).

## Why it was dropped — 2026-09-20

**The maintainer's call, and the cheaper instrument was already running.** A full run measured out
at $0.3856 per scenario-repeat, ~$11.6 and ~40 minutes for the corpus. Against that: thirty-one
rounds of retros on the anchor repo have found every defect that changed this project's direction
so far, at no marginal cost, on real sessions rather than reconstructed ones.

Then the subject disappeared. 303, 305, 306 and 307 were removed under 304's closing review, so
the arms would compare a diff against a bundle that no longer has a command to produce it.

**Verdict: `not_measured`.** Not `no_demonstrated_value` — that is a result, and no run produced
one. Nothing here claims the bundle would have failed; it claims nobody paid to find out.

## What was kept from the attempt

`benchmarks/310_bar.md`, the runner and its tests were never merged and are not on `main`. The one
durable finding is recorded instead:

**A `claude -p` arm spawned from inside Claude Code inherits the parent's messaging socket and
answers as the parent.** Observed: a one-turn arm replied *"that notification is for the agent
whose report I already incorporated"*. An arm that can hear its parent is blind to nothing, and the
measurement would have been silently void. Any future in-repo study that spawns judge sessions must
scrub `CLAUDE_CODE_MESSAGING_SOCKET` and its siblings before the child starts — the same prompt then
took 12–13 turns and produced a real answer.

## If it is ever revived

The pre-registration discipline from [309](309_test-impact-recall-gate.md) holds: the bar is
committed alone, before the corpus, runner and reporter exist, and the reporter names that commit
mechanically in every run. A bar ratified after its measurement exists is not a bar.
