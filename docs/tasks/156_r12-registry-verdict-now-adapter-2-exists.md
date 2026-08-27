---
id: 156
slug: r12-registry-verdict-now-adapter-2-exists
title: R1.2's condition is met — adapter #2 exists, so the registry verdict has to be written down either way
phase: 2
milestone: M7
status: done
depends_on: [019]
---

## Why this exists

R1.2 defers every plugin registry, base class, factory and DI container *"until adapter #2 (TS/JS)
exists and proves the shape"*. As of [019](019_typescript-adapter.md) it exists. The rule's condition
is therefore satisfied, and the answer — whichever way it goes — is now owed in writing: leaving it
implicit is how "YAGNI" quietly becomes "nobody looked".

The expected answer is **no registry**, and the evidence is already in the tree: `indexer._announce`
(`indexer.py:576`) loops `config.adapter_cmds`, and the extension→adapter map is built from what each
adapter announces, so a second language cost **zero** new abstraction — the empty core diff on 019's
PR is the proof. But "expected" is not "recorded", and the reverse case deserves a fair read too: 019
did add a per-adapter registry on the *test* side (`tests/contract/adapter_registry.py`, task 147),
which is worth naming as the one place a table earned its keep.

## Scope / Deliverables

- A written verdict in PLAN §19 (the decision log): registry or no registry, with the evidence, and
  what would reverse it.
- R1.2's own text updated to record that its condition has been met and what the answer was, so the
  next reader is not sent to re-derive it.
- If the answer is *no registry*: say explicitly which mechanisms already do the job
  (`config.adapter_cmds`, the announced-extension map) so a future adapter author does not invent one.
- If the answer is *a registry*: the minimal one, and nothing more — but that is a change to the core
  and would need its own ticket, not this one.

## Acceptance criteria

1. PLAN §19 carries the verdict with a date and the evidence cited by path.
2. R1.2 in `docs/ENGINEERING_RULES.md` states that adapter #2 landed and what the answer was.
3. No core code changes in this ticket. It is a decision record; a decision to *build* something is a
   separate ticket (which is the honest outcome either way).

## Out of scope

- Adapters #3–#4. Still deferred (PLAN §19) and not evidence for this question.

## References

ENGINEERING_RULES R1.2, R1.3; `code_atlas/indexer.py:576`; `tests/contract/adapter_registry.py`;
PLAN §19; tasks 019, 147.

---

## Session status

- **KEY:** 156 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** docs-only, no runtime code. Guarded by `tests/test_doc_size_budget.py` + `tests/test_agent_chain_budget.py` (tier-1 ≤ 25k) staying green.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

All 5 references resolve: R1.2 (`ENGINEERING_RULES.md:27`), `indexer._announce` (`indexer.py:576`), `config.adapter_cmds` (`config.py:87`), `tests/contract/adapter_registry.py`, PLAN §19. The one decision — registry or not — is a HOW resolved by evidence (the empty 019 core diff), not a want-decision: the ticket states the expected answer and this is a decision *record*, not a design choice for the user.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** S · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §R1.2 (change-type) ✅ · §R7.6 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — docs-only; no runtime code changes (AC3). Guarded by the two doc-budget tests staying green; verified via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | "the answer is owed in writing" | Record R1.2's now-met condition + verdict so nobody re-derives it | open |
| R1 | Scope 1 | verdict in PLAN §19 with evidence + what reverses it | §19 block: NO registry, cited by path, reversal condition | open |
| R2 | Scope 2 | R1.2 text updated: condition met + the answer | R1.2 gains the verdict | open |
| R3 | Scope 3/4 | if no registry, name the mechanisms that already do the job | cite adapter_cmds + announced-extension map | open |
| AC1 | AC1 | §19 carries verdict with date + evidence by path | Falsifiable by inspection: date + `file:line` cites present | open |
| AC2 | AC2 | R1.2 states adapter #2 landed + the answer | Falsifiable by inspection | open |
| AC3 | AC3 | no core code changes | Falsifiable: diff touches only docs | open |
| C1 | Out-of-scope | adapters #3–#4 not evidence | boundary | binding |
| C2 | R7.6 | prune as you add; doc-size budget green | doc-budget tests stay green | binding |

