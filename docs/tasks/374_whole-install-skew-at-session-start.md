---
id: 374
slug: whole-install-skew-at-session-start
title: 'An install whose halves all lag a release hears nothing, and a stale adapter checkout surfaces only when a build fails'
phase: 2
milestone: Adoption
status: done
depends_on: [348]
---

## Why this exists

This is the field report that meets the re-open condition of 348's decision in
[PLAN §19](../PLAN.md#19-project-context--decision-log): "an install that ran an old release
without knowing."

An anchor project (PHP + SQL + TS, ~22.9k files, Windows) observed the following on 2026-10-09:

- **No notice of 0.3.0.** The release shipped 2026-10-08. The anchor ran the 0.2.0 plugin with the
  0.2.0 tool install, and no line said a newer release existed. The 348 skew line compares the two
  halves only with each other, and the two halves agreed.
- **The adapter checkout is a third half, and nothing checks it before a build.** The checkout that
  `CA_<LANG>_CMD` points into had been pulled to contract 14. The first sign was a refused
  incremental build: `build_or_update_index` returned `no_usable_adapter`, with the detail
  `adapter 'php' speaks contract v14, but this core speaks v13`. Read tools kept serving a `behind`
  index, so the session ran on stale answers until the build was tried.
- **The skew line worked once a half moved.** After `claude plugin update`, the next session start
  printed `hooks expect code-atlas 0.3.0 but 0.2.0 is installed — run uv tool upgrade code-atlas`.
- **On Windows, `uv tool upgrade` fails halfway under a running server.** The package and six
  scripts moved to 0.3.0. Copying `code-atlas.exe` into `~/.local/bin` failed with
  `os error 32` (in use by the MCP server), so uv exited `Failed to upgrade code-atlas` even though
  the upgrade had mostly landed. Neither the README nor the skew line mentions this.
- **`server_stale_process: false` after the upgrade.** The server started on 0.2.0, then
  `uv tool upgrade` replaced the package under it. `get_index_status` then reported
  `server_version 0.2.0`, `server_stale_process: false`. A `/mcp` reconnect loaded 0.3.0. The cause
  was not traced. Both fields come from the memoised `_identity` (`build_info.py`), recomputed only
  when a loaded module's `(mtime, size)` moves. So either the disk still held 0.2.0 (uv may restore
  the old environment when it reports `Failed to upgrade`), or that probe missed the swap.
  **UNVERIFIED:** that the package itself reached 0.3.0 before the reconnect — how it was checked
  is not recorded.
- **The plugin did not update itself, and the reason is documented.** The Claude Code docs
  (`code.claude.com/docs/en/plugins/loading.md` and `install.md`, read 2026-10-09) say:
  - auto-update is **off by default** for third-party marketplaces;
  - it is enabled with `/plugin` → Marketplaces → *Enable auto-update*, or with `"autoUpdate": true`
    on the marketplace's `extraKnownMarketplaces` entry in a settings file;
  - it runs after the first message of an interactive session, after a random delay of up to ten
    minutes, and takes effect on `/reload-plugins` or the next launch.

  348's README records this as unmeasured (its A3).

The combined effect: once the plugin auto-updates, 348's skew line pulls the tool install along.
The adapter checkout still has no offline check, and the README does not yet say how to make the
plugin the half that moves first.

**What an offline check cannot see.** Scope 1–2 detect halves that *disagree*. In the 0.3.0 case
all three halves agreed on 0.2.0, so they stay silent there. Only auto-update (Scope 3) or a
re-decided release check (Scope 5) reaches that case; AC5 decides which.

## Scope

