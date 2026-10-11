---
id: 387
slug: agent-surface-names-382-385
title: 'An agent in a consuming repo cannot recognise 382–385: no map row, brief line or skill entry names a route, a claim re-run or a symbol-change check'
phase: 2
milestone: Adoption
status: todo
depends_on: [382, 383, 384, 385]
---

## Why this exists

382–385 shipped for the anchor project and their human docs landed with them (README, `docs/TOOLS.md`,
`docs/design/impact-and-claims.md`, CHANGELOG). The surfaces an **agent** reads were not touched:

- `RECOGNITION_MAP` (`code_atlas/tools/prompts.py`) — feeds `which_tool`, the server instructions'
  `core` rows and the generated plugin skill — has no row for "a URL / route a user reports" although
  `trace_capability(route=)` and `impact(routes=)` exist (385).
- The agent brief (`scripts/gen_skill.py` → `contrib/agent-brief.md`, written into a consumer's
  `AGENTS.md`) never names the shell route: `code-atlas query` / `--batch` (382), `--verify-claims`
  (383), `--snapshot-symbols` / `--changed-since` (384). These are not MCP tools, so no tool
  description can carry them.

So an agent in the anchor repo keeps re-implementing them by hand (its own URL→handler script,
eyeballing pasted claims, file-level diffs) — the very work 382–385 removed. The finding's subject is
the agent, so it generalises (PLAN §19, 2026-08-14).

## Scope

1. A recognition-map row routing a reported URL / route to `trace_capability` (`route=`).
2. Agent-brief: an occasion for "a bug report or test doc names a URL", and usage lines naming the
   shell route for batch answers, re-running pasted claims and per-symbol change since a revision.
3. Regenerate every `gen_skill.py` output; tool count stays 24; server-instructions cap (343) holds.

## Acceptance criteria

- **AC1:** `which_tool` and the generated skill contain a route row naming `trace_capability`.
- **AC2:** `contrib/agent-brief.md` names `code-atlas query`, `--verify-claims` and `--changed-since`,
  and has a URL occasion selecting `trace_capability`.
- **AC3:** the drift guards, doc budgets and the 2,048-char instructions cap stay green.

## Session status

- **KEY:** 387 · **work_doc_mode:** embed · **Current phase:** 0 refine · **Next action:** analysis. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · Run mode: `autorun 387 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/387-agent-surface-names-382-385` off `main`. Contract `.mango/run-contract-387.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 15 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 3 want-decision asked | 10 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `RECOGNITION_MAP` (`code_atlas/tools/prompts.py:24`), `trace_capability(route=)`, `impact(routes=)`,
`scripts/gen_skill.py`, `contrib/agent-brief.md`, `code-atlas query` with `--args` / `--batch` / `--verify-claim(s)` /
`--snapshot-symbols` / `--changed-since` (`code_atlas/query.py`), README, `docs/TOOLS.md`,
`docs/design/impact-and-claims.md` and CHANGELOG resolve.

**Recall.** 343-C1 (area: server instructions keep a 2,048-char prefix) → H1. 344-C3
(`verify-the-shipped-artifact-not-the-working-tree`) → every regenerated file is committed and checked by its drift guard.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,146 tokens) added H2, H8, H10.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the route row goes | how | `RECOGNITION_MAP`, `core=False`: the instructions render only `core` rows under `CLIENT_CAP` (`instructions.py:8`, 343-C1) |
| H2 | which tool the row names | how | `trace_capability` only — a row is one tool (`prompts.py:24`); its question (a URL someone reports) differs from the generic request-routing rows (`prompts.py:53-64`); `impact(routes=)` goes in the brief prose |
| H3 | how the URL occasion selects the route line | how | settled at design: `recognition_lines_by_tool` keeps the first line per tool (`gen_skill.py:316`) |
| H4 | where the shell route is named | how | not a tool (`main.TOOL_NAMES` stays 24), so no tool description can carry it: one constant in `gen_skill.py` rendered into both the brief and the skill (R6.7) |
| H5 | phrasing | how | generic, no anchor-repo name — an agent finding generalises (PLAN §19, 2026-08-14); R2 |
| H6 | tool count | how | stays 24 (ticket Scope 3) |
| H7 | regeneration | how | `python scripts/gen_skill.py --write`; every output is drift-guarded (`tests/test_skill_drift.py:24`) |
| H8 | release / version | how | a CHANGELOG `Unreleased` line, no bump: a release is cut separately (`CHANGELOG.md:16-18`, 381) and publishing one is a stop-and-confirm action (AGENTS.md) |
| H9 | the brief's size | how | `contrib/agent-brief.md` is outside the tier-1 chain (`tests/test_agent_chain_budget.py` never reads `contrib/`); R7.6 still caps the addition at a few lines |
| H10 | which brief sections carry the new lines | how | the URL occasion in `OCCASIONS`; the shell route under "How to spend the calls" (`gen_skill.py:331`) |
| W1 | write the brief into the anchor repo too? | want | **asked, settled by the maintainer:** no — code-atlas only |
| W2 | the acceptance bar | want | **ASSUMED (awaiting ratification):** presence in the generated surfaces, not a field measurement of agent behaviour (that is 200's) |
| W3 | drop the `route` / `routes` waivers once the brief teaches them | want | **ASSUMED (awaiting ratification):** yes. **Tripwire:** reverses 385's waiver (`tests/test_agent_brief_usage_completeness.py:22-23`); a waiver for a taught param is untrue |
