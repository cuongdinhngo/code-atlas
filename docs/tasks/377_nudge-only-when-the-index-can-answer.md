---
id: 377
slug: nudge-only-when-the-index-can-answer
title: 'The grep nudge says "ask the index first" while the index is behind, and a subagent never hears it'
phase: 2
milestone: Adoption
status: done
depends_on: [345]
---

## Why this exists

Two gaps in `code-atlas-nudge` (`code_atlas/hooks/nudge.py`):

- **It speaks when the index cannot answer well.** The only gate is that `graph.db` exists
  (`nudge.py:202`). While a build runs or the index is `behind`, "ask the index first" steers the
  agent to stale answers. This session's own start reported `behind @ a19b9eb` with a build
  running. context-mode drops every redirect to silence when its target is not ready (its
  `hooks/core/routing.mjs:28-32`; idea only, ELv2).
- **Dedupe is per `session_id` only** (`nudge.py:219-226`, read at `:247`). A subagent starts with
  a fresh context, but if its hook payload carries the parent's `session_id`, the parent's nudge
  silences it. context-mode keys on `agent_id` / `agent_type` (its `hooks/pretooluse.mjs:167`).

Blocking or redirecting Grep stays out of scope (345: grep proves absence).

## Scope

1. The nudge is silent unless the index is current — the same judgement `code-atlas-state`
   already makes (reuse it; no second notion of "current").
2. Dedupe key is `(session_id, agent_id)` when the payload has an `agent_id`, else `session_id`
   as today. The state file stays bounded (`KEPT_SESSIONS`).
3. The log line records the agent key, so 300's measurement can tell parent from subagent.

## Assumptions to prove at design

- **UNVERIFIED:** Claude Code's PostToolUse payload inside a subagent carries the parent's
  `session_id` plus an `agent_id`. Capture a real payload first; if it carries neither, Scope 2
  is void and only Scope 1 ships.
- Reading index state costs no more than the `stamped_symbol_shapes()` read already paid.

## Acceptance criteria

- **AC1:** replay 345's AC1 grep while a build lock is held → no output; release it → one line.
- **AC2:** replay it against a `behind` index → no output.
- **AC3:** two payloads, same `session_id`, different `agent_id` → each nudges once; same
  `agent_id` twice → once.
