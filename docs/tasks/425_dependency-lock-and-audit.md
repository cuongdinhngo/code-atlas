---
id: 425
slug: dependency-lock-and-audit
title: "What CI tests is what installs — Python dependencies locked with hashes, the MCP SDK floor above every advisory, and every ecosystem audited in CI and the gate"
phase: 2
milestone: Trust
status: done
depends_on: [423]
---

## Why this exists

`pyproject.toml` asks for `fastmcp>=3,<4`; there is no lock file, so CI, the images and a user's
install each resolve their own tree. Published FastMCP advisories sit inside that range (fixed in
3.2.0 and 3.4.10). Dev tools (`ruff`, `mypy`, `pytest`) are unpinned, and no step audits the Python,
npm or composer dependencies.

## Acceptance

1. **Floor:** `fastmcp>=3.4.10,<4`; the standard's SEC-MCP-09 row names the advisories it clears.
2. **Lock:** a `uv.lock` (hashes included) committed; CI and both Docker images install from it
   (`uv sync --frozen` or an exported hashed requirements file); dev tools pinned in the same lock.
   The npm adapters already lock (`package-lock.json`) and install with `npm ci`; composer installs
   from `composer.lock` — a test asserts each install line uses the lock.
3. **Audit:** `pip-audit` on the lock, `npm audit --omit=dev` for both adapters and
   `composer audit` run in CI and in `scripts/gate.sh`, failing at the threshold written in the
   standard (any known vulnerability with a fix available).
4. **Seen failing:** the audit step goes red on a seeded vulnerable pin (R6.5), recorded in the
   resolution.
5. The upgrade path a user follows (`uv tool install …@vX.Y.Z`) is unchanged; the CHANGELOG says
   the floor moved.

## Call sites

