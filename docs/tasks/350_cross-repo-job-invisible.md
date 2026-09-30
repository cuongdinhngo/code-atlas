---
id: 350
slug: cross-repo-job-invisible
title: 'The cross-repo job is outside the gate and absent from the orientation docs, so its floors drift unseen'
phase: 2
milestone: Coverage
status: done
depends_on: [018, 349]
---

## Why this exists

349 found the cross-repo floors stale for 16 days after 258 moved the counts by design. Nothing
told an agent the job existed: `AGENTS.md` never named it, `scripts/gate.sh` never runs it, and its
runbook listed six of the manifest's eleven samples and exported two of its four adapter commands.
The first GitHub run was 2026-09-28, the day after the repo went public, and it failed.

## Scope

1. `docs/AGENT_BRIEF.md` P8, ratified by the maintainer on 349's incident: a change that moves
   graph counts runs `scripts/cross_repo_validate.py --public-only` and re-floors in the same PR.
   Claim 349-C1 retires to it.
2. `AGENTS.md`: one line under the gate section pointing to P8. Paid for by cutting the stale
   private-repo Actions clause, the 237/220 archaeology and a duplicated `ci.yml` sentence.
3. `docs/runbooks/cross-repo-validation.md`: all eleven samples, the Python and SQL adapter
   commands, the re-floor rule, and that the job runs outside the gate.

## Proof

`tests/test_doc_size_budget.py` and `tests/test_agent_chain_budget.py` green at the existing
budgets; `scripts/gate.sh` GATE GREEN.