- **AC4:** a payload with no `agent_id` behaves exactly as today.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 377 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1 and merges after #56. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 375 - 376 - 377 - 378 - 379`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `fix/377-nudge-only-when-the-index-can-answer` off `fix/376-plugin-hook-without-console-scripts` (PR #56 — stacked).
  Contract `.mango/run-contract-377.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 11 unresolved surfaced | 1 want-decision asked | 10 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `nudge.py:202` (the `graph.db` gate), `:219-226` and `:247` (the session key), `KEPT_SESSIONS`,
`code-atlas-state`'s judgement (`state.py` `state_line`) and `stamped_symbol_shapes()` all resolve.

**Recall.** 345-C1 (area `claude-code hooks / output channel`) — the nudge already answers through
`additionalContext`, untouched; 360-C1 (`confirm-the-blocked-path-runs`) — the payload assumption is captured, not argued.

**Spike — the ticket's UNVERIFIED assumption** (Claude Code 2.1.295): `claude -p` in a scratch project with a
`PostToolUse` Grep hook dumping its payload, one Grep on the main thread and one in a general-purpose subagent:

```
{'session_id': '67f9e186-…', 'agent_id': None, 'agent_type': None, 'tool_name': 'Grep'} target_fn
{'session_id': '67f9e186-…', 'agent_id': 'a7784052ceb8a4d1a', 'agent_type': 'general-purpose', 'tool_name': 'Grep'} return 1
```

Same `session_id`, plus `agent_id`: Scope 2 is live (LESSONS 377-C1). The Claude Code hooks page agrees:
`agent_id` is "present only when the hook fires inside a subagent call".

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 45,623 tokens) added H7–H10 and W1; found H1–H6 correctly classified.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | one notion of "current" | how | `state.index_settled(payload, db)` extracted from `state_line` — both hooks call it (Scope 1, R1.8) |
| H2 | its cost | how | judged only after a grep matched a kind still fresh for its key — the speaking path; `get_index_status` measured ~20 ms |
| H3 | a silenced nudge | how | records nothing, so the kind stays fresh until the index settles |
| H4 | the payload | how | the spike above |
| H5 | the key | how | `session` alone (state keys unchanged — AC4), else `session/agent_id` |
| H6 | the log | how | the session column carries the key |
| H7 | `unknown` staleness (no git, no stamp) | how | silent — Scope 1: "silent unless the index is current" |
| H8 | an empty or non-string `agent_id` | how | absent, as `main` already coerces `session_id` (`nudge.py:247`) |
| H9 | both tool paths | how | the gate follows the parse, so Grep and a Bash grep share it |
| H10 | the judgement prints nothing | how | `index_settled` has no `_note`; `state_line` keeps its own |
| W1 | subagent keys share `KEPT_SESSIONS` | want | **ASSUMED (awaiting ratification):** keep 32; many subagents can evict the parent's entry, which costs one repeated nudge |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 11 raised | 11 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

376's final gate, the base of this branch: `21 passed · 0 failed · 0 skipped` — `GATE GREEN`. Ran at 61bd37ab.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "steers the agent to stale answers" | no nudge while the index cannot answer | ✅ |
| C1 | Why | "Blocking or redirecting Grep stays out of scope" | still `additionalContext` only | ✅ |
| C2 | Assumptions | "costs no more than the `stamped_symbol_shapes()` read" | judged on the speaking path only (H2) | ✅ |
| R1 | Scope 1 | silent unless current, the state hook's judgement | H1 | ✅ |
| R2 | Scope 2 | `(session_id, agent_id)` key, bounded | H5, W1 | ✅ |
| R3 | Scope 3 | the log records the agent key | H6 | ✅ |
| AC1 | AC | lock held → silent; released → one line | | ✅ |
| AC2 | AC | `behind` → silent | | ✅ |
| AC3 | AC | per-agent once | | ✅ |
| AC4 | AC | no `agent_id` → as today | `None`, `7`, `""` | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `None` under `try_index_write_lock`, a line after | |
| AC2 | yes — HEAD moved past `last_commit` → `None`, no state written | |
| AC3 | yes — three keys speak once each; repeats `None`; log keys `s1`, `s1/agent-a`, `s1/agent-b` | |
| AC4 | yes — state `{"s": ["reference"]}` after three agent-less payloads, one line | |

### Rule sections

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.8 (change-type) ✅ one index_settled behind state_line and the nudge · §R5.3 (change-type) ✅ the hook still never fails; any error stays silence · §R6.5 (change-type) ✅ AC1–AC3 red on the prior code · §R6.9 (change-type) ✅ AC4 asserts through main, the consumer of the payload · §R7.5 (change-type) ✅ comments ≤ 3 lines · §AGENT_BRIEF spike (recalled handle confirm-the-blocked-path-runs) ✅ the payload captured before design`

## Phase 2 — design

### Approach

1. `state.index_settled(payload, db)` and `state.index_answers(root)`; `state_line` calls the first, behaviour unchanged.
2. `nudge.dedupe_key(session, agent)`; `nudge(..., agent="")` keys the state and the log on it and asks
   `index_answers` only once a kind is fresh; `main` reads `agent_id`.
3. Tests: the fixture becomes a real `current` index (git HEAD + `last_commit`); AC1–AC4.
4. TOOLS.md's nudge paragraph, CHANGELOG, LESSONS 377-C1.

### Rejected alternatives

