---
id: 097
slug: recognition-probe-measures-names-not-recall
title: 'The recognition probe scored 14/14 off bare names — it cannot measure 081, and it misses the failure that costs'
phase: 1.5b
milestone: Measure
status: todo
depends_on: [081, 069, 074]
---

## Goal
Round 5 ran the first blind recognition probe (`docs/runbooks/tool-recognition-probe.md`) and scored
**14 / 14**, including the `find_callers` vs `find_references` confusion the protocol says to watch.
The round's own reading of that score: **the probe is saturated, and the rate is close to
meaningless.**

Two independent reasons, both of which the protocol currently cannot detect:

1. **Seven of the fourteen answers were given without ever reading a description.** The harness
   defers MCP tool schemas — the agent sees a bare name list and must explicitly fetch a schema
   before a tool is callable. The evaluator fetched 7. [081](081_routing-prompts-are-not-in-the-agents-surface.md)
   moved routing *into the tool descriptions*, and §0.5 is its stated proxy measurement — but more
   than half the descriptions were never in context, so **the proxy measured names, not descriptions,
   and 081's mechanism is untested**. §A.7 is recorded `NOT OBSERVED` for exactly this reason.
2. **Recognition is not recall.** The evaluator named `file_outline` correctly at Q4, had loaded its
   description, and then did not call it at the moment it would have prevented a committed error —
   hand-counting a 1,196-line legacy file's functions, getting it wrong, and shipping "eight" into a
   comment and a tracking registry. The probe asks *given the question, name the tool*. Real work
   fails at *given the situation, notice there is a question*. **Only the second faculty cost
   anything this round.**

## Evidence (field retro round 5, 2026-08-14, §0.5 + §2 + §11.1–§11.3, §11.6)
- Declared before scoring: *"Only 7 of the 14 tool descriptions were ever loaded into context … For
  the other 7 my answer below is derived from the name alone."*
- Second declared caveat: the host repo's own agent guide pre-routes five tool names verbatim, which
  is routing priming from outside code-atlas and biases the rate upward.
- §2 coverage: **6 of 14 tools in the work, 7 of 14 including probes.** Of the 8 unused, 5 "did not
  fit"; the other 3 are exactly the tools whose descriptions were never loaded (`find_callers`,
  `include_graph`) or loaded-but-not-recalled (`file_outline`).
- §2's three buckets ("did not fit" / "did not know it would answer this" / "knew it, did not trust
  it") have **no slot for the answer that was true**: *knew it, it fit, did not think of it in the
  moment*. That happened twice — `file_outline` (§11.3) and `search_symbol kind:"Function"` (§7.3,
  the redeclare-trap question answered by a narrower `grep`).
- Probe P4, post-hoc, on the legacy source the evaluator had already read by hand: **7 functions + 2
  closures with line ranges, ~1 KB** — *"the exact map I read 1,196 lines to build, and the exact
  count I got wrong."*

## Scope / Deliverables
This ticket changes the **measurement protocol and the routing surface**, not the index.

- **Record resident descriptions before scoring §0.5.** The probe template must require the evaluator
  to state how many of the N tool descriptions were in context at scoring time, and to mark each
  answer as name-only or description-backed. A rate scored off names must be reported as such.
- **Make the probe discriminating again.** A test a bare name list passes at 100 % measures nothing
  about descriptions. Design a §0.5 variant that can fail — candidates to weigh: questions phrased in
  the user's words rather than the tool's, near-miss pairs that names alone cannot separate, or
  scoring routing *only* over tools whose descriptions were loaded. Pick one and say why.
- **Add the fourth coverage bucket to §2:** *"knew it, it fit, did not think of it."* Mis-filing a
  recall failure as a discovery failure sends the wrong fix — discovery wants better descriptions,
  recall wants a workflow trigger.
- **Decide what a recall trigger is, for the one case the field named.** `file_outline` on a large
  source file before porting/reading it is, per §11.3, *"the highest-leverage uncalled tool in this
  repository"* and nothing in the tool surface or the workflow says so. Decide where such a trigger
  can honestly live (tool description? `next_tool_suggestions`? the onboarding runbook?) — and if the
  answer is "outside code-atlas", record that verdict, because it bounds what 081-style fixes can
  ever achieve.
- **Feed 074.** This round is n = 1 for the session type *legacy→unified port*; the protocol change
  must not reset the counter.

## Constraints
- R4 / no LLM in the core — a "trigger" must not become a heuristic that makes the core
  non-deterministic. `next_tool_suggestions` is existing, deterministic machinery; anything beyond it
  needs a stated reason.
- 061 — a suggestion field that fires on every payload has a token cost; scope it to the occasions
  that earn it.
- The probe protocol is a doc change; do not let it grow into a benchmark harness. 055 and 074 own
  measurement infrastructure.
- Do not re-open 081's reclassification decision — it stands. This ticket says its *measurement* did
  not happen, not that it was wrong.

## Acceptance criteria
- `docs/runbooks/tool-recognition-probe.md` requires a resident-description count and per-answer
  name-only / description-backed marking, and the retro template's §0.5 asks for it.
- The revised §0.5 has at least one question shape that a bare name list demonstrably fails; the
  design records why that shape discriminates.
- §2's bucket list has four buckets, with the new one defined and its opposite fix named.
- A written verdict on where a `file_outline`-before-you-read trigger can live, with the decision and
  its rationale recorded here.
- 081's `NOT OBSERVED` verdict is re-scorable in round 6 — i.e. the protocol now produces a number
  that could distinguish "descriptions route well" from "names are self-evident".

## References
Field retro round 5 §0.5 (both caveats), §2, §A.7, §11.1, §11.2, §11.3, §11.6, §7.3; candidates 6
and 7.
Related: [081](081_routing-prompts-are-not-in-the-agents-surface.md) (the fix this was meant to
measure), [069](069_tool-names-do-not-say-what-they-answer.md) (question-first descriptions;
`find_view_data` lacked an *occasion*, not recognition — the same recall/discovery split),
[074](074_does-the-index-harm-mechanism-questions.md) (the n-counter this round advances),
[055](055_recall-benchmark.md), [044](044_onboarding-runbook.md).
