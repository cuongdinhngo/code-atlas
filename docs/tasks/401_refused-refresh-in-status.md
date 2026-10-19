---
id: 401
slug: refused-refresh-in-status
title: "A refresh the hook skipped for an unusable adapter looks like a working refresh"
phase: 2
milestone: Freshness
status: done
depends_on: [355, 381]
---

## Why this exists

From the anchor project's Round-3 feedback ("a broken setup looks exactly like a working one"). It is
also seen on this maintainer's machine: `.code-atlas/refresh.log` repeats `refresh skipped: no_usable_adapter`
while the session shows nothing. On `main` the refusal goes only to stderr and the log
(`hooks/refresh.py:52-56`). `get_index_status` predicts a refusal for `coverage_loss` alone
(`get_index_status.py:302-309`, 355).

## Scope

1. The refresh records its last outcome (skipped / refused, with the reason and time) where `get_index_status`
   reads it, and the status names it with the fix, as 381's skew line does at session start.

## Acceptance criteria

- **AC1:** with an adapter that fails its handshake, a hook refresh, then `get_index_status`, names
  `no_usable_adapter` and the time.
- **AC2:** the next successful refresh clears it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 401 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews the PR; merging is theirs. **Revert path:** `git revert` the branch; a leftover `.code-atlas/refresh.refused` is then inert.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 401` — `REVIEWER: OFF` (waived, "with skipped reviewer") · `CHALLENGER: ON`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 0 want-decision asked | 5 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `hooks/refresh.py:52-56` (the refusal goes to stderr only), `get_index_status.py:302-309` (355's
`coverage_loss_pending`, the only predicted refusal), `build_or_update_index.py:78` (`NO_USABLE_ADAPTER`), and 381's
on-screen route (`hooks/state.py` `screen_lines`) all resolve at 8c0ddd00.

**Recall.** `a-route-list-must-come-from-the-tools-verdict` (388-C1): status must report the tool's own verdict,
not a prediction. `a-shell-surface-needs-an-agent-channel` (387-C1): a refusal that reaches only a log is exactly
that. `a-flag-loop-needs-a-clearable-flag` (357-C1). 381-C1 (area: hook output routing): SessionStart stdout
reaches only the agent; a person sees `systemMessage`.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the outcome is recorded | how | a sidecar `refresh.refused` beside `graph.db`, as 357's `write.pending` is (`index_lock.py`). Not a meta key: a refusal opens no write on the DB, and the record carries a wall-clock time that R4.2 keeps out of stored rows |
| H2 | which outcomes | how | every `refused` result (`no_usable_adapter`, `coverage_loss`, `contract_rebuild_required`, `index_incomplete`) and an exception the hook swallows (`refresh_error`). `busy` is not recorded: the holder serves it (357) |
| H3 | what clears it | how | any build that succeeds, through the tool's one success path (`_build`), so an MCP build clears it too — the adapters answered, so the record is history (AC2) |
| H4 | "with the fix" | how | the refusal's own `route` when it had one, else a `hint` per reason (R5.4c: no registered tool repairs an adapter) |
| H5 | where it is said | how | a `refresh_refused` field at every detail level, a summary clause, and the state hook: not settled, and on screen (381-C1). A reason another field already names on the summary (355's `coverage_loss_pending`, 347's `full_rebuild_required`) is not said twice |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=1 G=1 AC=2`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### Root cause

