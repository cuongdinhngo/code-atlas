---
id: 405
slug: plugin-release-check
title: "An install a tagged release behind, halves agreeing, is told by nothing — re-open PLAN §19's update check"
phase: 2
milestone: Freshness
status: done
depends_on: [348, 374, 381]
---

## Why this exists

Issue [#87](https://github.com/cuongdinhngo/code-atlas/issues/87), the anchor's maintainer, 2026-10-18.
The tool install and the plugin were both at 0.3.0 (plugin `0edda03`, installed 2026-10-12), while
`main` was at 0.5.0, 108 commits ahead. Marketplace auto-update was off (`known_marketplaces.json`
`lastUpdated` 2026-10-12). The two installed halves agreed, so the 374 skew line had nothing to
report. It spoke only because a local adapter checkout was already at contract 16.

That is PLAN §19's re-open condition, *"an install a tagged release behind, halves agreeing, told by
nothing"*, except for one thing: 0.3.0, 0.4.0 and 0.5.0 had never been tagged (381 E3). With no tags,
"a tagged release behind" could not be shown.

## Scope

1. Cut the missing tags. Each goes on the first `main` merge that carries its version, annotated
   like `v0.2.0`: `v0.3.0` → `da400407` (#50), `v0.4.0` → `e1af1374` (#75), `v0.5.0` → `289818ee`
   (#84). Pushed by the maintainer's approval in session.
2. Add the release check to the plugin, outside the core (R4.1): `release_check/` and the
   `code-atlas-release-check` script.
   - `--fetch <repo>` is an async `SessionStart` hook. It caches the highest `vX.Y.Z` tag from
     `git ls-remote --tags --refs`, at most daily.
   - `--expect-version X.Y.Z` is a sync hook. It reads only the cache, and when the cached release is
     newer it emits `systemMessage` plus `additionalContext` (381), in ASCII JSON.
3. Remove `test_the_top_release_is_tagged`'s strict xfail, which XPASSes once `v0.5.0` exists.
4. Edit PLAN §19 in place. Update the README *Upgrading* section, `contrib/claude-code/README.md`,
   the CONVENTION map and CHANGELOG *Unreleased*.

Out of scope: the hand snippet, Codex and OpenCode. A committed project file must never go online
(381's constraint), so the check ships with the plugin only.

## Acceptance criteria

- AC1: The newest release is the highest numeric `vX.Y.Z` tag. Non-release tags are ignored
  (`test_the_newest_tag_is_numeric_and_ignores_non_releases`).
- AC2: The remote is listed at most once a day
  (`test_fetch_stays_off_the_network_inside_a_day`, which uses a missing remote as proof).
- AC3: A line is emitted only when the cached release is newer, and it goes on screen and to the
  agent (`test_the_line_speaks_only_for_a_newer_release`,
  `test_the_session_start_hook_puts_the_line_on_screen`).
- AC4: Another event, broken stdin, opt-out, an offline fetch or an unreadable cache each give exit 0
  with an empty stdout (`test_every_other_path_is_silent`, `test_an_unreadable_cache_is_silent`).
- AC5: The plugin carries exactly the refresh plus the two release-check hooks. Only the cache read
  is sync, and all of them are behind the index gate
  (`test_the_plugin_adds_only_the_refresh_and_the_release_check`; the gate is covered by the existing
  parametrised plugin and teammate tests).

## Resolution

**Red runs (R6.5)**, on a copy inside `code-atlas-test`:
- Changing `newer <= mine` to `<` fails AC3's equal-release case.
- The pre-405 `hooks.json` fails AC5.

**Count-pin (P5):** `_plugin_state_command` in `test_release_discipline.py` matched on
`--expect-version` and so found two hooks. It now selects the `code-atlas-state` command.

**Deviation (P3):** none. §19 is re-decided rather than contradicted, and its entry is edited in place.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| — | none (no mango lifecycle; main-loop unmeasured) | — | 0 |

`LEDGER TOTAL: 0 · top cost driver: main loop (unmeasured)`
