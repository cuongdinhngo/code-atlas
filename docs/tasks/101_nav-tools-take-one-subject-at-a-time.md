---
id: 101
slug: nav-tools-take-one-subject-at-a-time
title: 'A ten-name sweep is ten calls, so the agent used a shell loop — a shape mismatch no cost metric can see'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [014, 013, 066]
---

## Goal
Before writing a single line of the port, the field session needed to know whether any of **ten**
helper-function names it was about to introduce were already taken globally. `search_symbol` with
`kind: "Function"` answers that exactly, and it never got called. Not from ignorance and not from
cost — from **granularity**: the graph takes one subject per call, so ten names is ten round-trips,
while a shell loop is one call for all ten.

The evaluator picked the tool whose shape matched the question. Its own account: *"I framed the task
as a sweep and picked the tool with a loop."* The sweep found a real collision — a global `getState`
with a **different signature** — and that finding drove the design of ~1,900 lines of the diff.

This is a distinct failure mode from every adoption finding so far, and the interview is right that no
existing metric sees it: [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) measures *cost per
call*, and the problem is not that a call is slow. **Ten calls is the wrong granularity for one
question.** Any tool that answers *"is this name taken"* will keep losing to a shell loop until it can
take a list.

## Evidence (field interview, 2026-08-14, §1 Moment 1 and §7.3)
- §1 Moment 1, "why didn't you call it": ***"(f) other — shape mismatch, not ignorance.** I had 10
  names to check at once. The graph is one-subject-per-call, so that is 10 round-trips; the shell loop
  is one call."*
- The command actually run: `grep -rn "function <name>(" src/ public/` over 10 candidate names — a
  sweep that searched **two directories**, where the graph would have searched the whole index.
- Round 5 §7.3 recorded the same event from the retro side and called it *"a recall failure"*. The
  interview refines that: it was not recall — the tool was known and it did not fit the question's
  shape.
- §7.3 of the interview states the general form: *"Any tool that answers 'is this name taken' will lose
  to a sweep until it can take a list."*

## Generality — why this one survives the "n = 1, one repo" filter
The question that lost — *are any of these N names already taken?* — is not specific to a migration or
to PHP. Renaming a batch of symbols, checking a list of candidate identifiers before generating code,
auditing a set of paths named in a diff: all are list-shaped, and an agent facing a list-shaped
question will reach for the tool that takes a list. The mismatch is between **the granularity of the
question and the granularity of the interface**, and both sides of that are code-atlas's, not the
anchor's.

Bounded on purpose: this ticket batches subjects, and does not become a query language.

## Scope / Deliverables
- **Decide which tools take a list of subjects, and which must not.** `search_symbol` is the clear
  case (a name-availability sweep). `impact` already takes multiple paths. Single-answer tools like
  `read_symbol` may be wrong to batch — a batched body read is just a file read. Record the verdict
  per tool rather than batching everything (**R1.2**).
- **Bound the fan-out and disclose the bound**, following [066](066_limit-clamped-silently.md): a
  batched call must say how many subjects it accepted, how many it clamped, and which. A silently
  truncated sweep is worse than ten honest calls, because a sweep's whole purpose is completeness.
- **Keep the per-subject answer shape.** The result must remain addressable per subject — a merged
  result set would re-create [070](070_ambiguous-qname-no-scoping.md)'s defect at batch scale.
- **Answer the empty-subject case per subject.** Each subject carries its own `reason`; one miss in a
  batch of ten must not colour the other nine (065's rule, applied element-wise).
- **Measure the win.** Ten single calls vs one batched call: tokens and wall clock, on a large index.
  If the saving is only latency and not tokens, say so — the argument here is *shape*, and it should
  survive on shape, not on a number that flatters it.

## Constraints
- **R4** — deterministic ordering: results follow the caller's subject order, not the store's.
- **061** — a batched payload must not repeat per-subject boilerplate ten times; that would trade a
  shape problem for a weight problem.
- **R3** — a changed input shape touches the tool contract and the conformance suite.
- **R1.2 / YAGNI** — one batched tool first, proven in the field, before the pattern spreads.
- Cost: a batch must not fan out into an unbounded index scan; the bound is part of the contract.

## Acceptance criteria
- `search_symbol` (or the tool the design selects) accepts N subjects, returns N addressable answers
  with per-subject reasons, and pins the whole payload in a test.
- Exceeding the bound reports the clamp and names what was dropped (066's rule), with a test.
- Single-subject calls are byte-identical to today (R4).
- Tokens and wall clock for 10 single calls vs 1 batched call are recorded on a large index.
- A written per-tool verdict on which tools do **not** get a list, with reasons.

## References
Field interview (round-5 companion, 2026-08-14) §1 Moment 1, §7.3, §8.4 item 3. Related:
[066](066_limit-clamped-silently.md) (disclose the bound), [065](065_empty-answer-cannot-explain-itself.md)
(per-subject reasons), [070](070_ambiguous-qname-no-scoping.md) (why answers must stay addressable),
[014](014_search-read-outline.md) and [013](013_nav-tools.md) (the tools),
[096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (the cost metric that cannot see this).
