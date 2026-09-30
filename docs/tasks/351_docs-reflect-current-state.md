---
id: 351
slug: docs-reflect-current-state
title: 'The standing docs lag the code: phase-2 delivery, 0.2.0, contract 13 and several phase-1 changes'
phase: 2
milestone: Adoption
status: done
depends_on: [343, 344, 345, 346, 347, 348, 349, 350]
---

## Why this exists

The maintainer asked for every doc to reflect code-atlas as it is on 2026-09-30. Phase 2 shipped a
plugin, four hooks, contract v13 and the first versioned release in four days, and the audit also
found phase-1 changes the standing docs never absorbed (258, 259, 260, 025, 117, 232).

## How it was audited

Five read-only auditors, one per doc group, each checking claims against code (`path:line` or a
command's output) and reporting WRONG / STALE / MISSING, with no guesses:

- root docs (README, CONTRIBUTING, SECURITY, CHANGELOG, AGENTS);
- PLAN and BACKLOG;
- TOOLS, CONVENTION and ENGINEERING_RULES;
- `design/`, `runbooks/` and ADAPTER_PLAYBOOK;
- adapter and contrib READMEs, `onboarding_llm/` and `phase3-onboarding/`.

Every finding was re-checked against the code before it was applied. Dated records were left alone:
`benchmarks/`, `tasks/`, LESSONS and TOKEN_LEDGER.

## What changed

- **Phase-2 delivery.** Plugin install, five hooks, the `additionalContext` channel, the skew line,
  `rebuild required`, `symbol_shapes`, and release discipline, updated in PLAN, TOOLS, CONVENTION,
  ENGINEERING_RULES R3.1, AGENTS, CONTRIBUTING, SECURITY, the contrib READMEs, ADAPTER_PLAYBOOK and
  the upgrade runbook.
- **Phase-1 drift.** Covered:
  - 258: one unresolved CALL, and proximity candidates.
  - 259: `CA_PAGE_LIMIT` versus the build-time fan-out.
  - 260: the fit-counter handle.
  - 025: PHP construct coverage.
  - 232: TS `REFERENCES`.
  - 117: the `ProseWriter` seam and the LLM model defaults.
  - 268: `minimal` defaults.
  - The CI identity guard.
- **Stale line citations.** Replaced by file or symbol names, which do not drift.
- **Generated brief.** Its hook sentence was fixed at the source (`scripts/gen_skill.py`) and
  regenerated.

## Left as is

- CONVENTION §3 does not list the `symbol_shapes` vocabulary (§5 names it and `contract.py` holds
  it). The file is at its budget.

## Proof

- `tests/test_doc_size_budget.py` and `tests/test_agent_chain_budget.py` pass at the existing
  budgets: every addition was paid for by pruning.
- `scripts/gen_skill.py` check exits 0.
- `scripts/gate.sh` is GATE GREEN.
