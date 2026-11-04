---
id: 434
slug: shrink-tool-descriptions
title: "Shrink the model-facing tool surface — descriptions answer when to call, docs keep the edge cases"
phase: 2
milestone: Surface
status: todo
depends_on: [428]
---

## Why this exists

The headline is "~69× fewer tokens", but a client that loads the whole surface pays a large fixed cost
before the first question. Measured 2026-11-04 at `8c7f7a12` through `fastmcp.Client.list_tools()`:
**24 tools, descriptions 45,574 chars + input schemas 13,514 chars = 59,088 chars (~14.8k tokens by
`code_atlas/tokens.py`, chars/4)**. The six longest descriptions are `find_callers` 6,350,
`find_references` 4,876, `read_symbol` 4,456, `impact` 4,178, `search_symbol` 4,134 and
`get_index_status` 2,913. Each docstring is the tool's full spec: BFS frontier rules, paging per depth,
tier-filter mechanics, and ticket numbers a model cannot use.

Claude Code defers MCP schemas until ToolSearch loads them, so there the cost is paid per tool loaded,
about 8k tokens for the six tools the server instructions name. A client that loads every tool up
front pays all 59k chars. Decision (maintainer, 2026-11-04): **keep all 24 tools exposed by default**;
shrink first, and keep the `CA_TOOLS` preset opt-in.

## Acceptance

1. Each description: the question it answers → when to use it and when not to → the 2–4 parameters an
   agent sets → the key response fields, one line each. Target ≤ 600 chars per tool (≤ 900 for the
   three most complex), ≤ 15,000 chars of descriptions in total.
2. Edge-case semantics move verbatim to `docs/TOOLS.md`, one anchor per tool; nothing is deleted.
   Ticket and rule references (`(NNN)`, `task NNN`, `R\d.\d`) leave model-facing text. The lint matches
   those forms, not every three-digit number, because limits and caps are legitimate.
3. Input-schema `description` strings are trimmed the same way.
4. A CI-gated test holds the total and per-tool budgets and the reference lint, next to the
   `tests/test_agent_chain_budget.py` budgets. `tests/test_tool_descriptions.py` (069, question-first
   openers) and `tests/test_tool_manifest.py` (428) stay green, with the manifest regenerated.
5. `list_tools()` description + schema size falls by ≥ 60% from 59,088 chars; before and after are
   recorded here.
6. No regression: the tool-recognition probe (`docs/runbooks/tool-recognition-probe.md`) routes the same
   or better, and tokens-to-answer keeps its correctness at both tiers.
7. The fixed cost is stated per client in `docs/runbooks/tokens-to-answer.md`: full surface, versus the
   six tools loaded on demand.

## Out of scope

- Changing the default surface (`CA_TOOLS`): decided above.
- Trimming per-response metadata (brief A3) and counting fixed overhead in the headline benchmark
  (brief A5): their own tickets.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 434 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute.
- `TRACK: backend` · Run mode: `autorun 434 - 435 - 436 --no-reviewer`, third — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` ·
  `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/434-shrink-tool-descriptions` from `main` at `e08d4b75`. Contract `.mango/run-contract-434.txt`. RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`. Budget: unknown.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 1 want-decision asked | 2 how-decision resolved+cited | 1 ASSUMED | skip: no`

`docs/TOOLS.md`, `tests/test_tool_descriptions.py`, `tests/test_tool_manifest.py`, `docs/runbooks/tool-recognition-probe.md`
and `docs/runbooks/tokens-to-answer.md` resolve. The exposure-checker was not dispatched: the one acceptance-bar conflict
below is found by measurement, and the maintainer decided the default surface.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the model-facing text lives | how | the tool function's docstring is the description (`code_atlas/main.py` `FunctionTool.from_function`); it becomes the short form, and what it drops moves to a per-tool *Behaviour* anchor in `docs/TOOLS.md` (AC2), which carries no size budget (`tests/test_doc_size_budget.py` `BUDGETS`) |
| H2 | the reference lint | how | the forms AC2 names — `(NNN)`, `(NNN/NNN)`, `task NNN`, `R\d.\d` — never a bare three-digit number |
| W1 | AC3 vs AC5 | want | **ASSUMED (awaiting ratification):** the input schemas carry **no** `description` strings (13,514 chars of types, defaults, `maxLength`, `anyOf null`), so AC3 has nothing to trim and AC5's ≥ 60% must come from descriptions alone: ≤ 23,635 chars total ⇒ descriptions ≤ 10,121. The budget is **10,000 chars of descriptions**, per tool ≤ 600 (≤ 900 for three), which also meets AC1. The schemas are API types and stay. |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Out of scope) | 3 decomposed | ROWS: C=0 R=0 G=1 AC=7`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/30 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