1. **An adapter ↔ core contract skew line at session start, offline.** For each configured
   adapter, `code-atlas-state` reports when the adapter's contract differs from
   `contract.CONTRACT_VERSION`. The line names the adapter, both contracts and the fix **for the
   side that is behind**, as 348's `skew_line` does: a checkout behind the core is pulled and its
   dependencies reinstalled; a core behind the checkout (the anchor's case, v13 vs v14) is
   upgraded. There is no network call (R4/R4.1), and the hook stays inside its 10 s timeout and
   silent with no index. How the contract is read is a design question; see the assumptions.
2. **One line for the whole install.** When more than one half lags, name each command, in the
   order they must run. A half lags when it is older than the newest of the three local halves.
   The order is: on Windows, disconnect the server first (the launcher lock, Scope 3); then tool,
   plugin, checkout; then reconnect the server (`/mcp`) or restart. The line is at most **90 tokens**
   (`estimate_tokens`, the state line's `TOKEN_BUDGET`).
3. **README *Upgrading*:**
   - replace "auto-update was not measured" with the documented behaviour above, and recommend
     enabling auto-update for this marketplace, at user level or in a project's
     `extraKnownMarketplaces` entry for an anchor's team;
   - on Windows, stop or disconnect the server before `uv tool upgrade`, or re-run it after;
   - a `/mcp` reconnect is enough to load the new server.
4. **Trace the `server_stale_process: false` observation.** First tell the two causes apart: did
   uv restore 0.2.0 on failure, or did the `(mtime, size)` probe miss files replaced with the same
   stamp? Then either fix the detection, or record why a running server cannot see the upgrade.
5. **Re-decide PLAN §19's 348 entry with this evidence.** Claude Code's auto-update already
   performs the network fetch outside the core. The question is whether that, together with
   Scope 1–2, closes the gap without a release check of code-atlas's own. Record the decision
   either way.

## Assumptions to prove at design

- **How the session-start hook learns an adapter's contract inside 10 s.** Two candidates were
  rejected while the ticket was reviewed:
  - *A build-time stamp compared with the core* catches nothing new. `meta.contract_version`
    already equals the core's contract at build time (the handshake forces it), and 347 already
    compares it. A checkout pulled after the build leaves the stamp equal to the core.
  - *Reading the constant from each adapter's entry file* makes the core parse PHP, TS and Python
    source (R1.1), and guess the entry file from a `CA_<LANG>_CMD` argv that may be a container.

  Two remain:
  - (a) launch each adapter and read its handshake with a short timeout. This is new for a hook
    that "never builds, reparses". It launches only `CA_<LANG>_CMD`, and a project file's
    `[adapter_cmd]` still needs `CA_TRUST_PROJECT_FILE=1` (341). Measure the cold start of all
    configured adapters together, on Windows, on the anchor.
  - (d) record a build or refresh that the handshake refused, as 355 records a refused refresh,
    and let the state line speak from it. This costs nothing at session start, but it speaks only
    after the first refused refresh.
- **Whether a project-level `extraKnownMarketplaces.<name>.autoUpdate` is honoured for a teammate
  who installed the plugin at user scope.** The docs imply it, but show only a managed-settings
  example. Measure it before the README recommends it.

## Acceptance criteria

- **AC1:** With the checkout's adapters on one contract and the core on another, in either
  direction, the `SessionStart` hook prints one line naming the adapter, both contracts and the
  fix for the side that is behind. It is silent when they match, silent with no index, and it
  exits 0 within the hook timeout. Each case is seen red first (R6.5).
- **AC2:** With the tool, the plugin and the checkout all on different versions, the hook names
  every half older than the newest one, with its command, in the Scope 2 order (the Windows
  disconnect step only on Windows), in at most 90 tokens.
- **AC3:** The README *Upgrading* section states the documented auto-update behaviour, how to turn
  it on per user and per project, the Windows launcher lock, and the `/mcp` reconnect.
- **AC4:** The `server_stale_process` observation is reproduced, the cause is named (uv restored
  the old package, or the probe missed the swap), and it is either fixed or explained in LESSONS.
- **AC5:** PLAN §19 carries the re-decided 348 entry, with its reason, including whether an
  install whose halves agree on an old release is told so.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 374 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges PR #53. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 374`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The maintainer answered refine's five want-decisions live.
- Branch `feat/374-whole-install-skew-at-session-start` off `main` (`e1e82688`). Contract `.mango/run-contract-374.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 0 by handle | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `code-atlas-state` (`hooks/state.py`), `contract.CONTRACT_VERSION`, `skew_line`,
`estimate_tokens`, `TOKEN_BUDGET`, `_identity` (`build_info.py:118`), `server_stale_process`,
`no_usable_adapter`, `CA_TRUST_PROJECT_FILE`, `[adapter_cmd]`, `meta.contract_version`, README
*Upgrading* and PLAN §19's 348 entry all resolve.

**Recall (area).** 348-C1 (`claude-code plugins / update`: a plugin moves only on a version bump),
344-C2 (hooks get `CLAUDE_PROJECT_DIR`, never `userConfig`), 345-C1 (plain hook stdout) — context only.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,622 tokens) added W4–W5 and the
trust note on W1; it found no item mis-classified.

| # | Decision | Class | Resolution |
|---|---|---|---|
| W1 | how the hook learns an adapter's contract | want | **maintainer: both** — launch each configured `CA_<LANG>_CMD` and read its handshake under a short timeout, and record a handshake-refused build for an adapter the launch cannot answer for |
| W2 | per-project auto-update in the README | want | **maintainer:** recommend per user; show the project setting, stated as unmeasured |
| W3 | AC5: is an all-agree old install told? | want | **maintainer:** no release check of our own; rely on Claude Code's auto-update; record that a non-plugin install whose halves agree stays silent |
| W4 | recommend auto-update at all (trust) | want | folded into W2's answer: recommend per user |
| W5 | the 90-token overflow | want | **maintainer:** collapse to a pointer — name each lagging half, point at README *Upgrading* for the ordered commands |
| H1 | AC4's cause | how | reproduced on Linux (Phase 1): `server_identity()` short-circuits the probe on its first call, so it is never seeded |
| H2 | a checkout's "version" | how | its handshake contract (`adapter.py:254`) — the only version an adapter announces |
| H3 | the plugin half's contract | how | the generated hook passes `--expect-contract`, beside 348's `--expect-version` (`gen_skill.py:178`) |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=4 R=5 G=1 AC=5`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/12 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Clarifications: H1–H3 cite code (Phase 0); W1–W5 cite the maintainer's live answers (Phase 0) — answered, so none reaches `j`. The first emission read `3 self-resolved`; `check_lines.py` refused it (`M != k + j`) and analysis re-emitted it.

### BASELINE

`scripts/gate.sh` on `main` (`e1e82688`), Linux, bare pytest: `21 passed · 0 failed · 0 skipped` —
`GATE GREEN — all 21 checks passed`. Ran at e1e82688.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "an install that ran an old release without knowing" | every lagging half of the install is named offline at session start | ✅ |
| C1 | Scope 1 | "There is no network call (R4/R4.1)" | the probe launches local commands only | ✅ |
| C2 | Scope 1 | "the hook stays inside its 10 s timeout and silent with no index" | one 3 s bound over all adapters, launched together; no index → no launch | ✅ |
| C3 | Scope 2 | "at most **90 tokens**" | `estimate_tokens(line) <= TOKEN_BUDGET`, else W5's pointer | ✅ |
| C4 | Assumptions | "a project file's `[adapter_cmd]` still needs `CA_TRUST_PROJECT_FILE=1` (341)" | the probe reads `load_config`'s `adapter_cmds`, which applies 341 | ✅ |
| R1 | Scope 1 | adapter ↔ core contract skew line, fix for the side behind | W1, H2 | ✅ |
| R2 | Scope 2 | one line for the whole install, commands in order | H3, W5 | ✅ |
| R3 | Scope 3 | README *Upgrading*: auto-update, Windows lock, `/mcp` | W2 | ✅ |
| R4 | Scope 4 | trace `server_stale_process: false` | H1 | ✅ |
| R5 | Scope 5 | re-decide PLAN §19's 348 entry | W3 | ✅ |
| AC1 | AC | one line naming adapter, both contracts, the fix; silent on match / no index; exit 0 in time; red first | both directions | ✅ |
| AC2 | AC | every half older than the newest, Scope 2 order, Windows step only on Windows, ≤ 90 tokens | 3 halves | ✅ |
| AC3 | AC | README states auto-update, per user/project, launcher lock, `/mcp` | W2 | ✅ |
| AC4 | AC | reproduced, cause named, fixed or explained | H1 | ✅ |
| AC5 | AC | PLAN §19 re-decided, incl. the all-agree case | W3 | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — the console script's stdout on a real index with a fake adapter at contract 1 and 99 | |
| AC2 | yes — `install_line` over three halves on three versions, `estimate_tokens` ≤ 90, the Windows step present iff `windows=True` | |
| AC3 | yes — the README section names each item | the per-project setting is stated unmeasured (W2) |
| AC4 | yes — a real swap of a loaded module after the first payload; pre-fix `stale_process` stays `False` | reproduced on Linux: `first False · second False · third False`; with a second payload before the swap, `second True` |
| AC5 | yes — the §19 entry names the all-agree case | |

### Blast radius

- `adapter.py`: a contract refusal becomes a typed `AdapterError` subclass, message unchanged.
- `tools/build_or_update_index.py`: the refusal payload is unchanged; it also records the contract.
- `hooks/state.py`: the tool↔plugin-only line stays byte-identical (348's tests).
- Generated hook tables gain `--expect-contract` before `--expect-version`, so 348's `endswith` holds.
- `build_info.py`: the probe is seeded on the first identity; `test_server_identity_is_live.py` covers it.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the probe launches every configured command alike, no language test · §R1.4 (change-type) ✅ the refusal record is a file beside graph.db, not SQLite · §R4.1 (change-type) ✅ local commands only, no network · §R4.2 (change-type) ✅ the probe writes nothing to the index · §R5.3 (change-type) ✅ the hook never raises; the build's refusal stays loud · §R6.5 (change-type) ✅ every AC1 case seen red first · §R7.5 (change-type) ✅ comments ≤ 3 lines`

## Phase 2 — design

### Approach

1. `adapter.py`: `AdapterContractError(AdapterError)` carries `key` and `announced`; `_read_handshake` raises it.
2. `adapter_skew.py` (new): `adapter_contracts(config)` launches every configured adapter at once,
   bounded by one 3 s deadline, and fills an unanswered adapter from `contract.refused` beside
   `graph.db`; `record_refusal` / `clear_refusals` keep that file.
3. `build_or_update_index.py`: a contract refusal is recorded; a build that runs clears the record.
4. `hooks/state.py`: `--expect-contract`; `install_line` names each lagging half — tool, plugin,
   adapters — and its fix: one half → one line with its fix; two or more → the Scope 2 order (Windows
   disconnect first, `/mcp` reconnect last), or W5's pointer past 90 tokens. Tool↔plugin alone keeps 348's line.
5. `gen_skill.py` + the two generated hook tables: `--expect-contract <CONTRACT_VERSION>`.
6. `build_info.py`: seed the probe when the identity is first computed (AC4).
7. README *Upgrading*, PLAN §19, LESSONS, TOOLS.md, `contrib/claude-code/README.md`, CHANGELOG.

### Rejected alternatives

- **Record only** — silent until a build is refused, the anchor's gap (W1).
- **A release→contract table in the core** — the plugin half can name its own contract (H3); a table
  needs a row per release and still cannot know a newer one.
- **Re-hashing the package per payload for AC4** — 164 measured 6.35 ms; seeding the probe suffices.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | typed contract refusal | `code_atlas/adapter.py` | every `AdapterError` catcher (subclass) | R1 | 1/1 |
| 2 | the probe + refusal record | `code_atlas/adapter_skew.py` (new) | — | R1, C1, C2, C4 | 1/1 |
| 3 | record / clear on build | `code_atlas/tools/build_or_update_index.py` | refusal payload unchanged | R1 | 1/1 |
| 4 | the install line | `code_atlas/hooks/state.py` | 348's skew tests | R1, R2, C3 | 1/1 |
| 5 | the hook passes its contract | `scripts/gen_skill.py`, `contrib/claude-code/settings.snippet.json`, `contrib/claude-code/plugin/hooks/hooks.json` | 348's hook-table test | R2 | 3/3 |
| 6 | probe seeded | `code_atlas/build_info.py` | identity tests | R4, AC4 | 1/1 |
| 7 | proving tests | `tests/test_install_skew.py` (new), `tests/test_server_identity_is_live.py` | — | AC1, AC2, AC4 | 2/2 |
| 8 | docs | `README.md`, `docs/PLAN.md`, `docs/LESSONS.md`, `docs/TOOLS.md`, `contrib/claude-code/README.md`, `CHANGELOG.md` | doc budget | R3, R5, AC3–AC5 | 6/6 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — the hook process | the `code-atlas-state` console script on a real index, `CA_FAKE_CMD` → the adapter fixture at contract 1 and 99, timed | authored | ✅ |
| AC2 | logic — the line | `install_line` on three halves at three versions, both platforms | authored | ✅ |
| AC3 | doc | the README section | — | ✅ |
| AC4 | process state | a real write to a loaded module between two `server_identity()` calls | authored | ✅ |
| AC5 | doc | the §19 entry | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_install_skew.py tests/test_server_identity_is_live.py`.

### Rollback

`git revert`; the next session start drops the probe, and `contract.refused` is ignored.

## Phase 3 — execute

Commits `917bcb95` (code, tests, hook tables), `fa8d6d33` (docs). **Red first** (R6.5): AC4's test on
the prior `build_info.py` — `1 failed, 13 passed`; the three AC1 speaking cases with the probe
switched off — `3 failed`. The silence cases (match, no adapter, no index, silent adapter) passed
before too: nothing spoke then, so they guard against a false line, not a missing one.

```
$ .venv/bin/python -m pytest -q tests/test_install_skew.py tests/test_server_identity_is_live.py
29 passed in 13.56s
Ran at fa8d6d33
```

**Verification sweep.** The diff is the approved list except two deviations:
- **D1 — `indexer.py` replaces `tools/build_or_update_index.py` (item 3).** The build tool's result
  cannot say whether adapters were launched (an up-to-date refresh starts none), so clearing there
  would wipe a live record. `indexer._announce` is the one place every build, refresh and read
  starts adapters: a contract refusal records, a full announce clears (R1.8).
- **D2 — `tests/test_release_discipline.py`.** The blast-radius note was wrong: `--expect-contract`
  sits between the script and `--expect-version`, so 348's `endswith` check failed; it now pins both.

**Design conformance.** Approach 1, 2, 4–7 implemented as approved; 3 deviated (D1).
Run-time detail: a lone adapter skew keeps AC1's one-line form; when the plugin's contract also lags
(the anchor), the whole-install line names the leading adapter, both contracts and each fix.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at b42e6c9b — files: `code_atlas/adapter.py`,
`code_atlas/adapter_skew.py`, `code_atlas/build_info.py`, `code_atlas/hooks/state.py`,
`code_atlas/indexer.py`, `scripts/gen_skill.py`, `contrib/claude-code/README.md`,
`contrib/claude-code/plugin/hooks/hooks.json`, `contrib/claude-code/settings.snippet.json`,
`tests/test_install_skew.py`, `tests/test_server_identity_is_live.py`,
`tests/test_release_discipline.py`, `README.md`, `CHANGELOG.md`, `docs/PLAN.md`, `docs/TOOLS.md`,
`docs/LESSONS.md`.

- **`reviewer` round 1 — LGTM** (62,326 tokens): R1.1, R1.4, R4.1/4.2, R5.3, R6.5, R6.10, R7.5,
  R7.6, R7.7 checked; D1 and D2 judged justified. Two optional minors, not taken (a change would
  stale the review): a partial announce leaves proven adapters' old `contract.refused` entries
  until the next full announce; a deadline that fires before `Popen` leaves one child unkilled.
- **`challenger` round 1** (ticket-blind, 56,650 tokens): 10 met · 0 not met · 0 can't tell.
  Qualifications: the uv-restore half of AC4 is unverified; red-first order is not visible in a diff.

Verdict: clean. Matrix `Ph3/4 proven by`: G1, R1, R2, C1–C4, AC1, AC2 → `tests/test_install_skew.py`
(15); R4, AC4 → `test_server_identity_is_live.py`; R3, R5, AC3, AC5 → the README / PLAN hunks.

## Phase 5 — finalise

**Durable lesson.** 374-C1 in `docs/LESSONS.md`: a memo guarded by a change probe must seed the probe
when it first computes; every test stubbed the probe, so none saw it.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover (AGENTS.md standing finish approval): push `feat/374-whole-install-skew-at-session-start`;
open the PR. Deferred to the maintainer: merge; a version bump so installed 0.3.0 plugins receive
`--expect-contract` (348-C1: content under an unchanged version does not update).

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 44,622 |
| 4 review | `reviewer` | 1 | 62,326 |
| 4 review | `challenger` (ticket-blind) | 1 | 56,650 |

`LEDGER TOTAL: 163,598 · top cost driver: 4 review/reviewer`
