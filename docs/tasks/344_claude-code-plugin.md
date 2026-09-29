---
id: 344
slug: claude-code-plugin
title: 'Ship code-atlas as a Claude Code plugin — server, hooks and skill in one install'
phase: 2
milestone: Adoption
status: todo
depends_on: [036, 099, 322]
---

## Why this exists

Every channel code-atlas controls reaches the model **before** or **after** the decision that
matters, never *at* it:

| Channel | When it speaks | Limit |
|---|---|---|
| Server `instructions` (300) | Session start | Capped and frozen (343) |
| Tool descriptions (069) | After a ToolSearch load | Claude Code delivers tools as deferred names, so the description is unseen until the model has already chosen the tool |
| Tool results | After a call | Silent when the agent never calls |
| Hooks `poke` / `signal` / `state` (036, 099, 322) | At the moment | **Offered, never installed**: `contrib/claude-code/settings.snippet.json` has to be merged by hand in each repo |

So in any repo where nobody read `contrib/`, the only channels in play are the first three. This
ticket makes the fourth a one-step install; 345 adds the hook that speaks at the grep decision.

## Evidence (anchor repo, 2026-09-29)

- Registration is still a hand-typed `claude mcp add-json` with an absolute interpreter path. A
  backslashed path fails as `Invalid configuration: : Invalid input` (anchor
  `CODE_ATLAS_SETUP.md` §3). The absolute path exists because a venv's console scripts are not on
  PATH — the same trap a plugin that launches `code-atlas*` by name walks into.
- The anchor's SessionStart hook `code-atlas-session-refresh.sh` starts a background incremental
  refresh on a `behind` index, which `code-atlas-state` does not. Upstream already has the refresh
  itself: `code-atlas-refresh` (053) — locked, a no-op without an index, always exit 0.

## Scope

1. **Plugin manifest in this repo:** `.claude-plugin/plugin.json` plus a `marketplace.json`, so
   `/plugin marketplace add <repo>` → `/plugin install code-atlas` covers every project for that user.
   It bundles:
   - **`mcpServers`**, launching the `code-atlas` server, which replaces `claude mcp add-json`;
   - **hooks**: `code-atlas-state` (SessionStart, PreCompact), `code-atlas-poke` (PostToolUse
     Edit/Write, async), `code-atlas-signal` (PostToolUse Read, PreToolUse Write) — the existing
     snippet, generated from the same source so the two cannot drift;
   - **skill**: the generated `contrib/skill/SKILL.md`, which holds the full recognition map that 343
     takes out of `instructions`. The two are independent: the skill ships the full map either way.

   This keeps the 036/099 rule: code-atlas writes to no settings file. The user's one install is
   the opt-in.
2. **Refresh on a `behind` index at SessionStart** by spawning `code-atlas-refresh` in the
   background, as its own SessionStart entry beside `code-atlas-state` — no new flag or second
   refresh path. It skips with one line when an adapter command
   is unset (the `coverage_loss_pending` case).
3. **Every hook gates itself on the repo.** A user-scope plugin fires in *every* project, so each
   command is a silent no-op when the cwd has no `.code-atlas/`.

## Acceptance criteria

- **AC0:** Both open questions below are decided at Gate 2 and recorded in this ticket before any
  code lands; AC1 then names the launch step it verifies.
