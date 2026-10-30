---
id: 419
slug: git-revision-arguments
title: "A revision read from the index cannot become a git option — every git call goes through one hardened chokepoint"
phase: 2
milestone: Trust
status: done
depends_on: []
---

## Why this exists

Internal security audit, 2026-10-27; advisory GHSA-66g7-7jr3-j5rc (private until 0.9.1).
`gitutil.changed_paths(root, since)` runs `git diff --name-only -z <since> --`. `since` is the
`last_commit` meta value of the index database, and the database can be committed by the indexed
repository, which `SECURITY.md` treats as untrusted. A value such as `--output=<file>` sits before
`--`, so git reads it as an option and truncates or overwrites that file. Reproduced with git 2.43.
It is reached with no user action: on server start (`instructions` → `get_index_status` → the
freshness guard) and from both SessionStart hooks (`code-atlas-refresh`, `code-atlas-state`).

## Acceptance

1. Every revision code-atlas passes to git is validated at the one function that runs git, against
   a full object id (`^[0-9a-f]{40}$` or `^[0-9a-f]{64}$`). An invalid one is answered as "git cannot
   answer" — the existing `None` path, so a build falls back to full — and the refusal is reported,
   never silent.
2. `--end-of-options` precedes every revision argument. git older than 2.24 (where it is missing)
   fails loud.
3. Every git invocation runs hardened against the indexed repo's configuration:
   `GIT_CONFIG_NOSYSTEM=1`, `GIT_TERMINAL_PROMPT=0`, `-c core.fsmonitor=false`,
   `-c core.hooksPath=/dev/null`, `-c core.sshCommand=`, `-c diff.external=`; `diff` also gets
   `--no-ext-diff --no-textconv`.
4. **Proving test:** a fixture repository whose database meta holds `last_commit =
   --output=<victim outside the repo>`. Build, the freshness guard, the overlay,
   `get_index_status`, the refresh hook and the state hook each run; the victim is byte-identical
   afterwards. The test is seen failing on the pre-fix tree first (R6.5).
5. A guard test: no subprocess call under `code_atlas/` names `git` outside `gitutil`, so the
   hardening has one home.

Out of scope: `release_check`'s `git ls-remote` (a separate, public ticket). The index-directory
trust and the text-injection paths are 420 and 421.

## Call sites

`code_atlas/gitutil.py` (`_run` and its seven callers); revisions reach it from
`tools/build_or_update_index.py`, `tools/freshness.py`, `overlay.py` (`built`) and `ref_check.py`.
Other callers: `build_info.py`, `indexer.py`, `tools/coverage.py`, `worktree_guard.py`.

## Resolution

- `gitutil._run` is the only git spawn: `HARDENED_ENV` and `HARDENED_CONFIG` on every call, and
  `diff` gains `--no-ext-diff --no-textconv`. A `revision=` argument is a full object id or the
  code-written `HEAD`, placed after `--end-of-options` and before `--`; anything else is reported on
  stderr (`code-atlas git: refused revision …`) and answered `None`. A failed revision call on git
  older than 2.24 says so on stderr.
- Deviation from AC3: `config_value` (preflight's `core.autocrlf`) keeps the system file, where Git
  for Windows sets that key; `config --get` runs nothing. Every other override applies to it.
- `rev-parse HEAD` keeps its literal `HEAD` without `--end-of-options` (rev-parse takes it only from
  git 2.30, and would read `--abbrev-ref` as a revision). `preflight._git_config` moved into gitutil.
- Proving: `tests/test_git_revision_arguments.py` — 10 red on 6f5cfc07, green after; it carries the
  six poisoned-meta arms, the refusal, the hardening, the old-git message and the AST guard.
- The guard refuses any `subprocess` import or `os` spawner outside `gitutil.py` and `adapter.py`
  (which launches `CA_<LANG>_CMD`): the challenger showed a git-literal match evaded by an alias.
- Not done: the old-git message needs a parsable `git --version`; an unparsable one stays `None`.
