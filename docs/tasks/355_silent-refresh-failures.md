---
id: 355
slug: silent-refresh-failures
title: 'A commit never refreshes the index, and a refused refresh never reaches the state line'
phase: 2
milestone: Adoption
status: todo
depends_on: [053, 322, 344]
---

## Why this exists

Field retro, 2026-09-30: "a broken setup looks exactly like a working one." Two gaps are ours.

1. **Hooks cover pull and checkout only.** `contrib/git/` ships `post-merge` and `post-checkout`.
   A local commit, amend or rebase moves HEAD with no refresh, so the anchor project wrote its own
   `post-commit` / `post-rewrite`. Every adopter would do the same.
2. **A refusal is computed, then dropped.** `get_index_status` sets `coverage_loss_pending`
   (`code_atlas/tools/get_index_status.py:257`), but the summary never reads it. So the MCP
   `instructions` line and `code-atlas-state` (silent when `current`) say nothing, while every
   refresh is refused. The refusal reaches only the hook's stderr (344).

## Scope

1. Ship `contrib/git/post-commit` and `post-rewrite`, same shape as the existing two: background,
   stderr kept, exit 0. Update `contrib/git/README.md`'s install line.
2. The one-sentence summary names a pending coverage loss and its route, lifted (316, R6.7); the
   state hook speaks for it even when the index is `current` (as 347 did for the contract era).
3. Nothing auto-rebuilds (202).

## Acceptance criteria

- **AC1:** With the hooks installed, `git commit` and `git commit --amend` trigger one background
  `code-atlas-refresh`; a test runs each hook script against a temp repo.
- **AC2:** On an index where `coverage_loss_pending` is set, the summary names it and its route,
  and `code-atlas-state` prints it on `SessionStart` at an unmoved HEAD.
- **AC3:** The server `instructions` still fit `CLIENT_CAP` (343).
- **AC4:** An index with no pending loss has a byte-identical summary.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 355 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** commit, gate, challenger.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 356 → 354 → 355;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/355-silent-refresh-failures` off `main` (`5b4f1667`). Contract `.mango/run-contract-355.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 2 want-decision asked | 2 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** All seven resolve on `5b4f1667`:
- `contrib/git/post-merge` and `post-checkout`;
- `contrib/git/README.md`'s install line;
- `coverage_loss_pending` (`get_index_status.py:257`);
- `_compose_summary`, which never reads it;
- `instructions._state` (`instructions.py:52`, which lifts the summary);
- `code-atlas-state`'s silence on `current` (`hooks/state.py`);
- the 347 precedent (`FULL_REBUILD_REQUIRED` speaks at an unmoved HEAD).

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines` and `344-C3`
`verify-the-shipped-artifact-not-the-working-tree` (the hooks ship as files).

**Spike (git 2.43.0, a scratch repo whose hooks only log).**

| Action | Hooks fired |
|---|---|
| `git commit` | `post-commit` |
| `git commit --amend` | `post-commit`, `post-rewrite amend` |
| `git rebase` of 3 picks | `post-commit` ×3, `post-rewrite rebase` |

The exposure-checker (ticket-blind `challenger`, 1 dispatch, 45,065 tokens) raised three decisions:

| # | Decision | Class | Resolution |
|---|---|---|---|
| A1 | what "one background refresh" means when an amend fires two hooks | want (bar) | **ASSUMED:** one spawn per `git commit` and per `--amend`. `post-rewrite` skips `amend`, which `post-commit` already covers, and refreshes once after a `rebase` |
| A2 | what "its route" is for a coverage loss | want (bar) | **ASSUMED:** the payload's own `hint`, lifted. 203 gives the loss no route: no tool configures an adapter (`get_index_status.py:253`). The data-discarding `allow_coverage_loss=true` is not put in a one-line summary |
| H1 | how loud the state line is on a lasting condition | how | as 347: it speaks at every state occasion while the loss holds. `_fit` never cuts the summary (`hooks/state.py` `_fit`) |
| H2 | the clause with a pending rebuild or a running build | how | appended to whatever sentence the state composes, because every refresh refuses under both (`_compose_summary`) |

A1–A2 rest on the maintainer's up-front hand-back; neither reverses a prior decision, and both are
surfaced in the PR.

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/11 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

H1–H2 cite the code; A1–A2 cite the hand-back, so `j = 0`. TIER is full because the change spans more
than one file and requirement.

### BASELINE

`main` at `5b4f1667` is CI run 36730042133's tree (4094 passed / 4 skipped on py3.12 and py3.13).
Per SG-2 it is not pasted as a `$` block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a broken setup looks exactly like a working one" | a refused refresh and an unrefreshed commit both become visible | |
| C1 | Scope 3 / 202 | "Nothing auto-rebuilds" | the hooks only call `code-atlas-refresh` | |
| C2 | 061 | — | no loss ⇒ byte-identical summary | |
| R1 | Scope 1 | `post-commit` + `post-rewrite`, same shape; README | A1 | |
| R2 | Scope 2 | summary names the loss and its route, lifted | A2 | |
| R3 | Scope 2 | state hook speaks at `current` | H1 | |
| AC1 | AC | commit and amend → one refresh each, tested on a temp repo | | |
| AC2 | AC | summary + `code-atlas-state` on `SessionStart` at an unmoved HEAD | | |
| AC3 | AC | instructions fit `CLIENT_CAP` | the every-state render gains a coverage-loss state | |
| AC4 | AC | no loss ⇒ byte-identical | | |

### AC validation

Every AC is falsifiable:
- AC1 counts stub invocations under real git;
- AC2 checks for substrings in the real payload and the real hook stdout;
- AC3 compares a length against `CLIENT_CAP - CAP_MARGIN`;
- AC4 checks string equality.

### Gap analysis

- **Now:**
  - no `post-commit` or `post-rewrite` hook ships;
  - `_compose_summary` ignores `COVERAGE_LOSS_PENDING`;
  - `state_line` is silent on `current` unless a full rebuild is pending.
- **Target:** both gaps close; nothing builds.

### Blast radius

- **The summary feeds:**
  - every `get_index_status` payload (at standard and verbose, where the loss is attached);
  - `instructions._state`;
  - `code-atlas-state`.
- **Tests that pin summary text:** `tests/test_server_instructions.py` (the every-state render) and
  the state-hook tests.
- **Docs:**
  - `contrib/git/README.md`;
  - TOOLS.md, the git line;
  - `runbooks/onboarding-a-repo.md`, the hooks paragraph.

### Rule sections

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R4.2 (change-type) ✅ the clause is a pure function of payload fields and a quiet index is byte-identical, §R5.3 (change-type) ✅ both hooks keep stderr and exit 0, §R6.7 (change-type) ✅ the clause lifts reason lost_languages and hint from the payload rather than restating them, §R7.6 (change-type) ✅ the README TOOLS and runbook lines are edited in place`

