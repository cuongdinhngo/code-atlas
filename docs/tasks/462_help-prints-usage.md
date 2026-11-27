---
id: 462
slug: help-prints-usage
title: "`code-atlas --help` prints usage instead of starting the MCP server"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: []
---

## Why this exists

Same field report as 456. `code-atlas --help` (and `-h`) starts the MCP stdio server and waits on stdin,
so there is no usage. An agent checking whether `verify_refs` can run in CI concluded it was
**MCP-only** and wrote that into the consumer's ADR. In fact `code-atlas query --verify-refs …
--fail-on moved,gone` exists, and only the README (`README.md:396`) says so. The CLI is the
part that makes a CI gate possible, and nothing on the command line shows it.

## Scope

1. `code-atlas --help` / `-h` prints usage and exits 0: the subcommands (`query`, …), the main
   `query` flags (`--verify-refs`, `--format`, `--fail-on`, `--refs-diff`), and one line saying that
   no arguments starts the MCP server.
2. `code-atlas query --help` lists every query flag (argparse's own help is enough).
3. No arguments → the MCP server, as today (hosts launch it that way).

## Acceptance

1. Test: `--help` exits 0 within 2 s with stdin closed, and its output contains `--verify-refs`.
2. Test: no arguments still serves MCP (the existing smoke test passes).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #195, then this PR — the last of the stack
- **Blocked on:** nothing
- **KEY:** 462 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, seventh and last —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/462-help-prints-usage` from 461's tip `0211fc35` (rebased there after 461's gate finding and doc scrub), in a worktree. Contract `.mango/run-contract-462.txt`;
  RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 1 want-decision asked | 9 how-decision resolved+cited | 1 ASSUMED | skip: no`

`code_atlas/main.py` `main()`, `code-atlas query --verify-refs` and `README.md:396` resolve. Exposure-checker: 6
returned (H5–H9, W1).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the trigger | how | `-h` / `--help` before a subcommand prints usage and exits 0 without reading config (Scope 1) |
| H2 | the content | how | `query` and its CI flags, `--expect-version`, the no-argument line; the sibling commands read from the installed entry points, not a hand list (Scope 1) |
| H3 | `query --help` | how | argparse's own (Scope 2) |
| H4 | no argument | how | the MCP server, as today (Scope 3) |
| H5 | `--help` after another argument | how | still usage — an agent appends it; a host passes none of these |
| H6 | an unknown flag | how | serves, as today (Scope 3) |
| H7 | docs | how | a README line where the CLI is described, and CHANGELOG |
| H8 | the test's bar | how | the ticket's own: exit 0 within 2 s, stdin closed, `--verify-refs` in the output |
| H9 | `query -h` | how | argparse's short form |
| W1 | the bare word `help` | want | **ASSUMED:** usage too |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=2`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "nothing on the command line shows it" | the CLI is discoverable | ✅ |
| R1 | Scope 1 | "`code-atlas --help` / `-h` prints usage and exits 0" | H1, H2 | ✅ |
| R2 | Scope 2 | "`code-atlas query --help` lists every query flag" | H3 | ✅ |
| C1 | Scope 3 | "No arguments → the MCP server, as today" | H4 | ✅ |
| AC1 | Acc 1 | "exits 0 within 2 s with stdin closed, and its output contains `--verify-refs`" | the test | ✅ |
| AC2 | Acc 2 | "no arguments still serves MCP (the existing smoke test passes)" | `test_mcp_server.py` stdio test | ✅ |

**Gap.** `main()` reads no flag but `--expect-version`; `--help` falls through to `build_server(config).run()`.

`BASELINE: green — the MCP-server, query CLI, language-agnostic and doc suites: 766 passed`

Ran at 0211fc35 (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-462.list)
766 passed in 27.08s
```

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5 seen failing on the base, R6.7 the sibling commands come from the entry points · §7 (change-type) ✅ R7.5 comments ≤ 3 lines, R7.6 one README clause · §9 (change-type) ✅ R9.1 usage reads no config and no repo file`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** (1) `main.usage()`; (2) `main()` prints it for `HELP_ARGS` and exits 0, before the version check and
the config. **Rejected:** an argparse parser for `main()` — it would reject the flags hosts pass and change the
no-argument path (Scope 3). **Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| usage | `code_atlas/main.py` | `test_mcp_server.py` (the stdio launch) | R1, C1 |
| proving test | `tests/test_help_prints_usage.py` | — | AC1 · 2/2 |
| docs | `README.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime (a spawned process) | integration: `python -m code_atlas.main --help`, stdin closed, 2 s | n/a | ✅ |
| AC2 | runtime (stdio MCP) | integration: the existing real-client stdio test | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_help_prints_usage.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `bae79ddc`. **Sweep.** Axis 1: the diff is the approved list; `ruff`, `mypy` clean.
Axis 2: (1)–(2) implemented-as-approved. The usage's tool line was checked against `query`'s parser: a tool takes
`--args JSON`.

Ran at 0211fc35 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_help_prints_usage.py   # base + the new test only
2 failed in 1.35s
```

At `bae79ddc` (superseded by the review round) the suites read `768 passed`; Phase 4 holds the reviewed tree's run.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show 360f5880:<this file>`, identical at `0211fc35`) + the branch diff.

- **Reviewer round 1** at `bae79ddc` (58,687 tokens): LGTM; three suggestions **taken** (`013d255f`): the `--fail-on`
  line read as one set while `--undocumented` takes only `any`; a guard that every flag `usage()` names is one
  `query --help` prints (R6.7 — the help text is a hand list); `help` and `--expect-version 0.0.0 --help` pinned.
- **Reviewer round 2** (verify-only, main loop, at `013d255f`): the three as described.
- **Challenger round 1** at `bae79ddc` (53,390 tokens): 7 rebuilt · 7 met. Its unchecked "exit 3" is `query.NOT_HELD`.

`CHALLENGER VERDICT: 7 requirement(s) rebuilt | 7 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at 013d255f
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_help_prints_usage.py $(cat .mango/baseline-462.list)
771 passed in 29.89s
```

Reviewed at 013d255f — files: `code_atlas/main.py`, `tests/test_help_prints_usage.py`, `README.md`, `CHANGELOG.md`;
working doc `docs/tasks/462_help-prints-usage.md`.

`Ph3/4 proven by`: R1, R2, C1, AC1, AC2 → `tests/test_help_prints_usage.py` (5) and the stdio smoke test.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `013d255f` — not stale. The reviews ran on `991de468`/`35adb291`; the rebase onto 461's
gate fix carried them unchanged (no file in common), and both runs above are on the rebased trees.

**Durable lesson.** None new: a usage text is a hand list of flags, R6.7's class — guarded here, as the rule says.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/462-help-prints-usage`; open its PR against `feat/461-undocumented-exports` (#195,
stacked). Deferred to the maintainer: ratify W1; merge after #195. Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,703 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 58,687 |
| 4 review | ticket-blind `challenger` | 1 | 53,390 |

`LEDGER TOTAL: 160,780 · top cost driver: 4 review / reviewer` — main loop unmeasured.
