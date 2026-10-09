---
id: 376
slug: plugin-hook-without-console-scripts
title: 'A plugin installed before the console scripts fails every hook with 127 instead of saying how to fix it'
phase: 2
milestone: Adoption
status: todo
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
2. When it is missing: the **SessionStart** hook prints one line naming the install command
   (README step 1) and exits 0; every other hook exits 0 silently, so the line is said once.
3. Generated from the same table as today: `plugin/hooks/hooks.json` and
   `contrib/claude-code/settings.snippet.json` stay in step (240's guard).
4. Never installs or edits anything (`tests/test_contrib_snippets.py` keeps holding).

## Assumptions to prove at design

- `command -v` is available in the shell Claude Code runs hooks under on every supported host
  (Linux, macOS, WSL2; native Windows runs hooks how? — check, do not assume).
- The added test stays inside the ~1.5 ms no-index cost (344): it runs only after the index test.

## Acceptance criteria

- **AC1:** with `PATH` stripped of the scripts, the generated SessionStart command exits 0 and
  prints exactly one line naming the install command.
- **AC2:** in the same state, a PostToolUse hook command exits 0 with no output.
- **AC3:** with the scripts present, every generated command is unchanged in behaviour.
- **AC4:** a repo with no `.code-atlas/` still exits at the first test.
