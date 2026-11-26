---
id: 452
slug: shared-adapter-config
title: "A git hook refreshes with the same adapters as the MCP server, or says which one it lacks"
phase: 2
milestone: Freshness
status: done
depends_on: [355, 401]
---

## Why this exists

Epic 451. On the PHP anchor every git-hook refresh was skipped (40 runs: 20 `coverage_loss`,
20 `no_usable_adapter`, 0 `refreshed`). The adapter commands (`CA_<LANG>_CMD`) are set in
`~/.profile`; the server, a Claude Code hook and a git hook each inherit a different environment,
and the anchor's session hook already re-reads `~/.claude.json` to make up for it. `refresh.log`
records neither the time nor which adapter was missing, so the context that lost them is unproven.

## Scope

1. **Prove first:** each `refresh.log` line carries a timestamp, the trigger (git hook name /
   session / poke) and the missing or failing adapter.
2. The adapter commands are resolvable from a file under `.code-atlas/` (local, never committed)
   that the server, `code-atlas-refresh` and every hook read; the environment still overrides it.
3. The git hooks in `contrib/git/` call `code-atlas-refresh` by the absolute path recorded at
   install, falling back to `PATH`.
4. No language name in the core (R1.1): the file maps whatever `CA_<LANG>_CMD` keys it holds.

## Acceptance criteria

- **AC1:** a git hook run with an empty environment (`env -i`) refreshes an index whose adapters
  are recorded only in the file.
- **AC2:** a skipped refresh's log line names the time, the trigger and the adapter.
- **AC3:** an environment variable set for one adapter wins over the file.
- **AC4:** on the PHP anchor, `git commit` produces a `refreshed` line (field check, recorded in this file).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 452 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 452 - 453 - 454 - 455 - 451`, first — `REVIEWER: OFF` (waived: "with
  skipped reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a
  want-decision is `ASSUMED`, never silent.
- Branch `feat/452-shared-adapter-config` from `docs/451-freshness-setup-epic` at `866a6dc9` (the epic's ticket
  files; stacked, the PR carries that commit). Contract `.mango/run-contract-452.txt` (mango 1.21.0), written
  before any code; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 4 want-decision asked | 3 how-decision resolved+cited | 4 ASSUMED | skip: no`

`.code-atlas/refresh.log` (the PHP anchor), `CA_<LANG>_CMD` (`config.ADAPTER_CMD_ENV`), `~/.claude.json`, `contrib/git/`,
`code-atlas-refresh` (`hooks/refresh.py`), 355 and 401 resolve. Recalled by handle (a new config source decides the
command code-atlas runs): 431-C1 `a-trust-root-never-rides-in-the-input`; by area: 389-C1 (freshness). The
exposure-checker (1 dispatch) returned 3; they are W2–W4.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the shared file lives | how | **not** under the repo: R9.1 / SEC-IN-03 — "nothing read from [the index directory] picks a command" — and 431-C1. A user-level `code-atlas/config.toml` under `XDG_CONFIG_HOME`, else `%APPDATA%` (Windows), else `~/.config`; `[adapter_cmd]` only. Every hook context has `HOME`. |
| H2 | precedence | how | user file → trusted project file → `CA_<LANG>_CMD`; the environment wins (scope 2) and a repo's file stays gated (341) |
| H3 | scope 3 (absolute path "recorded at install") | how | moves to 453: the path is known only to the installer 453 adds (453 scope 1). Here the contrib hooks pass `--trigger` only. |
| W1 | AC1's "empty environment" | want | **ASSUMED:** `env -i` plus `HOME` and a `PATH` holding the scripts — a user-level file is found through `HOME` |
| W2 | who writes the file | want | **ASSUMED:** 452 reads it, documented for hand-editing; 453's setup writes it from the current environment |
| W3 | how a skipped refresh surfaces | want | **ASSUMED:** the dated log line here, plus 401's existing status line; `unguarded` is 453's |
| W4 | the anchors' `~/.claude.json` fallback | want | **ASSUMED:** untouched — the environment still wins, so current setups keep working; 454 retires the anchors' scripts |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=4`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "every git-hook refresh was skipped" | a hook context without the shell's `CA_*` still refreshes | ✅ |
| R1 | Scope 1 | "each `refresh.log` line carries a timestamp, the trigger … and the missing or failing adapter" | UTC stamp, `--trigger`, `lost_languages` / `detail` | ✅ |
| R2 | Scope 2 | "resolvable from a file … that the server, `code-atlas-refresh` and every hook read; the environment still overrides it" | H1, H2 — one reader in `config.load_config` | ✅ |
| R3 | Scope 3 | "call `code-atlas-refresh` by the absolute path recorded at install" | H3: moved to 453 | ✅ (moved) |
| R4 | Scope 4 | "No language name in the core (R1.1)" | the file maps any key | ✅ |
| C1 | Why | "a repo's own file is not trusted to choose [a command]" (`config.py:466-470`) | H1 | ✅ |
| AC1 | Acc 1 | "a git hook run with an empty environment (`env -i`) refreshes an index whose adapters are recorded only in the file" | W1; the contrib `post-commit` script itself | ✅ |
| AC2 | Acc 2 | "a skipped refresh's log line names the time, the trigger and the adapter" | regex on stderr | ✅ |
| AC3 | Acc 3 | "an environment variable set for one adapter wins over the file" | `load_config` | ✅ |
| AC4 | Acc 4 | "on the PHP anchor, `git commit` produces a `refreshed` line (field check, recorded in this file)" | manual-check exclusion: the branch's refresh run on the PHP anchor under `env -i HOME PATH`, no commit made there | ✅ (exclusion) |

**Gap.** `config._adapter_cmds` (`config.py:456`) reads only the environment and a trust-gated project file, so a
process without the shell's `CA_*` has no adapter. `hooks/refresh.py:72-73` prints the bare reason, no time, no
trigger, no language. `indexer.COVERAGE_LOSS_HINT` points at `.code-atlas.toml`, which is refused without the flag.

`BASELINE: green — config, project-file trust, git hook, refresh, contrib, security-standard, session-state and language-agnostic suites: 588 passed`

Ran at 866a6dc9 (pre-change)
```
$ .venv/bin/python -m pytest -q $(cat .mango/baseline-452.list)
588 passed in 28.59s
```

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 the file is a table of any language key, R1.4 config.py touches no SQLite · §4 (change-type) ✅ R4.2 config_identity hashes the user file only when it exists, so an install without one keeps its id · §5 (change-type) ✅ R5.3 a malformed user file or an unknown key is a ConfigError · §6 (change-type) ✅ the proving test is seen failing on the base · §7 (change-type) ✅ R7.2/R7.6 docs pruned where they named .code-atlas.toml as the fix · §9 (change-type) ✅ R9.1 the command comes from a file outside the repo; the project file's gate is unchanged · §2 N/A because no adapter changes · §3 N/A because no contract vocabulary changes · §8 N/A because tomllib is stdlib`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `a-trust-root-never-rides-in-the-input` — traced: what picks a command is `config.adapter_cmds`, built once by
  `_adapter_cmds`; nothing else in `code_atlas/` reads a `CA_<LANG>_CMD` variable, so the new source joins there and
  only there, and it is read from outside the repo:

