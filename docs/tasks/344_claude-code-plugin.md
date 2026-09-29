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
