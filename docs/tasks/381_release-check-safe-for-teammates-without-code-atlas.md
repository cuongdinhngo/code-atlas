---
id: 381
slug: release-check-safe-for-teammates-without-code-atlas
title: 'An install a day behind its release still hears nothing a person reads, and any fix must leave a teammate without code-atlas untouched'
phase: 2
milestone: Adoption
status: todo
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