W1 counts as self-resolved because the handover handed it back; it stays `ASSUMED` until the maintainer ratifies it.

**Probe baseline** (blind, one fresh `sonnet` agent shown only `main`'s `tests/fixtures/tool_manifest.json`, the runbook's
questions verbatim, no answer key; `K = 24 / 24` resident): surface **24 / 24**, occasion-fit **6 / 6** (O1 `find_callers`, O2
`get_index_status`, O3 `get_index_status`, O4 `get_index_status`, O5 `impact`, O6 `find_callers`).

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a client that loads the whole surface pays a large fixed cost" | the surface shrinks; routing does not regress | ⚠ |
| AC1 | Acc 1 | "Target ≤ 600 chars per tool (≤ 900 for the three most complex), ≤ 15,000 chars" | W1 tightens the total to 10,000 | ⚠ |
| AC2 | Acc 2 | "Edge-case semantics move verbatim to `docs/TOOLS.md`" | H1, H2 | ⚠ |
| AC3 | Acc 3 | "Input-schema `description` strings are trimmed the same way" | none exist (W1) — vacuous | ⚠ |
| AC4 | Acc 4 | "A CI-gated test holds the total and per-tool budgets and the reference lint" | new test; 069 and 428 stay green | ⚠ |
| AC5 | Acc 5 | "falls by ≥ 60% from 59,088 chars" | measured before/after | ⚠ |
| AC6 | Acc 6 | "the tool-recognition probe … routes the same or better" | re-run blind against the baseline | ⚠ |
| AC7 | Acc 7 | "The fixed cost is stated per client in `docs/runbooks/tokens-to-answer.md`" | a short section | ⚠ |

`BASELINE: green — tests/test_tool_descriptions.py, test_tool_manifest.py, test_routing_surface.py, test_tool_surface.py on main at e08d4b75: 88 passed`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5: the budget test seen red on main's surface · §7 (change-type) ✅ R7.2, R7.6 · §9 (change-type) ✅ R9.4: the surface change named in CHANGELOG, the manifest regenerated`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.**
1. Each `code_atlas/tools/*.py` tool docstring → question opener (069 rules) → when to use / not → the 2–4 parameters an
   agent sets → the key response fields, one line each. ≤ 600 chars (≤ 900 for `find_callers`, `find_references`, `impact`).
2. The dropped text moves **verbatim** under `docs/TOOLS.md` *Behaviour by tool*, one `### <tool>` anchor each.
3. New `tests/test_tool_surface_budget.py`: `list_tools()` descriptions ≤ 10,000 chars total, per-tool caps, the H2 lint,
   each arm seen red on a planted case; the totals measured through `fastmcp.Client` like 069.
4. Regenerate `tests/fixtures/tool_manifest.json`; CHANGELOG *Unreleased* names the surface change (R9.4).
5. `docs/runbooks/tokens-to-answer.md`: the fixed cost per client (full surface vs the six on demand), before and after.
6. Every test that asserts on description text moves to the new wording or to `docs/TOOLS.md`.

**Rejected:** a separate `description=` beside a long docstring — two texts drift and the long one is still in source as
the de-facto spec; shrinking the schemas — they are the API's types; making the six-tool preset the default — decided.
**Change list:** `code_atlas/tools/*.py` (24 docstrings), `docs/TOOLS.md`, new `tests/test_tool_surface_budget.py`,
`tests/fixtures/tool_manifest.json`, tests asserting description text, `docs/runbooks/tokens-to-answer.md`, `CHANGELOG.md`;
bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file).
**Proving test:** `tests/test_tool_surface_budget.py`; regression: the blind probe re-run, tokens-to-answer.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
