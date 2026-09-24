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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 318 — refusal gate reads a strategy registry (working doc)

- **Ticket:** 318 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/318_refusal-gate-misses-sibling-resolution-statuses.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — PR #441 open; never merge

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Recalled: `184-C6` (`derived-not-listed-invariant`) — a hand-kept inventory beside data that already holds it is the drift R6.7 forbids; 318 is its gate-shaped sighting.

- H1 (how, cited Scope 3 "Teach `dynamic_import` (and, if not waived, `autoload`)"): both are taught, none waived — each has the same reads-as-absence failure as `dynamic_sql`, and both reach `find_orphans`' `resolution_unmodelled` (`find_orphans.py:88-101`, any stamp).
- H2 (how, cited Scope 1 "the source both the graph and the gate read"): the graph half is a test — every stamp the four adapters emit on their `unmodelled_resolution/` fixtures must be in the registry; the core's stamp reader stays unfiltered (Out of scope: "Changing what the graph emits").

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | refusal dimension covers every strategy token from one source; teach or waive both | registry + derived gate + two teachings | D1–D3 | AC1–AC3 | ✅ |
| R1 | Scope 1 | one shipped registry the graph and the gate read; not a bump | `UNMODELLED_RESOLUTION_STRATEGIES` | D1 | registry + adapter-stamp tests | ✅ |
| R2 | Scope 2 | gate derives the refusal set from it; non-strategy codes unchanged | `*contract.UNMODELLED_RESOLUTION_STRATEGIES` | D2 | AC1 | ✅ |
| R3 | Scope 3 | teach via `gen_skill.py` USAGE_RULES or waive, decided | one rule, both tokens | D3 | AC2 | ✅ |
| C1 | Constraints | R4.2 deterministic | tuple order; no network | D1 D2 | review | ✅ |
| C2 | Constraints | 313's four gaps and red arms stay green | existing file unchanged but for the derivation | D2 | `test_agent_brief_usage_completeness.py` | ✅ |
| C3 | Constraints | no `contract_version` bump | stays 10 | D1 | registry test | ✅ |
| C4 | Constraints | comments ≤ 3 lines | R7.5 | all | review | ✅ |
| AC1 | AC | refusal set derived from the registry, no hand membership | AST: no `RESOLUTION_*` strategy named | D4 | proving | ✅ |
| AC2 | AC | both taught (greppable) or waived; gate green | backticked needles | D4 | proving | ✅ |
| AC3 | AC | red arm: new token, no teaching, no waiver → named | monkeypatched registry | D4 | proving | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

- Q1 → H1; Q2 → H2.

## Phase 1 — Analysis

- Root cause (`validation`): `_refusal_reason_codes` (`tests/test_agent_brief_usage_completeness.py:102-115`) names `contract.RESOLUTION_DYNAMIC_SQL` by hand; its two siblings (`contract.py:240`, `:243`) have no grouping to derive from.
- Blast radius: the gate file, `contract.py` (one new tuple), the rendered brief (`contrib/agent-brief.md`, `contrib/skill/SKILL.md`, regenerated by `gen_skill.py --write`).

`TRACK: backend — 0/5 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 3 by change-type | 1 by recalled handle — R3.1 (change-type) ✅ grouping only, no bump · R4.2 (change-type) ✅ tuple order · R6.5 (change-type) ✅ red arm plus a removed-rule mutation · R6.7 (recalled handle derived-not-listed-invariant) ✅ membership derived from the registry`

