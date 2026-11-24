---
id: 451
slug: freshness-by-setup
title: "Epic: installing code-atlas sets up the hooks that keep the index fresh, or says it did not"
phase: 2
milestone: Freshness
status: in-progress
depends_on: [452, 453, 454, 455]
---

## Why this exists

Field report, 2026-11-24, from both anchor projects (the PHP anchor and a Python/TS one): agents stop asking
code-atlas, and the index is often behind HEAD. The two are one problem — a `behind` or
`rebuild required` index refuses or answers stale, the agent falls back to grep, and the habit holds.

What the anchors show:

- **The git hooks have not refreshed once on the PHP anchor:** `.code-atlas/refresh.log` holds 40 runs,
  20 `skipped: coverage_loss`, 20 `skipped: no_usable_adapter`, 0 `refreshed`. The adapter commands
  live in `~/.profile` only; the log carries no time or detail, so which hook context lost them is
  not yet known (452 proves it first).
- **Each anchor wrote its own freshness layer:** `.claude/hooks/code-atlas-session-refresh.sh`,
  `code-atlas-symbol-guard.sh` (the PHP anchor 19 KB, the Python/TS anchor an 11 KB port) and an
  `install-git-hooks` script. The copies already differ.
- **The session hook refreshes only `behind`;** `incomplete` and a contract change wait for a human
  (202, 053), so an upgrade leaves the index on `rebuild required` — this repo, today, at v20/v21.
- **Hooks find the scripts through `PATH`** (`command -v`); a git run from an IDE or GUI may lack it
  and the hook exits 0 silently.

## Goal

Setting up the hooks is the step after install, done by one product command, and an install without
them reports itself as unguarded instead of looking like a working one.

## Tickets (in order)

| # | Ticket | Closes |
|---|---|---|
| 452 | One adapter config every hook context reads; git hooks call absolute paths | the 40 skips |
| 453 | `code-atlas-setup`: install the hooks, report `unguarded` when they are missing | "a broken setup looks like a working one" |
| 454 | The anchors' session refresh and symbol guard become product scripts | the per-anchor copies |
| 455 | Opt-in background full rebuild on contract change or `incomplete` | `rebuild required` that never clears |

## Decisions this epic reopens (record in PLAN §19 when each lands)

- `contrib/git/README.md` / 053: "this project never writes into a user's `.git`" — 453 writes there,
  only on the explicit `code-atlas-setup` command.
- 202 / 053: "nothing auto-rebuilds; the hook does not build" — 455 builds only where setup recorded
  consent, behind 356's shadow index.

## Done when

All four tickets are done, and on both anchors one session start plus one `git pull` leaves
`get_index_status` `current` with no human command, measured on each anchor.

## Progress — 2026-11-24

All four tickets are built and in review: #183 (452) → #184 (453) → #185 (454) → #186 (455), stacked. The epic's
"done when" needs a release carrying them installed on both anchors, then one session start and one `git pull`
measured on each; until then it stays `in-progress`. Anchor field notes so far: the PHP anchor's own `post-commit`
went `coverage_loss` → `refreshed` with 452 (452 Phase 3), and a refused symbol grep costs 23 ms there with 454.
