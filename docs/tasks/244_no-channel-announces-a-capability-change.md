---
id: 244
slug: no-channel-announces-a-capability-change
title: 'Every honesty mechanism this project has built delivers in a response, so a user who has already concluded that a question is unanswerable never calls again and never learns the fix shipped — three instances in one session, and the only regression class the test suite structurally cannot catch, because nothing in the repo goes red'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [243, 221, 099, 100]
---

## Why this exists (field retro round 17)

The project's answer to a false zero has been, consistently and correctly, **to make the answer
honest**: `reason` on every empty result, `try_instead`, `truncated`, `cross_language`,
`server_stale_process`. The round-17 retro's §6 *What to keep* is that list, and §4 argues its value
against a shell tool that reports 14 matches as 0 with no signal.

Every one of those mechanisms is a field in a response. A response reaches a caller. It does not
reach a **non-caller**, and a user who has concluded that a class of question is unanswerable is a
non-caller by definition. The conclusion is self-sealing: obeying *"don't ask X"* generates no
evidence against itself, so it survives every fix to X indefinitely.

This is a regression class with no guard, and it cannot have the usual kind: when a shipped
capability goes unused because the user's model of the tool is stale, **nothing in this repo turns
red**. The suite is green, the gate is green, and the capability is worth zero.

## Evidence — three instances in one session

1. **A memory that over-generalised, and cost the session's most valuable question.** An earlier
   round measured `find_callers` on a T-SQL procedure returning 0 against a real 42 and recorded
   *"grep is primary for SQL callers and writers."* Round 17 did not call code-atlas about T-SQL at
   all, and its retro counted that as a saving. The memory was right about **callers** — re-measured
   2026-09-11, the same shape still has 0 linked inbound edges (what 221/238 changed is that the zero
   is now *disclosed*, not that it became non-zero). It was wrong about **T-SQL**: the question the
   session actually needed — how two signatures differ — was in the index the whole time
   ([242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)).
   Nothing distinguished "this relation is unmodelled" from "this language is out of scope", so one
   measured miss retired a whole language.
2. **A shipped capability with no name to ask for.** `find_mirror_subtrees` landed with 115 and is
   reachable through `architecture_overview` and `subtree_dependencies`, but is not itself a tool
   name. Round 17's highest-ranked wish — *"`diff_twin` for the ALPHA/BETA convention … highest value by
   a distance"* — is half of what already ships.
3. **A predicate one `detail_level` out of reach.** [243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md),
   which is this ticket's narrowest case and is ticketed separately because it is fixable on its own.

Five rounds of this backlog have recorded roll-out as the binding constraint and deliberately kept it
off the board because *"this backlog accepts only code"*. Instances 1-3 are the counter-argument: the
binding constraint has a code-shaped face, and this ticket is only that face.

## Scope

**Cheapest mechanism first, and prove it is needed before building the next one.** This ticket is
deliberately allowed to close having shipped one small thing.

- **Establish what a reader can already learn without calling a nav tool.** `get_index_status` is the
  session's first call and the only channel that reaches a non-caller. Inventory what it says today
  about *what this index can and cannot answer* — as opposed to how big and how fresh it is.
- **Name the unit.** A capability statement is not a statistic: *"CALLS across php→sql: not
  modelled"* is actionable, `linked: 0` is a number the reader must interpret. 231's
  `capabilities_by_language` stamp and 204's `cross_language` census are both already on disk; decide
  whether the unit is derived from them or declared beside them.
- **Decide the delivery, cheapest admissible option and no more.** Candidates, to be accepted or
  rejected in writing: a field at `standard` (243's shape); an entry in `next_tool_suggestions`; a
  line in the `claim` string (100); the write-time signal seam (099/240). Rejecting the larger ones
  is a deliverable.
- **Out of scope, explicitly:** notifying anybody, versioning the tool surface, anything that reaches
  outside the process, and any LLM-written prose (R4). Also out of scope: a change to the memory or
  documentation of any consumer repository — this ticket buys a channel, not a correction.

## Constraints

- **R4 / R4.1** — deterministic, no network, no LLM. A capability statement is derived from stamps
  the build already wrote.
- **061 / 223 / test_agent_chain_budget** — the first call of every session is the most expensive
  place in the product to add a sentence. Whatever ships here is measured and bounded, and a
  single-language index with nothing to disclose must stay byte-identical.
- **R5.2 / R5.6** — never claim a capability the stamp cannot vouch for; a pre-stamp index says it
  cannot tell.
- **R1.2 / YAGNI** — one channel. Do not build a capability registry, a subscription, or a
  negotiation.
- **R7.6** — if the honest answer is that this belongs in a doc rather than a payload, say so and
  prune rather than add.

## Acceptance criteria

- A written inventory of what `get_index_status` tells a non-caller today about answerability, and
  the gap named in one sentence.
- One mechanism shipped, with every rejected candidate rejected in writing.
- The added cost on the cheap path measured; byte-identical output asserted for an index with nothing
  to disclose.
- A test that fails if the mechanism stops reflecting a stamped capability change — the guard this
  regression class has never had.
- Instances 1 and 2 above re-checked against the shipped mechanism: would a session reading only the
  first call now avoid each conclusion? Answer in the task file, with the payload quoted.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.6, §4, §5, §6. Related:
[243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md) (the narrow
instance), [242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
(the capability instance 1 never found),
[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) /
[238](238_the-honest-zero-predicate-is-gated-on-the-zero.md) (the fixes that shipped and went
unread), [099](099_write-time-signal-seam.md) /
[240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md) (the existing
out-of-band seams), [100](100_claim-signing-output-mode.md) (the `claim` line the same retro used
verbatim), [065](065_empty-answer-cannot-explain-itself.md) (where the in-band line of work began).
PLAN §19's evidence filter classes this finding as agent-subject — *"how an agent frames a task, when
it is receptive to information"* — which generalises by default and needs no second repository.

## Token usage

| Phase | Tokens |
|---|---|
| — | not yet started |
