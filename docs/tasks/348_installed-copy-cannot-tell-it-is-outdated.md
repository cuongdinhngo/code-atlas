---
id: 348
slug: installed-copy-cannot-tell-it-is-outdated
title: 'An installed code-atlas has no version to compare against, so an anchor project never learns it is outdated'
phase: 2
milestone: Adoption
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 348 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges PR [#12](https://github.com/cuongdinhngo/code-atlas/pull/12), then tags the merge commit `v0.2.0` (W1). **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`; *"with
  skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/348-release-version-discipline` off `main` (`ef796df9`). Contract `.mango/run-contract-348.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 2 by handle | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 3 want-decision asked | 6 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** All eight references resolve:
- `pyproject.toml` `version = "0.1.0"`;
- the plugin and marketplace `version` fields, both `0.1.0`;
- `code_atlas/adapter.py:254`, the handshake refusal;
- `scripts/gen_skill.py` `_claude_code_hooks`;
- `code_atlas/hooks/state.py`;
- `importlib.metadata`, in `build_info`;
- PLAN §19;
- R4/R4.1.

**Recall.**
- By area: `345-C1` (the output channel), `344-C1` (the `if` filter) and `344-C2` (plugin
  `userConfig`).
- By handle: `343-C2` and `344-C3`, because the change ships generated plugin files.

**Spikes, run in an isolated `CLAUDE_CONFIG_DIR` on Claude Code 2.1.284, against a local
directory marketplace cloned from `ef796df9`:**

| Step | Result |
|---|---|
| install | `code-atlas@code-atlas` `Version: 0.1.0` |
| a content change with the version unchanged, then `marketplace update` and `plugin update` | `✔ code-atlas is already at the latest version (0.1.0).` |
| bump to `0.2.0`, then `claude plugin marketplace update code-atlas` | the installed version stays `0.1.0` |
| `claude plugin update code-atlas@code-atlas` | `✔ Plugin "code-atlas" updated from 0.1.0 to 0.2.0 for scope user. Restart to apply changes.` |
| does a session start auto-update? | **not measured** — the auto-mode classifier refused copying credentials into the isolated config; not worked around |
| `uv tool install git+file://…`, then a commit bumping to 0.2.0, then `uv tool upgrade code-atlas` | `code-atlas v0.1.0` → `code-atlas v0.2.0` |

`known_marketplaces.json` carries no `autoUpdate` key for the added marketplace.

**Want-decisions — asked, and answered by the maintainer (2026-09-30, AskUserQuestion).** The
exposure-checker (one dispatch, 40,984 fresh) surfaced these.

| # | Question | Answer |
|---|---|---|
| W1 | AC3's tag: autorun may not push one, and it belongs on the merge commit | the PR bumps the version and adds the changelog; the maintainer tags `v0.2.0` after merge |
| W2 | Scope 4: a network "newer release" check | reject for now; record it in PLAN §19 with a re-open condition |
| W3 | Where the changelog starts | at 0.2.0, noting 0.1.0's unversioned v10–v13 span |

**How-decisions — resolved and cited:**

| # | Decision | Resolution | Citation |
|---|---|---|---|
| H1 | first version | `0.2.0` — before 1.0, a rebuild-forcing change moves the minor | semver §4 (0.y.z); ticket Scope 1 |
| H2 | where release metadata lives | `CHANGELOG.md`'s top heading names version · contract · schema; the AC1 test parses it, with no second table | R6.7; ticket Scope 1 "e.g." |
| H3 | skew direction | both directions; the fix named is for the older side | ticket Scope 2 "on a mismatch … the upgrade command" |
| H4 | the snippet also carries `--expect-version` | 344's snippet==plugin drift test compares the two tables | `tests/test_claude_code_plugin.py` `test_the_plugin_hook_list_matches_the_snippet` |
| H5 | the installed version | `build_info.package_version()`, renamed from `_package_version` so there is one definition | R6.7; `build_info.py:40` |
| H6 | the README states only what was measured | auto-update is stated as unmeasured | ticket "Assumptions" |

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 2 by handle | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Assumptions to prove at design, Acceptance criteria, title) | 5 decomposed | ROWS: C=3 R=4 G=1 AC=5`
`CLARIFICATION: 3 raised | 0 self-resolved (cited) | 3 for human decision`
`TRACK: backend — 0/16 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

The three are W1–W3. Each went to the maintainer, who answered all three on 2026-09-30 (Phase 0), so none is still open.

### BASELINE

