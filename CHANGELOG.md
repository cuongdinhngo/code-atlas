# Changelog

One entry per release, newest first. Each heading names the release, its date, and the contract and
schema versions it ships. `tests/test_release_discipline.py` reads the top heading. A change to
`CONTRACT_VERSION` or `SCHEMA_VERSION` therefore needs a new release, and the first test run says so.

Each entry flags the two costs an upgrade can carry:

- **Full rebuild required.** The index's contract or schema moved. Run `code-atlas-build --full`.
  Until then `get_index_status` leads with `rebuild required`.
- **Adapter checkout must be updated.** The adapters speak the new contract. Pull the checkout that
  `CA_<LANG>_CMD` points into, and reinstall its dependencies. An older adapter fails the handshake.

How to upgrade each install route is in the README, under *Upgrading*.

## Unreleased

- A build stamps the HEAD it read before parsing, so a commit landing mid-build leaves the index
  `behind` instead of falsely `current` (360). An index built across such a move cannot be told
  apart: if `get_index_status` says `current` but a file committed then is missing, run
  `code-atlas-build --full` once.

## 0.2.0 — 2026-09-30 · contract 13 · schema 6

The first versioned release. `0.1.0` was never bumped while the contract moved from v10 to v13, so
no install could tell which code it ran.

- **Full rebuild required.** Every index built before contract v13 needs `code-atlas-build --full`.
- **Adapter checkout must be updated.** Every adapter speaks v13 (`symbol_shapes`).
- The Claude Code plugin (marketplace `cuongdinhngo/code-atlas`) ships the server, the hooks and the
  skill.
- The state hook names a plugin/package version skew and the command that closes it.
- An index from an older contract reports `rebuild required` on every channel.
- The read/write-time signal and the grep-time nudge reach the model as `additionalContext`.
