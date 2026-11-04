---
id: 436
slug: query-broken-pipe
title: "`code-atlas query` reports a closed stdout pipe as an \"unreadable index\""
phase: 2
milestone: CLI
status: in-progress
depends_on: []
---

## Why this exists

Reproduced 2026-11-04 at `8c7f7a12`, three of three runs:

```
$ code-atlas query get_index_status --args '{}' | true
code-atlas query: unreadable index at …/.code-atlas/graph.db: BrokenPipeError: [Errno 32] Broken pipe
Exception ignored on flushing sys.stdout:
```

The index is fine; the reader closed the pipe. `code_atlas/query.py:386` catches every `Exception`
after the database opens and labels it "unreadable index", so a closed pipe sends the user to rebuild a
healthy index. The second line is the interpreter failing to flush stdout again at shutdown.

## Acceptance

1. A closed stdout ends `code-atlas query` quietly: no "unreadable index" line and no shutdown flush
   error. It exits with the conventional status, following Python's documented SIGPIPE guidance
   (point stdout at devnull before exit).
2. A real database error still names the unreadable index: a non-database file at `db_path` produces
   the message as today.
3. Tests: piping into a reader that closes early produces neither line; the non-database file case
   keeps its message.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 436 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer's merge.
- `TRACK: backend` · Run mode: `autorun 434 - 435 - 436 --no-reviewer`, this ticket first — `REVIEWER: OFF (--no-reviewer)` ·
  `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `fix/436-query-broken-pipe` from `main` at `e08d4b75`. Contract `.mango/run-contract-436.txt` (mango 1.19.0 scripts).
  RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`. Budget: unknown.

## Phase 0 — refine

`PREMISE: 1 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

`code_atlas/query.py:386` resolves. The ticket fixes the behaviour and both acceptance cases; nothing is left for the
maintainer, so refine self-skips and the exposure-checker does not run.

## Phase 1 — analysis

`SECTIONS: 2 found (Why this exists · Acceptance) | 2 decomposed | ROWS: C=0 R=0 G=1 AC=3`
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

H1 — the exit status: `141` (128 + SIGPIPE), what a POSIX shell reports when `git` or `cat` dies on a closed pipe;
Python's `signal` docs ("Note on SIGPIPE") give the devnull redirect. A named constant beside `NOT_HELD`.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a closed pipe sends the user to rebuild a healthy index" | the message names the cause, not the index | ⚠ |
| AC1 | Acc 1 | "A closed stdout ends `code-atlas query` quietly" | H1; no stderr line | ⚠ |
| AC2 | Acc 2 | "A real database error still names the unreadable index" | the generic branch stays | ⚠ |
| AC3 | Acc 3 | "piping into a reader that closes early produces neither line" | a subprocess test | ⚠ |

`BASELINE: green — tests/test_query_cli.py on main at e08d4b75: 21 passed`

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5: the test seen red with the branch removed · §7 (change-type) ✅ R7.2, R7.5`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** In `query.main`, `except BrokenPipeError` before the generic catch calls `_pipe_closed()`: `os.dup2` devnull
onto stdout's descriptor, return `PIPE_CLOSED = 141`. **Rejected:** `signal.signal(SIGPIPE, SIG_DFL)` — POSIX only, and it
kills the process mid-asyncio without the exit code the CLI documents.
**Change list:** `code_atlas/query.py` (the modes move into `_run`), `tests/test_query_cli.py`, `CHANGELOG.md`; bookkeeping (`docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md`, this file).
**Proving test:** `tests/test_query_cli.py::test_a_reader_that_closes_the_pipe_is_not_an_unreadable_index`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

Main loop, no dispatch. **Verification sweep:** 3 files, all on the change list. **Seen failing (R6.5):** with the
`except BrokenPipeError` branch removed, the test is red — "unreadable index … BrokenPipeError" and exit 120; restored,
green. `tests/test_query_cli.py` 22 passed (`test_a_file_that_is_not_a_database_exits_one` holds AC2). By hand,
`code-atlas query get_index_status --args '{}' | true` prints nothing and exits 141. `ruff`, `mypy` clean.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The rule-book reviewer was waived by the run's argument; no reviewer
step ran (no `reviewer`, no `reviewer-max`, no native `/code-review`).

- **`challenger` round 1** (ticket-blind, 51,070 tokens, at `b642996c`): 6 met · 0 not met.
  - **Important 1, taken** in `3a4a1f0e`: `--snapshot-symbols -` writes without a flush, so a small answer met the closed
    pipe at shutdown (exit 120, "Exception ignored"). The modes now run in `_run` and `main` flushes stdout inside the
    guard. The test is parametrized over a tool answer and a small snapshot; with the flush removed the snapshot case is
    red (1 failed, 1 passed), restored green.
  - **Important 2, taken** in `3a4a1f0e`: the first commit's `ruff format` rewrote untouched lines; reverted to `main`'s.
  - **Minor, taken:** `_pipe_closed` tolerates a stdout with no descriptor. **Minor, not taken:** Windows reports a closed
    pipe as `OSError` EINVAL, which this branch does not catch — the dev loop and the reproduction are POSIX; disclosed.
- Seen after the fix: `tests/test_query_cli.py`, `test_symbol_changed_since.py`, `test_verify_claim.py` 60 passed.

Verdict: clean (challenger only — REVIEWER: OFF), both Importants landed.
`Ph3/4 proven by`: AC1, AC3 → `test_a_reader_that_closes_the_pipe_is_not_an_unreadable_index` (both cases); AC2 →
`test_a_file_that_is_not_a_database_exits_one`; G1 → AC1.

Reviewed at 3a4a1f0e

## Phase 5 — finalise

**Durable lesson.** 436-C1 `a-write-is-not-delivered-until-flushed` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate.** Docker on the final tree (the host gate is red on two tests that fail identically on \`main\` —
the host's PATH \`code-atlas\` is 0.9.1):

Ran at 54270034

```
$ scripts/docker-test.sh
5723 passed, 8 skipped in 713.65s (0:11:53)
```

### Outward actions

Under the handover: push `fix/436-query-broken-pipe`; open its PR against `main`. Deferred to the maintainer: merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | ticket-blind `challenger` | 1 | 51,070 |

`LEDGER TOTAL: 51,070 · top cost driver: 4 review / challenger` — main loop unmeasured.
