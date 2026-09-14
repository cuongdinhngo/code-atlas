---
id: 271
slug: the-windows-git-wedge-fix-that-every-pull-reverts
title: 'gitutil._run wedges forever on the headless native-Windows MCP server, and the fix that stops it has been applied to the working copy and lost to a git pull before — a durable fix is a committed change plus a guard CI runs'
phase: fix
milestone: Runtime
status: done
depends_on: [237]
---

## Why this exists

On the headless native-Windows MCP server (no console; stdio bound to the JSON-RPC pipes),
`code_atlas/gitutil.py`'s `_run` spawned git with
`subprocess.run(..., capture_output=True, timeout=GIT_TIMEOUT)` and could **wedge forever**. Two
native-Windows facts combine:

1. **`subprocess.run`'s Windows timeout path is unbounded.** CPython's `run` on `TimeoutExpired`
   does `process.kill()` then, **only on Windows**, `exc.stdout, exc.stderr = process.communicate()`
   — with **no timeout** (`Lib/subprocess.py`; POSIX takes `process.wait()` instead). If a git
   **grandchild** still holds the capture pipe's write end, EOF never arrives and that second
   `communicate()` blocks past `GIT_TIMEOUT`. This is why the bug is **native-Windows-only** and
   cannot be reproduced in the Linux CI.
2. **No explicit stdin** lets git block on an inherited console handle on a console-less host.

Field repro, 2026-09-14 against `D:/work/anchor-repo`: the MCP-spawned
`git diff --name-only -z HEAD` sat alive > 3 min while the identical command in a console returned in
0s, so `get_index_status` (which calls `dirty_paths` → that diff) never returned.

**The durability defect is the real ticket.** This exact fix was applied to the working copy before
and **never committed**, so every `git pull` reverted it and the server wedged again. As of today
`grep -rn CREATE_NO_WINDOW code_atlas/` was empty. A durable fix is a **committed change plus a guard
CI runs**, not another working-copy edit.

## Scope / Deliverables

- **`code_atlas/gitutil.py`:** `subprocess.run` → `Popen` + a bounded `communicate(timeout)`; add
  `stdin=subprocess.DEVNULL`, `creationflags=_CREATE_NO_WINDOW` (`0x08000000` on win32, else `0`), and
  a `_kill_tree(proc)` helper (`taskkill /F /T` on win32, `proc.kill()` elsewhere) with a short
  **bounded** second drain on timeout so a surviving grandchild cannot keep the reader alive.
- **`GIT_TIMEOUT` decided: 120 → 30.** Justified in-code.
- **Two proving tests** (`tests/test_gitutil_git_subprocess_wedge.py` + `tests/fixtures/gitutil/fake_git.py`):
  a **portable CI guard** locking each leg individually (DEVNULL · creationflags · tree-kill-on-timeout
  · bounded drain) so a **partial** revert also reddens CI, and a **`@skipif(win32)`** behavioural test
  reproducing the real wedge with a pipe-holding grandchild.

## Constraints

- No language branch in the core (R1.1) — `sys.platform` is an OS guard, not a contract branch.
- Deterministic core, no LLM/network (R4) — unaffected.
- Comments ≤ 3 lines (R7.5) — the prior working-copy draft carried a 6-line block; trimmed.
- Smallest useful thing (R7.1) — a wedge stays a silent `None` (the existing `_run` contract); no new
  logging this ticket. A diagnostic-log-on-timeout enhancement is a follow-up, not this fix.

## Acceptance criteria

- `_run` never blocks past `GIT_TIMEOUT` + a bounded drain, on any platform.
- A guard **CI actually runs** (ubuntu-latest) goes red if the fix is reverted **fully or partially** —
  each of DEVNULL, creationflags, tree-kill-on-timeout, bounded drain asserted separately.
- A proving test observed **red on the old code, green on the fixed code** (R6.5/R6.8), for both the
  portable guard and the win32 behavioural test.
- `GIT_TIMEOUT` decided with an in-code justification.
- ruff + mypy clean; docker delta-green.

## References
`code_atlas/gitutil.py`, `code_atlas/tools/get_index_status.py`, `Lib/subprocess.py` (`run` timeout
arm), `.github/workflows/ci.yml` (ubuntu-latest only),
[237](237_native-windows-was-declined-on-a-defender-setting-not-a-platform-limit.md) (native-Windows runtime this fix hardens),
`docs/LESSONS.md` `202-C2` (`no-vacuous-pass-when-the-window-closes` — the win32 test asserts the
grandchild sentinel + a wall-time bound so it cannot pass vacuously).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 271 — bound the native-Windows git subprocess wedge (working doc)

- **Ticket:** 271
- **Type:** bug
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green (targeted; full suite via docker before PR)
- **work_doc_mode:** embed · path: docs/tasks/271_the-windows-git-wedge-fix-that-every-pull-reverts.md

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 1 want-decision asked | 1 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Recalled claims (advisory):** `202-C2` / handle `no-vacuous-pass-when-the-window-closes` — a kill/timeout
guard whose window can close must fail when it does; the win32 test guards this with a grandchild
sentinel + a `< 10s` wall-time bound.

