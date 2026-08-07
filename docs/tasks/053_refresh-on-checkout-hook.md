---
id: 053
slug: refresh-on-checkout-hook
title: Nothing refreshes the index when the repo changes outside the agent's editor
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [052, 036, 016]
---

## Goal
Four mechanisms keep an index current, and there is a hole between them that a working repo falls
through every day.

| Layer | Covers | Automatic? |
|---|---|---|
| Read-through freshness (035) | **one** drifted file per tool call (`READ_THROUGH_CAP = 1`) | yes, at query time |
| Poke hook (036) | files the agent itself edits via `Edit` / `Write` | yes, `PostToolUse` |
| `build_or_update_index(full=false)` | everything git can name since `last_commit` | **no — someone must call it** |
| Full rebuild | contract bump, older schema, no usable git diff | no |

The hole is the third row. `git pull`, `git checkout <branch>`, a rebase, a teammate's merge, an edit
made in an IDE or a second terminal — none of it goes through `Edit`/`Write`, so the poke hook never
sees it, and read-through freshness repairs **one file per call** before returning `index_stale`
(`tools/freshness.py:13,41-42`). A pull that touches 300 files leaves an index that answers confidently
and wrongly until somebody thinks to rebuild.

**Detection already works; only the trigger is missing.** `get_index_status` reports `behind` when
`last_commit != head_commit` *or* an indexed file is dirty
(`tools/get_index_status.py:_staleness`, 047), and `dirty_indexed_files` says how many. The
recommended discipline — call `get_index_status` first, rebuild if it is not `current` — is written
into the onboarding runbook and it is correct. It is also entirely dependent on an agent choosing to
follow it at the start of every session, and round 1 showed what happens to disciplines that depend on
that: the session wrote the policy and then made zero graph queries.

The symmetric fix exists already for the other half of the problem. 036 ships a `PostToolUse` hook
because "the agent edited a file" is an event. "The repo moved under you" is also an event, and git
will tell us about it.

## Scope / Deliverables
- **A refresh entry point**, mirroring `code-atlas-poke`: a console script in `pyproject.toml`
  (`[project.scripts]`) backed by a module under `code_atlas/hooks/`, which runs the equivalent of
  `build_or_update_index(full=false)` against the repo it is invoked in.
- **Git hook snippets in `contrib/git/`**, with a README, following the shape of
  [`contrib/claude-code/`](../../contrib/claude-code/):
  - `post-merge` — fires after `git pull` / `git merge`.
  - `post-checkout` — fires on branch switch **and** on `git checkout <file>`; git passes a third
    argument that is `1` only for a branch checkout, and the hook must use it or it will fire on every
    single-file checkout.
  - Say plainly in the README that these are *not installed automatically* — `.git/hooks` is not
    version-controlled, and silently writing into a user's `.git` is not something this project does.
- **Never build an index that does not exist.** Same rule as the poke hook
  (`hooks/poke.py:60-62`): no index → no-op, exit 0. A git hook is not an onboarding path, and a
  `post-merge` that starts a 17-minute full build is a trap.
- **Never block the git operation.** Always exit 0, and run out of band unless
  [052](052_incremental-noop-cost.md) shows an incremental is fast enough to run inline. A `post-merge`
  that costs 62 s is worse than a stale index, because the person waiting will delete the hook.
- **One writer at a time (R4.3).** A hook can fire while the MCP server is mid-build, and two `git
  pull`s can overlap. Decide the policy — a lock file, or detect-and-skip — and make "another build is
  running" a clean no-op, not a partial write. Write down which and why.
- **Runbook section** in [`runbooks/onboarding-a-repo.md`](../runbooks/onboarding-a-repo.md) next to
  the existing "Optional: eager freshness" paragraph, stating what each layer covers and what is left
  to the operator, so the table above is documented somewhere a reader will find it.

## Constraints
- **Gated on [052](052_incremental-noop-cost.md).** The cost of a `git pull`-shaped incremental decides
  whether this runs inline, in the background, or not at all. Do not build the hook and then discover
  the number.
- **Opt-in, like 036.** Nothing here may change behaviour for someone who has not installed it, and
  nothing may write to `.git/hooks` without the operator doing it themselves.
- **Fail visibly on install errors, silently on the rest** — the poke hook's convention
  (`hooks/poke.py:82-88`): a broken install prints one stderr line, a path outside the project or a
  suffix no adapter owns is a quiet no-op.
- **No language branch in the core (R1.1)**; the hook module reuses `indexer` / `store` and learns
  nothing about PHP.
- **Determinism (R4.2)** — a hook-driven incremental and a hand-called one must produce the same rows.
- **No new contract or schema (R3).**

## Acceptance criteria
- The console script runs an incremental against a repo with an existing index, and is a no-op with
  exit 0 when there is no index — both asserted.
- `post-checkout` fires on a branch switch and does **not** fire on `git checkout -- <file>`, asserted
  against git's third argument.
- Two overlapping invocations do not both write: the second is a clean no-op with exit 0, asserted.
- A hook failure never makes the git command fail (exit status asserted).
- The `contrib/git/` README states the install steps and that they are manual.
- The runbook documents all four freshness layers and what each does not cover.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/hooks/poke.py` (the shape to mirror: stdin/CLI path, no-op without an index, always exit 0,
visible install failures), `contrib/claude-code/settings.snippet.json` + its README (the opt-in
distribution pattern), `pyproject.toml` `[project.scripts]`.
`code_atlas/tools/freshness.py:13` (`READ_THROUGH_CAP = 1` — why one call cannot repair a pull),
`:41-42` (the `stale` fallout).
`code_atlas/tools/get_index_status.py` `_staleness` (detection, 047) and `dirty_indexed_files`.
`code_atlas/tools/build_or_update_index.py:70-79` (`_run`) and `code_atlas/indexer.py:128-204`
(`incremental_update`).
Prior art for the freshness layers: [035](035_read-through-freshness.md),
[036](036_edit-index-hook.md), [016](016_incremental-git.md), [047](047_staleness-scoped-to-indexed-files.md).
Origin: freshness review, 2026-08-07 — the four layers were enumerated and the pull/checkout path was
the one nothing covers.
