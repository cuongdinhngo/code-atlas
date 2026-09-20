---
id: 306
slug: agent-change-brief-from-explicit-graph-seeds
title: "An agent starts with grep because no bounded change brief turns explicit seeds into the graph context it needs"
phase: 3
milestone: Change-Assurance
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 306 — Agent change brief (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 303/305 open PRs #408/#409 — branch includes 305 tip.
- **reviewer:** off · **challenger:** on

## Phase 0
`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`
**INPUT KIND:** ticket.
| H1 | Module | `code_atlas/change_brief.py` + `--brief`/`--brief-out` on check | ticket Scope; no 25th MCP tool |
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Analysis / Design
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R2 (change-type) ✅ · R4.1 (change-type) ✅ · R5.5 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`
`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_change_brief.py -q`

## Phase 3–5
Execute: change_brief + check flags + evidence_bundle section + tests + module count.
`REVIEWER: OFF` — waived.
`CHALLENGER: ON` — VERDICT CLEAN (agent 6fcb2fcc). Gate 4: challenger CLEAN; reviewer waived.
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