- **AC1:** On a clean machine with code-atlas pip-installed **into a venv not on PATH**,
  `/plugin install` plus at most one documented step gives a connected server and all four hook
  commands (`code-atlas-state`, `-poke`, `-signal`, `-refresh`). There is no `claude mcp add-json`,
  no settings merge and no hand-typed interpreter path. This is verified on a running Claude Code
  (not from docs, per 200's A-4 discipline).
- **AC2:** In a repo with no index, no hook prints anything and each exits 0. A test covers each
  command, and the per-hook cost in a non-indexed repo is measured and recorded (Windows and
  POSIX) — a Python entry point pays interpreter startup, so the number is measured, not promised.
- **AC3:** A test fails when the plugin's hook list and `settings.snippet.json` disagree.

## Open questions

- **Launching.** `mcpServers` and hook commands name `code-atlas*`, which a venv install does not
  put on PATH. Decide between a plugin `userConfig` interpreter path, a `pipx`/`uv tool` install
  requirement, or a launcher shim under `${CLAUDE_PLUGIN_ROOT}` — and whether a cheap pre-filter
  can skip the Python spawn in repos with no `.code-atlas/`.
- **Adapters.** The plugin cache holds a clone, but the PHP and TS/SQL adapters need a Composer or npm
  install, and `CA_<LANG>_CMD` is still per-machine. Decide whether the plugin defaults `CA_*_CMD` to
  `${CLAUDE_PLUGIN_ROOT}/adapters/...` with a first-run install step, or stays server-and-hooks only
  and leaves adapters to the README.

## Outward actions

Publishing the marketplace (the public repo's `.claude-plugin/` on `main`) is an outward action: it
takes its own explicit approval at finalise, separate from the PR.

## Out of scope — follow-up

- **The grep-time nudge** — 345.
- **`code-atlas init`**, for what has to live *in* the repo for a team: a `.code-atlas.toml`
  skeleton, a marker-fenced routing block in CLAUDE.md/AGENTS.md, and git hooks. The plugin is per
  user; `init` is per repo. Ticket it once this lands, and only if a second anchor project asks.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 344 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun` (unattended, stops at the PR). Run arg *"with skipped
  reviewer"* = `--no-reviewer` only; the ticket-blind challenger keeps its seat.
- Contract `.mango/run-contract-344.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN
  | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 4 want-decision asked | 11 how-decision resolved+cited | 4 ASSUMED | skip: no`

Premise: `contrib/claude-code/settings.snippet.json`, `code-atlas-state`/`-poke`/`-signal`/`-refresh`
(`pyproject.toml` scripts), `contrib/skill/SKILL.md`, `scripts/gen_skill.py`, `hooks/refresh.py`,
036/099/322 — all resolve. Ambiguous: the anchor's `CODE_ATLAS_SETUP.md` §3 and
`code-atlas-session-refresh.sh` live in another repo — evidence only, nothing here resolves against them.

Recall: `343-C2` (`formatter-rewrites-untouched-lines`) by handle — this change edits
`scripts/gen_skill.py`, a shared generator. Advisory.

**Spike — what Claude Code 2.1.284 actually hands a plugin** (throwaway plugin via `--plugin-dir`,
`claude -p` in a fresh git repo). The docs research had said the MCP server runs from the plugin root;
the spike says otherwise:

| Probe | Observed |
|---|---|
| MCP server cwd | the **project** dir; `CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_ROOT` exported |
| `${user_config.python}` in `mcpServers.env` | expands (`/usr/bin/python3`; empty when unset) |
| same option in a hook's env (`CLAUDE_PLUGIN_OPTION_PYTHON`) | **absent** |
| same option in an exec-form hook's `args` | the hook **did not run** |
| hook cwd | the project dir; `CLAUDE_PROJECT_DIR` exported |
| `claude plugin validate` | passes; warns only on a missing `author` |

**Want-decisions — handed back by the maintainer** (*"You have my approval to choose the best
approach, make the necessary decisions"*), so each is `ASSUMED (awaiting ratification)`:

| # | The want | ASSUMED answer | Why |
|---|---|---|---|
| W1 | Launching (open question 1): how do `mcpServers` and hooks reach `code-atlas*` from a venv not on PATH? | **The console scripts go on PATH through a tool install** — `uv tool install` or `pipx install` — and every command names them. No `userConfig`, no shim. Hooks pre-filter in the shell: `[ -d "$CLAUDE_PROJECT_DIR/.code-atlas" ] \|\| exit 0` runs before any Python spawns. | The spike rules out a `userConfig` interpreter path: it reaches the server but never a hook. A shim would still need a path from somewhere. A tool install is the one step that needs no typed path. |
| W2 | Adapters (open question 2): does the plugin default `CA_<LANG>_CMD`? | **Server and hooks only.** Adapters stay per machine, per the README; a plugin-launched server inherits the user's environment. | The PHP and TS/SQL adapters need a Composer/npm install that a plugin cache clone does not run. Defaulting a command that cannot start turns a clear "unconfigured" into a launch failure (R5.3). |

**How-decisions — resolved and cited.**

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Where does the plugin live? | `contrib/claude-code/plugin/`, with the marketplace at the repo root's `.claude-plugin/marketplace.json` (`source: "./contrib/claude-code/plugin"`). A root plugin would auto-load the repo's own (untracked, absolute-path) `.mcp.json` and put `hooks/` and `skills/` at the top level. | CONVENTION §1 (`contrib/` holds the offered integrations); spike (`.mcp.json` auto-loads at a plugin root) |
| H2 | The fourth hook | `code-atlas-refresh` as its own `SessionStart` entry, `async: true`, plugin-only. The snippet keeps its three commands. AC3's drift test compares the plugin against the snippet plus that one entry. | ticket Scope 2; `contrib/claude-code/README.md` (the snippet's documented three) |
| H3 | How the skill ships | `gen_skill.py --write` writes it a second time, into the plugin's `skills/code-atlas/SKILL.md`, the same bytes as `contrib/skill/SKILL.md` — one generator, two outputs. | ticket Scope 1 (*"the generated `contrib/skill/SKILL.md`"*); R6.7 |

**Exposure-checker (1 dispatch, ticket-blind, 43,020 fresh).** It raised 11; one repeats H3. The
other ten, classified:

| # | Decision | Class | Resolution | Citation |
|---|---|---|---|---|
| H4 | Which file is generated? | how | Both, by `gen_skill.py` — it already renders the snippet (`render_claude_code_snippet`); the plugin's `hooks.json` joins it | `scripts/gen_skill.py:28,203`; `contrib/claude-code/README.md` §Regenerate |
| H5 | The `if:` suffix filters | how | Derived from the shipped adapters, as the snippet's are | `contrib/claude-code/README.md` (*"generated from each shipped adapter's own declared suffixes"*); R6.7 |
| H6 | Timeouts and async | how | The snippet's own values; refresh `async: true` with `timeout: 600`, so an incremental never stalls a session start | `settings.snippet.json`; `contrib/git/post-merge:8` (refresh runs in the background) |
| H7 | Who detects `behind` | how | `code-atlas-refresh` itself — incremental only, a no-op without an index | `code_atlas/hooks/refresh.py:36-58` |
| H8 | The adapter-unset "one line" vs AC2's silence | how | No conflict: the line is `refresh.py`'s stderr `skipped:` line, and it can only fire in an **indexed** repo; AC2 covers the unindexed one | `code_atlas/hooks/refresh.py:52-58` |
| H9 | Marketplace name and version | how | Both named `code-atlas`; `plugin.json` `version` = `pyproject.toml`'s, pinned by the drift test | `pyproject.toml:6-7`; R6.7 (one definition site) |
| H10 | Which install path the README leads with | how | Plugin first for Claude Code; the manual snippet stays for hand installs and other hosts | ticket *Why this exists* (*"makes the fourth a one-step install"*) |
| H11 | Native Windows | how | The hooks are bash one-liners; native Windows is untested here and becomes a design-time coverage-gap exclusion | AGENTS.md (runtime on native Windows, 237) |
| W3 | Plugin clone vs installed code-atlas version drift | want → **ASSUMED** | Accepted and documented: the plugin carries commands and a skill, not code | handed back by the maintainer |
| W4 | A user who already wired the snippet or `claude mcp add` | want → **ASSUMED** | The README tells them to remove the old wiring; no detection | handed back by the maintainer |

**`ASSUMED` count: W1–W4 = 4, each awaiting the maintainer's ratification on the PR.** The run does not
stop for them: the maintainer explicitly handed these decisions back, so they are not unresolved (`j = 0`).

## Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 7 found (Why this exists, Evidence, Scope, Acceptance criteria, Open questions, Outward actions, Out of scope — follow-up) | 7 decomposed | ROWS: C=5 R=6 G=1 AC=4`
`CLARIFICATION: 6 raised | 6 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/10 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

### BASELINE — `config.test_command` on the untouched checkout

The branch point is `e58d8c13`, the tree 343's baseline ran on, so the run is not repeated.
Ran at e58d8c13

```
$ .venv/bin/python -m pytest -q -p no:cacheprovider
3984 passed, 4 skipped in 379.03s (0:06:19)
```

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Why | "makes the fourth a one-step install" | the hooks reach a session without a settings merge | `contrib/claude-code/README.md` §Install step 2 (hand merge) | open |
| C1 | Evidence | "a venv's console scripts are not on PATH" | launching by name needs them on PATH | W1 | open |
| C2 | Evidence | "`code-atlas-refresh` (053) — locked, a no-op without an index" | reuse it | `hooks/refresh.py:36-58` | met — reused |
| C3 | Scope 1 | "code-atlas writes to no settings file" | no command writes a host settings file | `tests/test_contrib_snippets.py::test_no_code_atlas_command_writes_to_any_install_target` | open |
| C4 | Open questions | "Launching" / "Adapters" | decided before code (AC0) | W1, W2 | ASSUMED |
| C5 | Out of scope | "grep-time nudge — 345"; "`code-atlas init`" | nothing of either here | — | constraint |
| R1 | Scope 1 | "`.claude-plugin/plugin.json` plus a `marketplace.json`" | manifest + marketplace | H1 | open |
| R2 | Scope 1 | "`mcpServers`, launching the `code-atlas` server" | plugin `.mcp.json` | spike: server cwd = project | open |
| R3 | Scope 1 | "hooks … generated from the same source" | `gen_skill.py` renders both | H4 | open |
| R4 | Scope 1 | "skill: the generated `contrib/skill/SKILL.md`" | a second output of `render_skill` | H3 | open |
| R5 | Scope 2 | "spawning `code-atlas-refresh` in the background" | SessionStart, `async: true` | H2, H6 | open |
| R6 | Scope 3 | "a silent no-op when the cwd has no `.code-atlas/`" | shell pre-filter on all four | W1 | open |
| AC0 | AC | "decided at Gate 2 and recorded in this ticket before any code lands" | W1/W2 recorded here | Phase 0 | met at Gate 2 |
| AC1 | AC | "venv not on PATH … `/plugin install` plus at most one documented step … all four hook commands" | live install, isolated config | — | open |
| AC2 | AC | "no hook prints anything and each exits 0 … cost … measured and recorded (Windows and POSIX)" | test per command + timing | — | open |
| AC3 | AC | "fails when the plugin's hook list and `settings.snippet.json` disagree" | drift test | — | open |

### AC validation

| AC | Value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | "at most one documented step"; "all four hook commands" | the step is `uv tool install` (or `pipx install`); the four are `code-atlas-state`, `-poke`, `-signal`, `-refresh` (`pyproject.toml` scripts) | yes — a live `claude` run in an isolated config dir |
| AC2 | "no hook prints anything"; cost "Windows and POSIX" | empty stdout + stderr, exit 0; POSIX measurable here, **Windows is not** (no Windows host) | yes on POSIX; Windows → coverage-gap exclusion (design) |
| AC3 | drift | plugin hooks minus the refresh entry, with the pre-filter stripped, == the snippet | yes |

### Clarifications — all six self-resolved

1. Launching → W1 (ASSUMED; the spike shows `userConfig` never reaches a hook).
2. Adapters → W2 (ASSUMED).
3. AC1's "no hand-typed interpreter path" → met by W1: nothing names an interpreter.
4. AC2's Windows figure → no Windows host in this run; recorded as an exclusion, never an invented number.
5. "four hook commands" → the four console scripts, `refresh` included (ticket AC1 text).
6. Plugin placement → H1.

### Universal inventory — N = 4 hook commands (AC2, R6)

1 `code-atlas-state` · 2 `code-atlas-poke` · 3 `code-atlas-signal` · 4 `code-atlas-refresh`.
Per-item: each gated, each silent in an unindexed repo.

### Gap analysis

Current: hooks are offered as a snippet merged by hand; the server is registered by hand with an
absolute interpreter path. Target: one `/plugin install` after a tool install.

### Blast radius

`scripts/gen_skill.py` (`GENERATED`, `render_claude_code_snippet`, `render_skill` callers);
`tests/test_skill_drift.py` parametrises over `GENERATED`, so new outputs are guarded on arrival;
`tests/test_contrib_snippets.py` sweeps `contrib/*/` (the plugin sits one level deeper, outside
`OFFERS`) and every `contrib/` file for suffix claims and console-script names. Docs: README install,
`contrib/claude-code/README.md`, CONVENTION §1.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the generator names no language and suffixes come from shipped_adapters, §R2.1 (change-type) ✅ the plugin encodes no repo or framework name, §R5.3 (change-type) ✅ no adapter command is defaulted to one that cannot start (W2), §R6.5 (change-type) ✅ the AC3 drift test is seen red on a mutated hook list, §R6.7 (change-type) ✅ plugin files come from the generator and the version from pyproject.toml, §R7.2 (change-type) ✅ BACKLOG and TOKEN_LEDGER in the finishing commit, §R7.6 (change-type) ✅ the README install section is rewritten plugin-first and not appended to`

N/A: §3 because no contract field moves · §4 because nothing touches the index pipeline · §8 because
no dependency is added. R7.5 is checked at execute.

## Phase 2 — design

### Approach

1. **Plugin at `contrib/claude-code/plugin/`**: `.claude-plugin/plugin.json`, `.mcp.json`
   (`code-atlas`, by name), `hooks/hooks.json`, `skills/code-atlas/SKILL.md`. Marketplace at
   `.claude-plugin/marketplace.json`, `source: "./contrib/claude-code/plugin"`.
2. **One hook table, two renderings.** `gen_skill.py` builds the hook dict once from a `command(name)`
   mapper: the snippet maps a name to itself; the plugin maps it to
   `[ -d "${CLAUDE_PROJECT_DIR:-.}/.code-atlas" ] || exit 0; exec <name>` and adds the refresh entry
   (`SessionStart`, `async: true`, `timeout: 600`).
3. **Every plugin file is in `GENERATED`**, `plugin.json` taking its version from `pyproject.toml`,
   so `test_skill_drift.py` guards each.
4. **Tests** (`tests/test_claude_code_plugin.py`): AC3 drift (plugin == snippet + refresh, pre-filter
   stripped) with a mutation control; AC2 each of the four gated commands run by `bash -c` in an
   unindexed repo → exit 0, no output; the gated command still runs in an indexed repo; the manifest
   version equals the package's.
5. **Docs**: README install leads with the plugin; `contrib/claude-code/README.md` gains the plugin
   route and the remove-the-old-wiring note (W4); CONVENTION §1 names the plugin path.

### Rejected alternatives

- **A `userConfig` interpreter path.** It reaches the server but never a hook (spike), so the hooks would still need PATH.
- **A launcher shim that searches for a venv.** It has to guess at a path the user never told it. A tool install is the one step that needs no guess.
- **The plugin at the repo root.** It would auto-load the repo's own untracked `.mcp.json` and scatter `hooks/` and `skills/` at the top level.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | A plugin MCP server's cwd is the project dir | verified — spike |
| A2 | A plugin hook's env carries `CLAUDE_PROJECT_DIR` | verified — spike |
| A3 | `claude plugin marketplace add <local repo>` + `claude plugin install` resolves a relative `source` subdirectory | novel-untested → AC1's live install is shaped to fail if it is false |
| A4 | Native Windows runs these bash one-liners | novel-untested → coverage-gap exclusion (no Windows host) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | hook table + plugin renderers, into `GENERATED` | `scripts/gen_skill.py` | `test_skill_drift.py` (parametrised), `test_contrib_snippets.py`, `test_poke_snippet_covers_every_adapter.py` read the snippet | R1–R6 | 1/1 |
| 2 | generated plugin files (4) + marketplace | `contrib/claude-code/plugin/**`, `.claude-plugin/marketplace.json` | `test_contrib_snippets.py` suffix/console-script sweeps read every `contrib/` file | R1–R4 | 5/5 |
| 3 | plugin tests | `tests/test_claude_code_plugin.py` | new | AC2, AC3, R6 | 1/1 |
| 4 | install docs | `README.md`, `contrib/claude-code/README.md`, `docs/CONVENTION.md` | `test_contrib_snippets.py` README checks; doc size budget | G1, W4 | 3/3 |
| 5 | bookkeeping | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file | bookkeeping tests | R7.2 | — |

Trace — the consumers of the snippet path and the generator. Ran at e58d8c13

```
$ grep -rln "CLAUDE_CODE_SNIPPET_PATH\|POKE_SNIPPET_PATH\|render_claude_code_snippet\|GENERATED\|settings.snippet.json" scripts tests code_atlas --include=*.py
scripts/gen_skill.py
tests/test_sql_column_nullability_identity_pk.py
tests/test_agent_brief_in_indexed_repo.py
tests/test_poke_snippet_covers_every_adapter.py
tests/test_skill_drift.py
tests/test_session_state_hook.py
```

`test_sql_column_nullability_identity_pk.py` matches the SQL word `GENERATED`, not the generator.
`test_session_state_hook.py:184` and `test_agent_brief_in_indexed_repo.py:52` read the snippet —
proof collateral whose input does not move: item 1 keeps the snippet's bytes identical.

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

`formatter-rewrites-untouched-lines` — does not apply because it names no producer or consumer to
trace; it is honoured at execute by formatting nothing wholesale.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | e2e | manual-recorded — live `claude plugin marketplace add` + `install` in an isolated `CLAUDE_CONFIG_DIR`, `uv tool install` into a temp dir, `claude -p` + `claude mcp list` | n/a | ✅ |
| AC2 (POSIX) | runtime | integration — each gated command under `bash -c` in an unindexed tmp repo; timing loop recorded | n/a | ✅ |
| AC2 (Windows) | runtime | none — no Windows host | n/a | ❌ → exclusion |
| AC3 | logic | unit — structural comparison + mutation control | n/a | ✅ |

**Coverage-gap exclusion** — AC2's Windows cost figure (and A4): item AC2-Windows · risk tier low
(hooks exit 0 on any failure) · why deferred: no native Windows host in this run · follow-up: measure
on the first Windows install · `expiry: when a native Windows host runs /plugin install code-atlas` ·
`seen: 344`. Approved under the maintainer's handover (*"make the necessary decisions"*); surfaced in
the PR and DISCLOSURE.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_claude_code_plugin.py -k "hook_list_matches_the_snippet"` —
fails before (no plugin file), passes after.

### Rollback + porting

`git revert` the branch, or close the PR unmerged; a user uninstalls with
`/plugin uninstall code-atlas`. One repo; nothing to port.

`SCOPE: M` — unchanged.
