---
id: 382
slug: batch-query-from-a-shell
title: 'Every answer is reachable only through an MCP session; a script that needs a thousand answers has no way to ask'
phase: 2
milestone: Adoption
status: done
depends_on: []
---

## Why this exists

The only shell entry point that touches the index is `code-atlas-build`
(`code_atlas/cli.py:110`, "Build or update this repo's code-atlas index from a shell"). Every
*question* goes through the MCP server, so it is asked by an LLM agent, one tool call at a time,
paying context for each payload.

Deterministic consumers need many answers and no model:

- a script in a consuming repo that anchors its own records (tickets, test docs, notes) to code —
  per record, `impact_modules` on the files a fix touched, `find_references` on the tables it names,
  `search_symbol` for the qnames it cites. A batch of a thousand such records is ordinary;
- CI checks that re-implement a graph question with `grep` because they cannot call the tool;
- re-running signed claims (383).

Routing those through an agent spends tokens on answers no model needs to read, and makes a
deterministic pipeline depend on a model. What the consumer stores, and where, stays in the
consuming repo; this ticket only gives it a way to ask.

## Scope

1. `code-atlas query <tool> --args '<json>'` prints the tool's payload as JSON — the **same payload**
   the MCP tool returns for the same arguments at the same revision.
2. `code-atlas query --batch <file.jsonl>`: one `{"tool": ..., "args": {...}}` per line in, one
   payload per line out, in order, over a single opened index (no per-line startup).
3. Exit status: `0` answered (including an honest empty with `reason`), non-zero only for a usage
   error or an unreadable index. An empty answer is not a failure.
4. Read-only: `build_or_update_index` and `generate_onboarding` are refused by `query` (they
   already have entry points with their own locking).

## Assumptions to prove at design

- The served tools can be invoked without the MCP transport (tool functions take plain args and
  return the payload dict). Decide whether `fit` counters (260) and the live token counter (379)
  count shell calls, and say so.
- One process can hold the index open for a batch without fighting the writer lock that git-hook
  refreshes take.

## Acceptance criteria

- **AC1:** for every read tool in `main.TOOL_NAMES`, a fixture shows `query` output equal to the
  MCP payload for the same args at the same rev (payload equality, not "similar").
- **AC2:** a 1,000-line batch over a fixture index runs in one process; its wall time is recorded
  in the task.