Baseline record — tree `14cae92` (historical: shared with 321, same base). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider` → `4394 passed, 4 skipped in 371.77s`.

`BASELINE: green`

## Phase 2 — Design

- A1 `contract.UNMODELLED_RESOLUTION_STRATEGIES = (RESOLUTION_AUTOLOAD, RESOLUTION_DYNAMIC_IMPORT, RESOLUTION_DYNAMIC_SQL)`.
- A2 the gate unions reach statuses with the registry; the default refusal needle is the backticked token, so prose about PSR-4 autoloading cannot keep `autoload` green.
- A3 one USAGE_RULES line teaching both, beside the `dynamic_sql` rule; artifacts regenerated.
- Rejected: two waivers (the tokens are the same absence trap `dynamic_sql` is taught for); filtering unknown stamps in `store.py` (changes what the graph reports — Out of scope).

**Assumptions:** `find_orphans` refuses on any stamped strategy, not only `dynamic_sql` — verified (`find_orphans.py:88`, `if stamped:`).

| Handle | Answer |
|--------|--------|
| `derived-not-listed-invariant` | traced — see below |

Trace record — tree `4eac2db5bea5b1b559455f0ab06a10c777221d2f`. Command `grep -n "UNMODELLED_RESOLUTION_STRATEGIES" code_atlas/contract.py tests/test_agent_brief_usage_completeness.py`:

```
tests/test_agent_brief_usage_completeness.py:113:            *contract.UNMODELLED_RESOLUTION_STRATEGIES,
code_atlas/contract.py:248:UNMODELLED_RESOLUTION_STRATEGIES: tuple[str, ...] = (
```

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | registry | code_atlas/contract.py | named-subset sweeps (tier-2 words absent) | R1 C3 | 1/1 |
| D2 | derived refusal set, backticked default needle | tests/test_agent_brief_usage_completeness.py | 313's gate | R2 C2 | 1/1 |
| D3 | teaching rule + regenerated artifacts | scripts/gen_skill.py · contrib/agent-brief.md · contrib/skill/SKILL.md | brief golden + budget tests | R3 | 1/1 |
| D4 | proving tests | tests/test_refusal_gate_strategy_registry.py | new file | AC1–AC3 | 1/1 |
| D5 | 184-C6 seen, BACKLOG, ticket, ledger | docs/* | bookkeeping tests | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | logic | unit (AST over the gate) | n/a | ✅ |
| AC2 | logic | unit (rendered brief) | n/a | ✅ |
| AC3 | logic | unit (monkeypatched registry) | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_refusal_gate_strategy_registry.py -q`

Rollback: revert the branch. Porting: single repo.

`SCOPE: S` (unchanged)

## Phase 3 — Execute

**Branch:** fix/318-refusal-gate-registry

Pre-change record — tree `14cae92` plus the uncommitted proving test (historical): `8 failed`.

Mutation record (historical, not committed): the rendered brief with the new rule's line removed → `_missing_surface_items` = `['refusal:autoload', 'refusal:dynamic_import']`.

Sweep record — tree `4eac2db5bea5b1b559455f0ab06a10c777221d2f`. Commands: the proving test plus the brief/skill/budget/contract/unmodelled suites (re-run on this tree), `mypy code_atlas`:

```
165 passed in 14.07s
Success: no issues found in 93 source files
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — A1–A3 implemented-as-approved`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN (11 met, 0 not met, 0 can't tell). Probes: the AST invariant, the PSR-4 incidental-mention loophole (closed by backticked needles), an independent AC3 replay, no adapter or version change, and `find_orphans`' claim read in code (`find_orphans.py:88-100`).

Verdict: `clean (challenger only — REVIEWER: OFF)`

## Phase 5 — Finalise

Outward (handover-authorised only): pushed `fix/318-refusal-gate-registry`, opened [#441](https://github.com/cuongdinhngo/code-atlas/pull/441). Never merge.

Durable lesson: `184-C6` (`derived-not-listed-invariant`) seen 184, 318 → recurring type-2 claim; destination R6.7 already cites it — proposed as `/mango:promote` evidence, **not written**. Falsification: still true — the AST test fails if a strategy constant is hand-named again.

Revert: revert the PR.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | 73,084 |

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: 73,084 (subagent dispatch only) · top cost driver: review/challenger round 1`
