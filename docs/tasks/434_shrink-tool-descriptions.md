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