`main` at `ef796df9` is the merge of #11. Its tree is the 347 branch head that gated green:
`GATE GREEN — all 21 checks passed`. Per SG-2 that run is not pasted as a pre-change evidence block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "This ticket makes an old install find out it is old" | a version to compare against, and a line that compares it | met |
| C1 | Scope 2 | "Deterministic, no network (R4)" | the skew check is offline | constraint |
| C2 | Scope 4 | "may never live in `code_atlas/`" | there is no network code at all (W2) | constraint |
| C3 | run | only the branch push and PR-open are authorised | the tag is deferred (W1) | constraint |
| R1 | Scope 1 | "Semver … tag … changelog … a test" | 0.2.0, `CHANGELOG.md`, `test_release_discipline.py` | met (tag deferred, W1) |
| R2 | Scope 2 | "bakes the plugin's version … compares … one line" | `--expect-version` and `skew_line` | met |
| R3 | Scope 3 | "upgrade section … per install route" | README *Upgrading* | met |
| R4 | Scope 4 | "Decide … Record" | PLAN §19 entry | met |
| AC1 | AC | contract/schema bump without a version bump fails | `test_the_top_release_is_the_code_that_ships` + 3 red controls | met |
| AC2 | AC | the plugin hook with a skewed package prints; silent when matched or with no index | real plugin command via bash with the installed script | met |
| AC3 | AC | version bumped, tag, changelog, marketplace version | 0.2.0 everywhere; tag after merge (W1) | met (tag deferred) |
| AC4 | AC | README covers every route and the spike | three routes and the measured behaviour | met |
| AC5 | AC | Scope 4 in PLAN §19 | yes | met |

### Blast radius

- **Hook commands.** `gen_skill._claude_code_hooks` feeds the snippet and the plugin, so the
  `SessionStart` and `PreCompact` commands change. Consumers:
  - `tests/test_claude_code_plugin.py`, which reads the script names;
  - `tests/test_session_state_hook.py`, which asserts the snippet command.
- **The version bump.** It reaches the plugin manifest and the marketplace entry, and moves
  `server_version` in the provenance payload.
- **`build_info._package_version`.** It is called only in `build_info.py`; the one outside
  reference is `tests/test_server_build.py:220`.
- **Docs:**
  - README;
  - PLAN §19;
  - TOOLS.md (the state line);
  - `contrib/claude-code/README.md`;
  - `CONVENTION.md` §1, where the map line was reverted because the budget ran over by 3 tokens and
    LICENSE is not listed either.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ skew_line names no language only release numbers and install commands, §R4.1 (change-type) ✅ no network call is added anywhere and the update check is rejected in PLAN §19, §R6.5 (change-type) ✅ three drift cases and the missing rebuild flag are each seen red, §R6.7 (change-type) ✅ the release is read from CHANGELOG and pyproject and the installed version from one build_info function, §R7.6 (change-type) ✅ the CONVENTION map line was dropped rather than raising its budget`

## Phase 2 — design

### Approach

1. **Version 0.2.0.** `pyproject.toml` moves. `gen_skill --write` regenerates the plugin manifest
   and the marketplace entry.
2. **`CHANGELOG.md`.** The heading reads `## <version> — <date> · contract <n> · schema <n>`. Each
   entry flags **Full rebuild required** and **Adapter checkout must be updated**.
3. **`tests/test_release_discipline.py`.** `release_drift()` checks three things against the top
   entry: that it is pyproject's version, that it names `CONTRACT_VERSION` and `SCHEMA_VERSION`, and
   that an era move carries the rebuild flag. It has red controls for each drift. The same file
   covers the skew line and runs the plugin hook live.
4. **Skew.** `gen_skill` writes `code-atlas-state --expect-version <version>` into both tables.
   `state.skew_line()` compares that version with `build_info.package_version()` and names the fix
   for the older side. It is silent when the versions match or the installed one is unknown. `main`
   prints it before the summary, only when an index exists, and a broken index read does not
   suppress it.
5. **Docs.** README *Upgrading*, PLAN §19, TOOLS.md, and the contrib README.

### Rejected alternatives

- **A pinned `{version: (contract, schema)}` table in a test.** It is a second copy of what the
  changelog must say anyway (R6.7).
- **The skew in the plugin only.** 344's drift test requires the snippet and the plugin to match,
  and a hand install drifts just the same.