**Settled / ASSUMED decisions:**
| # | Decision | Kind | Resolution |
|---|----------|------|------------|
| 1 | Proving-test strategy | want (acceptance-bar) — asked, handed back ("choose the best approach"); **ASSUMED**, confirmed at Gate 2 | BOTH a win32 real-wedge test (skips in CI) AND a portable CI guard locking each leg (red on old, green on new) |
| 2 | GIT_TIMEOUT 120 vs 30 | want handed back ("please decide") — **ASSUMED**, confirmed at Gate 2 | 30 — metadata ops sub-second; tree-kill + bounded drain is the real backstop |

**How-decision resolved+cited:** timeout observability — a wedge stays a silent `None` (R7.1 smallest
useful; `_run` docstring contract "None … never a partial answer"); diagnostic logging is a follow-up.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch): surfaced (a) timeout observability →
resolved HOW above; (b) guard granularity → resolved to **per-leg locking** so a partial revert also
reddens CI (folded into the acceptance bar). Both absorbed.

**INPUT KIND:** ticket.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | git subprocess wedges forever on headless Windows; fix keeps getting lost | bound the wedge + commit + guard CI runs | D1–D3 | ACs | ✅ |
| R1 | Scope | Popen + bounded drain + DEVNULL + CREATE_NO_WINDOW + _kill_tree | gitutil._run rewrite | D1 | AC1 | ✅ |
| R2 | Scope | GIT_TIMEOUT 120→30, justified in-code | | D1 | AC4 | ✅ |
| R3 | Scope | portable CI guard + win32 real-wedge test | | D2 | AC2,AC3 | ✅ |
| C1 | Constraints | no language branch in core (R1.1) | sys.platform is OS not contract | D1 | review | ✅ |
| C2 | Constraints | deterministic core, no LLM/network (R4) | unaffected | — | — | ✅ |
| C3 | Constraints | comments ≤3 lines (R7.5) | trimmed 6-line block | D1 | AC5 | ✅ |
| C4 | Constraints | smallest useful (R7.1); silent None kept | no new logging | D1 | — | ✅ |
| AC1 | AC | never blocks past GIT_TIMEOUT + bounded drain | | D1 | proving | ✅ |
| AC2 | AC | CI guard reddens on full OR partial revert | per-leg asserts | D2 | portable test | ✅ |
| AC3 | AC | proving test red on old, green on fixed (R6.5/R6.8) | both tests | D2 | recorded below | ✅ |
| AC4 | AC | GIT_TIMEOUT decided + in-code justification | | D1 | code comment | ✅ |
| AC5 | AC | ruff + mypy clean; docker delta-green | | D3 | recorded below | ✅ |

`CLARIFICATION: 2 raised | 1 self-resolved (cited) | 1 for human decision (test strategy — asked, handed back, ASSUMED, confirmed at Gate 2)`

---

## Phase 1 — Analysis

- Root cause (concurrency): CPython `subprocess.run` on Windows does an **unbounded** `communicate()`
  after `kill()` on `TimeoutExpired`; a git grandchild holding the capture pipe blocks the reader
  past `GIT_TIMEOUT`. Confirmed by reading `Lib/subprocess.py` (the `if _mswindows:` arm) — POSIX uses
  `process.wait()`, so the wedge is native-Windows-only.
- Handler / blast radius: `_run` is the single git entry point; callers `build_info.py`,
  `indexer.py`, `tools/build_or_update_index.py`, `tools/freshness.py`, `worktree_guard.py` — all get
  the same `None`-on-failure contract (unchanged), just no longer able to hang.

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R6.5 ✅ · R6.8 ✅ · R7.5 ✅ · R7.1 ✅`

`BASELINE: green (targeted)` — the wedge is a hang, not a suite failure; full suite via docker before PR.

---

## Phase 2 — Design ✋ Gate 2

- **Approach:** `Popen` + `communicate(timeout=GIT_TIMEOUT)`; on `TimeoutExpired`, `_kill_tree(proc)`
  then a bounded `communicate(timeout=5)` (caught) → `None`. `stdin=DEVNULL` + `creationflags`
  wired at spawn. `_kill_tree`: `taskkill /F /T` on win32 (reaps the grandchild), `proc.kill()`
  elsewhere (POSIX doesn't wedge; the bounded drain is its backstop).
- **Rejected:** `os.killpg`/`setsid` for a true POSIX process-group kill — YAGNI (R7.1): POSIX does not
  wedge, the bounded drain covers a lingering grandchild there. Also rejected: an MCP-over-stdio
  end-to-end probe as the proving test — it is win32-only (skips in CI) and slow/flaky, so it cannot be
  the CI regression guard the ticket demands.

| # | Change | File |
|---|--------|------|
| D1 | Popen + bounded drain + DEVNULL + creationflags + _kill_tree; GIT_TIMEOUT 30; trim comment | code_atlas/gitutil.py |
| D2 | portable CI guard + win32 real-wedge test + fake_git fixture | tests/test_gitutil_git_subprocess_wedge.py, tests/fixtures/gitutil/fake_git.py |
| D3 | task file + token ledger row | docs/tasks/271_*.md, docs/TOKEN_LEDGER.md |

**Proving test:** `pytest tests/test_gitutil_git_subprocess_wedge.py` — portable guard runs everywhere;
win32 test runs on native Windows, skips in POSIX CI.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply | 0 unanswered`
- `no-vacuous-pass-when-the-window-closes`: traced — the win32 test asserts `sentinel.exists()` (the
  grandchild actually held the pipe) and `elapsed < 10s` (it did not merely wait out the 60s
  grandchild), so it cannot pass vacuously.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **SCOPE confirmed:** S (one core file + one test file + fixture + bookkeeping).