`config.cause_taxonomy` class: **integration**. The hook's only channel was stderr (`refresh.py:52-56`), which the
git and plugin hooks send to a log. Nothing a session reads (status, instructions, the state line) could see it.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a broken setup looks exactly like a working one" | a refused refresh is visible where a session looks | ✅ |
| R1 | Scope 1 | "records its last outcome … where `get_index_status` reads it, and the status names it with the fix" | H1–H5 | ✅ |
| C1 | R5.4 | — | a `route` only when the refusal carried one; otherwise a `hint` | ✅ |
| C2 | R4.2 | — | no wall-clock in stored rows: the time lives in the sidecar | ✅ |
| AC1 | AC | "names `no_usable_adapter` and the time" | field, summary and screen line, after a real hook refresh against a handshake-failing adapter | ✅ |
| AC2 | AC | "the next successful refresh clears it" | the record, the field and the clause are gone | ✅ |

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.4 (change-type) ✅ the sidecar helpers sit in index_lock.py beside write.pending; tools never import hooks · §R4.2 (change-type) ✅ no stored row changes · §R5.4 (change-type) ✅ C1 · §R6.5 (change-type) ✅ the proving test observed red on main · §R6.9 (recalled handle 387-C1) ✅ the test asserts the consumer: the state line and screen_lines · §R7.5 (change-type) ✅ every new comment ≤ 3 lines`

## Phase 2 — design

**Approach.** `index_lock.py` gains `record_refresh_refused` (an atomic replace), `clear_refresh_refused` and
`read_refresh_refused`. The hook records each refusal and each swallowed exception with a UTC `at`. `_build` clears
the record after any successful build. `get_index_status` attaches `refresh_refused` (`reason`, `at`, `detail`, and
`route` or `hint`) and appends a summary clause. `state.index_settled` treats it as unsettled, and `screen_lines`
puts it on screen.

**Rejected.** A meta key in `graph.db` (H1). Predicting a handshake failure in status: that would mean launching
every adapter on a read call, as 381's skew line does only at session start.

| # | Change | File | Covers |
|---|---|---|---|
| 1 | sidecar helpers | `code_atlas/index_lock.py` | H1 |
| 2 | record | `code_atlas/hooks/refresh.py` | H2, AC1 |
| 3 | clear | `code_atlas/tools/build_or_update_index.py` | H3, AC2 |
| 4 | field + summary | `code_atlas/tools/get_index_status.py` | H4, H5, AC1 |
| 5 | on screen | `code_atlas/hooks/state.py` | H5 |
| 6 | proving test | `tests/test_refused_refresh_in_status.py` (new) | AC1, AC2 |
| 7 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | R7.2 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | R7.2 |

`HANDLES: 3 recalled | 2 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- 388-C1 → traced: status reads the hook's recorded verdict, never a prediction (`_attach_refresh_refused`).
- 387-C1 → traced: the refusal now reaches the status and the session-start screen (`test_the_session_start_line_puts_it_on_screen`).
- 357-C1 → does not apply: no loop runs while the record exists. A failed unlink leaves a stale record (residual, DISCLOSURE).

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — hook + status on a file DB | a real `refresh()` against the fake adapter's `not-json-handshake` mode | authored (`tests/fixtures/adapter`) | ✅ |
| AC2 | integration | a second `refresh()` with the adapter fixed | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test.** `pytest -q tests/test_refused_refresh_in_status.py` (WSL, `~/ca-r3w`).

## Phase 3 — execute

Branch `fix/401-refused-refresh-in-status` from 8c0ddd00. **Red first** on `main` (8c0ddd00, the test with its new
imports replaced by string constants): `4 failed, 1 passed` — the passing one is the unreadable-record guard,
silent on `main` by construction. **Green:** the five tests plus the refresh, state, summary, coverage-loss and
server suites, `459 passed`. `ruff check` clean; `mypy code_atlas` clean (103 files).

Axis 1 (the diff ⊆ the change list): rows 1–8, nothing else. Axis 2: the approach as designed.

## Phase 4 — review

`REVIEWER: OFF` — waived by the run's "with skipped reviewer". `CHALLENGER: ON`.

**Challenger** (ticket-blind `mango:challenger`, 63,811 tokens) on 6e9a1aa0: `CHALLENGE: 3 met · 0 not met · 0
can't tell`, no Important finding. Its Minors:
1. **Race (residual, not fixed).** The hook writes the record after the lock is released. A build that succeeds and
   clears in that window leaves a record over a good index until the next build. Comparing `at` with `built_at`
   would need two clocks to agree; the window is one hand-off and it heals itself.
2. A `route` is a shell command (`code-atlas-build --full`), as `full_rebuild_required` already names one. Kept.
3. "last refresh refused at <time>" is a past-tense claim, true while the record stands (R5.6). Kept.

**Scope reconciliation.** The diff matches change-list rows 1–8. `SCOPE: S` holds.

## Phase 5 — finalise

**Durable lessons.** None new. 388-C1 and 387-C1 gain 401 (P1, traced in Phase 2).

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 2 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

The two that cannot promote here: `/mango:promote` is the maintainer's pass between tickets.

### Outward actions

Under AGENTS.md's standing approval and the maintainer's handover of 2026-10-19: push
`fix/401-refused-refresh-in-status`, then open the PR against `main`. Merging stays with the maintainer.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | `challenger` (ticket-blind) | 1 | 63,811 |

`LEDGER TOTAL: 63,811 · top cost driver: challenger`
