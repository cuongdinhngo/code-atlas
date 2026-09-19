---
id: 300
slug: the-index-is-registered-permitted-and-never-chosen
title: 'The index is registered, permitted and never chosen — 0 tool calls in three uncoached sessions'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [074, 200, 266, 268]
---

## Goal
Three uncoached headless sessions asked an ordinary navigation question with all 24 code-atlas tools
**registered, connected and permitted**, and made **0 index calls** between them. Find out why an
agent that can use the index does not, and change whatever is responsible.

This is not a measurement of answer quality. It is prior to one: [074](074_does-the-index-harm-mechanism-questions.md)
cannot buy a granted arm until this moves, because a granted cell that never calls the index is a
native-tools cell wearing the arm's label.

## The evidence (protocol: [`benchmarks/074_mechanism-question.md`](../benchmarks/074_mechanism-question.md), *Preflight findings*)

| Session | Repo | Client | Tool calls | code-atlas calls |
|---|---|---|---|---|
| 2026-08-27, benchmark cell (granted) | anchor | Aug build | 68 | 0 |
| 2026-09-19, `probe --uncoached` | this repo | 2.1.278 | 10 | 0 |
| 2026-09-19, `probe --uncoached` | anchor | 2.1.278 | 25 | 0 |

In the two 2026-09-19 sessions the transcript header records 52 resident tools of which 24 are
code-atlas, the server `connected`, `ToolSearch` resident, and `permission_denials: []`. The work was
done with `Glob` / `Grep` / `Read`. Nothing was blocked and nothing was missing; the tools were simply
not selected. The anchor session cost $1.73 and took 26 turns.

`scripts/arm_preflight.py probe --uncoached` is the instrument, and it is cheap enough to re-run after
every candidate change.

## Why this is not the same ticket as 200 or 268
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) is about whether an agent can *recognise*
which tool answers a question; [268](268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md)
is about what 24 descriptions cost before the first question. Both were argued from prompt shape. This
ticket has an instrument and n = 3 of the end state neither predicted: full availability, zero uptake.
Its findings may well close or re-aim one of them.

## Scope / Deliverables
- **Name the cause before changing anything.** Candidate classes to separate, not a fix list:
  tool descriptions that do not match the question's vocabulary; a first-move prior toward `Grep`
  that nothing in the surface disturbs; 24 descriptions diluting each other ([268](268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md));
  no signal that an index for *this* repo exists and is current.
- **Establish whether the harness is the variable.** Every datapoint above is a **headless one-shot**
  session. The August field round reached 22 index calls in 117 (19 %) in an *interactive* session
  with the repo's `AGENTS.md` brief present ([266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md)).
  Measure interactive vs headless with the same question before concluding the product is at fault.
- **Whatever changes, re-run the instrument** on both repos and record the before/after counts.

## Constraints
- Nothing repo-identifying from the anchor enters this repository — counts, verdicts and question
  *shapes* only (074 C1). Transcripts stay outside the tree.
- Do not coach the probe to make the number come out (074 C4). Coaching has its own mode and it is
  not evidence of uptake.
- R4 is not at stake: this measures agent behaviour, not server determinism.

## Acceptance criteria
- A named cause, or an explicit "not identified" with the candidates that were ruled out and how.
- The interactive-vs-headless question answered with counts, so the 19 % / 0 % gap is explained or
  shown to be the harness.
- If a cause is named and fixed: `probe --uncoached` on both repos, before and after, in this file.
- 074's blocker is either lifted (the granted arm can be built) or restated in 074 with what remains.
