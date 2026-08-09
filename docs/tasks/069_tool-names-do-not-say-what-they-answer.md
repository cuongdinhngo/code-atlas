---
id: 069
slug: tool-names-do-not-say-what-they-answer
title: '`find_view_data` went uncalled in the exact session it was built for'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [062, 063, 038]
---

## Goal
Round 3 called **5 of 14 tools**. Two of the nine misses were not "no such question" — they were
*"the name gave me no model of what it would return, so I never spent a call finding out"*. One of
them, `find_view_data`, is the tool this project spent three tickets building, and the session that
skipped it was working *entirely* on a view and the data reaching it. A capability nobody can
recognise has the same field value as a capability that does not exist.

## Evidence (field retro round 3, 2026-08-09)
- `find_view_data` — **0 calls**. The evaluator's reason, verbatim: *"Discoverability failure. My work
  was entirely about a view (`tabs.php`) and the data reaching it. I could not tell from the name what
  'view data' meant in this codebase's terms, so I never tried. If it does what I now guess, this was
  the session it was built for."*
- `explain_path` — **0 calls**: *"Name gave me no model of what it would return, so I never spent a
  call finding out."*
- `reachable_from` — **0 calls**: *"Never occurred to me. Name did not connect to any question I had."*
- Contrast: **zero** failed argument forms across 17 calls, three different name shapes, all first
  try. The tools that *were* found worked flawlessly. The loss is entirely at recognition time.
- Contrast again with a tool that was found and used well: `search_symbol`'s single most valuable
  answer came from a **directory name in a returned path** (`src/Application/Alpha/…`). The session
  reached for it because "search symbol" needs no explanation.
- `find_view_data`'s current description opens with *"View-scope keys `qname` publishes via
  rule-derived `PROVIDES_VIEW_DATA` edges"* — every noun in it is code-atlas vocabulary
  (`view-scope`, `rule-derived`, the edge kind). None of it is the question a caller has, which is
  *"what variables does this handler make available to its template?"*
- The rules channel is **off by default**, so on most repos the honest answer is "this tool has
  nothing for you" — and the description never says so. A caller who tries it once on an unconfigured
  repo, gets nothing, and never returns has been taught the wrong lesson.

## Scope / Deliverables
- **Rewrite the tool descriptions the caller actually reads**, question-first: what user question does
  this answer, what does a hit look like, when is it empty. Mechanism vocabulary moves after the
  question, not before it. Cover at minimum `find_view_data`, `explain_path`, `reachable_from` —
  the three named misses — and review the other eleven for the same failure.
- **Say when a tool is inert.** `find_view_data` on a repo with no `indirection_rules` should be
  distinguishable, from the payload, from `find_view_data` on a handler that publishes nothing. This
  is the same defect class as [065](065_empty-answer-cannot-explain-itself.md) and should reuse
  whatever channel that ticket lands.
- **Test the naming instead of arguing about it.** Give a reader the 14 descriptions and a list of
  real questions from the round-1/2/3 sessions, and record which tool they pick for each. A
  description that does not route its own question is not fixed. That mapping is the deliverable —
  it can also be re-run after any future tool is added.
- **Decide whether the prompts surface should route.** `tools/prompts.py` already registers with the
  server; if a question-to-tool map belongs there rather than in each description, say so and put it
  there.
- **Do not add tools.** This ticket changes what the server says about itself. Nothing about the
  graph or the contract moves.

## Constraints
- 061 — descriptions are paid for on every session's tool list; shorter and clearer, not longer.
- R2 — descriptions must not name a framework or a repo's conventions; "the variables a handler
  publishes to its template" is a language-level idea, "the Blade view bag" is not.
- R4 — no behaviour change; if a payload field is added for the inert case, it follows 065's shape.

## Acceptance criteria
- Each of the 14 tool descriptions opens with the caller's question, not the mechanism.
- The routing exercise is recorded in the working doc, with the before/after pick-rate for the
  questions drawn from the three field rounds.
- `find_view_data` on a repo with no rules configured is distinguishable from a handler with no keys.
- No tool description references a framework, a repo, or an edge kind before the question it answers.

## References
Field retro round 3 §2 (coverage table and the "why not" column), §11a (5/14 called, ~1.8% of session
tokens), §9 (discoverability named as one of the four defect classes).
`code_atlas/tools/find_view_data.py`, `explain_path.py`, `reachable_from.py`, `prompts.py`.
Related: [062](062_view-databag-producer.md) / [063](063_view-databag-array-keys.md) (the capability
that went unused), [038](038_explain-path.md), [065](065_empty-answer-cannot-explain-itself.md)
(the inert-vs-empty channel).