- **AC3:** an empty answer exits `0` and carries the same `reason` / `try_instead` the tool gives.
- **AC4:** the tool count (24) is unchanged — `query` is a CLI over existing tools, not a new tool.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 382 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1 and merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 381 - 382 - 386 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/382-batch-query-from-a-shell` off `main` (`a6e0e6b4`). Contract `.mango/run-contract-382.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 1 want-decision asked | 11 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `code_atlas/cli.py:110` (`code-atlas-build`'s parser), `main.TOOL_NAMES`, the fit counters (`tools/fit.py`)
and 379's `est_tokens_vs_grep_read` resolve.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 42,689 tokens) added H9–H11; kept W1 a want.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the entry point | how | a `query` subcommand on the `code-atlas` script — the ticket's Scope 1 spelling; no subcommand still serves stdio (`main.main`) |
| H2 | the payload source | how | the repo's own server, in process, through fastmcp's in-memory `Client`: argument validation and payload are the MCP route's by construction (Scope 1 "same payload") |
| H3 | exit codes | how | `0` any answer; `2` usage (argparse, bad JSON, unknown or refused tool, a pydantic argument rejection); `1` config error, no index file, a file that is not a database, a `schema_version_mismatch` answer (Scope 3) |
| H4 | batch validation | how | every line checked before any is asked; a call a tool rejects mid-batch stops there, after the answers before it |
| H5 | refused tools | how | `build_or_update_index`, `generate_onboarding` (Scope 4) |
| H6 | `CA_TOOLS` | how | honoured as the server honours it (`main.allowed_tools`) |
| H7 | caller roots (366) | how | the client declares the project root, as a client at the index root would |
| H8 | output | how | one compact JSON line per answer, `ensure_ascii=False`; `-` reads stdin |
| H9 | which index | how | `CLAUDE_PROJECT_DIR`, else cwd — `code-atlas-build`'s rule (`cli._project_root`) |
| H10 | startup work | how | `build_server` starts no build and takes no lock; read-through repair stays the tool's own, as over MCP |
| H11 | blank lines, stdout | how | blank lines skipped (README says so); stdout carries payloads only, FastMCP logs go to stderr |
| W1 | do shell calls count in fit (260) and est. tokens (379)? | want | **ASSUMED (awaiting ratification):** no — both count what an agent asked, and one 1,000-line batch would drown them (`build_server(count=False)`) |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=4 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

CI on PR #62's head `8da204e3` — the tree `main` squash-merged as `a6e0e6b4`, this branch's base: 5/5 checks
green (lint·type·test on 3.12 and 3.13, adapter manifests, image build, rulebook grep-gates). Ran at a6e0e6b4.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a script that needs a thousand answers has no way to ask" | a shell route to every read tool | ✅ |
| C1 | Why | "What the consumer stores … stays in the consuming repo" | `query` prints; it stores nothing | ✅ |
| R1 | Scope 1 | `query <tool> --args '<json>'`, the same payload | H1, H2 | ✅ |
| R2 | Scope 2 | `--batch`, one line in, one out, in order, one opened index | H4, H8 | ✅ |
| R3 | Scope 3 | exit 0 answered, non-zero only usage / unreadable | H3 | ✅ |
| R4 | Scope 4 | the two writers refused | H5 | ✅ |
| AC1 | AC | `query` == MCP payload for every read tool | | ✅ |
| AC2 | AC | 1,000-line batch in one process, wall time recorded | 4.66 s (below) | ✅ |
| AC3 | AC | an empty answer exits 0 with the tool's `reason` / `try_instead` | | ✅ |
| AC4 | AC | the tool count stays 24 | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — parsed JSON equality per tool; 22 read tools, a guard test fails if one lacks an argument row | 10/22 answer ok with rows, so equality is not empty-vs-empty |
| AC2 | yes — 1,000 lines, 1,000 payloads, one `query.main` call | 4.66 s on the fixture index (Linux, `tests/test_query_cli.py -s`) |
| AC3 | yes — `reason` and `try_instead` equal the MCP payload's | |
| AC4 | yes — `len(TOOL_NAMES) == 24` pinned by `tests/test_documented_tool_count.py` | |

**Assumptions answered.** Tools run without the transport: the in-memory client is the full MCP call path, no
stdio. The writer lock: `test_a_batch_answers_while_a_writer_holds_the_lock` holds `write.lock` and still answers,
labelled `build_in_progress`. Fit / est.-token counters: W1.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ query.py names no language · §R1.2 (change-type) ✅ no registry: the server's own branches serve both routes · §R4.2 (change-type) ✅ payloads unchanged, the shell prints the MCP payload · §R6.5 (change-type) ✅ every new test fails on main (query does not exist) · §R7.5 (change-type) ✅ comments ≤ 3 lines`

## Phase 2 — design

### Approach

1. `main.build_server(..., count=True)`: `count=False` registers the same tools without `fit.wrap`.
2. `main.main()`: `code-atlas query …` routes to `query.main`; no argument still serves stdio.
3. `code_atlas/query.py`: parse and validate every request, refuse the writers, then one in-memory client over
   `build_server(config, count=False)` declaring the project root; print each `structured_content` as a line.
4. README (*What you can ask it*), CONVENTION's map, CHANGELOG.

### Rejected alternatives

- **Call the tool functions directly** — skips FastMCP's argument validation, so `"5"` and `5` could answer
  differently from MCP; payload equality would be a claim to keep true, not a construction.
- **A new `code-atlas-query` script** — the ticket spells `code-atlas query`; the server's script already ships
  in the image's `ENTRYPOINT`.
- **Count shell calls** — W1.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the in-memory client returns the MCP payload | verified | AC1 against `Client(build_server(config))` with the same root |
| a reader is not blocked by `write.lock` | verified | the lock test |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `count` flag, `query` dispatch | `code_atlas/main.py` | every served tool (default unchanged) | R1, R2 | 1/1 |
| 2 | the command | `code_atlas/query.py` | new | R1–R4 | 1/1 |
| 3 | proving tests; core-module pin 98 → 99 | `tests/test_query_cli.py`, `tests/test_core_is_language_agnostic.py` | — | AC1–AC4 | 2/2 |
| 4 | docs | `README.md`, `docs/CONVENTION.md`, `CHANGELOG.md` | the doc budgets | G1 | 3/3 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — the MCP call path | shell lines vs `Client(build_server)` payloads, 22 tools | n/a | ✅ |
| AC2 | integration | a 1,000-line batch through `query.main` | n/a | ✅ |
| AC3 | integration | an empty `find_callers` both routes | n/a | ✅ |
| AC4 | unit | `TOOL_NAMES` count pins | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_query_cli.py`.

### Rollback

`git revert`; nothing is stored.

## Phase 3 — execute

Commits `ec2cafc8` (code, tests), `3e11f3cd` (docs), `5a389a6c` (challenger fixes). **Red first** (R6.5): on `main`
`code_atlas.query` does not exist, so `tests/test_query_cli.py` fails to import, and `code-atlas query` serves stdio.

**Verification sweep.** File axis: the diff is the change list; `ruff check`, `mypy code_atlas` clean. Behaviour
axis: Approach 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at 5a389a6c — files: `code_atlas/main.py`,
`code_atlas/query.py`, `tests/test_query_cli.py`, `tests/test_core_is_language_agnostic.py`, `README.md`,
`docs/CONVENTION.md`, `CHANGELOG.md`; working doc: this file.

- **`challenger` round 1** (ticket-blind, 54,184 tokens): 8 met · 0 not met · 3 can't tell. Findings: a file that is
  not a database raised a traceback from `build_server`; a tool failing on the index exited 2 as a usage error;
  stdin untested; most AC1 rows possibly empty-vs-empty; the README named only `fit_counts`; AC2's time not yet
  recorded. Fixed in `5a389a6c`: both exit 1 with a line, tests for the corrupt file, stdin with a blank line, and
  10/22 tools asserted non-empty; README names both counters and the mid-batch stop. AC2 recorded above.

Verdict: clean (challenger only — REVIEWER: OFF). Matrix `Ph3/4 proven by`: R1–R4, AC1–AC3 →
`tests/test_query_cli.py`; AC4 → the count pins; G1, C1 → the diff and README.

## Phase 5 — finalise

**Durable lesson.** None new.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/382-batch-query-from-a-shell`; open the PR against `main`.
Deferred to the maintainer: ratify W1; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 42,689 |
| 4 review | `challenger` (ticket-blind) | 1 | 54,184 |

`LEDGER TOTAL: 96,873 · top cost driver: challenger`
