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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 427 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute.
- `TRACK: backend` · Run mode: `autorun 427 - 430 - 424 - 425 - 428 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/427-distribution-pinning` from `main` `8fca451d`; the four tickets after it stack on it.
  Contract `.mango/run-contract-427.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 2 want-decision asked | 8 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** README, `contrib/claude-code/plugin/`, `scripts/gen_skill.py`, `contrib/codex/`, `contrib/opencode/`,
`code_atlas/hooks/state.py`, `release_check/`, `code_atlas/main.py`, `code_atlas/index_trust.py` resolve.
Recall (type 2, by handle): 410-C1 `a-word-list-is-not-a-grammar` (AC7 is a phrase lint), 344-C3
`verify-the-shipped-artifact-not-the-working-tree` (the plugin), 414-C1 `run-the-ac-on-main-before-the-design`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 55,052 tokens) raised the items below; two more
were added from the code read (H7, H8).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | which tag a doc names | how | `v` + `pyproject.toml`'s version, the one source gen_skill already reads (`gen_skill.py:_package`); a release bump moves every line, and the docs test fails until it does |
| H2 | lines that are not `git+` installs | how | a checkout install (`pip install -e .`, `--from <checkout>`) installs what you checked out; the lint refuses only an untagged `git+` URL and an install by package name |
| H3 | the upgrade line once installs are pinned | how | `uv tool upgrade` never moves a pin (`state.py:234`), so the fix becomes `uv tool install --force git+…@v<release>`, the release being the plugin's `--expect-version`; 381's "reinstall unpinned" line goes (it tells a user to unpin, SEC-PL-04) |
| H4 | how the server learns the plugin's release | how | the plugin manifest launches `code-atlas --expect-version <version>`, generated by `gen_skill.py`; no flag (hand-wired `.mcp.json`, uvx) means no expectation |
| H5 | how the server refuses | how | stderr + exit 2, the `IndexTrustError` precedent (`main.py:233`) |
| H6 | hook activation | how | the shell gate wakes on the index **database** (`.code-atlas/graph.db`), not the directory; every Python entry behind it already goes through `load_config` → `index_trust.check_index` (`index_trust.py:77`) and is silent on the refusal; the release check, which loads no config, gains the same check |
| H7 | other hosts | how | Codex's commands carry `PLUGIN_GATE` itself (`${CLAUDE_PROJECT_DIR:-.}` reads `.` there); OpenCode's plugin checks the database file before it spawns |
| H8 | the release check's git | how | `ls-remote` runs from the cache directory with `gitutil.HARDENED_CONFIG` / `HARDENED_ENV`; the core gains no network call (R4.1) |
| W1 | auto-update advice | want | **ASSUMED (awaiting ratification):** the marketplace is added at a release tag (`cuongdinhngo/code-atlas#vX.Y.Z`, Claude Code `plugins/cli-reference.md`); the README's "turn on auto-update" section is removed, and one line says not to enable it for a marketplace added without a tag |
| W2 | what is a mismatch | want | **ASSUMED (awaiting ratification):** any inequality between the plugin's release and a server whose version is known refuses; the one command installs the plugin's release (`uv tool install --force git+…@v<plugin>`), which fixes either direction; contract skew stays the hook's warning; no escape hatch beyond launching without the flag |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=8`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W2 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a user runs whatever was pushed last" | installs, upgrades, plugin and server name one release | ⚠ |
| AC1 | Acc 1 | "every install and upgrade line … names a release tag" | H1–H3; docs test over README, contrib READMEs, generated plugin files, state hook constants | ⚠ |
| AC2 | Acc 2 | "No auto-update advice while the marketplace tracks a branch" | W1; docs test | ⚠ |
| AC3 | Acc 3 | "not the PyPI packages with similar names (named)" | README names `code-atlas-mcp` and `codeatlas` (PyPI JSON API, 2026-10-31) | ⚠ |
| AC4 | Acc 4 | "refuses with the one command that fixes it" | H4, H5, W2; fixture mismatch → exit 2, match → serves | ⚠ |
| AC5 | Acc 5 | "only when the index database exists and git does not track it" | H6; fixture repo committing `.code-atlas/graph.db` → every hook silent | ⚠ |
| AC6 | Acc 6 | "Codex and OpenCode snippets carry the same gate" | H7; cross-host test extended | ⚠ |
| AC7 | Acc 7 | "refuses skill or hook text that tells the agent to auto-approve …" | phrase lint over the skill, brief and hook files, seen failing on planted text | ⚠ |
| AC8 | Acc 8 | "cwd outside the indexed repo and the 419 hardening" | H8; SECURITY.md row updated | ⚠ |
| C1 | Call sites | "standard rows SEC-PL-01..05, 07, 08, SEC-IN-14 (network part), SEC-GV-07" | each row closes on the test that holds it | ⚠ |

