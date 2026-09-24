---
id: 318
slug: refusal-gate-misses-sibling-resolution-statuses
title: "313's usage-completeness gate reads refusal statuses from a hand-list, so the sibling unmodelled-resolution tokens dynamic_import and autoload ship untaught and unwaived"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [313, 296]
---

## Why this exists (#425 review — challenger/reviewer, not a field retro)

313 (#425) shipped a completeness gate that derives shipped params from AST and capabilities from live
signals, but its **refusal dimension enumerates a hand-curated set of five constants**
(`tests/test_agent_brief_usage_completeness.py:102-115`, `_refusal_reason_codes`). It reads each
constant's live *value* — so value-drift is caught — but the *membership* is maintained by hand. Two
sibling tokens in the same family escape it entirely: `RESOLUTION_DYNAMIC_IMPORT = "dynamic_import"`
(`contract.py:243`, 294/295) and `RESOLUTION_AUTOLOAD = "autoload"` (`contract.py:240`), both under the
same `UNMODELLED_RESOLUTION` comment block as the gated `RESOLUTION_DYNAMIC_SQL` (`:245`, 296). They
are the same "reads as absence" class an agent must know about, yet they are neither enumerated in the
gate, taught in the brief, nor waived — so 313's own goal ("impossible to *ship* a refusal status
untaught") is only partly enforced, and AC2's "(or a new refusal reason)" is exercised only via the
param path, never a genuinely new refusal constant.

## Goal

Make the refusal dimension of the gate cover **every** unmodelled-resolution strategy token from a
single shipped source, so adding a fourth token cannot ship untaught, and teach (or explicitly waive)
`dynamic_import` and `autoload`.

## Scope / Deliverables

1. **A single shipped registry of the strategy tokens** — group the three `RESOLUTION_*` tokens under
   `UNMODELLED_RESOLUTION` into one tuple/frozenset in `contract.py` (e.g. `UNMODELLED_RESOLUTION_STRATEGIES`),
   the source both the graph and the gate read. Not a contract bump — the vocabulary is unchanged.
2. **The gate derives the refusal set from that registry** instead of the hand-list in
   `_refusal_reason_codes` (`tests/test_agent_brief_usage_completeness.py:102-115`), keeping the
   non-strategy refusal codes (`roots_matched_nothing`, `walk_budget_exhausted`, `no_roots_configured`)
   as they are.
3. **Teach `dynamic_import` (and, if not waived, `autoload`) in the brief** via `scripts/gen_skill.py`
   USAGE_RULES, or record an explicit `REFUSAL_WAIVERS` entry with a stated why — the decision is made,
   not left implicit.

## Constraints

- R4.2: the gate stays deterministic (sorted/frozenset iteration, no network).
- 313's four measured gaps and its existing red-arm tests stay green.
- No `contract_version` bump — the three tokens already ship; this only groups them.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** The gate's refusal set is derived from a single shipped registry of unmodelled-resolution
  strategy tokens, not a hand-maintained membership list.
- **AC2** With the registry in place, `dynamic_import` and `autoload` are each either taught in the
  brief (greppable) or carry an explicit `REFUSAL_WAIVERS` entry — the gate is green with neither
  silently unhandled.
- **AC3** Red arm: adding a new strategy token to the registry with no brief teaching and no waiver
  turns the gate red and names it (mirrors the existing `brand_new_filter` param test).

## Out of scope

- Changing what the graph emits for any resolution strategy, or the strategies themselves.
- The param/capability dimensions of the gate — unchanged.

## References
`tests/test_agent_brief_usage_completeness.py:102-115` (`_refusal_reason_codes`), `:37-41`
(`REFUSAL_WAIVERS`); `code_atlas/contract.py:238-245`; `scripts/gen_skill.py` USAGE_RULES;
[313](313_the-agent-brief-teaches-prose-tied-to-nothing.md), ENGINEERING_RULES R4.2.