### AC validation

All three ACs are falsifiable by inspection + the doc-budget gate. No want-decision (verdict is evidence-derived, cited). No AC-value mismatch.

### Root cause (taxonomy: config)

R1.2 named a condition ("until adapter #2 exists") that 019 satisfied, but nothing recorded the resulting verdict — leaving "YAGNI" indistinguishable from "nobody looked."

### Blast radius

`docs/PLAN.md` (§19 verdict), `docs/ENGINEERING_RULES.md` (R1.2), the task file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`. No `code_atlas/`, no tests, no adapter (AC3).

## Phase 2 — design

### Approach

Write the verdict in both places, evidence-cited: **NO core registry.** The announce-handshake +
`config.adapter_cmds` + `extension_index`/`_owners` already select adapters from data; the 019 core
diff was empty; the only per-adapter table is test-side (147). Reversal condition stated: an adapter
needing core-side per-language behaviour → its own ticket.

**Prune-as-you-add (R7.6).** PLAN was at its 24k ceiling, so the verdict block required removing what
it supersedes: the §2 "expect contract v2 / registry-until-#2" speculation, two now-retired risk-table
rows, the M7 "expect contract v2" prediction (019 needed none), and a redundant 059 caveat sentence.
This also repaired a latent breach the 150 merge left on `main` — its BACKLOG narrative expansion and
two `todo`→`done` status syncs slipped past 150's delta-green because that image was built before the
final edits; the doc-size and backlog-bookkeeping gates on this branch caught and fixed both.

### Rejected alternatives

- **Build a minimal registry now** — R1.2's own logic: two implementations revealed the abstraction is *the contract*, not a registry; building one would be the "invents the wrong one" failure. Rejected on the evidence.
- **Record only in PLAN §19, not R1.2** — the next reader meets R1.2 first; leaving its condition open re-sends them to re-derive. AC2 requires the rule itself carry the outcome.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | docs | §19 block w/ date + path cites | ✅ |
| AC2 | docs | R1.2 verdict text | ✅ |
| AC3 | process | diff is docs-only | ✅ |

### Proving test

No runtime test — this is a decision record (AC3 forbids code). The guarding tests are
`tests/test_doc_size_budget.py` and `tests/test_agent_chain_budget.py` (tier-1 ≤ 25k): both must stay
green after the R1.2 addition, proving the record was added without breaching the doc budget. ACs are
otherwise inspection-falsifiable. Invocation: `pytest tests/test_doc_size_budget.py tests/test_agent_chain_budget.py -q`.

### SCOPE

`SCOPE: S` — two doc edits + bookkeeping. Branch `feat` (a recorded verdict enabling future work).

## Phase 3 — execute

**Branch:** `feat/156-registry-verdict`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| PLAN §19 verdict block (NO registry, evidence by path, reversal condition) | implemented-as-approved |
| R1.2 text records condition-met + verdict + mechanisms | implemented-as-approved |

No deviations. `SCOPE: S` held.

### Verification sweep (Axis 1)

Diff = `docs/PLAN.md`, `docs/ENGINEERING_RULES.md`, `docs/tasks/156_*.md`, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md`. No `code_atlas/`, no tests, no adapters (AC3 satisfied).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | PLAN §19 "Decision — R1.2 registry verdict" block (date 2026-08-27 + `config.py`/`indexer.py`/`adapter.py` cites) |
| AC2 | R1.2 in `ENGINEERING_RULES.md` (condition-met + NO-registry verdict) |
| AC3 | verification sweep: diff docs-only |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

A decision record produces no new durable engineering lesson — the verdict itself lives in PLAN §19 and R1.2, which is where it belongs.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Delta-green (Docker / Linux)

`full suite → 2133 passed, 1 skipped, 0 failed (151.67s)` — includes `test_doc_size_budget`,
`test_agent_chain_budget`, and `test_backlog_bookkeeping` (all three the R7.6 pruning + frontmatter
syncs had to satisfy). Bare pytest on Windows can't collect the doc tests that import `code_atlas`
(`fcntl`) — the recorded platform exclusion.

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: docs-only diff (AC3), all doc-validating gates green in Docker. Maintainer reviews on the PR.
