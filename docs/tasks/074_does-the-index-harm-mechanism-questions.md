---
id: 074
slug: does-the-index-harm-mechanism-questions
title: 'The one repeated benchmark cell says the index may make control-flow answers worse — resolve it at n ≥ 3'
phase: 1.5b
milestone: Measure
status: todo
depends_on: [055, 067, 045]
---

## Goal
The founding-premise benchmark (PLAN §19, 2026-08-08) recorded one accidental repeat: the **mechanism
question**, run twice under the indexed arm's configuration — once with the server **denied**, once
with it **granted** — produced **opposite verdicts**. The denied run was right. It is recorded as a
threat to validity and left unresolved at n = 1. It is the only datapoint in the project suggesting the
index does not merely fail to pay for itself but **actively costs accuracy**, and it sits on the
question type the replacement claim is supposed to serve. Resolve it, and be willing to act on a bad
answer.

## Why this is not just noise
A mechanism is available, and it is already documented from a different field session.
[067](067_first-page-not-representative.md) recorded a *fully correct* `find_callers` result — 23 of
23, hand-verified — that made the session **worse**, because page 1 was 100 % of the tree the agent
must not touch and 0 % of the tree it had to change. The session "briefly read that page as *no `src/`
callers*" before `grep` contradicted it. That is the shape the hypothesis predicts: **a confident,
cheap, partial answer that terminates the reasoning which would have reached the truth.** Round 3
called that call the single question where the graph was a net loss, at roughly twice the tokens.

So there are two independent observations pointing the same way, and both are compatible with an
index that is *correct* and still harmful. A benchmark scoring precision and recall would rank them
exactly backwards — round 3's own words.

Countervailing evidence to hold at the same time: the agent reached for the index in **22 of 117 tool
calls (19 %)**. A 19 %-adoption arm losing on tokens measures **adoption**, not capability — that is
why PLAN calls fit the binding constraint. But the *wrong-cause* cell is not explained by low adoption:
being denied the tool made the answer **better**, which low adoption cannot produce.

## Scope / Deliverables
- **Re-run the mechanism question at n ≥ 3 per arm**, two arms only: server **granted** vs server
  **denied**, identical prompt, identical fresh headless session per cell, no coaching. Ground truth
  established by hand before the runs, as in the original protocol.
- **Score cause-correctness, not tokens.** Tokens are secondary here and must not decide the verdict —
  055 already established that the cost metric cannot see the worst failures.
- **Record the mechanism when the granted arm is wrong.** For each wrong answer, capture *which tool
  call preceded the wrong turn* and whether the payload was correct-but-unrepresentative (the 067
  shape), confidently empty (the [065](065_empty-answer-cannot-explain-itself.md) shape), or simply
  ignored. A verdict without a mechanism is not actionable.
- **Pre-register what each outcome causes**, before running, so the result cannot be argued after the
  fact:
  - *granted ≈ denied* → the original cell was session variance; delete the threat from §19 and stop
    spending on it.
  - *granted worse, mechanism identified* → the mechanism becomes a ticket, and the tool's description
    or ordering changes; 067 is likely already that ticket.
  - *granted worse, no mechanism* → **narrow the recommended scope in writing**: state in PLAN §19 and
    the README which question types the index is for, and which it should be kept out of. Scope
    narrowing is an acceptable, expected outcome of this ticket.
- **Extend to a second mechanism-shaped question** only if the first replicates. One question at n ≥ 3
  beats five at n = 1 — the original benchmark's chief weakness.

## Constraints
- Nothing repo-identifying from the anchor repo enters this repository. Aggregate counts, verdicts and
  question *shapes* only, as with every prior field record.
- The comparison arm is **native tools only**. A resident-LSP arm is out of scope: that server was
  uninstalled from the anchor repo on 2026-08-07, and the original run's LSP arm invoked it **zero
  times in 84 tool calls** — there is no answer-quality comparison to be had, and the project must not
  claim one.
- R4 is not at stake — this measures agent behaviour, not server determinism. Say so in the write-up so
  the variance is not mistaken for a server defect.
- Do not change any tool to make the number come out. This ticket produces a measurement and a decision;
  code changes belong to whatever ticket the mechanism names.

## Acceptance criteria
- n ≥ 3 per arm on one mechanism question, with per-run verdicts and the pre-registered consequences
  recorded before the runs.
- Each wrong granted-arm answer has a named mechanism or an explicit "not identified".
- PLAN §19's "unresolved" threat is either deleted (variance) or replaced by a scope statement naming
  the question types the index is not for.
- The README's and PLAN's value claims match the outcome, in the same change.

## References
`docs/PLAN.md` §19 — *Founding-premise benchmark (2026-08-08)*, the "Threats, recorded rather than
hidden" paragraph (the repeat and its opposite verdicts) and the 22/117 adoption figure. Related:
[055](055_recall-benchmark.md) (why the cost metric cannot see this),
[067](067_first-page-not-representative.md) (an independent instance of correct-but-harmful),
[065](065_empty-answer-cannot-explain-itself.md) (confident emptiness as a candidate mechanism),
[045](045_tokens-to-answer-local-repo.md) (the local-tier harness).