`pyproject.toml`, new `uv.lock`, `.github/workflows/ci.yml`, `scripts/gate.sh`,
`docker/Dockerfile`, `docker/Dockerfile.runtime`, `tests/test_ci_and_gate_agree.py`;
standard rows SEC-SC-06, 07, SEC-MCP-09.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 425 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W2 and merges after #125.
- `TRACK: backend` · Run mode: `autorun 427 - 430 - 424 - 425 - 428 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/425-dependency-lock-and-audit`, **stacked on `feat/424-ci-hardening`** (#125).
  Contract `.mango/run-contract-425.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 2 want-decision asked | 6 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `pyproject.toml` (`fastmcp>=3,<4`, `dev = ["pytest", "ruff", "mypy"]`), `.github/workflows/ci.yml`
(`pip install .` :40-41, `pip install -e ".[dev]"` :75, `pip install ruff mypy` for the Python adapter's analyser),
`scripts/gate.sh`, `docker/Dockerfile` (`pip install -e ".[dev]"` :36), `docker/Dockerfile.runtime`,
`tests/test_ci_and_gate_agree.py` resolve; `uv.lock` is to be created. The npm adapters install with `npm ci` and
composer from `composer.lock` already. Advisories, read 2026-10-31 (`gh api /advisories`): FastMCP
GHSA-7xgj-8392-5q4r (fixed 3.4.10), CVE-2026-32871 / GHSA-vv7q-7jx5-f767, CVE-2026-27124 / GHSA-rww4-4w9c-7733,
CVE-2025-64340 / GHSA-m8x7-r2rg-vh5g (fixed 3.2.0); the MCP Python SDK (FastMCP's base) GHSA-w4fh-qvv9-3v23,
GHSA-5h93-6whr-6q8j, GHSA-rwrf-2pqf-9j8j, GHSA-84m7-p3x7-pcfv (fixed 1.30.0), GHSA-vj7q-gjh5-988w (1.28.1),
GHSA-jpw9-pfvf-9f58, GHSA-hvrp-rf83-w775 (1.27.2). Installed here: fastmcp 3.4.11, mcp 1.30.0.
Recall (type 2, by handle): 427-C1 `a-loader-guard-misses-the-entry-that-loads-nothing` (enumerate every install
line, not the ones named); 424-C1 `a-subset-reader-must-fail-closed` (the install-line test refuses a line it
cannot classify).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | what a user's install resolves | how | `uv tool install git+…@vX.Y.Z` and pipx ignore `uv.lock`, so the floors in `pyproject.toml` are what a user gets: `fastmcp>=3.4.10,<4` **and** `mcp>=1.30.0` (the SDK floor SEC-MCP-09 names) |
| H2 | how CI and the images install from the lock | how | `uv sync --frozen` (the `dev` group / extra) in CI and the test image; the runtime image installs `--no-dev` from the same lock |
| H3 | dev tools pinned | how | `pytest`, `ruff`, `mypy` resolve in the same lock; the Python adapter's analyser step installs from it too, not `pip install ruff mypy` |
| H4 | the audit tools | how | `pip-audit` (on an exported, hashed requirements file of the lock), `npm audit --omit=dev` per adapter, `composer audit`; each in `ci.yml` and `gate.sh` (parity) |
| H5 | "fails at the threshold" | how | any known vulnerability with a fix available fails; the threshold is written in SEC-SC-06/07 |
| H6 | the install-line test | how | reads every install line in `ci.yml`, `gate.sh` and both Dockerfiles; a `pip install` / `npm install` / `composer install` without the lock form fails |
| W1 | `pip-audit` is a dev dependency | want | **ASSUMED (awaiting ratification):** it joins the `dev` lock group, pinned like the others, rather than a one-off `pipx run` in CI |
| W2 | the audit's network need in the gate | want | **ASSUMED (awaiting ratification):** the gate runs the audits (they query advisory databases); offline, the gate reports the audit step SKIP (exit 2, not a pass), the existing rule for a check that cannot run |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=5`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W2 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "What CI tests is what installs" | one hashed lock for CI and both images; floors above every advisory | ⚠ |
| AC1 | Acc 1 | "`fastmcp>=3.4.10,<4`; the standard's SEC-MCP-09 row names the advisories it clears" | H1; SEC-MCP-09 lists the GHSA ids above | ⚠ |
| AC2 | Acc 2 | "a `uv.lock` (hashes included) committed; CI and both Docker images install from it … a test asserts each install line uses the lock" | H2, H3, H6 | ⚠ |
| AC3 | Acc 3 | "`pip-audit` … `npm audit --omit=dev` … `composer audit` run in CI and in `scripts/gate.sh`" | H4, H5, W1, W2 | ⚠ |
| AC4 | Acc 4 | "the audit step goes red on a seeded vulnerable pin" | a temporary lock pinning `fastmcp==3.1.0`: `pip-audit` red, recorded | ⚠ |
| AC5 | Acc 5 | "the upgrade path … is unchanged; the CHANGELOG says the floor moved" | CHANGELOG *Unreleased*; 427's tagged install untouched | ⚠ |
| C1 | Call sites | "standard rows SEC-SC-06, 07, SEC-MCP-09" | each closes on its guard | ⚠ |

`BASELINE: green — Docker on feat/424-ci-hardening at d4d95c73 (5413 passed, 8 skipped; its one failure fixed test-only in 83a530de)`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.4: the audits fail the build; R6.5: seen red on a seeded pin · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §8 (change-type) ✅ R8.2: no runtime dependency added beyond the SDK floor; R8.3: the lock is committed and installed from · §9 (change-type) ✅ R9.6: each closed MUST names a test or CI step · §5 (change-type) ✅ R5.3: an audit finding fails loud`

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 427-C1: the install-line test greps every `pip`/`uv`/`npm`/`composer` invocation in `ci.yml`, every workflow,
  `gate.sh` and both Dockerfiles — not a named list of steps.
- 424-C1: an install line the test cannot classify fails ("unclassified install line"), never passes.

**Approach.**
1. `pyproject.toml`: `fastmcp>=3.4.10,<4`, `mcp>=1.30.0`; dev tools and `pip-audit` resolved in the lock.
2. `uv lock` → committed `uv.lock`; CI installs with `uv sync --frozen` (pinned `astral-sh/setup-uv` by SHA, per 424);
   the test image and the runtime image install from the lock (runtime `--no-dev`).
3. Audits: `uv export --frozen --format requirements-txt` (hashed) → `pip-audit --strict -r`; `npm audit --omit=dev`
   in both adapters; `composer audit` in the PHP adapter — one CI job and one `gate.sh` step each (parity).
4. `tests/test_dependency_lock.py`: the floors clear the advisories named in SEC-MCP-09 (read from the row);
   `uv.lock` exists, carries hashes and agrees with `pyproject.toml` (`uv lock --check`); every install line uses a lock.
5. Seeded pin (AC4) run once and recorded in the working doc.
6. Docs: SEC-SC-06, SEC-SC-07, SEC-MCP-09 rows; SECURITY.md supply-chain line; CHANGELOG; README dev setup.

**Rejected:** an exported `requirements.txt` committed beside the lock (two files to keep in step, R6.7); `pipx run
pip-audit` in CI (an unpinned tool at audit time).

**Change list:** `pyproject.toml`, `uv.lock` (new), `.github/workflows/ci.yml`, `scripts/gate.sh`, `docker/Dockerfile`,
`docker/Dockerfile.runtime`, `tests/test_ci_and_gate_agree.py`, new `tests/test_dependency_lock.py`,
`docs/SECURITY_STANDARD.md`, `SECURITY.md`, `README.md`, `CHANGELOG.md`; bookkeeping.

**Proving tests:** `tests/test_dependency_lock.py`; the audit seen red on a seeded `fastmcp==3.1.0`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

`implementer` landed Approach 1–6 in `f58d4899`…`8007aa6f`. **Verification sweep.** File axis: the change list plus
recorded deviations — `cross-repo.yml` and `tokens-to-answer-sample.yml` (they ran `pip install .`, caught by the
install-line sweep), `CONTRIBUTING.md` (dev setup). Behaviour axis as approved: the `dev` extra kept (every `.[dev]`
doc line still works) with `pip-audit` in it; `astral-sh/setup-uv` pinned by SHA (`v10.3.0`, uv `0.11.28`) replaces
`setup-python`; the install check stays non-editable (`uv sync --frozen --no-editable` into a temp env); `composer
audit` reads its abandoned-package policy from `COMPOSER_AUDIT_ABANDONED=report` (Composer 2.7.1 has no flag) —
vulnerabilities still fail. Audits on the real lock: pip-audit, both `npm audit --omit=dev` and `composer audit`
report nothing.

**Seen failing (R6.5), AC4.** In a temporary worktree pinning `fastmcp==3.1.0`, re-locked and exported:

```
# execute-time record (a seeded worktree by design, not the tree under review)
$ pip-audit --strict --require-hashes --disable-pip -r req.txt
Found 5 known vulnerabilities in 1 package
fastmcp 3.1.0   PYSEC-2026-2475     3.2.0
fastmcp 3.1.0   PYSEC-2026-2476     3.2.0
fastmcp 3.1.0   GHSA-7xgj-8392-5q4r 3.4.10,4.1.2
exit=1
```

A seeded `lodash@4.17.15` in `adapters/sql` failed `npm audit --omit=dev` (1 high, exit 1); the floor test went red
in that worktree too.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 79,444 tokens): 6 met · 2 partly met · 1 can't tell (AC4's record lives
  here, below the line it may not read). Taken in `57faf512` and `c898efe4`:
  - **Important** — the install sweep missed `npx`, a bare `uv run`, lock-bypassing flags and every file outside
    the four it named: it now globs `.github/**`, `scripts/*.sh` and `docker/*`, joins `\` continuations, and
    allows `npx` / `uv run` only in their pinned or frozen forms — nine planted failures, six planted passes.
  - Minor, taken: SEC-SC-06 names the two exact-version installs without a hash (the `uv` installer in the
    images, the CLI under test); SEC-SC-07's threshold is held by the commands (`--strict`, no ignore flags), not
    only by the row's words; CONTRIBUTING notes a stale venv SKIPs the audit; `mcp>=1.30.0,<2`.
  - Minor, accepted: the `audit` job is not a required check (a ruleset change, the maintainer's); the audit runs
    on push and PR, not on a schedule.
- **Round 2: verify-only, main loop.**

Verdict: clean (challenger only — REVIEWER: OFF), W1–W2 standing for ratification.
`Ph3/4 proven by` (`tests/test_dependency_lock.py`): AC1 → `test_the_floors_clear_every_advisory_sec_mcp_09_names`;
AC2 → `test_uv_lock_is_committed_and_every_package_has_a_hash`, `test_the_lock_agrees_with_pyproject`,
`test_every_install_line_in_the_repo_goes_through_a_lock`; AC3 →
`test_the_audit_threshold_is_written_in_the_standard_and_held_by_the_commands` + `test_ci_and_gate_agree`'s four
audit rows; AC4 → the record above; AC5 → CHANGELOG *Unreleased*; C1 → `tests/test_security_standard.py`.

Reviewed at c898efe4.

## Phase 5 — finalise

**Durable lesson.** None new: the review's one Important finding — an install sweep over a named file list that
missed the files and forms it did not name — is 427-C1's class (enumerate every entry, not the ones a list names)
and 424-C1's (a line the sweep cannot classify fails). Both bump `seen` (P1).

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 2 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 2 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

**The final gate:** the suite in Docker on the final tree, and the fast gate (audits included) on the host.

Ran at 42fa2351

```
$ scripts/docker-test.sh
5474 passed, 8 skipped in 664.70s (0:11:04)
$ PATH=.venv/bin:$PATH scripts/gate.sh --fast
  20 passed · 0 failed · 2 skipped
```

`42fa2351` adds only the bookkeeping and `PYSEC` to the tracker-key guard's standard prefixes (the AC4 record quotes
pip-audit's PyPA ids) on top of the reviewed `c898efe4`.

### Outward actions

Under the handover: push `feat/425-dependency-lock-and-audit`; open its PR against `feat/424-ci-hardening`.
Deferred to the maintainer: ratify W1–W2; merge after #125; optionally make `audit` a required check.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 3 execute | `implementer` | 1 | 122,695 |
| 4 review | ticket-blind `challenger` | 1 | 79,444 |
| 4 review | `implementer` (review fixes, resumed) | 2 | 133,033 |

`LEDGER TOTAL: 335,172 · top cost driver: 4 review / implementer` — main loop unmeasured.
