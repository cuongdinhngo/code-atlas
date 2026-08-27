---
id: 164
slug: server-build-names-the-repo-not-the-running-process
title: '`server_build` names the repo HEAD, not the code the process loaded — the field built to make a build verifiable reports a commit that did not answer'
phase: 1.5b
milestone: Agent-trust
status: in-progress
depends_on: [162, 125, 100]
---

## Why this exists (field retro round 10, 2026-08-26)

162 shipped `server_build` on every Pillar-1 payload so an answer could name the binary that produced
it (8-D / 9-D). Its first field outing produced a **confident falsehood**, and it is the round's
headline:

> The MCP server process started at **19:55:05**. The files carrying 158–163 were written to disk at
> **20:02:19** — seven minutes later. Every payload that carried a stamp reported **`3d70ab2`**, the
> post-fix SHA, while the process was running pre-fix code. **0 of 6 fixes fired in real work; all 6
> fire on a freshly-started server on the same commit.**
>
> "Had I trusted `server_build` — which is exactly what 162 was built to let me do — I would have filed
> six *shipped but does not work in the field* findings. All six would have been wrong."

This is **worse than the 8-D it repairs**: an unstamped payload is a known unknown; a stamp read from
the repository is a wrong answer wearing the fix's clothes. Two servers on one machine (pids 7301 and
11699, started 10 minutes apart across the write) reported the **same build** and had **different
behaviour**.

The file's own docstring already states the invariant this breaks: *"a retro must never quote a commit
that did not answer"* (`build_info.py:1-7`).

## Root cause

- `code_atlas/build_info.py:38-47` — `_git_build_id()` returns `gitutil.head_commit(root)[:7]` for the
  **checkout the package sits in**. That is the repository's HEAD, not the code Python imported.
- `code_atlas/build_info.py:60-64` — `server_identity()` is `@lru_cache(maxsize=1)`, so the value is
  computed once **at first call**, not at import. A `git pull` between process start and first call is
  therefore already invisible; one after the first call is equally invisible.
- The `+dirty` guard (`build_info.py:47`) defends the **worktree-dirty** axis only. The
  **process-vs-repo** axis — the one a long-lived stdio server lives on — is undefended.
- `code_atlas/build_info.py:49-57` — `_content_build_id()`, a sha256 over every `.py` **under the
  loaded package root**, is exactly the honest identifier, but it runs only as a fallback when no git
  checkout is found.

An editable install with a checkout — the maintainer's and every developer's normal setup — takes the
git branch every time, so the honest identifier is the one path that never runs where it is needed.

## Scope

Make the stamp describe the **process**, and disclose the divergence rather than hide it.

1. Derive the build id from the **loaded package** (the `_content_build_id()` shape), computed once,
   for every install mode — checkout, wheel, container alike.
2. When a git checkout is present, keep the commit as **context, not identity**: report the repo's HEAD
   alongside, and set **`stale_process: true`** when the loaded-content id does not correspond to that
   HEAD's content.
3. `server_provenance()` (`build_info.py:67-76`) carries the new field to every Pillar-1 payload that
   162 already stamps — one spelling, no per-tool work.

The exact field names and whether the git commit stays under `server_build` or moves beside it are a
**design decision**, recorded with the rejected alternative. The binding requirement is: *an answer must
never name a commit whose code did not produce it, and a divergence must be visible in-band.*

### Explicitly not in scope

- Restarting, reloading or hot-swapping the server. This ticket makes divergence **legible**, not
  impossible.
