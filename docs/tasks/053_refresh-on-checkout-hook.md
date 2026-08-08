---
id: 053
slug: refresh-on-checkout-hook
title: Nothing refreshes the index when the repo changes outside the agent's editor
phase: 1.5b
milestone: Freshness
status: done
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

## Outcome

- **Entry point:** `code-atlas-refresh` → `code_atlas.hooks.refresh` — reuses
  `build_or_update_index(full=false)`; no index → exit 0; install errors → one stderr line; always
  exit 0.
- **Overlap:** shared non-blocking flock on `.code-atlas/write.lock` inside
  `build_or_update_index` (and thus refresh); loser → hook skip / tool `mode: busy`.
- **Mode:** out of band — `contrib/git/post-merge` and `post-checkout` spawn refresh in the
  background (052 / field ~62s; not inline). stderr kept; stdout discarded. `post-checkout`
  requires git’s 3rd arg `1`.
- **Opt-in:** README states hooks are not installed automatically; never writes `.git/hooks`.
- **Runbook:** four-layer table under “Optional: eager freshness”.
- **Proving:** `tests/test_git_refresh_hook.py` — **946 passed** at tip (pre-review commit).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 053 — refresh-on-checkout-hook (working doc)

- **Ticket:** 053 · local `docs/tasks/053_refresh-on-checkout-hook.md`
- **Type:** feature / freshness
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full
- **BASELINE:** green — tip `a28daed` (052 done on main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 0 unresolved | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**Exposure-checker:** [Challenger](d82a8468-6376-4efb-a1f0-dc9d3cb14cea) — none (ready).

**HOW (cited, not asked):**
- Out-of-band refresh (not inline): ticket L55–57 + field ~62s + 052 Outcome (hooks out of band when not proven fast).
- Overlap policy product bar = second writer clean no-op exit 0; lockfile vs detect-and-skip is implementer HOW (design picks lockfile).
- Unblocked despite 052 “stays gated” note: ticket already authorises OOB when not fast enough; user invoked `/solve 053`.

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=6 G=1 AC=7`

| ID | Interpretation | Status |
|----|----------------|--------|
| G1 | Close the pull/checkout freshness hole with an opt-in git-hook refresh path | ⏳ |
| R1 | Console script + `code_atlas/hooks/` module ≡ incremental when index exists | ⏳ |
| R2 | `contrib/git/` post-merge + post-checkout + README (manual install) | ⏳ |
| R3 | No index → no-op exit 0 (not an onboarding full build) | ⏳ |
| R4 | Never block git (always exit 0); OOB unless proven fast — **OOB chosen** | ⏳ |
| R5 | One writer: second overlapping invoke is clean no-op exit 0; policy written | ⏳ |
| R6 | Runbook documents all four freshness layers + gaps | ⏳ |
| C1 | Gated on 052 cost → OOB path | ⏳ |
| C2 | Opt-in; never auto-write `.git/hooks` | ⏳ |
| C3 | Fail visibly on install errors; silent otherwise (poke convention) | ⏳ |
| C4 | No language branch in core (R1.1) | ⏳ |
| C5 | Determinism R4.2 vs hand-called incremental | ⏳ |
| C6 | No new contract/schema (R3) | ⏳ |
| AC1 | Script runs incremental with index; no-op exit 0 without — asserted | ⏳ |
| AC2 | post-checkout: branch switch only (git 3rd arg `1`); not file checkout — asserted | ⏳ |
| AC3 | Overlapping invocations: second clean no-op exit 0 — asserted | ⏳ |
| AC4 | Hook failure never fails git command (exit 0) — asserted | ⏳ |
| AC5 | contrib/git README: install steps + manual | ⏳ |
| AC6 | Runbook: four layers + what each does not cover | ⏳ |
| AC7 | pytest / ruff / mypy green | ⏳ |

### AC validation (falsifiability)

| AC | Measurable form | Notes |
|----|-----------------|-------|
| AC1 | subprocess exit 0; index mutated iff db existed | unit |
| AC2 | hook script / helper returns skip when argv[3]!="1" | unit (no real git needed) |
| AC3 | hold lock in one process; second exits 0 without write | unit |
| AC4 | forced exception path still exit 0 | unit |
| AC5 | README greppable “not installed automatically” / install steps | doc |
| AC6 | runbook section names 035/036/incremental/full | doc |
| AC7 | CI commands | suite |

`CLARIFICATION: 0 raised | 0 self-resolved beyond refine HOW | j=0`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 2 | unmeasured (blocking retrieval) |
| review | challenger | 2 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass all gates (incl. push/PR) |
| 2026-08-08 | Proceed 053 via OOB path; 052 scale profile still unset |
| 2026-08-08 | Gate 1+2 cleared (standing) |
| 2026-08-08 | Review round 1: share write.lock + keep stderr; round 2 LGTM/PASS |

## Session status

- **Phase:** finalise
- **Reviewed at:** `507274daee247b382569369d1666286168d8e892`
- **Reviewed files:** refresh.py, index_lock.py, build_or_update_index.py, contrib/git/*, tests/test_git_refresh_hook.py, pyproject.toml, runbook, PLAN, README, LESSONS, BACKLOG, task 053, core module-count tests

## Phase 2 — Design

**Approach**
1. `code_atlas/hooks/refresh.py` + `[project.scripts] code-atlas-refresh` — mirror poke: always exit 0; no index → no-op; install/config errors → one stderr line.
2. Body calls existing `build_or_update_index.create(config)(full=False)` so rows match a hand-called incremental (R4.2); never invents a second write path.
3. **Out of band:** contrib git hooks spawn `code-atlas-refresh` in the background and exit 0 immediately (field ~62s / 052 → not inline).
4. **Overlap:** non-blocking `fcntl` exclusive lock on `.code-atlas/refresh.lock` beside the DB; lock held → clean skip exit 0 (written in README). Prefer lockfile over SQLite busy so the second process never opens a second writer.
5. `contrib/git/{post-merge,post-checkout,README.md}` — post-checkout exits early unless `$3=1`.
6. Runbook: four-layer table next to “Optional: eager freshness”.
7. Tests: no-index noop; with-index runs; lock contention; post-checkout arg helper; forced error still exit 0.

**Rejected**
- Inline sync in the hook (ticket + 052: 62s deletes the hook).
- Auto-writing `.git/hooks` (opt-in / never silent install).
- Relying only on SQLite `busy_timeout` (not a clean intentional no-op; harder to assert).

**Assumptions**
- `fcntl.flock(LOCK_NB)` works on Linux CI / dev hosts — **verified** by proving test AC3.
- Reusing `build_or_update_index.create` from a hook process is R4.3-safe when only one lock holder runs it — **verified** by AC3.

**Change list**

| Change | Area | Rows |
|--------|------|------|
| refresh module + lock helper | `code_atlas/hooks/refresh.py` | R1 R3 R4 R5 C3 C4 C5 AC1 AC3 AC4 |
| console script | `pyproject.toml` | R1 |
| git hook snippets + README | `contrib/git/` | R2 C2 AC2 AC5 |
| proving tests | `tests/test_git_refresh_hook.py` | AC1–AC4 AC7 |
| runbook four layers | `docs/runbooks/onboarding-a-repo.md` | R6 AC6 |
| PLAN/README touch if needed | docs | R7.2 |

**Proving test:** `tests/test_git_refresh_hook.py`

**Gate 2:** standing clears.
