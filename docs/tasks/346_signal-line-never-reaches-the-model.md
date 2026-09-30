---
id: 346
slug: signal-line-never-reaches-the-model
title: 'The read-time signal prints plain stdout, which Claude Code never shows the model'
phase: 2
milestone: Adoption
status: done
depends_on: [099, 344]
---

## Why this exists

`code-atlas-signal` (099) exists to put one line inside a `Read` result. It prints that line as
plain stdout (`code_atlas/hooks/signal.py`, `main`: `print(line)`).

## Evidence (Claude Code 2.1.284, 2026-09-29, found by 345)

- A PostToolUse hook on `Read` that printed a marker as plain text: asked to quote any text a hook
  added, the model answered `NONE`.
- The same marker as `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": …}}`
  was quoted back verbatim.
- Until 344 the signal never fired at all (a `|`-joined `if` never matches). Since 344 it fires,
  and its line still does not reach the model.

## Scope

1. Emit the signal's line as `hookSpecificOutput.additionalContext` for the event it ran on
   (`PostToolUse` for `Read`, `PreToolUse` for `Write`), as `code-atlas-nudge` does (345).
2. Keep the 150-token cap and the silence rules unchanged.

## Acceptance criteria

- **AC1:** A test asserts the signal's stdout is that JSON shape, naming the event from the payload.
- **AC2:** A live `claude -p` session on an indexed repo quotes the signal's line after a `Read`.
- **AC3:** The `Write` (PreToolUse) path is proven the same way, or the ticket records why it could not be.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 346 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges PR [#10](https://github.com/cuongdinhngo/code-atlas/pull/10). **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`; *"with
  skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/346-signal-reaches-the-model` off `main`. Contract `.mango/run-contract-346.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

These references were checked and all resolve:
- `code_atlas/hooks/signal.py` `main` → `print(line)`;
- `code-atlas-nudge` (`code_atlas/hooks/nudge.py` `main`);
- `TOKEN_BUDGET = 150`;
- the snippet and plugin hook tables: `Read` at `PostToolUse`, `Write` at `PreToolUse`;
- 344's single-rule `if`.

Recall:
- By area: `345-C1` (the output channel) and `344-C1` (the `if` filter).
- By handle: `343-C2` and `344-C3`, because the change adds a shared helper to `code_atlas/hooks`.

The ticket fixes what to change and how to prove it, so it holds no product decision.

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists, Evidence, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=2 G=1 AC=3`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

`main` at `27ff2f99` has the same tree as `d80325ec` (`git diff --quiet` → exit 0). That tree gated
green: `scripts/gate.sh` → `GATE GREEN — all 21 checks passed` (PR #9). A targeted run on the
untouched checkout also passed: the signal, hook-offer, nudge and plugin tests, 57 passed. That run is
not pasted as an evidence block: it ran on the pre-change tree, which the checker refuses by design
(SG-2).

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "put one line inside a `Read` result" | the line must reach the model | met |
| C1 | Evidence | plain text → `NONE`; `additionalContext` JSON → verbatim | JSON is the channel (345-C1) | constraint |
| C2 | Evidence | "Since 344 it fires" | wiring unchanged | constraint |
| R1 | Scope 1 | "`additionalContext` for the event it ran on … as `code-atlas-nudge` does" | one shared JSON shape | met |
| R2 | Scope 2 | "Keep the 150-token cap and the silence rules unchanged" | `read_signal`/`write_signal`/`signal` untouched | met |
| AC1 | AC | "stdout is that JSON shape, naming the event from the payload" | subprocess test, both events | met |
| AC2 | AC | "live `claude -p` … quotes the signal's line after a `Read`" | live session | met |
| AC3 | AC | "`Write` (PreToolUse) path is proven the same way" | live session | met |

### Clarifications — 3, all self-resolved

1. **A payload without `hook_event_name`.** It falls back to the event the tool is wired at:
   `Read` → `PostToolUse`, `Write` → `PreToolUse`. Source: the module docstring and the hook tables.
2. **The argument form (`code-atlas-signal Read path`).** A human types it at a shell, so it keeps
   the bare line. Source: `signal.py` `main`, where the argv branch exists for shell use.
3. **Codex (`contrib/codex/hooks.json`).** It runs the signal with no matcher. Its tool names are
   not `Read`/`Write` (`contrib/codex/README.md`, "No `matcher`"), so the signal is silent there by
   construction and the output shape cannot regress it.

### Blast radius

- `signal.py` `main`: the only producer of this output.
- `nudge.py` `main`: it moves to the shared helper.
- `tests/test_write_time_signal.py`: its stdin test asserted the plain `in done.stdout`.
- `docs/TOOLS.md`: the read-time signal section.
- `docs/LESSONS.md` 345-C1: its evidence line.

### Rule sections

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the helper names no language and no tool beyond the two the module already owns, §R6.5 (change-type) ✅ the live plain-stdout control answered NONE, §R6.7 (change-type) ✅ the JSON shape has one definition shared by signal and nudge, §R7.6 (change-type) ✅ TOOLS.md replaces its prints-a-line sentence rather than adding one`

## Phase 2 — design

### Approach

1. `code_atlas/hooks/__init__.py` gains `additional_context(event, line)`, the one JSON shape.
   `nudge.py` calls it.
2. `signal.main`:
   - A stdin payload prints `additional_context(event, line)`. The event is the payload's
     `hook_event_name`, or `DEFAULT_EVENT[tool]`.
   - The argv form prints the bare line.
   - Silence prints nothing.
3. Tests cover four cases: the JSON shape for both events, the fallback, silence, and the argv form.
4. Docs: `TOOLS.md`, and the 345-C1 evidence line.

### Rejected alternatives

- **Hard-code `PostToolUse`, as the nudge does.** The `Write` line would name the wrong event; the
  ticket asks for "the event it ran on".
- **JSON on the argv form too.** A human at a shell would read an envelope. No host uses that form.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | `additionalContext` reaches the model from `PostToolUse` | verified — 345-C1 and AC2 below |
| A2 | `additionalContext` reaches the model from `PreToolUse` | verified — AC3 below |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | shared JSON helper | `code_atlas/hooks/__init__.py`, `code_atlas/hooks/nudge.py` | the nudge's output (its test pins it) | R1 | 2/2 |
| 2 | event-aware output | `code_atlas/hooks/signal.py` | every host wiring the signal; Codex (clarification 3) | R1, R2 | 1/1 |
| 3 | tests | `tests/test_write_time_signal.py` | proof collateral | AC1 | 1/1 |
| 4 | docs | `docs/TOOLS.md`, `docs/LESSONS.md` | doc budgets | R1 | 2/2 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines` — traced.** I ran `.venv/bin/ruff format --diff
  tests/test_write_time_signal.py`. It proposes rewrites only inside the `_hook` helper this change
  moved (`script = (…)`, `env={…}`), and it was not applied. `code_atlas/hooks/*` →
  `3 files already formatted`.
- **`verify-the-shipped-artifact-not-the-working-tree` — does not apply**, because the change ships
  no plugin file. The live runs call the installed venv console script `code-atlas-signal`, whose
  source is this tree (editable install).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | subprocess test (the host's stdin/stdout path) | n/a | ✅ |
| AC2 | runtime/3p | live `claude -p` session | n/a | ✅ |
| AC3 | runtime/3p | live `claude -p` session | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_write_time_signal.py -k 'hook_stdin_payload or pre_tool_use_event'`.
It fails before the change, when `json.loads` hits the plain line, and passes after.

### Rollback

`git revert`. One repo, no migration.

## Phase 3 — execute

Commit `65e6a0a1` on `fix/346-signal-reaches-the-model`.

Ran at 65e6a0a1

```
$ .venv/bin/python -m pytest -q tests/test_write_time_signal.py
18 passed in 7.33s
```

**Live (Claude Code 2.1.284).** The scratch repo held one committed `shapes.py` with 6 functions,
indexed with the Python adapter (`full: 1 file(s), 7 node(s), 6 edge(s)`). The hooks came from
`--settings`: `Read` at `PostToolUse` and `Write` at `PreToolUse`, both running
`.venv/bin/code-atlas-signal`.

Ran at 65e6a0a1

```
$ claude -p "Use the Read tool to read shapes.py. Then quote verbatim … any text a hook added …" --settings settings.json --allowedTools Read
code-atlas: shapes.py defines 6 symbols — area:1, centroid:6, diagonal:5, perimeter:2, surface:4, volume:3

$ claude -p "… same prompt …" --settings plain.json --allowedTools Read   # control: signal piped to its bare line
NONE

$ claude -p "Use the Write tool to create a new file new_mod.py … quote … any text a hook added …" --settings settings.json --allowedTools Write
PreToolUse:Write hook additional context: code-atlas: new_mod.py is untracked — symbol queries answer `not_indexed` until it is committed and reindexed (092).
```

**Sweep.**
- Axis 1: the diff is the 6 files of the change list.
- Axis 2: Approach bullets 1–4 were implemented as approved. No deviation.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `65e6a0a1`):** 4 met · 0 not met · 2 can't tell. The two it
could not check are AC2 and AC3, which are live sessions it cannot run; they are recorded in Phase 3.
It ran `tests/test_write_time_signal.py tests/test_grep_nudge.py` read-only: 32 passed. It confirmed
the nudge's output is unchanged: the same dict goes to the same `json.dumps`, and `test_grep_nudge`
still parses it. Its concerns:

- **Codex receives JSON now.** The signal is silent under Codex by construction, because Codex's
  tool names are not `Read` or `Write` (clarification 3). Nothing Codex could see changed shape.
- **The argv form is an addition.** It is covered by `test_a_shell_call_prints_the_bare_line` and
  documented in `TOOLS.md`.

No fix was needed and nothing was re-dispatched.

`Ph3/4 proven by`: G1, R1, R2, AC1–AC3 — 6/6.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 65e6a0a1 — the diff `main..65e6a0a1`. Working doc:
`docs/tasks/346_signal-line-never-reaches-the-model.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `65e6a0a1` only bookkeeping changes — this doc, `docs/BACKLOG.md` (row
closed) and `docs/TOKEN_LEDGER.md`. All are exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

- **`345-C1` was seen again and re-checked.** The same channel carried the signal live, on
  `PreToolUse` too. `seen: 345, 346` is recorded in `docs/LESSONS.md`.
- **It is not a promotion candidate.** It is type 5 (an environment fact), and the promotion step
  only escalates a recurring type-2 claim.
- **The baseline refusal recurred.** It is already recorded as SG-2; no new signal was filed.

### Outward actions

1. Push `fix/346-signal-reaches-the-model` — pre-authorised.
2. Open PR #10 — pre-authorised.

Deferred to the maintainer: the merge.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | review | `challenger`, round 1 | 47,883 fresh |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 47,883 · top cost driver: review/challenger`