Ran at 866a6dc9 (pre-change)
```
$ grep -rn "_CMD\"\|environ.get(\"CA_" code_atlas --include=*.py | grep -v config.py
code_atlas/hooks/state.py:107:    return os.environ.get("CA_STATE_VERBOSE", "").strip() in {"1", "true", "yes"}
code_atlas/hooks/poke.py:21:    return os.environ.get("CA_POKE_VERBOSE", "").strip() in {"1", "true", "yes"}
code_atlas/hooks/signal.py:49:    return os.environ.get("CA_SIGNAL_VERBOSE", "").strip() in {"1", "true", "yes"}
code_atlas/hooks/refresh.py:27:    return os.environ.get("CA_REFRESH_VERBOSE", "").strip() in {"1", "true", "yes"}
code_atlas/indexer.py:378:    ".code-atlas.toml, or export CA_<LANGUAGE>_CMD"
code_atlas/indexer.py:1266:            f"adapter {key!r} has no configured command — set CA_{key.upper()}_CMD"
code_atlas/adapter.py:495:        {"language": name, "enable": f"CA_{name.upper()}_CMD"}
```

**Approach.** (1) `config.user_config_path(env)`: `$XDG_CONFIG_HOME`, else `%APPDATA%` on Windows, else
`$HOME/.config`, joined with `code-atlas/config.toml`, derived only from the mapping it is given (a test's mapping
never reaches the real home). (2) `_read_user_file` parses it, `[adapter_cmd]` only; anything else or bad TOML is a
`ConfigError`. (3) `_adapter_cmds` layers user file → trusted project file → environment. (4) `config_identity`
hashes the user file's bytes only when it exists, so an install without one keeps its id (R4.2); `Config.user_file`
lets `config_stale` re-derive it. (5) `refresh` takes `--trigger <name>` and prints
`<UTC> code-atlas refresh skipped (<trigger>): <reason> — lost: <langs> | <detail>`; the contrib hooks pass their
name. (6) `COVERAGE_LOSS_HINT` and the unconfigured-adapter message name the user file. (7) `tests/conftest.py`
points `XDG_CONFIG_HOME` at an empty temp dir so the suite never reads the developer's file.
**Rejected:** a file under the repo's `.code-atlas/` (the ticket's wording) — R9.1 makes the index directory
untrusted input, so it could not choose a command without the trust flag, which is the gap; re-reading
`~/.claude.json` in core (the anchors' fix) — it couples the core to one MCP client; a new `CA_USER_CONFIG` knob —
`XDG_CONFIG_HOME` already moves it.
**Assumptions:** `HOME` is set for git hooks run from a terminal, an IDE or a GUI — `verified` (POSIX login
environment; W1 records the acceptance reading). `tomllib` parses the same file on every host — `verified` (stdlib).
**Proving test:** `tests/test_user_adapter_config.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| user file + layering + identity | `code_atlas/config.py` | every `load_config` caller; `test_config*`, `test_project_file_trust`, `test_page_limit_max_candidates_split` (identity) | R2, R4, C1 · 1/1 |
| hint names the user file | `code_atlas/indexer.py` | `get_index_status`, `build_or_update_index`, `test_server_instructions.py:162` | R2 |
| dated, triggered skip line | `code_atlas/hooks/refresh.py` | `test_git_refresh_hook.py:65,88` (substring asserts, kept) | R1 · 1/1 |
| `--trigger` | `contrib/git/post-{merge,checkout,commit,rewrite}` | `test_silent_refresh_failures`, `test_a_refused_refresh_is_served`, `test_reads_during_a_refresh` (run them) | R1 · 4/4 |
| suite isolation | `tests/conftest.py` | every subprocess test | R2 |
| proving test | `tests/test_user_adapter_config.py` | — | AC1–AC3 · 3/3 |
| docs | `README.md`, `contrib/git/README.md`, `docs/PLAN.md`, `CHANGELOG.md` | — | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime (a git hook under a stripped environment) | integration: the contrib `post-commit` run under `env -i HOME PATH`, index read back | n/a | ✅ |
| AC2 | integration (the refresh process's stderr) | integration: subprocess, regex on the line | n/a | ✅ |
| AC3 | logic (layer order) | unit: `load_config` | n/a | ✅ |
| AC4 | runtime on the anchor | manual-recorded (exclusion below) | n/a | ✅ |

**Coverage-gap exclusions.**
- AC4 · risk: medium · why deferred: a real `git commit` on the PHP anchor is an outward write to another repo; the field
  check runs this branch's refresh there under `env -i HOME PATH` instead and records the line · follow-up: the
  installed hooks re-checked once 453 ships · expiry: 453 · seen: 452
- R2's location (added at review, challenger round 1) · risk: low · why deferred: the ticket names `.code-atlas/`;
  R9.1 / SEC-IN-03 forbid a command chosen from the index directory, so the file is user-level (H1) — ASSUMED
  under the handover, for the maintainer to ratify · follow-up: ratify or reject on the PR · expiry: 453 · seen: 452
- R3 (added at review) · risk: medium · why deferred: an absolute path exists only at install, which 453 adds (H3)
  · follow-up: 453 scope 1 · expiry: 453 · seen: 452

`EXCLUSIONS: 3 recorded | 3 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert the branch; a user file left behind is ignored by older releases. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer`, at `f42cc139`. **Sweep.** Axis 1: the diff is the approved list plus two recorded deviations;
`ruff` and `mypy` clean. Axis 2: approach bullets (1)–(7) implemented-as-approved.

**Deviations (recorded).**
- D1 `tests/test_git_refresh_hook.py:106` asserted the old `code-atlas refresh skipped:` prefix — proof collateral
  the design's trace listed only as "substring asserts, kept"; it now asserts the dated, triggered line.
- D2 `docs/TOOLS.md` carries the same `CA_<LANG>_CMD` row as `README.md`; both name the user file. The PLAN entry
  sits in §19's 341 line; §11 was tightened to stay under `test_doc_size_budget` (20,000 tokens).
- The hint lost "before rebuilding" for "first": the longer path pushed the server `instructions` past
  `CLIENT_CAP` (`test_server_instructions.py`, 1956 > 1928).

The proving test on the base (only the test file added):

Ran at 866a6dc9 (pre-change)
```
$ .venv/bin/python -m pytest -q tests/test_user_adapter_config.py
E   ImportError: cannot import name 'user_config_path' from 'code_atlas.config'
1 error in 0.09s
```

**AC4 field check (the PHP anchor, no commit made there).** the PHP anchor's own, unmodified `.git/hooks/post-commit` (what a
`git commit` runs), under a stripped environment, writing to its `refresh.log` — first with the installed 0.11.0,
then with this branch's scripts first on `PATH` and the adapters only in a user file:

Ran at 11867fef
```
$ cd the PHP anchor && env -i HOME=$HOME CA_REFRESH_VERBOSE=1 PATH=$HOME/.local/bin:/usr/bin:/bin sh .git/hooks/post-commit; tail -1 .code-atlas/refresh.log
code-atlas refresh skipped: coverage_loss
$ env -i HOME=$HOME XDG_CONFIG_HOME=<scratch>/xdg CA_REFRESH_VERBOSE=1 PATH=<branch venv>/bin:/usr/bin:/bin sh .git/hooks/post-commit; tail -1 .code-atlas/refresh.log
code-atlas refresh: refreshed
```

So the cause of the 40 skips is confirmed: the hook's environment has no `CA_<LANG>_CMD`.

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone; payload = the raw ticket (`git show 866a6dc9:<this file>`) + the branch diff, working doc excluded.

- **Round 1** at `05d1eb22` (67,923 tokens): 8 rebuilt · 5 met · 2 not met · 1 can't tell. **Taken:** F3 — the
  plugin's session refresh passes `--trigger session-start`; F4 — a user file naming a missing adapter binary yields a
  dated `no_usable_adapter — …` line naming the adapter, end to end (`11867fef`). **Recorded:** R2's location and R3
  as exclusions (Phase 2), ASSUMED under the handover. Minor, not taken: an unreadable user file is skipped by
  `config_identity` but raises in `load_config` — the id must never raise, as for the project file.
- **Round 2** (resumed, at `11867fef`; the fixes left the approved set): R2, R3 not met, covered by the exclusions;
  AC4 can't tell. **Round 3** (resumed, AC4 only, handed the raw field output): still can't tell — the field check ran
  this branch's refresh, not a `git commit` through the installed 0.11.0 hook. AC4's exclusion (expiry 453) is that
  substitution; the challenger, blind to the working doc, did not count it. **Round 4** (resumed, AC4 only): the field
  check re-run at `11867fef` through the PHP anchor's own `post-commit` script into its `refresh.log` — met, with caveats
  carried to the PR: the `refreshed` line is the verbose one; the PHP anchor still skips until a release with this change is
  installed and its user file exists; its hook still finds the script through `PATH` until 453.

`CHALLENGER VERDICT: 8 requirement(s) rebuilt | 6 met | 2 not met | 0 can't tell | 2 not-met covered by a recorded exclusion`

Ran at 11867fef
```
$ .venv/bin/python -m pytest -q <baseline-452 list> tests/test_user_adapter_config.py tests/test_reads_during_a_refresh.py tests/test_server_instructions.py tests/test_hook_offers_agree_across_hosts.py tests/test_claude_code_plugin.py <skill/plugin suites> tests/test_doc_size_budget.py
696 passed in 40.32s
```

Reviewed at 11867fef — files: `code_atlas/config.py`, `code_atlas/hooks/refresh.py`, `code_atlas/indexer.py`,
`contrib/git/post-{merge,checkout,commit,rewrite}`, `contrib/git/README.md`, `scripts/gen_skill.py`,
`contrib/claude-code/plugin/hooks/hooks.json`, `tests/conftest.py`, `tests/test_user_adapter_config.py`,
`tests/test_git_refresh_hook.py`, `tests/test_claude_code_plugin.py`, `README.md`, `docs/TOOLS.md`, `docs/PLAN.md`,
`CHANGELOG.md`; working doc `docs/tasks/452_shared-adapter-config.md`.

`Ph3/4 proven by`: R1, AC1–AC3 → `tests/test_user_adapter_config.py` (9); R4 → `tests/test_core_is_language_agnostic.py`;
AC4 → the field check above; R2 (location), R3 → exclusions, expiry 453.

## Phase 5 — finalise

Stale-review guard: `git diff --name-only 11867fef..HEAD` plus the working tree holds only bookkeeping (this file,
`docs/LESSONS.md`, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`) — not stale.

**Durable lesson.** 452-C1 `a-hook-inherits-no-shell-profile` (type 2) and 452-C2 `symbol:check_lines.py` (type 1),
both first sightings, in `docs/LESSONS.md`.

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=1 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/452-shared-adapter-config`; open its PR against `main` (stacked: it carries the epic's
ticket commit `866a6dc9`). Deferred to the maintainer: ratify W1–W4 and the R2-location / R3 exclusions; merge; install
a release with this change on the PHP anchor and write its user file — until then its real `git commit` still skips.

Next: 453 (`code-atlas-setup`), branched from this one. Revert: revert the branch's commits; a user file left behind is
ignored by older releases.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 50,297 |
| 4 review | ticket-blind `challenger` | 1 | 67,923 |
| 4 review | ticket-blind `challenger` | 2 | 4,148 (resumed: 72,071 cumulative − 67,923) |
| 4 review | ticket-blind `challenger` | 3 | 1,913 (resumed: 73,984 − 72,071) |
| 4 review | ticket-blind `challenger` | 4 | 1,573 (resumed: 75,557 − 73,984) |

`LEDGER TOTAL: 125,854 · top cost driver: 4 review / challenger` — main loop unmeasured.
