---
id: 381
slug: release-check-safe-for-teammates-without-code-atlas
title: 'An install a day behind its release still hears nothing a person reads, and any fix must leave a teammate without code-atlas untouched'
phase: 2
milestone: Adoption
status: done
depends_on: [348, 374]
---

## Why this exists

This is a second field report that meets the re-open condition of the 374 entry in
[PLAN §19](../PLAN.md#19-project-context--decision-log): "an install running an old release
without knowing."

An anchor project (PHP + SQL + TS, ~22.9k files, Linux) observed the following on 2026-10-10:

- **The developer learned of the update by asking.** They asked whether the index was current, and
  then why nothing had told them code-atlas had moved.
- **Three halves, three ages:**

  | Half | State |
  |---|---|
  | plugin | `0.2.0`. The marketplace clone was 8 days old and 173 commits behind `main`. |
  | tool install | `0.3.0`, pinned by the uv receipt to `?rev=54242f1`. That is 53 commits behind `main`, and `main` still says `0.3.0`. |
  | adapter checkout | 1 commit behind (docs only) |

- **The 348 skew line fired, but no person read it.** At session start the hook printed
  `hooks expect code-atlas 0.2.0 but 0.3.0 is installed — run claude plugin marketplace update …`.
  SessionStart stdout goes into the agent's context, not the developer's screen, and the agent did
  not relay it until it was asked. The offline check worked, but the developer never saw it.
- **Auto-update was off.** `known_marketplaces.json` has no `autoUpdate` key for this marketplace,
  which is the documented default for a third-party marketplace. 374 makes auto-update the half
  that moves first. The developer never turned it on, and nothing prompted them to.
- **A pinned tool install cannot be upgraded.** The receipt's `?rev=` pin makes
  `uv tool upgrade code-atlas` a no-op. **UNVERIFIED:** how the pin got there. The README
  installs from `git+…` with no rev.
- **53 commits shipped under one version.** `main` moved from `54242f1` to `864ae8a` and kept
  `0.3.0`. Even with auto-update on, Claude Code does not move a plugin whose `version` is unchanged
  (348's spike). Whether those commits count as "a newer release" is a definition question
  (Scope 3).
- **The newest release has no tag.** `git ls-remote --tags origin` lists only `v0.2.0`. A check
  that reads tags would call 0.2.0 the newest release.

**The constraint that outranks the check.** The anchor commits its Claude Code configuration:
project hooks in `.claude/settings.json` and a committed `.code-atlas.toml`. Most of its
developers do not install code-atlas: they have no plugin, no console scripts, no index and no
adapter checkout. Anything this ticket adds, whether a hook command, a settings recommendation or a
README step an anchor copies into its repo, must leave those developers' sessions exactly as they
are today. That means no error, no prompt, no added latency, no network call and no line of
output.
374 left one such risk open: the README suggests a project-level
`extraKnownMarketplaces.<name>.autoUpdate` for a team, which may **prompt every teammate who
trusts the folder to install the marketplace**. That suggestion was never measured.

## Scope

1. **Teammates without code-atlas are untouched (non-negotiable).** Every new or changed path,
   whether a hook command, a script, a settings snippet or a README recommendation for committed
   project settings, does nothing on a machine that has no index, no plugin or no console scripts.
   It prints nothing, exits 0, makes no network call and shows no prompt. The gate comes before any
   other work, as 344's `[ -d .code-atlas ] || exit 0` and 376's missing-scripts exit do today.
2. **A person reads the line.** When the session-start hook has something to say (skew, lag,
   rebuild required), the developer sees it, not only the agent. Candidate: SessionStart JSON
   output with `systemMessage`. Measure what Claude Code shows. The agent keeps its own copy.
3. **Define "newer" before checking for it.** A release is a tagged `vX.Y.Z` (348). Then:
   - tag every release, and add a gate test that fails when `CHANGELOG.md`'s top version has no tag;
   - decide whether untagged commits under an unchanged version are "newer". The 53-commit span
     says the answer must be stated, either way.
4. **Re-decide PLAN §19's network release check with this report.** If adopted, it must:
   - live outside `code_atlas/` (R4/R4.1) and off the MCP path;
   - run only after Scope 1's gate passes;
   - be opt-out (`CA_NO_UPDATE_CHECK=1`);
   - be cached at most once a day per user, not per project;
   - be bounded by a short timeout;
   - be silent when offline, when there is no `git` and when the remote fails;
   - never block the session.

   If it is rejected, record why the Scope 2 line and auto-update are enough, given that this report
   happened with the skew line firing.
5. **Pinned installs.** `code-atlas-state` names a `?rev=`-pinned tool install, which
   `uv tool upgrade` cannot move, and gives the unpinned install command. README *Upgrading* says
   the same.
6. **Project-level auto-update, measured or withdrawn.** Measure, on the current Claude Code, what a
   committed `extraKnownMarketplaces` entry does for a teammate who does not have code-atlas: a
   prompt, a silent install or nothing. If it prompts or installs, remove the team recommendation
   from the README and say why.

## Assumptions to prove at design

- **SessionStart `systemMessage` reaches the developer's screen** on the current Claude Code, and the
  agent still receives the line. Measure both.
- **The cost of the gate for a teammate without code-atlas is zero in practice.** Time the
  hook on a machine with no `.code-atlas/`, no scripts and no `jq`, on Linux and on Windows Git Bash.
  The bar is no measurable delta against the hook absent.
- **Where a network check can live without breaking R4.1.** `code-atlas-state` sits in
  `code_atlas/hooks/`, inside the core. Candidates: a separate console script outside `code_atlas/`,
  or the plugin's hook command itself.
- **Why the receipt was pinned.** Find the install route that writes `?rev=`, whether a `setup.py`
  path, a README line or a hand install, before writing the fix line.

## Acceptance criteria

- **AC1 (teammate without code-atlas):** In a repo that commits the anchor's shape of configuration,
  a session on a machine with no plugin, no console scripts and no index prints nothing, exits 0,
  makes no network call (proved with the network blocked, and with a stub on `PATH` that records any
  `git`/`curl` invocation), shows no prompt and adds no measurable start-up time. It is run on Linux
  and Windows Git Bash, each case is seen red first against a deliberately ungated build (R6.5), and
  every new path in this ticket passes it.
- **AC2:** With the plugin behind the tool install, the developer sees the skew line on screen at
  session start, and the agent's context still carries it.
- **AC3:** Every release has a `vX.Y.Z` tag, and a test fails when `CHANGELOG.md`'s top version has
  none. `v0.3.0` exists.
- **AC4:** A `?rev=`-pinned tool install is named at session start with the unpinned install
  command. The line is silent for an unpinned install.
- **AC5:** The measured project-level `extraKnownMarketplaces` behaviour for a teammate without
  code-atlas is recorded in the README, and the team recommendation is kept or withdrawn
  accordingly.
- **AC6:** PLAN §19 carries the re-decided entry. If a network check ships, it meets every Scope 4
  bound and AC1. If it does not, the entry says what tells an install like this report's that it
  is behind.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 381 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer pushes `v0.3.0` (E3), ratifies W1–W3, checks E1/E4 on a live Claude Code, and merges after #64. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 381 - 382 - 386 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/381-release-check-safe-for-teammates` off `feat/386-unqualified-exec-in-a-host-string` (PR #64 — stacked).
  Contract `.mango/run-contract-381.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 3 want-decision asked | 10 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** PLAN §19's 348/374 entry, `code_atlas/hooks/state.py`, the plugin hooks
(`contrib/claude-code/plugin/hooks/hooks.json`), the hand snippet, README *Upgrading*,
`tests/test_release_discipline.py` and `.github/workflows/ci.yml` resolve.

**Recall (area).** 345-C1 (a PostToolUse hook's plain stdout never reaches the model) and 348-C1 (a plugin
moves only when its version does) — both about where a hook's line lands, the ticket's Scope 2.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 45,530 tokens) added W3 and H10.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | what Scope 1 gates | how | every command code-atlas offers: the plugin's (already gated, 344/376) and the **hand snippet**, which named each script bare — exit 127 for a teammate whose project merged it. Now gated like the plugin's, never speaking (`gen_skill.render_claude_code_snippet`) |
| H2 | how a person reads the line | how | SessionStart answers JSON — `systemMessage` for the developer, `additionalContext` with every line for the agent; Claude Code's `hooks.md`: SessionStart plain stdout goes to context, `systemMessage` "surface[s] a message to the user" |
| H3 | PreCompact | how | plain text: `hooks.md` says PreCompact discards `systemMessage` (and adds no stdout to context — a follow-up) |
| H4 | "newer" | how | a tagged `vX.Y.Z` (348's definition, Scope 3); untagged commits are not newer and gather under CHANGELOG *Unreleased* |
| H5 | the tag gate | how | `test_the_top_release_is_tagged`, strict xfail only while the version is 0.3.0 (E3); CI's test job `fetch-depth: 0` to read tags |
| H6 | pin detection | how | `sys.prefix/uv-receipt.toml`, the `code-atlas` requirement's git URL carrying `?rev=`/`?tag=`; the reinstall names the receipt's own URL |
| H7 | why the receipt was pinned | how | measured, uv 0.11.28: `git+URL` writes no rev, `git+URL@<sha>` writes `?rev=<sha>`, and `uv tool upgrade` then says "Nothing to upgrade"; no route in this repo names `@<ref>`, so it was a hand install (this machine's receipt is pinned too, `?rev=864ae8a`) |
| H8 | where a network check could live | how | moot — W1 rejects it |
| H9 | the team auto-update setting | how | withdrawn: `settings-reference.md` / `plugins/loading.md` say a committed `extraKnownMarketplaces` entry is registered and cloned in the background for anyone trusting the folder — a network call on a teammate's machine (Scope 6's "installs" branch) |
| H10 | repos that already merged the old snippet | how | CHANGELOG *Unreleased* and the contrib README say re-copy it |
| W1 | a network release check | want | **ASSUMED (awaiting ratification):** rejected again — PLAN §19 says why and what tells such an install now |
| W2 | which lines go on screen | want | **ASSUMED (awaiting ratification):** a skew/lag, a pinned install, a pending rebuild; a behind or building index stays agent-only |
| W3 | a deliberate pin nagged every session? | want | **ASSUMED (awaiting ratification):** yes, no opt-out — the fix is one command, and a pin is the report's failure |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=6 G=1 AC=6`
`CLARIFICATION: 16 raised | 16 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/17 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

The base is 386's branch; its gate is recorded in 386's Phase 3. Ran at dfdb7048.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "The developer learned of the update by asking" | a person hears what the hook knows | ✅ |
| C1 | Why | "must leave those developers' sessions exactly as they are today" | Scope 1 before everything | ✅ |
| R1 | Scope 1 | teammates without code-atlas untouched | H1 | ✅ |
| R2 | Scope 2 | a person reads the line | H2, W2 | ✅ (display: E1) |
| R3 | Scope 3 | define newer; tag every release; gate | H4, H5 | ✅ (tag: E3) |
| R4 | Scope 4 | re-decide the network check | W1 | ✅ |
| R5 | Scope 5 | name a pinned install | H6, H7 | ✅ |
| R6 | Scope 6 | measure or withdraw the team setting | H9 | ✅ (live: E4) |
| AC1 | AC | silent, exit 0, no network, no prompt, no delay; Linux + Git Bash; red first | | ✅ Linux / E2 |
| AC2 | AC | the skew line on screen and in context | | ✅ / E1 |
| AC3 | AC | every release tagged; a failing test; `v0.3.0` exists | | ✅ test / E3 |
| AC4 | AC | a pin named with the unpinned command; silent unpinned | | ✅ |
| AC5 | AC | the measured behaviour in the README; kept or withdrawn | documented behaviour, withdrawn | ✅ / E4 |
| AC6 | AC | PLAN §19 re-decided; what tells such an install | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — rc 0, empty stdout/stderr, no stub invocation, for 10 commands × bash/sh; ungated copy red; median spawn 1.48 ms against 1.47 ms for `true` (bar: < 5 ms) | Git Bash: E2. "Network blocked": `unshare -rn` is not permitted on this host, so the recording stubs (`git`, `curl`, `wget`, `uv`) and a `PATH` holding nothing else stand in; no `jq` on that `PATH` either |
| AC2 | the JSON: yes; a person seeing it: **manual-check exclusion E1** | |
| AC3 | the test: yes; the tag: **E3** | |
| AC4 | yes — receipt fixtures, pinned and unpinned | |
| AC5 | documented: yes; live: **E4** | |
| AC6 | yes — the entry's text | |

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R4.1 (change-type) ✅ no network call anywhere; state.py reads a local TOML · §R1.1 (change-type) ✅ no language branch · §R6.5 (change-type) ✅ the teammate test red on the old snippet (9 failed), the tag test proven to flip · §R6.7 (change-type) ✅ the snippet and plugin come from one generator · §R7.5 (change-type) ✅ comments ≤ 3 lines · §R7.6 (change-type) ✅ PLAN's 374 bullet merged with 381's, net-neutral against its budget`

## Phase 2 — design

### Approach

1. `gen_skill.render_claude_code_snippet` gates each command with `plugin_command`; regenerate.
2. `state.py`: `pinned_line`, `screen_lines`; SessionStart answers JSON when a screen line exists.
3. `get_index_status.REBUILD_LEAD` names the summary lead the hook keys on.
4. `test_the_top_release_is_tagged` + CI `fetch-depth: 0`; `release_drift` reads the top release's own body.
5. README *Upgrading*, contrib README, TOOLS.md, PLAN §19, CHANGELOG *Unreleased*.

### Rejected alternatives

- **A network check in a separate script** — W1; every hook path also reaches teammates.
- **A dismissal file for the pin line** — state for one line, W3.
- **Tagging `v0.3.0` from this run** — an outward action outside the handover (E3).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| SessionStart `systemMessage` reaches the screen, the agent keeps `additionalContext` | verified (docs) / novel-untested (live) | `hooks.md`; E1 |
| the gate costs a teammate nothing measurable | verified (Linux) | 1.48 ms vs 1.47 ms median of 25 spawns |
| where a network check could live | n/a | W1 |
| why the receipt was pinned | verified | H7 |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | gate the snippet | `scripts/gen_skill.py`, `contrib/claude-code/settings.snippet.json` | every project that merges it | R1, AC1 | 2/2 |
| 2 | on screen; the pin | `code_atlas/hooks/state.py`, `code_atlas/tools/get_index_status.py` | SessionStart output | R2, R5, AC2, AC4 | 2/2 |
| 3 | the tag gate | `tests/test_release_discipline.py`, `.github/workflows/ci.yml` | CI checkout | R3, AC3 | 2/2 |
| 4 | proving tests and their neighbours | `tests/test_teammate_without_code_atlas.py`, `tests/test_state_line_on_screen.py`, `tests/test_session_state_hook.py`, `tests/test_claude_code_plugin.py`, `tests/test_hook_offers_agree_across_hosts.py`, `tests/test_poke_snippet_covers_every_adapter.py` | — | AC1–AC4 | 6/6 |
| 5 | docs | `README.md`, `contrib/claude-code/README.md`, `docs/TOOLS.md`, `docs/PLAN.md`, `CHANGELOG.md` | doc budgets | R3, R4, R6, AC5, AC6 | 5/5 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime — a real shell, real hook commands | `tests/test_teammate_without_code_atlas.py` | authored | ✅ Linux / ❌ Git Bash (E2) |
| AC2 | runtime — the host's rendering | JSON shape tests | authored | ❌ E1 (recorded exclusion) |
| AC3 | repo state | the tag test | the repo | ❌ E3 (recorded exclusion) |
| AC4 | integration | receipt fixtures through `state.main` | authored | ✅ |
| AC5 | the host's behaviour | the docs, quoted | docs | ❌ E4 (recorded exclusion) |
| AC6 | doc | PLAN §19 | n/a | ✅ |

**Exclusions** (each with a non-author-checkable expiry):
- **E1 — the line on a real screen.** `expiry:` the maintainer opens a Claude Code session in a repo whose
  hooks expect another version and records here whether the line showed.
- **E2 — Windows Git Bash.** `expiry:` `tests/test_teammate_without_code_atlas.py` passes on a Windows host
  under Git Bash (it skips on `nt` today), recorded here.
- **E3 — `v0.3.0`.** Pushing a tag is outside the handover. `expiry:` `git ls-remote --tags origin v0.3.0`
  prints a line; the strict xfail then fails and is removed.
- **E4 — a teammate trusting a folder with `extraKnownMarketplaces`.** `expiry:` a session as such a teammate,
  network observed, recorded in the README sentence that says "documented, not yet measured live".

`EXCLUSIONS: 4 recorded | 4 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_teammate_without_code_atlas.py tests/test_state_line_on_screen.py tests/test_release_discipline.py`.

### Rollback

`git revert`; projects keep whichever snippet they merged.

## Phase 3 — execute

Commits `a2bc96ea` (the gated snippet), `c29911f8` (on screen, the pin), `5daf90ef` (the tag test), `3c3e7b4a`
and `1eff00cf` (docs). **Red first** (R6.5): with the pre-381 snippet the teammate test fails 9 cases (every
bare command, exit 127); a local, unpushed `v0.3.0` tag flips the strict xfail to a failure (tag removed after).

**Verification sweep.** File axis: the diff is the change list; `ruff check .`, `mypy code_atlas onboarding_llm`
clean; 358 hook, doc and release tests green with one expected xfail. Behaviour axis: Approach 1–5 implemented
as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at 1eff00cf — files: the change list above;
working doc: this file.

- **`challenger` round 1** (ticket-blind, 64,671 tokens): 6 met · 2 not met · 2 can't tell. Not met: `v0.3.0`
  does not exist (E3); AC5 is documented, not measured (E4). Can't tell: the Windows / blocked-network arm
  (E2, and the stub stand-in above) and the live display (E1). Residuals answered: the test image keeps
  `.git` (`.dockerignore`: "`.git` is kept"), so the tag test runs there; `scripts/gate.sh` runs in a full
  local clone; the reinstall URL is the receipt's own, query stripped. No code change was needed.

Verdict: clean (challenger only — REVIEWER: OFF), with E1–E4 open for the maintainer. Matrix `Ph3/4 proven by`:
R1, AC1 → the teammate test; R2, R5, AC2, AC4 → `tests/test_state_line_on_screen.py`; R3, AC3 → the tag
test; R4, R6, AC5, AC6 → README and PLAN §19.

## Phase 5 — finalise

**Durable lessons.** 381-C1 (where a SessionStart line lands) and 381-C2 (uv pins only on `@<ref>`), in LESSONS.

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=2 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/381-release-check-safe-for-teammates`; open the PR against 386's branch (stacked on #64).
Deferred to the maintainer: push `v0.3.0` (`git tag v0.3.0 a6e0e6b4 && git push origin v0.3.0` — the
commit is the maintainer's call), ratify W1–W3, E1/E2/E4, merge after #64.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 45,530 |
| 0 refine | `claude-code-guide` (hook and settings docs) | 1 | 84,718 |
| 4 review | `challenger` (ticket-blind) | 1 | 64,671 |

`LEDGER TOTAL: 194,919 · top cost driver: claude-code-guide`