`BASELINE: red — test_install_skew::test_a_checkout_behind_the_core_is_named_with_its_fix (host), test_release_discipline::test_the_plugin_hook_names_a_skew_against_the_installed_package (host)`

The two are 423's host exclusions (installed uv tool 0.7.0); Docker on `main` is the reference run below.

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.8: one gate string shared by the plugin, the snippet and Codex · §2 (change-type) ✅ R2.4: only public package names · §4 (change-type) ✅ R4.1: the release check stays outside the core · §5 (change-type) ✅ R5.3: a version mismatch fails loud with the fix · §6 (change-type) ✅ R6.5: every new guard seen failing; R6.7: the tag is derived from pyproject · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §9 (change-type) ✅ R9.2: network git hardened; R9.6: each closed MUST names a test`

## Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 410-C1: the AC7 lint matches phrases as whole patterns over normalised text, and each pattern is seen
  matching a planted sentence and not matching the shipped skill (one positive and one negative control per pattern).
- 344-C3: the plugin manifest and hooks are checked as `gen_skill.py` renders them **and** as committed (the
  existing drift guard), not only the working tree.
- 414-C1: on `main`, `grep -rn "auto-update\|git+https" README.md contrib` shows the unpinned lines and the
  auto-update advice the ACs name (README.md:140-148, 245-259); `plugin.json` launches bare `code-atlas`.

**Approach.**
1. `scripts/gen_skill.py`: `RELEASE_TAG = "v" + version`; `INSTALL_SCRIPTS` names `git+…@<tag>`; the manifest's
   server gets `args: ["--expect-version", version]`; `PLUGIN_GATE` tests `-f …/.code-atlas/graph.db`.
2. `code_atlas/main.py`: `--expect-version X` against `build_info.package_version()`; unequal and known → stderr
   `code-atlas: refusing to serve: the plugin is X, this server is Y — run: uv tool install --force git+…@vX`, exit 2.
3. `code_atlas/hooks/state.py`: upgrade constants name the tagged reinstall; `pinned_line` and its screen slot
   removed (it told a user to unpin).
4. `release_check/`: silent unless the project's index loads (`load_config`); `ls-remote` from the cache
   directory with the hardened config and env.
5. Docs: README install/upgrade/auto-update/look-alike text, `contrib/claude-code/README.md`, `contrib/codex/`,
   `contrib/opencode/`; SECURITY.md network and git sections; SECURITY_STANDARD rows; CHANGELOG *Unreleased*.
6. Tests: a docs test (AC1–AC3), server refusal (AC4), hook silence on a committed index (AC5), cross-host gate
   (AC6), skill-text lint (AC7), release-check cwd and hardening (AC8).

**Rejected:** a shell `git ls-files` in the gate (an unhardened git in the untrusted repo, on every hook);
refusing only when the plugin is newer (two rules for one mismatch, and the hook already names the direction).

**Change list:** `scripts/gen_skill.py` and its generated files (`contrib/claude-code/plugin/**`,
`contrib/claude-code/settings.snippet.json`, `.claude-plugin/marketplace.json`), `code_atlas/main.py`,
`code_atlas/hooks/state.py`, `release_check/__init__.py`, `README.md`, `contrib/claude-code/README.md`,
`contrib/codex/hooks.json`, `contrib/codex/README.md`, `contrib/opencode/code-atlas.js`, `SECURITY.md`,
`docs/SECURITY_STANDARD.md`, `CHANGELOG.md`, new and adjusted tests under `tests/`; bookkeeping
(`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file, budgets if moved).

**Proving tests:** `tests/test_distribution_pinning.py` (new; AC1–AC8 arms) — each arm seen red on `main`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