## Phase 2 — design

### Approach

1. **Hooks.**
   - `contrib/git/post-commit` has `post-merge`'s shape: a background `code-atlas-refresh`, stderr
     kept, exit 0.
   - `contrib/git/post-rewrite` is the same shape, gated to `$1 = rebase`.
   - README: the install line lists all four hooks, plus two behaviour rows.
2. **Summary.** `_compose_summary` splits into `_compose_state` (the old body, unchanged) plus one
   clause for an indexed payload carrying `COVERAGE_LOSS_PENDING`:
   `— <reason>: <lost languages> — <hint>`.
3. **State hook.** It is silent at `current` only when neither a full rebuild nor a coverage loss is
   pending.

### Rejected alternatives

- **Refresh on `post-rewrite amend` too.** Two spawns per amend (A1).
- **Put `allow_coverage_loss=true` in the summary.** It discards covered rows; the one-line headline
  should name the safe fix (A2).
- **A new summary branch that returns early.** It would drop the staleness the sentence already
  states.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | amend fires `post-commit` + `post-rewrite amend`; a rebase fires `post-commit` per pick + `post-rewrite rebase` | verified — spike |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | two hooks | `contrib/git/post-commit`, `contrib/git/post-rewrite` | none identified (never auto-installed) | R1, AC1 | 2/2 |
| 2 | summary clause | `code_atlas/tools/get_index_status.py` | status, instructions, state hook | R2, AC2, AC4 | 1/1 |
| 3 | state hook | `code_atlas/hooks/state.py` | SessionStart / PreCompact output | R3, AC2 | 1/1 |
| 4 | tests | `tests/test_silent_refresh_failures.py` (new), `tests/test_server_instructions.py` | proof collateral | AC1–AC4 | 2/2 |
| 5 | docs | `contrib/git/README.md`, `docs/TOOLS.md`, `docs/runbooks/onboarding-a-repo.md` | doc budgets | R1 | 3/3 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3.
- **`verify-the-shipped-artifact-not-the-working-tree`** — traced in Phase 3: the hooks' committed mode
  and bytes (`git ls-files -s`).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime (git) | the shipped hook files, copied into a temp repo, run by real `git commit` / `--amend` / `rebase`, against a logging stub on PATH | n/a | ✅ |
| AC2 | integration | a real fake-adapter index read with no adapter configured; `get_index_status` and `python -m code_atlas.hooks.state` on stdin | n/a | ✅ |
| AC3 | logic | `_render_on_every_state` with a four-language loss | n/a | ✅ |
| AC4 | logic | `_compose_summary` string equality | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_silent_refresh_failures.py`. On `5b4f1667` four of five fail:
the hook files are missing, the summary lacks the loss, and the state hook is silent. AC4 passes as a
guard. All five pass after.

### Rollback

`git revert`. The hooks are never installed by the project, so nothing on an adopter's machine moves.
