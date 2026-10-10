---
id: 376
slug: plugin-hook-without-console-scripts
title: 'A plugin installed before the console scripts fails every hook with 127 instead of saying how to fix it'
phase: 2
milestone: Adoption
status: done
depends_on: [344]
---

## Why this exists

Every plugin hook is `PLUGIN_GATE` + `exec code-atlas-<hook>` (`scripts/gen_skill.py:43`). The
gate spares a repo with no index, but in an indexed repo whose `PATH` lacks the console scripts
(install step 1 of `contrib/claude-code/README.md` skipped, or a venv not on `PATH`), `exec`
fails with `command not found` and exit 127 on every hook, every session.

The user sees hook errors, not the one command that fixes them. Every other hook path exits 0 by
design ("always exits 0", `hooks/state.py`). context-mode handles the same class with a cheap
"are the launch-critical files there?" probe before doing anything (its
`hooks/heal-partial-install.mjs:141-160`; idea only — its self-repair is out of scope here).

## Scope

1. The generated gate checks the command exists (`command -v`) before `exec`.
2. When it is missing: only the SessionStart `code-atlas-state` command prints one line naming
   the install command (README step 1) and exits 0; every other command — SessionStart's
   `code-atlas-refresh` included — exits 0 silently, so the gate is per-command.
3. Only `render_plugin_hooks` changes: `settings.snippet.json` stays byte-identical (a hand install
   already has the scripts), and 240's guard keeps holding.
4. Never installs or edits anything (`tests/test_contrib_snippets.py` keeps holding).

## Assumptions to prove at design

- `command -v` is available in the shell Claude Code runs hooks under on every supported host
  (Linux, macOS, WSL2; native Windows runs hooks how? — check, do not assume).
- The added test stays inside the ~1.5 ms no-index cost (344): it runs only after the index test.

## Acceptance criteria

- **AC1:** with `PATH` stripped of the scripts, the generated SessionStart commands exit 0 and
  print exactly one line, across both, naming the install command.
- **AC2:** in the same state, a PostToolUse hook command exits 0 with no output.
- **AC3:** with the scripts present, every generated command is unchanged in behaviour.
- **AC4:** a repo with no `.code-atlas/` still exits at the first test.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 376 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W2, merges after #55, and bumps the plugin version in a release. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 375 - 376 - 377 - 378 - 379`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `fix/376-plugin-hook-without-console-scripts` off `fix/375-read-time-containment-in-source-slice` (`e5c1b0f5`, PR #55 — stacked).
  Contract `.mango/run-contract-376.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 2 want-decision asked | 7 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `PLUGIN_GATE` (`gen_skill.py:43`), `contrib/claude-code/README.md` step 1, `hooks/state.py`'s
"always exits 0", `tests/test_contrib_snippets.py`, the plugin `hooks.json` and the snippet all resolve.

**Recall (area `claude-code plugins`).** 348-C1 — an installed plugin moves only when its `version` does (H6);
344-C1 — the `if` filter is one rule per entry, untouched here.

**Spike.** In an indexed project with `PATH=/usr/bin:/bin`: today's gate exits **127** under `sh` (dash) and
`bash` (`exec: code-atlas-state: not found`); the probed gate prints the line and exits **0** under both.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,383 tokens) added W1–W2 and H7.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the install command named | how | README step 1: `uv tool install git+https://github.com/cuongdinhngo/code-atlas.git` (`contrib/claude-code/README.md:32`) |
| H2 | the snippet | how | unchanged: its commands carry no gate, and a hand install's step 1 is the scripts; 240's guard compares the ungated tables |
| H3 | PreCompact and the background refresh | how | silent — Scope 2: only SessionStart speaks |
| H4 | Windows | how | Claude Code docs (hooks page, read 2026-10-09): shell form runs under `sh -c`, Git Bash on Windows, PowerShell only without Git Bash — where today's `[ -d … ]` gate already cannot run |
| H5 | which script the probe tests | how | the one `exec` names |
| H6 | reaching installed plugins | how | only on a plugin version bump (348-C1) — the maintainer's release |
| H7 | a stale script on PATH | how | out of scope: 348/374's skew line names a lagging install |
| W1 | the line's channel | want | **ASSUMED (awaiting ratification):** plain stdout, the channel 348's skew line already uses at SessionStart |
| W2 | "said once" | want | **ASSUMED (awaiting ratification):** once per session start, until installed — once ever needs state, and Scope 4 forbids writing |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

Clarifications: H1–H7 cite code and docs; W1–W2 are resolved by the handover's delegation as `ASSUMED`.
TIER full: a generator, a generated table and tests — more than one file.

### BASELINE

375's final gate, the base of this branch: `21 passed · 0 failed · 0 skipped` — `GATE GREEN`. Ran at cde19da9.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "not the one command that fixes them" | the user is told the install command, never a 127 | ✅ |
| C1 | Scope 4 | "Never installs or edits anything" | the probe reads only | ✅ |
| C2 | Assumptions | "runs only after the index test" | probe after `[ -d … ] \|\| exit 0` | ✅ |
| R1 | Scope 1 | `command -v` before `exec` | every plugin command | ✅ |
| R2 | Scope 2 | SessionStart one line, others silent | W1, W2 | ✅ |
| R3 | Scope 3 | one table, in step | H2 | ✅ |
| AC1 | AC | SessionStart: exit 0, exactly one line naming the install | `sh` and `bash` | ✅ |
| AC2 | AC | a PostToolUse hook: exit 0, no output | every non-speaking command | ✅ |
| AC3 | AC | scripts present: unchanged | same argv reaches the script | ✅ |
| AC4 | AC | no index: exits at the first test | `bash -x` trace never reaches `command -v` | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `stdout == MISSING_SCRIPTS_LINE + "\n"`, rc 0, empty stderr | |
| AC2 | yes — `(0, "", "")` | widened to every non-speaking command |
| AC3 | yes — a stub echoes its argv; equals the ungated command | |
| AC4 | yes — `"command -v" not in` the `-x` trace | |

