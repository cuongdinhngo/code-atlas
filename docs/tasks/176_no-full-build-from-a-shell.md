---
id: 176
slug: no-full-build-from-a-shell
title: 'No full build from a shell — `code-atlas-refresh` runs the incremental path but never a full one, so a first build and a post-config rebuild both require an MCP client'
phase: 1.5b
milestone: Freshness
status: done
depends_on: [010, 053]
---

## Why this exists (field episode, 2026-08-27)

The maintainer, trying to rebuild after wiring the second adapter:

> *"`[project.scripts]` đã có 4 entry (`code-atlas-poke`, `-refresh`, `-signal`, `-llm`) nhưng không có
> `code-atlas build [--full]`. Muốn rebuild phải qua một MCP client — nên không rebuild được từ shell,
> từ CI, hay sau khi đổi config. Đây cũng chính là thứ mà mục roll-out trong retro cần."*

**Narrowed after checking the source, because the gap is smaller and more specific than "no build
CLI".** `code-atlas-refresh` already runs *"the same path as `build_or_update_index(full=false)`"*
(`hooks/refresh.py:1-8`). What no entry point can do is:

- a **full** build — there is no `--full`, on any script;
- a **first** build — refresh is deliberately a *"safe no-op with no index (never builds)"*.

So the fix is a flag on machinery that already exists, not a new subsystem. And it is on the roll-out
critical path: round 11 §11.g's break-even condition is *`.mcp.json` + one CI job + delete the scanner
lines the graph answers*, and **a CI job cannot call an MCP tool.**

## Root cause

- `pyproject.toml` `[project.scripts]` — `code-atlas` is the **MCP server** (`code_atlas.main:main`);
  the three hook helpers are `poke` (one file, task 036), `refresh` (incremental, task 053) and
  `signal`. None takes a full-build path.
- `code_atlas/hooks/refresh.py:1-8` — by design: incremental only, and never builds without an index,
  so a git hook can never trigger a multi-minute first build.
- `code_atlas/tools/build_or_update_index.py` owns the whole build entry (lock, schema mismatch,
  report shaping — `:101,177,196,213`); a CLI must reuse it rather than call `indexer` directly, or the
  two paths will drift on locking and reporting.

## Scope

One shell entry point for a build, reusing the existing tool path.