- **Gate on `build_in_progress` and a HEAD compare in the nudge** — a second notion of "current" (Scope 1).
- **Judge before parsing the grep** — every grep would pay ~20 ms for a line most never earn.
- **Key on `agent_type`** — two subagents of one type would share a key.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a subagent's payload carries the parent's `session_id` + `agent_id` | verified | the spike, Claude Code 2.1.295 |
| the judgement's cost | verified | `get_index_status` 20.0 ms on this repo, paid on the speaking path only |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `index_settled`, `index_answers` | `code_atlas/hooks/state.py` | `state_line` (its tests) | R1 | 1/1 |
| 2 | gate, key, log | `code_atlas/hooks/nudge.py` | the state file, the log's readers (300) | R1–R3 | 1/1 |
| 3 | fixture + AC tests | `tests/test_grep_nudge.py` | 345's tests on a `current` index | AC1–AC4 | 1/1 |
| 4 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | — | G1 | 2/2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

### Recalled handles

| # | Handle | Answer |
|---|---|---|
| 1 | `confirm-the-blocked-path-runs` | traced — `claude -p … --settings settings.json` (dump hook) → the two payload rows above |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — a real lock | `try_index_write_lock` held over `nudge()` | n/a | ✅ |
| AC2 | integration — git + store | a real repo whose HEAD moved past `last_commit` | n/a | ✅ |
| AC3 | logic | `nudge()` with three keys, the log read back | n/a | ✅ |
| AC4 | integration — the CLI | `main()` on stdin payloads | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_grep_nudge.py tests/test_session_state_hook.py`.

### Rollback

`git revert`; the state file's agent keys age out under `KEPT_SESSIONS`.

## Phase 3 — execute

Commits `ce5abf64` (code, tests), `d48a737b` (docs). **Red first** (R6.5), the code stashed:
`pytest tests/test_grep_nudge.py` gave `3 failed, 15 passed` — AC1, AC2 and AC3 (AC3 by its new
`agent` argument). Behaviourally, through `main` on the prior code: `[('parent', True), ('agent-a', False)]`
— the subagent was silenced; after: `[('parent', True), ('agent-a', True)]`. AC4 passed before too.

The first run on the new code turned four 345 tests red: their fixture was an index `unknown` to git,
which Scope 1 now silences (H7). The fixture became a `current` index, which is what 345 meant.

**Verification sweep.** File axis: the diff is the change list; `ruff check`, `mypy code_atlas` clean.
Behaviour axis: Approach 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at d48a737b — files: `code_atlas/hooks/state.py`,
`code_atlas/hooks/nudge.py`, `tests/test_grep_nudge.py`, `docs/TOOLS.md`, `CHANGELOG.md`; working doc: this file.

- **`reviewer` round 1 — LGTM** (50,017 tokens): `state_line` traced old vs new, behaviour-identical; R1.1,
  R1.4, R4, R7.5. Observations, no change: eviction follows first insertion (W1); the ~20 ms on the speaking
  path; only the nudge reads `nudge.log`; a non-git project now hears no nudge (H7 — named in the PR);
  `build_in_progress` read twice on `state_line`'s unsettled path.
- **`challenger` round 1** (ticket-blind, 47,796 tokens): 7 met · 0 not met · 2 can't tell — the cost and the
  payload capture are not in the diff; both are recorded here (H2, the spike).

Verdict: clean. Matrix `Ph3/4 proven by`: R1–R3, AC1–AC4 → `tests/test_grep_nudge.py`; C1 → `additionalContext` unchanged.

## Phase 5 — finalise

**Durable lesson.** 377-C1 in `docs/LESSONS.md`: a subagent's hook payload carries its parent's `session_id`
plus `agent_id` (environment, verified on Claude Code 2.1.295).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `fix/377-nudge-only-when-the-index-can-answer`; open the PR against 376's branch
(stacked on #56). Deferred to the maintainer: ratify W1 and the 377-C1 classification; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 45,623 |
| 4 review | `reviewer` | 1 | 50,017 |
| 4 review | `challenger` (ticket-blind) | 1 | 47,796 |

`LEDGER TOTAL: 143,436 · top cost driver: 4 review/reviewer`
