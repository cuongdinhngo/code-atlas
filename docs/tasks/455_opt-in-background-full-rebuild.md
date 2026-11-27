---
id: 455
slug: opt-in-background-full-rebuild
title: "A repo that opted in rebuilds in the background on a contract change, instead of waiting on `rebuild required`"
phase: 2
milestone: Freshness
status: done
depends_on: [453, 356]
---

## Why this exists

Epic 451. `code-atlas-refresh` never runs a full rebuild (`hooks/refresh.py:67-69`, 053), and the
anchors' session hook stops at `incomplete` ("a human's call"). After an upgrade the index stays on
`rebuild required` until someone types the command; this repo shows it today (index v20, server v21).
The reason was a killed build leaving no index; 356 now builds behind a shadow and keeps serving the
old one, so that risk is gone.

## Scope

1. `code-atlas-setup` asks once (default no) whether this repo allows a background full rebuild;
   the answer is recorded under `.code-atlas/`.
2. Where allowed, SessionStart, on a contract change or `incomplete`, starts a detached
   (`setsid`, outside the hook's timeout) `code-atlas-build --full` under the write lock and says so
   in one line; a build already running starts nothing.
3. Where not allowed, the state line is unchanged.
4. PLAN §19 records the reversal of 202 / 053 for opted-in repos.

## Acceptance criteria

- **AC1:** an index stamped with an older contract, consent recorded → one detached full build
  starts; the old index answers until it publishes.
- **AC2:** no consent → no build, byte-identical state line.
- **AC3:** two session starts in a row start one build.
- **AC4:** killing the hook process does not kill the build.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 455 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 452 - 453 - 454 - 455 - 451`, fourth — `REVIEWER: OFF` (waived: "with
  skipped reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a
  want-decision is `ASSUMED`, never silent.
- Branch `feat/455-opt-in-background-full-rebuild` from 454's tip `2281b927`, in a worktree. Contract
  `.mango/run-contract-455.txt`; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

`hooks/refresh.py:67-69`, 053, 202, 356 and `code-atlas-setup` resolve. Recalled by handle: 454-C1
`per-call-hook-reads-the-cheapest-signal` (the state hook decides). Exposure-checker ran before any code: 3 returned
(W3–W5).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | detach | how | its own session (`start_new_session`, `DETACHED_PROCESS` on Windows), the same launcher as 454's refresh |
| H2 | one build | how | the build lock (R4.3) plus a marker holding when the last start was |
| H3 | the old index meanwhile | how | 356: a full rebuild builds a shadow and keeps serving the live one |
| W1 | how consent is asked | want | **ASSUMED:** `code-atlas-setup --auto-rebuild` / `--no-auto-rebuild`, recorded, default `ask`; no prompt (setup also runs non-interactively) |
| W2 | the trigger | want | **ASSUMED:** SessionStart only, on `full_rebuild_required` or `incomplete`; never from git hooks or the refresh |
| W3 | a failed rebuild | want | **ASSUMED:** at most one start per six hours; the line names when it started and the log, never a retry loop |
| W4 | after it finishes | want | **ASSUMED:** nothing extra — the `rebuild required` clause disappears with the stale index |
| W5 | what consent covers | want | **ASSUMED:** the flag's help names the cost (minutes of CPU on a large repo) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=0 R=4 G=1 AC=4`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "After an upgrade the index stays on `rebuild required` until someone types the command" | consented repos rebuild themselves | ✅ |
| R1 | Scope 1 | "`code-atlas-setup` asks once (default no) … recorded under `.code-atlas/`" | W1 | ✅ |
| R2 | Scope 2 | "starts a detached … `code-atlas-build --full` under the write lock and says so in one line; a build already running starts nothing" | H1, H2 | ✅ |
| R3 | Scope 3 | "Where not allowed, the state line is unchanged" | AC2 | ✅ |
| R4 | Scope 4 | "PLAN §19 records the reversal of 202 / 053 for opted-in repos" | one §19 line | ✅ |
| AC1 | Acc 1 | "older contract, consent recorded → one detached full build starts; the old index answers until it publishes" | stand-in build records `--full`; 356 holds the second half | ✅ |
| AC2 | Acc 2 | "no consent → no build, byte-identical state line" | equality with the unflagged line | ✅ |
| AC3 | Acc 3 | "two session starts in a row start one build" | marker | ✅ |
| AC4 | Acc 4 | "killing the hook process does not kill the build" | SIGKILL the hook, the build still writes | ✅ |

**Gap.** `state_line` names `rebuild required` and starts nothing; `code-atlas-refresh` never full-builds (053).

`BASELINE: green — state, setup, guard, build CLI, instructions, language-agnostic, doc-budget and contrib suites: 431 passed`

Ran at 2281b927 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-455.list)
431 passed in 32.59s
```

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 the state hook names no language, R1.4 no SQL outside store.py · §4 (change-type) ✅ R4.2 without consent the line is byte-identical (AC2) · §5 (change-type) ✅ R5.5 a failed start is named on the line, never retried in a loop · §6 (change-type) ✅ the proving test is seen failing on the base · §7 (change-type) ✅ R7.6 the PLAN entry folds into §19 and the profiler line points at its runbook · §9 (change-type) ✅ R9.1 the consent is read as one of two values, R9.3 the marker and log go through containment`