- Pillar-2 onboarding payloads (162's recorded scope boundary stands).
- `sign` / `claim` output shape beyond inheriting the corrected provenance.

## Constraints

- **R4.2 determinism** — identical loaded artifact ⇒ identical id. No timestamps, no pid, no mtime in
  the id itself.
- **Hot path** — `server_identity()` is lru-cached and 162 measured ~53–60 B per payload against a
  test-pinned ≤ 80 B. A content hash walks the package tree **once per process**; prove the per-payload
  cost is unchanged and the one-time cost is bounded.
- **R3** — provenance is payload furniture, not contract vocabulary. No `contract_version` bump.
- **R1.1** — no language branch.
- **061** — omit-when-empty: a process that matches its repo adds no new field.

## Acceptance criteria

1. A server whose loaded code differs from the checkout's HEAD reports a build id derived from the
   **loaded code**, and carries `stale_process: true` (or the design's recorded equivalent) — pinned by
   a test that simulates the divergence without a real `git pull`.
2. A server whose loaded code matches HEAD is **byte-identical** to today's payload (061).
3. The per-payload byte cost stays within 162's pinned budget; the one-time cost of hashing the package
   tree is measured and recorded.
4. Determinism holds (R4.2): the same loaded artifact yields the same id across processes and hosts.
5. No `contract_version` bump (R3); no language branch (R1.1).
6. The wheel / no-checkout path still names a build (125's original guarantee) and is unchanged.

## References

Field retro round 10 §0.a, §12, §12.c, §15 (**the round's single requested change**), §14 (7-G / 8-D /
9-D reopened *because of their own fix*). `code_atlas/build_info.py:1-7,38-47,49-57,60-64,67-76`.
Related: [162](162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md) (the fix this
repairs), [125](125_no-payload-names-the-server-build.md) (the origin),
[100](100_claim-signing-output-mode.md) (`sign`).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 164
- **work_doc_mode:** embed (below this separator) — configured `embed`; ticket is a tracked local file.
- **Run args:** `--no-challenger` (maintainer "with skipped review"); reviewer still runs report-only.
- **CHALLENGER:** OFF (--no-challenger)
- **Review phase:** SKIPPED per run arg "with skipped review" (AGENTS.md convention: run without the review phase; maintainer reviews on the PR). Gate 4 waived — not reintroduced. Self-checks run: mypy delta-clean, ruff clean, proving test + AC1/AC3 logic verified in-conversation.
- **Phase:** 3 execute — complete (commit `d9f978a`); Gate 4 waived; → finalise.
- **BASELINE:** red (platform-excluded, `import fcntl` on Windows); `build_info` isolate green; Docker before PR.

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 3 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Surfaced (advisory): `125-C1` (server-identity origin), `162-C1` (stamp-at-the-builder), `061` (omit-when-empty). Field-naming is a design HOW the ticket delegates; binding requirement already stated.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** M · **TIER:** full

`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=8 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R4.2 (change-type) ✅ · §R3 (change-type) ✅ · §R1.1 (change-type) ✅ · §R5.5 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.5 (change-type) ✅`
`BASELINE: red — bare pytest fails at collection (import fcntl, Windows platform exclusion); build_info isolate green; delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Scope preamble | "Make the stamp describe the process, and disclose the divergence rather than hide it" | The build id must identify the code the process loaded, and any process-vs-repo gap must be in-band | `build_info.py:39-48,60-66` today returns repo HEAD | open |
| R1 | Scope 1 | "Derive the build id from the loaded package … for every install mode" | Identity = content of loaded package, computed once, for checkout/wheel/container alike | `_content_build_id()` exists (`build_info.py:51-59`) but only as fallback | open |
| R2 | Scope 2 | "keep the commit as context, not identity … set `stale_process: true` when loaded-content id does not correspond to HEAD's content" | On divergence report loaded id + repo HEAD alongside + `stale_process:true`; on match keep the commit (061) | `_git_build_id()` unconditionally wins today | open |
| R3 | Scope 3 | "`server_provenance()` carries the new field to every Pillar-1 payload that 162 already stamps — one spelling" | Field rides the single helper; consumers inherit it (R6.7 derived-not-listed) | `server_provenance()` `build_info.py:69-76`; 9 consumers (grep) | open |
| AC1 | AC 1 | diverged ⇒ id from loaded code + `stale_process:true`, pinned by a test simulating divergence w/o real `git pull` | Falsifiable: test monkeypatches loaded≠HEAD, asserts loaded-derived id + flag | new test | open |
| AC2 | AC 2 | matching ⇒ **byte-identical** to today's payload (061) | Falsifiable: byte-equality; match keeps git-commit `server_build`, no new field | pin test | open |
| AC3 | AC 3 | per-payload byte cost within 162's ≤80B budget; one-time hash cost measured+recorded | Falsifiable: existing ≤80 byte test holds; one-time cost measured (script/test) + recorded in task file | `test_...byte_cost` (≤80) | open |
| AC4 | AC 4 | determinism (R4.2): same loaded artifact ⇒ same id across processes/hosts | Falsifiable: stability test, no clock/pid/mtime in id | `test_server_identity_is_stable` | open |
| AC5 | AC 5 | no `contract_version` bump (R3); no language branch (R1.1) | Falsifiable: contract test + R1.1 grep-gate | contract test / grep-gate | open |
| AC6 | AC 6 | wheel / no-checkout path still names a build (125), unchanged | Falsifiable: existing no-git test stays green | `test_build_id_without_git_uses_content_hash` | open |
| C1 | Constraint | R4.2 determinism — no timestamps/pid/mtime in id | Guard the id derivation | — | binding |
| C2 | Constraint | Hot path — per-payload cost unchanged; one-time tree walk bounded | lru-cache identity; hash tree once/process | `test_build_stamp_needs_no_git_on_the_hot_path` | binding |
| C3 | Constraint | R3 — provenance is furniture, no `contract_version` bump | =AC5 | — | binding |
| C4 | Constraint | R1.1 — no language branch | =AC5 | — | binding |
| C5 | Constraint | 061 — omit-when-empty: matching process adds no new field | =AC2 | — | binding |
| C6 | Not-in-scope | No restart/reload/hot-swap | Make divergence legible, not impossible | — | boundary |
| C7 | Not-in-scope | No Pillar-2 onboarding payloads (162's boundary) | Stay on Pillar-1 stamp | — | boundary |
| C8 | Not-in-scope | No `sign`/`claim` shape change beyond inherited provenance | claim.py inherits only | — | boundary |

### AC validation (independently re-derived)

- All six ACs are **falsifiable** (test/grep/byte-count); none carries a bare ✅.
- No AC-value mismatch. The ≤80B budget matches 162's pinned test; 7-char build id unchanged.
- **Design tension resolved by the ticket text, not a Gate-0 question:** AC1 (diverged → loaded-content id) and AC2 (matching → byte-identical, `server_build` still the git commit) are jointly satisfiable only under one reading — `server_build` stays the git commit **when loaded==HEAD**, and becomes the loaded-content id **only on divergence** (Scope 2: "keep the commit as context, not identity … set `stale_process:true` when loaded-content id does not correspond to HEAD's content"). Cited HOW; design picks the exact field mechanism (import-time capture of loaded content vs first-call).

### Root cause (taxonomy: logic)

`build_info.py:39-48` `_git_build_id()` returns repo HEAD unconditionally when a checkout exists; `_content_build_id()` (the honest process identifier) runs only as a git-absent fallback. `server_identity()` is `@lru_cache` computed at first call, so a disk change between process start and first call is already invisible. The process-vs-repo axis is undefended (the `+dirty` guard covers only worktree-dirty).

### Blast radius

- Handler: `code_atlas/build_info.py` (identity derivation + `server_provenance()`).
- Consumers (inherit via helper, R6.7): `tools/{nav_result,read_symbol,get_index_status,file_outline,subtree_dependencies,reach_shared,impact_modules,explain_path,claim}.py` — no per-tool edit expected.
- Tests: `tests/test_server_build.py`, `tests/test_server_build_on_payloads.py`.
- Universal inventory `N=1` change site (the helper); the "every Pillar-1 payload" denominator is covered by construction (single spelling) + the existing consumer-invariant tests.
- Repos touched: `app` only. No adapter, no store, no contract, no schema.

## Phase 2 — design

### Approach

Capture the **loaded** code's identity at **import** and use it to defend the process-vs-repo axis:

1. Freeze `_LOADED_BUILD_ID = _content_build_id()` at module import (process start ≈ what was loaded). Guarded so naming the build never raises (module invariant).
2. `server_identity()` (still `@lru_cache`) decides on the process-vs-disk comparison:
   - **No git checkout** → `build = _LOADED_BUILD_ID` (wheel / container — AC6, 125).
   - **Checkout, `_content_build_id() == _LOADED_BUILD_ID`** (disk unchanged since load) → `build = _git_build_id()` — the commit (or `commit+dirty`), **byte-identical to today** (AC2). The commit is the loaded code's identity because content agrees.
   - **Checkout, content differs** (disk moved under a running process) → `build = _LOADED_BUILD_ID` (the honest loaded id) + `stale_process: True` + `repo_head: <HEAD[:7]>` as context. The commit becomes context, not identity (AC1).
3. `server_provenance()` emits `server_stale_process: true` and `server_repo_head` **only on divergence** (061 omit-when-empty) — one spelling, inherited by all 9 Pillar-1 consumers via the single helper (R6.7). `claim.py` inherits the corrected `build` automatically; its shape is unchanged (ticket scope boundary C8).

The `+dirty` axis (worktree vs commit) is untouched and stays inside `_git_build_id()`; `stale_process` is the orthogonal process-vs-disk axis, exactly as the ticket frames it.

### Rejected alternatives

- **Content-hash as identity always** (`server_build` = content hash in every mode; commit only ever a context field). Cleanest single rule, but on a matching process it changes `server_build` from the git commit to a hash → **not byte-identical to today** → violates AC2/061. Rejected: AC2 forces the commit to remain the identity when content agrees.
- **Compute the loaded id lazily at first call** (no import-time capture). Fails the ticket's own root cause: a disk change between process start and first call stays invisible. Import-time capture is what makes "loaded" mean loaded.
- **Report `repo_head` as `_git_build_id()` (commit+dirty)**. More disk detail, but `repo_head` names a commit; the `+dirty` disk state is already implied by `stale_process`. Kept `repo_head` = plain `HEAD[:7]`.

### Field-name decision (the HOW the ticket delegated)

`server_stale_process` / `server_repo_head` — `server_`-prefixed to match the existing `server_build`/`server_version` payload namespace. Rejected bare `stale_process`/`repo_head` for namespace inconsistency. Recorded per ticket instruction.

### Assumptions

| Assumption | Tag |
|---|---|
| At import, package `.py` files on disk == the code Python loaded (negligible import-window race) | verified (reasoning; import runs at process start) |
| `_content_build_id()` re-walk at first `server_identity()` call is one-time (lru-cached) and cheap | novel-untested → resolved by AC3 measurement + the hot-path test already pinning no-git-per-payload |
| Adding optional keys to `server_identity()`/`server_provenance()` breaks no consumer | verified (blast-radius grep: all consumers use key access; the one exact-shape test is non-diverged → 2 keys) |

No `novel-untested` third-party/runtime assumption remains: the one-time cost is proven by the AC3 measurement (a real number, recorded) — not an integration risk.

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| Freeze `_LOADED_BUILD_ID` at import (guarded) | `code_atlas/build_info.py` | import-time disk walk once/process; no consumer reads this symbol | R1, AC6 | 1/1 |
| Rewrite `server_identity()` for process-vs-disk divergence; keep `_git_build_id()` intact | `code_atlas/build_info.py` | `test_dirty_checkout...` calls `_git_build_id()` (kept); return type widens to `dict[str, object]` (mypy) | R2, AC1, AC2, AC4, AC6 | 1/1 |
| Extend `server_provenance()` with divergence fields (omit-when-empty) | `code_atlas/build_info.py` | 9 tool consumers spread `**server_provenance()` (inherit; non-diverged byte-identical) | R3, AC1, AC2 | 1/1 |
| Proving test + determinism/byte-cost-on-divergence + measurement | `tests/test_server_build.py` | new tests only; no existing test edited | AC1, AC3, AC4 | 1/1 |
| Record one-time hash cost (measured) | task file (this doc) | none identified | AC3 | 1/1 |
| Docs: BACKLOG status, TOKEN_LEDGER row | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | R7.2 bookkeeping test | R7.2 | 1/1 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

(The `RECALL:` line surfaced 3 claims **by symbol** and 0 **by handle** — 0 type-2 handles to trace. The mechanical blast-radius grep above is folded into the change list regardless.)

### Rule compliance

- **R4.2** — id from content bytes / commit; no clock/pid/mtime. Import-time capture is deterministic given the bytes. ✅
- **R3** — payload furniture only; no `contract_version` bump, no `contract.py` edit. ✅ (AC5)
- **R1.1** — no language branch. ✅ (AC5)
- **R5.5** — `stale_process`/`repo_head` sourced from the divergence computation that owns the whole fact. ✅
- **R6.5** — proving test recorded red pre-change. ✅
- **R7.5** — comments ≤3 lines. ✅ (execute)
- **R7.2** — BACKLOG + TOKEN_LEDGER updated before PR. ✅

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | logic (pure fn on monkeypatched loaded≠disk) | unit | ✅ |
| AC2 | logic (payload byte-equality, non-diverged) | unit | ✅ |
| AC3 | logic (≤80 byte stamp) + measurement | unit + manual-recorded (timing number) | ✅ |
| AC4 | logic (stable across calls; no clock/pid/mtime) | unit | ✅ |
| AC5 | logic (no contract bump) + guard (R1.1 grep-gate) | unit + grep-gate | ✅ |
| AC6 | logic (no-git path) + runtime (container) | unit + integration (docker-gated, existing) | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

No layer-match ❌; no coverage-gap exclusion required.

### Proving test

`test_stale_process_when_loaded_differs_from_disk` in `tests/test_server_build.py`: monkeypatch `build_info._LOADED_BUILD_ID` to a value ≠ `_content_build_id()`, `_git_root` to `tmp_path`, `gitutil.head_commit` to a fixed SHA, `working_tree_dirty` False; clear the `server_identity` cache. Assert `server_identity()["build"] == <patched loaded id>`, `["stale_process"] is True`, `["repo_head"] == sha[:7]`, and `server_provenance()["server_stale_process"] is True`. **Fails pre-change** (today `build == commit`, no `stale_process`), passes post-change.

Invocation: `pytest tests/test_server_build.py -k stale_process` (full suite via Docker before PR).

### Rollback + porting

Rollback: revert `build_info.py` + the added tests (single module, no schema/contract/migration). Porting: `app` is the only repo; no shared-code fan-out.

### SCOPE

`SCOPE: M` — unchanged from analysis. Change-list is 3 edits to one core module + tests + docs bookkeeping; did not cross to L. Branch type `feat` matches (a new honesty field), no branch/PR-type drift.

## Phase 3 — execute

**Branch:** `feat/164-server-build-names-the-running-process`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Freeze `_LOADED_BUILD_ID` at import (guarded, degrade not raise) | implemented-as-approved |
| `server_identity()` three-branch process-vs-disk logic; `_git_build_id()` kept | implemented-as-approved |
| `server_provenance()` emits `server_stale_process`/`server_repo_head` omit-when-empty | implemented-as-approved |

No deviations. `SCOPE: M` held; diff did not exceed the approved list.

### Verification sweep (Axis 1 — file set)

Diff = `code_atlas/build_info.py`, `tests/test_server_build.py`, this working doc — all in the approved list; no file outside, no untouched-line reformatting. (`.mango/` is pre-existing untracked, not this change.) Docs bookkeeping (BACKLOG/TOKEN_LEDGER) done at finalise.

### Empirical outputs

Non-diverged (matching process, dirty worktree of the branch):
```
identity {'version': '0.1.0', 'build': 'fa13f9a+dirty'}
provenance {'server_version': '0.1.0', 'server_build': 'fa13f9a+dirty'}   # 2 keys → byte-identical shape
```
Diverged (AC1, loaded id pinned below disk content, git present):
```
DIVERGED identity: {'version': '0.1.0', 'build': '0ldc0de', 'stale_process': True, 'repo_head': 'abcdef1'}
DIVERGED provenance: {'server_version': '0.1.0', 'server_build': '0ldc0de', 'server_stale_process': True, 'server_repo_head': 'abcdef1'}
AC1 OK
```
AC3 one-time cost (measured):
```
AC3 one-time walk: 72 .py files, 780502 bytes, 6.35 ms
```
mypy (delta-clean; the 5 errors are the pre-existing Windows `fcntl` in `index_lock.py`, untouched):
```
code_atlas\index_lock.py:25: error: Module has no attribute "flock"  [attr-defined]  (×5, index_lock only)
Found 5 errors in 1 file (checked 72 source files)
```
ruff: `All checks passed!` on both changed files.

**Proving test:** `test_stale_process_when_loaded_differs_from_disk` — fails pre-change (today `build == commit`, no `stale_process`), asserts loaded id + `stale_process` + `repo_head` post-change. Full-suite run via Docker before PR (bare pytest red at collection on Windows `fcntl` — the recorded baseline exclusion).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_stale_process_when_loaded_differs_from_disk` |
| AC2 | `test_matching_process_is_byte_identical_and_omits_stale_fields` + existing `test_server_provenance_is_the_get_index_status_spelling` |
| AC3 | `test_one_time_hash_walk_is_bounded` + recorded 6.35 ms / 780 KB measurement |
| AC4 | `test_stale_process_is_deterministic_across_calls` + existing `test_server_identity_is_stable_across_calls` |
| AC5 | R1.1 grep-gate + no `contract.py`/`contract_version` change in diff |
| AC6 | existing `test_build_id_without_git_uses_content_hash` + `test_runtime_image_reports_server_build` (docker) |

## Phase 5 — finalise

**Delta-green (Docker / Linux host):**
```
tests/test_server_build.py tests/test_server_build_on_payloads.py → 23 passed, 1 skipped
full suite → 2124 passed, 1 skipped, 0 failed (200.95s)
ruff check . → All checks passed!
mypy code_atlas → Success: no issues found in 72 source files
```
Bare pytest on Windows is red at collection (`import fcntl`) — the recorded platform baseline exclusion; delta-green confirmed in-container per README *Testing*.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`164-C1` (type-2, `identity-names-the-loaded-process-not-the-disk`, seen: 164) recorded in LESSONS.md as `proposed`. seen=1 → not a promotion candidate; legitimately stays in lessons_path. Relates to `125-C1`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase skipped by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

0 subagent dispatches this run → ledger complete with 0 rows. Main-loop output noise is not measured by mango (`rtk gain` for that axis).

### Review

SKIPPED per run arg "with skipped review" (AGENTS.md convention). Reviewer + challenger both waived; no `Reviewed at` marker → stale-review guard waived consistently. Self-checks stood in: mypy/ruff green (Docker), full suite delta-green, proving test passing.
