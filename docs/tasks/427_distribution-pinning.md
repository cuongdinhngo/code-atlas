---
id: 427
slug: distribution-pinning
title: "A user installs and upgrades to a named release, the plugin and server agree on it, and hooks wake only on an index code-atlas built"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

The install and upgrade instructions (README, the state hook's upgrade line, the plugin README)
point at the tip of `main`, so a user runs whatever was pushed last. A plugin one release apart
from the installed server only warns. The plugin's hooks wake on `[ -d .code-atlas ]`, a
directory any repo can ship. The release check runs `git ls-remote` from the indexed repo's
working directory. And another package on PyPI carries a near-identical name and description:
code-atlas is not published there, which no doc says.

## Acceptance

1. **Pinned installs:** every install and upgrade line in the docs, the plugin and the state hook
   names a release tag (`git+https://…@vX.Y.Z`); a docs test fails on an unpinned `git+` URL or a
   bare `pip install code-atlas` / `uv tool install code-atlas`.
2. **No auto-update advice** while the marketplace tracks a branch (docs test).
3. **Look-alike packages:** README says code-atlas is installed from this repository only and is
   not the PyPI packages with similar names (named).
4. **Version agreement:** a server started by a plugin of another release refuses with the one
   command that fixes it, instead of warning (fixture: mismatch → refusal; match → runs).
5. **Hook activation:** hooks run only when the index database exists and git does not track it
   (the 420 check), not on the directory; fixture: a repo shipping `.code-atlas/` keeps every hook
   silent.
6. **Other hosts:** the Codex and OpenCode snippets carry the same gate
   (`test_hook_offers_agree_across_hosts` extended).
7. **Skill text lint:** a test refuses skill or hook text that tells the agent to auto-approve,
   widen permissions or follow tool output as instructions (SEC-PL-07).
8. **Network git in a neutral directory:** the release check's `ls-remote` runs with a cwd outside
   the indexed repo and the 419 hardening; SECURITY.md lists it as code-atlas's one network call
   in the core path.

## Call sites

`README.md`, `contrib/claude-code/plugin/` (README, `hooks.json` via `scripts/gen_skill.py`),
`contrib/codex/`, `contrib/opencode/`, `code_atlas/hooks/state.py`, `release_check/`,
the server start path that reads the plugin's expected version; standard rows SEC-PL-01..05, 07, 08,
SEC-IN-14 (network part), SEC-GV-07.