## Phase 2 — design

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `per-call-hook-reads-the-cheapest-signal` — does not apply because the rebuild branch runs once per session start
  inside the state line, which already builds the status payload; it adds a marker read, no per-call cost.

**Approach.** (1) `setup_hooks.script_path` generalises `refresh_command`; `rebuild_consent`; `--auto-rebuild` /
`--no-auto-rebuild` recorded as `rebuild`, kept on re-run. (2) `state.start_rebuild` + a shared `_detach`;
`state_line(refresh=True)` calls it on `full_rebuild_required` or `incomplete`. **Rejected:** starting it from the
git hooks (a pull would launch a minutes-long build in an IDE); an interactive prompt (setup also runs on a first
build without a terminal). **Assumptions:** a process in its own session survives the hook's kill — `verified` by
AC4's test. **Proving test:** `tests/test_background_rebuild.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| consent | `code_atlas/setup_hooks.py` | `test_code_atlas_setup.py` | R1 |
| rebuild | `code_atlas/hooks/state.py` | `test_session_state_hook.py` (the older-era test runs main without consent) | R2, R3 |
| proving test | `tests/test_background_rebuild.py` | — | AC1–AC4 · 4/4 |
| docs | `docs/TOOLS.md`, `README.md`, `docs/PLAN.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R4, R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | — | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | runtime (a spawned process) | integration: a stand-in build records its argv | n/a | ✅ |
| AC4 | runtime (process lifetime) | integration: SIGKILL the hook process, the build still runs | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert; `code-atlas-setup --no-auto-rebuild` turns it off per repo. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer`, in a worktree, at `bd08fbc5`. **Sweep.** Axis 1: the diff is the approved list; `ruff`
and `mypy` clean. Axis 2: approach (1)–(2) implemented-as-approved. Deviation: PLAN §2's profiler sentence now
points at the onboarding runbook, which already holds it (R7.6, to fit the new §19 line under the budget).

Ran at 2281b927 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_background_rebuild.py
5 failed in 3.73s
```

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone; payload = the raw ticket (`git show 2281b927:<this file>`) + the branch diff, working doc excluded.

- **Round 1** at `68f23baa` (71,924 tokens): 8 rebuilt · 6 met · 2 not met. **Taken** (`f7efb12b`): the `behind` refresh
  branch ran before the rebuild branch, so an upgrade followed by a pull — the common case — started a refresh that
  refuses and never the rebuild, while the line said "refreshing"; the marker now follows a real start, so a failed
  start does not block retries for six hours. **Accepted:** consent is a flag, not a prompt (W1); a second contract
  change inside six hours is named, not rebuilt (W3); the §19 line is terse.
- **Round 2** (resumed, verify-only, at `f7efb12b`): the fix and its test verified.

`CHALLENGER VERDICT: 8 requirement(s) rebuilt | 8 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at f7efb12b
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-455.list) tests/test_background_rebuild.py
437 passed in 42.96s
```

Reviewed at f7efb12b — files: `code_atlas/setup_hooks.py`, `code_atlas/hooks/state.py`, `tests/test_background_rebuild.py`,
`docs/TOOLS.md`, `README.md`, `docs/PLAN.md`, `CHANGELOG.md`; working doc
`docs/tasks/455_opt-in-background-full-rebuild.md`.

`Ph3/4 proven by`: R1–R3, AC1–AC4 → `tests/test_background_rebuild.py` (6); R4 → the §19 line.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after the review — not stale.

**Durable lesson.** 455-C1 `the-stronger-remedy-is-checked-first` (type 2, first sighting) in `docs/LESSONS.md`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/455-opt-in-background-full-rebuild`; open its PR against
`feat/454-session-refresh-and-guard-in-product` (stacked), published as one commit carrying this tree. Deferred to
the maintainer: ratify W1–W5; merge after #185.

Next: close epic 451. Revert: revert the commit; `code-atlas-setup --no-auto-rebuild` turns it off per repo.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,193 |
| 4 review | ticket-blind `challenger` | 1 | 71,924 |
| 4 review | ticket-blind `challenger` | 2 | 2,703 (resumed: 74,627 cumulative − 71,924) |

`LEDGER TOTAL: 122,820 · top cost driver: 4 review / challenger` — main loop unmeasured.