- **A network check** (W2).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | Claude Code updates a plugin only when `version` moves, through `claude plugin update` | verified — spike |
| A2 | `uv tool upgrade` picks up a new commit from a git source | verified — spike |
| A3 | Auto-update at session start for a third-party marketplace | unmeasured — the README says so and gives the manual commands (the ticket's "states whatever the spike measured") |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | version bump + regenerated manifests | `pyproject.toml`, `contrib/claude-code/plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `server_version` in provenance | R1, AC3 | 3/3 |
| 2 | changelog | `CHANGELOG.md` | none identified | R1, AC1 | 1/1 |
| 3 | `--expect-version` in the hook table | `scripts/gen_skill.py`, `contrib/claude-code/settings.snippet.json`, `contrib/claude-code/plugin/hooks/hooks.json` | 344 plugin tests, 322 state tests | R2 | 3/3 |
| 4 | skew line; public `package_version` | `code_atlas/hooks/state.py`, `code_atlas/build_info.py` | `tests/test_server_build.py` | R2, AC2 | 2/2 |
| 5 | tests | `tests/test_release_discipline.py`, `tests/test_claude_code_plugin.py`, `tests/test_session_state_hook.py`, `tests/test_server_build.py` | proof collateral | AC1, AC2 | 4/4 |
| 6 | docs | `README.md`, `docs/PLAN.md`, `docs/TOOLS.md`, `contrib/claude-code/README.md` | doc budgets | R3, R4, AC4, AC5 | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`.** I ran `.venv/bin/ruff format --diff code_atlas/hooks/state.py
  code_atlas/build_info.py scripts/gen_skill.py tests/test_release_discipline.py` and got
  `2 files would be reformatted, 2 files already formatted`. The proposals fall on untouched lines
  only: `build_info.py`'s `STALE_IMPACT_*` conditional, and `gen_skill.py`'s `OCCASIONS` check and
  string quoting. None was applied.
- **`verify-the-shipped-artifact-not-the-working-tree`.** I ran `git show HEAD:contrib/claude-code/plugin/hooks/hooks.json | grep -c
  "expect-version 0.2.0"` → `2`. The committed `marketplace.json` and `plugin.json` both show
  `"version": "0.2.0"`. `test_every_generated_file_is_committable` covers the paths.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | logic | unit test over the real `CHANGELOG.md` + red controls | n/a | ✅ |
| AC2 | integration | the plugin's own command via `bash`, the installed console script, a real payload; plus unit tests | n/a | ✅ |
| AC3 | logic | committed version fields (`git show HEAD:`), manifest test | n/a | ✅ |
| AC4 | manual-recorded | README section against the spike table above | n/a | ✅ |
| AC5 | manual-recorded | PLAN §19 entry | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_release_discipline.py -k 'top_release or skew_against'`.
It fails before the change, because the test file and `CHANGELOG.md` did not exist and the hook
passed no version. It passes after.

### Rollback

`git revert`. The version returns to 0.1.0 and no index is touched.

## Phase 3 — execute

Commit `0656e684` on `feat/348-release-version-discipline`.

Ran at 0656e684

```
$ .venv/bin/python -m pytest -q tests/test_release_discipline.py
12 passed in 0.56s
$ echo '{"hook_event_name":"SessionStart","source":"startup"}' | CLAUDE_PROJECT_DIR=$PWD .venv/bin/code-atlas-state --expect-version 0.1.0
code-atlas: hooks expect code-atlas 0.1.0 but 0.2.0 is installed — run `claude plugin marketplace update code-atlas && claude plugin update code-atlas@code-atlas` (or re-copy the hook snippet)
code-atlas: rebuild required @ bfb1e74 · 622 files · 8,456 symbols — index contract v10, server v13 — run `code-atlas-build --full` (or build_or_update_index allow_full_rebuild=true)
```

**Sweep.**
- Axis 1: the diff is the 17 files of the change list.
- Axis 2: Approach bullets 1–5 were implemented as approved.
- One correction was made while testing, and it is not a deviation. The skew line was first
  computed after `state_line`, so a broken index read swallowed it. It now comes first, and a failed
  summary still prints the skew.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `0656e684`): 8 met · 0 not met · 0 can't tell.** It ran 68
tests read-only. It ran the hook live on `SessionStart` and on `PreCompact`, and with a garbage
`graph.db`; every run printed the skew line and exited 0.

It raised four concerns. None of them blocks:

1. **AC1 rests on the changelog heading.** A contract bump that edits the top heading's numbers in
   place, without bumping the version, passes when only one entry exists. The heading is the
   authority by design (H2, R6.7). A pinned table would be edited in place just as easily, and
   review sees either edit. This is recorded, not changed.
2. **Two lines at once.** With a skew and a stale index, the hook prints two lines, skew first. The
   90-token budget is per line: the skew line is about 40 tokens, and `_fit` still caps the summary
   line.
3. **A `load_config` failure** loses both lines. This is the hook's existing fail-silent rule.
4. **The spike claims** are the author's own and were not reproduced by the challenger. The README
   states that auto-update is unmeasured.

`Ph3/4 proven by`: G1, R1–R4, AC1–AC5 — 10/10. The tag is deferred by W1.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 0656e684 — the diff `main..0656e684`. Working doc:
`docs/tasks/348_installed-copy-cannot-tell-it-is-outdated.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `0656e684` only bookkeeping changes, and all of it is exempt. That is
this doc, `docs/LESSONS.md`, `docs/BACKLOG.md` (the row closed) and `docs/TOKEN_LEDGER.md`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`348-C1` (type 5, the plugin update behaviour) is recorded in `docs/LESSONS.md`.

### Outward actions

1. Push `feat/348-release-version-discipline` — pre-authorised.
2. Open PR #12 — pre-authorised.

Deferred to the maintainer: the merge, and then the tag on the merge commit (W1):
`git tag -a v0.2.0 -m "code-atlas 0.2.0" <merge-sha> && git push origin v0.2.0`.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 40,984 fresh |
| 2 | review | `challenger`, round 1 | 54,257 fresh |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 95,241 · top cost driver: review/challenger`
