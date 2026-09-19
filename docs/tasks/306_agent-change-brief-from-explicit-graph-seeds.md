---
id: 306
slug: agent-change-brief-from-explicit-graph-seeds
title: "An agent starts with grep because no bounded change brief turns explicit seeds into the graph context it needs"
phase: 3
milestone: Change-Assurance
status: todo
depends_on: [100, 266, 303]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Given explicit changed paths, qnames or a base revision, emit the smallest deterministic context
brief an agent needs before editing: affected symbols/modules, resolved inbound relationships,
architecture constraints and every uncertainty that limits the answer.

## Scope / Deliverables

1. Inputs are explicit paths/qnames or the changed set selected by 303. No natural-language
   interpretation and no LLM.
2. Reuse impact seed planning, signed claims, module attribution and configured architecture rules;
   do not create a new traversal.
3. Render a bounded Markdown brief with: change identity, likely blast radius, strongest callers,
   affected modules, applicable confirmed rules, suggested first files and caveats.
4. Rank before truncation and state what each cap removed. The brief has a measured token ceiling.
5. Make the brief available as a section of 305's evidence bundle and as explicit stdout; it is not
   committed by default.

## Constraints

- This is dynamic change context, not 266's static “when to use code-atlas” brief and not a reading
  syllabus.
- `RESOLVED`, `HEURISTIC`, stale, unindexed and truncated facts stay distinguishable.
- A file is suggested because a graph fact ranks it, never because a repository/framework name is
  hard-coded.
- No 25th MCP tool; the first surface is the Change Assurance shell workflow.

## Acceptance criteria

- A fixture change with planted callers/modules/rules produces the expected bounded brief from the
  same rows returned by the underlying tools.
- The highest-ranked resolved evidence survives a forced cap; HEURISTIC-only evidence cannot crowd
  it out.
- Missing roots, stale subjects, incomplete coverage and walk truncation each render an actionable
  caveat rather than an empty section.
- The committed token reporter proves the configured ceiling on fixture and pinned-sample inputs.
- Identical seeds and graph produce byte-identical Markdown.
- Removing any source tool's caveat makes a consumer-level test fail.

## Out of scope

- Deciding what code to write, editing source, generating a plan or asking an LLM to summarize.
- Curated reading order, page-per-module output or implicit prompt interception.

## References

[100](100_claim-signing-output-mode.md), [266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md),
[303](303_pre-pr-evidence-is-scattered-across-tools.md),
`code_atlas/tools/impact.py`, `code_atlas/tools/claim.py`,
`code_atlas/tools/impact_modules.py`, ENGINEERING_RULES R2, R4.1, R5.5, R5.6 and R5.8.
