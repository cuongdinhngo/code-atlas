---
id: 081
slug: routing-prompts-are-not-in-the-agents-surface
title: 'The four routing prompts have never been reachable by an agent — 069 fixed discoverability in a channel the agent cannot see'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [069, 017, 038]
---

## Goal
The server registers four prompts — `explore_area`, `find_usages`, `impact_of_change`, and
`which_tool` (069's answer to a capability nobody could find). Round 4's evaluator reported it could
not call `which_tool` and, crucially, **could not have**: in its client only the 14 tools are part of
the surface a model sees, while MCP prompts surface as human-invoked entries. Across four field rounds
no prompt has been exercised once. A routing hint the agent cannot reach cannot fix an agent's routing
problem, and a delivery channel with zero field evidence should not be counted as shipped capability.

## Evidence (field retro round 4, 2026-08-10, §0.5 and §A.5)
- Verbatim: *"The 4 prompts are not reachable from this client's tool surface; only the 14 tools are
  exposed to me. A prompt that the agent cannot invoke cannot fix a discoverability problem for that
  agent."*
- §A.5's verdict on 069 is **IMPROVED, not fixed**: the descriptions half is verified — first lines
  read *"Who calls this function or method?"*, *"Where is this symbol used across the codebase?"*,
  *"What does this file define, and on what lines?"*, *"What variables does this handler make available
  to its template?"*, *"Find a symbol from part of its name or text"* — while the `which_tool` half is
  **not exercisable** and the `capability_not_configured` half did not apply (this index has rules
  configured).
- Rounds 1–3 called 0 prompts as well; none of the three retros noticed, because none of them was
  asked. This ticket exists partly because round 4's questionnaire asked.
- Countervailing fact worth keeping: descriptions **did** work. The same session recorded
  `find_view_data` as *"not a discoverability failure this time: its description states the question it
  answers"* — it went uncalled because no view-data question arose, which is occasion, not recognition.

## The real question
Not "make prompts reachable" — that is a client's decision, not ours. The question is **where routing
guidance belongs when the only surface an agent reliably sees is the tool list**. Three candidate
answers, and the ticket must choose with the field evidence in hand:
1. **Descriptions carry it all** (069's verified half). Cheapest, already proven to work, bounded by
   how much text a description can hold before it dilutes.
2. **A tool that answers "which tool"** — routing as a callable, discoverable like everything else,
   at the cost of one more entry in a 14-tool surface and a description that must itself be
   self-explaining.
3. **Keep the prompts for humans and stop counting them as agent-facing** — document them as operator
   recipes, and move any agent-critical routing into (1).

## Scope / Deliverables
- **Establish the fact from outside**, not from our own assumptions: record which surfaces the target
  clients expose to a model (tools always; prompts as human entries in at least one client), and cite
  the observation rather than the docs.
- **Choose one of the three designs and apply it**, including deleting or relabelling what the chosen
  design makes dead. A registered prompt nobody can reach is payload weight in the same sense 061
  measured.
- **Re-verify 069's remaining halves** with a live probe: the `capability_not_configured` branch on an
  index with no `view_data` rule, and whatever replaces `which_tool`.
- **Give the next retro a real recognition test.** Round 4's §0.5 was voided by protocol order; the
  measurement it was meant to produce is still missing, and whatever ships here needs it as its
  acceptance evidence rather than a self-report.
- **State the cost of a 15th tool** if design 2 wins — 069's own reasoning was that a surface an agent
  scans has a budget.

## Constraints
- R1.2 / YAGNI — do not build a routing framework; the smallest thing that puts the guidance where the
  agent looks.
- 061 — if the prompts stay, they must earn their registration; if they go, say what replaces them.
- 069 stays authoritative for description *content*; this ticket is about the *channel*.
- No LLM in the core (R4) — routing guidance is static text or a deterministic tool, never a model
  call.

## Acceptance criteria
- A recorded, cited statement of which surfaces reach a model in the clients we target.
- One design chosen, implemented, and the alternatives rejected in writing.
- No registered capability remains that an agent cannot invoke, unless it is explicitly labelled
  operator-facing in the README and the plan.
- A recognition measurement exists that a future field round can run without contaminating itself.

## References
Field retro round 4 §0.5 (could not call it), §A.5 (`IMPROVED, not fixed`), §2 (`find_view_data`
description worked), §11 item 2 (probe-shaped evidence caveat). Related:
[069](069_tool-names-do-not-say-what-they-answer.md) (question-first descriptions + `which_tool`),
[017](017_impact-engine.md) (where the prompts were introduced),
[038](038_explain-path.md) (the tool round 4 expected to want and never called),
[061](061_payload-weight.md) (capability that earns nothing).
