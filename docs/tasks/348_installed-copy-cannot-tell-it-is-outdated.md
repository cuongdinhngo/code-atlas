---
id: 348
slug: installed-copy-cannot-tell-it-is-outdated
title: 'An installed code-atlas has no version to compare against, so an anchor project never learns it is outdated'
phase: 2
milestone: Adoption
status: todo
depends_on: [344, 347]
---

## Why this exists

An anchor project runs code-atlas from one of these installs:

- `uv tool install git+…` (or `pipx`);
- a checkout wired by `scripts/setup.py`;
- the Claude Code plugin (344), which is two halves installed separately: the plugin, from the
  marketplace, and the console scripts, from a tool install.

None of them can tell that a newer code-atlas exists, or that its halves disagree.

- `pyproject.toml` has been `version = "0.1.0"` through contract v10→v13. The repo has no release
  tag and no changelog.
- The plugin and marketplace versions are the package version (344, R6.7). Claude Code updates an
  installed plugin when its `version` moves, so with the version frozen, a plugin install never
  receives a change.
- The plugin half and the tool half can drift. Hooks from a newer plugin can call a script that an
  older package does not ship, or ship with other behaviour. Nothing reports the skew.
- A tool install at contract v13, with `CA_<LANG>_CMD` pointing into an older checkout, fails the
  adapter handshake at build time (`code_atlas/adapter.py:254`). It is never warned about earlier.

347 makes an upgraded install report an older index. This ticket makes an old install find out it
is old.

## Scope

1. **Version discipline.**
   - Semver for the package; a git tag `vX.Y.Z` per release.
   - A changelog whose entries flag *full rebuild required* and *adapter checkout must be updated*.
   - A test that fails when `CONTRACT_VERSION` or `SCHEMA_VERSION` moves without a package version
     bump, e.g. a pinned `{version: (contract, schema)}` table.
2. **Plugin ↔ package skew, offline.** `gen_skill.py` bakes the plugin's version into the
   `SessionStart` hook command. `code-atlas-state` compares it to the installed package version
   (`importlib.metadata`). On a mismatch it prints one line that names both versions and the upgrade
   command. Deterministic, no network (R4).
3. **An upgrade section in the README.** Per install route:
   - the upgrade command;
   - when a full rebuild is needed (it points at 347's line);
   - that the adapter checkout moves with the core.
4. **Decide, with evidence: does an explicit "is there a newer release" check earn its place?**
   Such a check calls the network. It may never live in `code_atlas/` (R4, R4.1) or run on the MCP
   path. Record the decision either way.

## Assumptions to prove at design

- A spike on Claude Code 2.1.284 answers two questions:
  - Does a directory or GitHub marketplace plugin update on its own when `version` moves, or only
    through `claude plugin marketplace update` or `claude plugin update`?
  - Is auto-update on by default for a third-party marketplace?
  The README section states whatever the spike measured.

## Acceptance criteria

- **AC1:** Bumping `CONTRACT_VERSION` or `SCHEMA_VERSION` without bumping `project.version` fails a
  test. The same test passes with the bump. It goes red on the drifted case (R6.5).
- **AC2:** The plugin's `SessionStart` hook, run against an installed package whose version differs
  from the plugin's, prints one line naming both versions and the upgrade command. It is silent when
  they match, and silent with no index (344 gate).
- **AC3:** The package version is bumped, the first tag and changelog entry exist, and the
  marketplace entry carries the new version.
- **AC4:** The README upgrade section covers every install route above and records the spike's
  measured update behaviour.
- **AC5:** Scope 4 is decided and recorded in PLAN §19, with its reason.