### Rule sections

`RULE SECTIONS: 5 applicable — 4 by change-type | 1 by recalled handle — §R1.8 (change-type) ✅ one plugin_command builds every gated hook, ungate is its inverse · §R6.5 (change-type) ✅ AC1 and AC2 red on the old hooks.json · §R6.7 (change-type) ✅ the tests derive the command set from the generated file · §R7.5 (change-type) ✅ comments ≤ 3 lines · §R5.3 (recalled handle claude-code plugins) ✅ the hook never fails; the line is the loud part`

## Phase 2 — design

### Approach

1. `PLUGIN_GATE` keeps the index test only; `plugin_command(command, speak)` appends
   `command -v <script> >/dev/null 2>&1 || exit 0` — or `{ echo '<line>'; exit 0; }` when it speaks — then `exec <command>`.
2. `_claude_code_hooks` takes `Callable[[str, bool], str]`: a speaking state hook for SessionStart, a silent one for
   PreCompact; the snippet's lambda ignores `speak`, so the snippet is byte-identical.
3. `ungate()` recovers the console-script command for the tests' table comparison and stubs.
4. Regenerate `hooks.json`; the plugin README and CHANGELOG name the line.

### Rejected alternatives

- **Probe in the snippet too** — a hand install's step 1 is the scripts; H2.
- **A marker file so the line is said once ever** — Scope 4 forbids writing (W2).
- **`systemMessage` JSON for the user** — a second channel beside 348's skew line (W1).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `command -v` in the hook shell | verified | spike under dash and bash; Claude Code docs H4 |
| inside the no-index cost | verified | the probe follows the index test; AC4's trace |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `plugin_command`, `ungate`, the line | `scripts/gen_skill.py` | every generated hook; the snippet (unchanged) | R1–R3 | 1/1 |
| 2 | regenerated table | `contrib/claude-code/plugin/hooks/hooks.json` | installed plugins after a version bump | R1, R2 | 1/1 |
| 3 | proving tests, `ungate` in helpers | `tests/test_claude_code_plugin.py` | 240's table guard | AC1–AC4 | 1/1 |
| 4 | docs | `contrib/claude-code/README.md`, `CHANGELOG.md` | — | G1 | 2/2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime — the hook shell | the generated command under real `sh` and `bash`, empty `PATH` | n/a | ✅ |
| AC2 | runtime | every other generated command under `sh` | n/a | ✅ |
| AC3 | runtime | each command against argv-echo stubs | n/a | ✅ |
| AC4 | runtime | `bash -xc` trace | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_claude_code_plugin.py tests/test_contrib_snippets.py`.

### Rollback

`git revert`; regenerate.

## Phase 3 — execute

Commits `f0318621` (generator, table, tests), `96170210` (docs). **Red first** (R6.5): with the old `hooks.json`
restored, `-k "missing or first_test"` gave `6 failed, 5 passed` — AC1 (`sh`, `bash`) and AC2 red; AC4 passed
before too (it guards the order, not a new behaviour). A first draft's line held an apostrophe that closed the
`echo`'s quotes; AC1 is what would have caught it, and the line now has none.

```
$ .venv/bin/python -m pytest -q tests/test_claude_code_plugin.py tests/test_contrib_snippets.py
59 passed in 0.54s
Ran at 61bd37ab
```

```
$ scripts/gate.sh
21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
Ran at 61bd37ab
```

**Verification sweep.** File axis: the diff is the change list; `ruff check scripts tests` clean; the snippet is
unchanged (`gen_skill.py` reported only `hooks.json` stale). Behaviour axis: Approach 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at 96170210 — files: `scripts/gen_skill.py`,
`contrib/claude-code/plugin/hooks/hooks.json`, `tests/test_claude_code_plugin.py`, `contrib/claude-code/README.md`,
`CHANGELOG.md`; working doc: this file.

- **`reviewer` round 1 — LGTM** (59,503 tokens): AC1–AC4 and Scope 4 checked; `ungate` cannot split inside
  the echoed line. Minors: the hand-wrapped `poke` dict — taken in `04514d00`, verify-only in the main loop
  (same file, layout only, 59 tests green); the `_speaker` comprehension's layout — left; the version bump —
  deferred to the maintainer.
- **`challenger` round 1** (ticket-blind, 57,660 tokens): 8 met · 0 not met · 1 can't tell — native Windows
  hook execution and the probe's cost were not measured (H4 is the docs' word).

Verdict: clean. Matrix `Ph3/4 proven by`: every row → `tests/test_claude_code_plugin.py`; C1 → the generated commands echo only.

## Phase 5 — finalise

**Durable lesson.** None new; the apostrophe that broke the `echo` was caught by AC1 before commit.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `fix/376-plugin-hook-without-console-scripts`; open the PR against 375's branch
(stacked on #55). Deferred to the maintainer: ratify W1–W2; merge; a plugin version bump (348-C1).

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 44,383 |
| 4 review | `reviewer` | 1 | 59,503 |
| 4 review | `challenger` (ticket-blind) | 1 | 57,660 |

`LEDGER TOTAL: 161,546 · top cost driver: 4 review/reviewer`