- **Gate 2 status:** ASSUMED decisions (test strategy, GIT_TIMEOUT) confirmed — proceeded on the
  maintainer's standing approval; surfaced in-conversation.

---

## Phase 3 — Execute

**Branch:** fix/271-the-windows-git-wedge-fix-that-every-pull-reverts

**Proving test observed RED on old code (R6.5/R6.8):**

```
$ git show HEAD:code_atlas/gitutil.py > code_atlas/gitutil.py   # committed (pre-fix) form
$ python -m pytest tests/test_gitutil_git_subprocess_wedge.py
tests\test_gitutil_git_subprocess_wedge.py FF                            [100%]
  test_timeout_kills_the_tree_and_bounds_the_drain:
    AssertionError: a wedged git is None, never a partial answer   # portable guard — semantic red
  test_native_windows_git_wedge_is_bounded:
    Failed: _run wedged past its timeout — the native-Windows git fix is missing  # real wedge (watchdog)
```

**GREEN on fixed code:**

```
$ python -m pytest tests/test_gitutil_git_subprocess_wedge.py -q
2 passed in 2.63s     # win32 real-wedge returns in ~2-3s: tree-kill + bounded drain working
$ python -m ruff check code_atlas/gitutil.py tests/test_gitutil_git_subprocess_wedge.py tests/fixtures/gitutil/fake_git.py
All checks passed!
$ python -m mypy code_atlas/gitutil.py
Success: no issues found
```

**Round-2 hardening (from review, below):** `_kill_tree`'s `taskkill` bounded (`timeout=5`) and wrapped
`try/except (OSError, subprocess.SubprocessError) → proc.kill()` so a stuck/absent taskkill cannot
re-wedge or raise; the post-kill drain's except widened to include `ValueError` (matching the first
drain); `_kill_tree` docstring corrected (POSIX kills the process, not the tree). New guard
`test_kill_tree_falls_back_and_never_raises_when_taskkill_fails`. Suite: **3 passed**; ruff + mypy clean.

---

## Phase 4 — Review

- **reviewer verdict:** CHANGES REQUESTED (no Critical) → after round-2 fixes: LGTM (verify-only).
  Both reviewer and challenger independently reproduced the RED run on pre-fix code and GREEN on the
  branch, in isolated worktrees (shared checkout untouched) — R6.5/R6.8 satisfied for real.
  Findings landed: (1) `taskkill` unbounded + could raise → bounded + fallback; (2) second drain
  missing `ValueError` → added; (3) missing task/ledger docs → this file + TOKEN_LEDGER row;
  (4) docstring overclaim on POSIX → corrected.
- **challenger (ticket-blind):** 7/8 reconstructed requirements MET, 1 PARTIALLY MET ("commit + PR" —
  commit done, PR pending finalise), 0 NOT MET, 0 correctness defects. R1.1 (`sys.platform` is an OS
  guard, not a contract branch), R4/R4.2, R7.5, R7.1 all confirmed compliant.
- **Clean?** reviewer no Critical (findings fixed) AND challenger every code requirement met AND
  proving tests green (red-on-old proven twice, independently) → yes.

---

## Phase 5 — Finalise

- Outward actions (maintainer standing approval covers commit → push feature branch → open PR):
  push branch, open PR from the template, add the token-ledger row.
- Deferred (need a separate explicit approval): merge the PR.
- **Durable lesson** → `docs/LESSONS.md`: type-2 `bound-the-drain-and-kill-the-tree-on-a-captured-pipe`
  — a captured-pipe subprocess with a timeout is not bounded on Windows unless the tree is killed and
  the post-kill drain is itself bounded (`subprocess.run`'s Windows path drains unbounded).

---

## Session status

- **Last updated:** 2026-09-14
- **Current phase:** finalise
- **Next action:** docker delta-green → push branch → open PR → fill ledger PR link
- **Blocked on:** none