1. A `--full` capability reachable from a shell, and a first build when no index exists — as a flag on
   `code-atlas-refresh`, or a new `code-atlas-build` script. Design picks one and records why (the
   safety property of refresh's *"never builds"* default must not be lost for git hooks).
2. Exit codes and one-line stderr output usable from CI: success, nothing-to-do, busy peer (R4.3),
   and failure distinguishable.
3. It goes through `build_or_update_index`'s path, so the lock, the schema-mismatch answer and the
   report shape are identical to the MCP route.

### Explicitly not in scope

- A general CLI surface for the query tools. This is the build only.
- The CI job itself and `.mcp.json` — those belong to the consuming repo, deliberately not filed here
  (round 11 §11.i).
- What the build should *do* when scope changed — [172](172_incremental-is-blind-to-a-scope-change.md).

## Constraints

- **R4.3** — one mutex shared with the server; a busy peer is a clean skip, not an error.
- **053's safety property** — the git-hook path must keep *never builds without an index*; a `--full`
  flag must be opt-in per invocation.
- **R6.5** — the entry point is covered by the gate's `entry points (derived from [project.scripts])`
  check, so a new script must appear there.
- **Determinism** — same tree ⇒ same rows as the MCP route (R4.2); the CLI adds no second code path
  for the build itself.

## Acceptance criteria

1. A full build runs from a shell with no MCP client, on a repo with **no** existing index, and
   produces the same rows as the MCP route — pinned by a test.
2. The incremental hook path still never builds without an index (053), pinned.
3. Exit codes distinguish success · nothing-to-do · busy peer · failure, each pinned.
4. The build goes through `build_or_update_index`; no second lock and no second report shape.
5. `scripts/gate.sh`'s entry-point check covers the new script.
6. Determinism (R4.2); no language branch (R1.1); no contract bump (R3).

## References

Field episode 2026-08-27, finding (4), narrowed against source (refresh already covers incremental).
Round 11 §11.g (break-even needs a CI job), §11.i (roll-out is not filed as a ticket, but the
capability it needs is). `pyproject.toml` `[project.scripts]`; `code_atlas/hooks/refresh.py:1-8`;
`code_atlas/tools/build_or_update_index.py:101,177,196,213`. Related:
[010](010_index-status-and-build-tools.md) (the tool this must reuse),
[053](053_refresh-on-checkout-hook.md) (the existing shell path),
[172](172_incremental-is-blind-to-a-scope-change.md).

## Session status

- **KEY:** 176 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-176.txt`.
- **Branch:** `feat/176-no-full-build-from-a-shell`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2166 passed, 0 failed` (bare `pytest` on this Linux host; the AGENTS.md Docker note covers the maintainer's Windows box, not this one).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

The one unresolved item is Scope 1's *"as a flag on `code-atlas-refresh`, or a new `code-atlas-build`
script — design picks one and records why"*. That is a **how-decision**: the ticket states the property
that must survive (053's *never builds without an index*), so it is resolvable from the source without
asking. Resolved in Phase 2 → *Rejected alternatives*, cited `code_atlas/hooks/refresh.py:1-8`. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 12 applicable — 11 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.4 (change-type) ✅ · §R1.8 (change-type) ✅ · §R4.2 (change-type) ✅ · §R4.3 (change-type) ✅ · §R5.3 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅ · §R7.5 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2166 passed, 0 failed, 0 skipped (bare pytest, Linux host, 99.22s)`

**Premise:** `pyproject.toml [project.scripts]` (5 entries, no build), `code_atlas/hooks/refresh.py:1-8`
(incremental-only, never builds), `code_atlas/tools/build_or_update_index.py:101,177,196,213` (lock,
schema mismatch, report shaping) and `scripts/gate.sh:70-107` (entry-point check derived from
`[project.scripts]`) all resolve as described.

**Recall:** `014 — code-atlas --help is not an install smoke test` (by area: console-script entry
points — **applied**, see AC5's test: it proves the declaration via `importlib.metadata` + a `.load()`,
never by invoking the binary); `derived-not-listed-invariant` (R6.7, by handle — the gate derives the
entry-point set from `pyproject.toml`, so a new script needs no second list; traced in Phase 2).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a build must be reachable from a shell / CI, without an MCP client | one console script that builds | `pyproject.toml` has no build entry | open |
| R1 | Scope 1 | `--full` reachable from a shell + a first build when no index exists | flag or new script; record which and why | `refresh.py:1-8` | open |
| R2 | Scope 2 | exit codes + one-line stderr usable from CI: success · nothing-to-do · busy · failure | four distinct codes, one stderr line each | new CLI | open |
| R3 | Scope 3 | goes through `build_or_update_index` — one lock, one report shape | reuse `create(config)`, add no second path | `build_or_update_index.py:67-74` | open |
| AC1 | AC 1 | full build from a shell, no index, same rows as the MCP route — pinned | Falsifiable: two identical trees, `store.counts()` equal | proving test | open |
| AC2 | AC 2 | the hook path still never builds without an index (053) — pinned | Falsifiable: refresh on an index-less repo writes no db | proving test | open |
| AC3 | AC 3 | four exit codes each pinned | Falsifiable: one test per code | proving test | open |
| AC4 | AC 4 | build goes through the tool; no second lock, no second report shape | Falsifiable: the CLI never imports `indexer` | source + AC1's row equality | open |
| AC5 | AC 5 | `gate.sh`'s entry-point check covers the new script | Falsifiable: declared set == installed set, and it loads | proving test | open |
| AC6 | AC 6 | determinism (R4.2), no language branch (R1.1), no contract bump (R3) | Falsifiable: grep-gate + no `contract.py` edit | grep-gates | open |
| C1 | Constraint | R4.3 — one mutex shared with the server; a busy peer is a clean skip | the CLI takes no lock of its own | `build_or_update_index.py:68` | binding |
| C2 | Constraint | 053's safety property — the hook path keeps *never builds without an index* | `--full` must be opt-in **per invocation** | `refresh.py:1-8` | binding |
| C3 | Constraint | R6.5 — the gate's entry-point check must cover the new script | declared ⊆ installed, and it imports | `scripts/gate.sh:78-99` | binding |
| C4 | Constraint | determinism — the CLI adds no second code path for the build itself | one call into `create(config)` | — | binding |

### Root cause (taxonomy: config / surface)

Not a defect in the build — a **missing surface**. `build_or_update_index` already does everything
(full, first, incremental, lock, refusal); the three shell entry points that exist are hooks, and a hook
is deliberately the wrong shape for CI: `refresh` never builds without an index and always exits 0, so
it can neither perform the first build nor tell a CI job that a build failed.

### Blast radius

- `pyproject.toml` `[project.scripts]` — one added row; `scripts/gate.sh` and `ci.yml` derive their
  check from it and need no edit (R6.7).
- `code_atlas/cli.py` is a **new** module in the core, so the two `core_modules()` guard-the-guard
  counts (`test_sql_confinement.py:32`, `test_core_is_language_agnostic.py:42`) move 72 → 73. Both
  guards then run over the new module too — the R1.1 and SQL-confinement gates now cover it.
- No change to `build_or_update_index`, `indexer`, `store`, the contract, or any hook.

## Phase 2 — design

### Approach

A **new** `code-atlas-build` console script → `code_atlas/cli.py::main`. It resolves the project root
exactly as `refresh` does (`CLAUDE_PROJECT_DIR` or cwd), calls
`build_or_update_index.create(load_config(root))(full=…)` — the MCP route's own callable — and does one
further thing only: maps that payload onto an exit code and one stderr line.

`--full` forces a full build; with no flag the tool's existing fallback covers the first build (no
`last_commit` ⇒ `full_build`), so "first build from a shell" needs no new logic. Exit codes:
`0` built · `3` nothing to do (`wrote.files == 0`) · `4` busy peer (`mode: busy`) · `1` failed
(`mode: refused`, or any exception).

### Rejected alternatives

- **`code-atlas-refresh --full`** (the ticket's first option). Rejected: `refresh`'s contract is *always
  exit 0, never build without an index* (`refresh.py:1-8`) — a git hook must never fail a git command.
  CI needs the exact opposite on both axes. One entry point carrying two opposite exit-code contracts
  behind a flag is how 053's safety property gets lost by accident later; two entry points keep each
  contract stateable in one sentence. C2 is then structural, not a convention.
- **A CLI that calls `indexer.full_build` directly.** Rejected by Scope 3 / AC4 and R4.3: it would need
  its own lock and its own report shaping, and the two paths would drift.
- **A general `code-atlas <verb>` CLI surface.** Out of scope, and R7.4/R1.2 — one verb has one script.

### Assumptions

| Assumption | Tag |
|---|---|
| `build_or_update_index(full=False)` already falls back to a full build with no index | verified (`build_or_update_index.py:177-186`, `_run`: `last is None` ⇒ `full_build`) |
| A busy peer returns `mode: "busy"` rather than raising | verified (`:68-70`; `test_git_refresh_hook.py:109`) |
| An unusable adapter returns `mode: "refused"` rather than raising | verified (`_adapter_refused`, `:77-101`; empirically exit 1) |
| A non-git tree cannot reach the incremental path | verified — `_run` needs `head_commit`; the AC3 test therefore inits a real git repo |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `code-atlas-build` console script | `pyproject.toml` | gate.sh + ci.yml derive from it | R1, AC5 | 1/1 |
| The CLI: payload → exit code + one stderr line | `code_atlas/cli.py` (new) | new module; no existing caller | R1, R2, R3, AC1–AC4 | 1/1 |
| Proving tests (6) | `tests/test_build_cli.py` (new) | new file | AC1, AC2, AC3, AC5 | 1/1 |
| `core_modules()` guard counts 72 → 73 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` | the two guards now cover `cli.py` | AC6 | 1/1 |
| README *Build from a shell*; CONVENTION layout row | `README.md`, `docs/CONVENTION.md` | R7.2/R7.6 | R7.2 | 1/1 |
| BACKLOG status + token ledger row | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | R7.2 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** The gate derives the entry-point set rather than
  listing it, so adding a script needs no second list; only the editable install has to be refreshed.

  ```
  $ grep -n 'declared = set(tomllib' scripts/gate.sh          # Ran at 9423240
  81:declared = set(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["scripts"])
  ```

- `014 — code-atlas --help is not an install smoke test` — **traced.** AC5's test proves the
  declaration through `importlib.metadata` + `.load()`, never by invoking the binary (which for the
  server entry would hang on stdin).

  ```
  $ .venv/bin/python -c "import importlib.metadata as md; print(sorted({e.name for e in md.entry_points(group='console_scripts') if e.dist and e.dist.name=='code-atlas'}))"
  ['code-atlas', 'code-atlas-build', 'code-atlas-llm', 'code-atlas-poke', 'code-atlas-refresh', 'code-atlas-signal']
  # Ran at 9423240 (working tree, after `uv pip install -e . --no-deps`)
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a real subprocess, a real index, two trees) | integration test | ✅ |
| AC2 | integration (the hook binary on an index-less repo) | integration test | ✅ |
| AC3 | integration (four real process exits, incl. a held `flock`) | integration test | ✅ |
| AC4 | logic (no second lock / report shape) | source + AC1's row equality | ✅ |
| AC5 | integration (installed metadata + `.load()`) | integration test | ✅ |
| AC6 | guard (grep-gates) + logic (deterministic) | the two `core_modules()` guards | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_build_cli.py::test_full_build_from_shell_with_no_index_matches_mcp_route` — plus the three
exit-code tests. `pytest tests/test_build_cli.py`. Red pre-fix by construction (no `code_atlas.cli`).

### Rollback + porting

Rollback: revert `code_atlas/cli.py`, the `pyproject.toml` row, the new test file and the two count
bumps, then `uv pip install -e . --no-deps`. Porting: `app` only.

### SCOPE

`SCOPE: M` — one new module + one declaration + tests + bookkeeping; branch `feat` matches (a new
capability, not a correctness fix).

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| New `code-atlas-build` script → `code_atlas/cli.py::main` | implemented-as-approved |
| Root resolution identical to `refresh` (`CLAUDE_PROJECT_DIR` or cwd) | implemented-as-approved |
| Calls `build_or_update_index.create(load_config(root))(full=…)`; no second lock/report | implemented-as-approved |
| `--full` opt-in per invocation; no flag ⇒ the tool's own first-build fallback | implemented-as-approved |
| Exit codes 0 / 3 / 4 / 1, one stderr line each | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

Red run — the proving test against the pre-fix tree (`code_atlas/cli.py` absent):

```
$ .venv/bin/pytest -q tests/test_build_cli.py            # Ran at 9423240
    from code_atlas import cli
E   ImportError: cannot import name 'cli' from 'code_atlas'
ERROR tests/test_build_cli.py — 1 error during collection
```

The four exit codes, driven end-to-end through the installed script:

```
$ code-atlas-build --full   →  code-atlas build: full: 1 file(s), 1 node(s), 0 edge(s)   exit=0
$ code-atlas-build          →  code-atlas build: incremental: 0 file(s), …               exit=3
$ code-atlas-build --full   →  code-atlas build: skipped: another build is running       exit=4   (peer holds write.lock)
$ code-atlas-build --full   →  code-atlas build: refused: no_usable_adapter (…)          exit=1   (no CA_<LANG>_CMD)
# Ran at 9d13d393010ab714d6b6e56beaacfeb0da69ad8d
```

Green run:

```
$ .venv/bin/pytest -q                                    # Ran at 9d13d393010ab714d6b6e56beaacfeb0da69ad8d
__SUITE__
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 82 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_full_build_from_shell_with_no_index_matches_mcp_route` (rows equal to the MCP route) |
| AC2 | `test_refresh_hook_still_never_builds_without_an_index` (both with and without `--full`) |
| AC3 | `test_nothing_to_do_is_its_own_exit_code`, `test_busy_peer_is_its_own_exit_code`, `test_failure_is_its_own_exit_code`, and AC1's `exit 0` |
| AC4 | the CLI imports only `build_or_update_index`; AC1's row equality; no second lock |
| AC5 | `test_build_cli_is_a_declared_entry_point` (declared == installed, and it loads) |
| AC6 | both `core_modules()` guards now include `cli.py`; no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** baseline `2166 passed / 0 failed` → after
`__SUITE__`. ruff + mypy green. The suite runs natively here; the AGENTS.md
"use Docker" note is a Windows-host platform exclusion and does not apply to this machine.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`176-C1` (type-2, `a-test-must-strip-the-ambient-adapter-env`, seen: 176) recorded as `proposed`.
A negative-control test that only removes *its own* fixture env inherits the gate's `CA_PHP_CMD` and
silently becomes a positive control — green in isolation, red under `gate.sh`. Falsified? No: observed
directly in this run (the failure test passed alone and failed under the gate's environment). seen=1 →
stays in `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: red→green proving test, full suite delta-green, ruff/mypy green.
