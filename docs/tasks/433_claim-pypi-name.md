---
id: 433
slug: claim-pypi-name
title: "Claim `code-atlas` on PyPI — publish the signed release there through Trusted Publishing"
phase: 2
milestone: Release
status: done
depends_on: [427, 431]
---

## Why this exists

The exact name `code-atlas` is unclaimed on PyPI (JSON API 404, 2026-11-04); only look-alikes
(`code-atlas-mcp`, `codeatlas`) are taken. While it is free, anyone can publish `code-atlas`, and
`pip install code-atlas` / `uvx code-atlas` — the natural guess — would run a stranger's code. 427
defends with docs; owning the name removes the hazard at its source. Decision (maintainer,
2026-11-04): **keep the name and claim it** with a real release, not a placeholder (PEP 541 lets PyPI
reclaim an empty name-squat). 431's "Why this exists" wrongly says the name is taken.

The release is already most of the way there: `pyproject.toml` names `code-atlas`, and `release.yml`
builds the sdist and wheel from a verified signed tag and attests them. Only the PyPI upload is missing.

## Acceptance

1. `release.yml` gains a PyPI publish job using Trusted Publishing only (OIDC `id-token: write`, a
   `pypi` GitHub environment, no API token secret, action pinned by SHA), uploading the same files the
   `build` job produced, with PyPI attestations.
2. `SEC-SC-13` moves from `n/a` to a guard (a test that the publish job has no token input and runs in
   the `pypi` environment); 431's text and its C1 row stop claiming "no PyPI".
3. 427's install rule allows a **pinned** PyPI line (`code-atlas==X.Y.Z`); an unpinned bare
   `pip install code-atlas` stays forbidden. The README names the look-alikes and carries one sentence
   that distinguishes this project (deterministic, offline, no LLM in the core, SQLite only).
4. The next signed tag is on PyPI, owned by the maintainer: `pip index versions code-atlas` lists it and
   the PyPI JSON API returns 200.

## Maintainer switches (outside the repo — the agent cannot do these)

- pypi.org → *Publishing* → add a **pending publisher**: owner `cuongdinhngo`, repo `code-atlas`,
  workflow `release.yml`, environment `pypi`.
- GitHub → *Settings → Environments* → create `pypi` with a required reviewer.
- Sign and push the release tag (`docs/runbooks/releasing.md`); approve the `pypi` deployment.

## Out of scope

- Bundling and auto-wiring adapters in the wheel (brief B1, part 2): the wheel ships the core only, so
  docs must not imply `uvx code-atlas` indexes a repo with no `CA_<LANG>_CMD`. Needs its own ticket and
  a PLAN §19 entry.
- MCP registry listings (brief B2) — after the name is owned.

## Resolution

**Refused by PyPI, closed without publishing (2026-11-04).** Adding the pending publisher on pypi.org
failed: *"This project name is too similar to an existing project."* PyPI compares a new name with
separators removed and confusable letters folded, so `code-atlas` collides with `codeatlas`; the JSON
API's 404 only said no project exists under that spelling. Nobody else can register `code-atlas`
either, and `pip install code-atlas` cannot resolve to `codeatlas` (PEP 503 keeps them distinct), so the
typosquat hazard is closed by PyPI itself. Maintainer decision: drop PyPI; the attested GitHub Release
stays the only channel. The `pypi` job, its guard and the pinned-line lint were reverted; SEC-SC-13 stays
`n/a` with this reason, and 431 and the README say it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 433 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer's merge (re-scoped, see Resolution).
- `TRACK: backend` · Run mode: `autorun 433 --no-reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` ·
  `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `chore/433-claim-pypi-name` from `main` at `8c7f7a12`. Contract `.mango/run-contract-433.txt` (mango
  1.19.0, updated mid-run from 1.17.3 at the maintainer's request; `autorun` and its scripts are byte-identical).
  RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`.
- Budget: unknown — no per-call counts in `docs/TOKEN_LEDGER.md`.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 6 unresolved surfaced | 3 want-decision asked | 3 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `.github/workflows/release.yml`, `docs/tasks/431_release-pipeline.md`, `docs/tasks/427_distribution-pinning.md`,
`docs/runbooks/releasing.md`, `docs/SECURITY_STANDARD.md` (SEC-SC-13, SEC-GV-07) and `pyproject.toml` (`name = "code-atlas"`)
resolve. PyPI JSON API for `code-atlas`: 404 (2026-11-04).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | job shape | how | a third job `pypi` after `publish`, mirroring 431's split (`release.yml` `publish` has no checkout, so it runs no repo code): no checkout, `id-token: write` only, the `pypi` environment, `pypa/gh-action-pypi-publish` pinned by SHA (`tests/test_ci_hardening.py` pin arm), uploading only the wheel and sdist from the digest-checked artifact. PEP 740 attestations are the action's default under Trusted Publishing |
| H2 | the README line | how | the README keeps "not published on PyPI" until the first upload lands (AC4 runs after merge; `test_the_readme_names_the_look_alike_packages` holds that sentence); the runbook names the flip as the step after the first upload |
| H3 | 427's lint | how | `BY_NAME` in `tests/test_distribution_pinning.py` passes `code-atlas==<this release>` / `==X.Y.Z` and still flags a bare or other-version line, the way `GIT_URL` already treats `@<tag>` |
| W1 | which tags reach PyPI | want | **ASSUMED (awaiting ratification):** stable tags only; a PEP 440 pre-release stays a GitHub pre-release, so a dry run never burns an immutable PyPI version |
| W2 | the first PyPI version | want | **ASSUMED (awaiting ratification):** the next ordinary signed release claims the name; no dedicated release, no placeholder |
| W3 | canonical channel | want | **ASSUMED (awaiting ratification):** the attested GitHub Release stays canonical (wheel, sdist, SBOM); PyPI is a Trusted-Publishing mirror of the same files |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Maintainer switches) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=4`
`CLARIFICATION: 6 raised | 6 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

W1–W3 count as self-resolved because the handover handed them back; each stays `ASSUMED` until the maintainer ratifies it.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "owning the name removes the hazard at its source" | the maintainer owns `code-atlas` on PyPI | ⚠ |
| AC1 | Acc 1 | "`release.yml` gains a PyPI publish job using Trusted Publishing only" | H1, W1 | ⚠ |
| AC2 | Acc 2 | "`SEC-SC-13` moves from `n/a` to a guard" | the row names `release_shape`; 431's text corrected | ⚠ |
| AC3 | Acc 3 | "427's install rule allows a **pinned** PyPI line" | H3; README differentiator sentence; SEC-GV-07 reworded | ⚠ |
| AC4 | Acc 4 | "The next signed tag is on PyPI, owned by the maintainer" | after merge, by the maintainer — exclusion | ⚠ |
| C1 | Switches | "add a **pending publisher** … create `pypi` with a required reviewer" | maintainer actions, named in the runbook | ⚠ |

`BASELINE: green — targeted suite on main at 8c7f7a12: 255 passed, 1 excluded (test_the_plugin_hook_names_a_skew_against_the_installed_package: the host's PATH code-atlas is 0.9.1, the venv's 0.10.0 — host state, not code)`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5: each new arm seen failing on a planted variant · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §9 (change-type) ✅ R9.6: SEC-SC-13 held by a test, not a document`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.**
1. `release.yml`: job `pypi` (`needs: publish`, `environment: pypi`, `permissions: id-token: write`, no checkout):
   download the artifact, skip on `release/PRERELEASE` (W1), copy `*.whl` and `*.tar.gz` into `dist/`, publish with
   `pypa/gh-action-pypi-publish` (no `password`, attestations left on).
2. `tests/test_release_discipline.py`: `release_shape` gains the `pypi` arms, each with a planted red variant — a token
   input, no environment, a write scope or checkout in `pypi`, attestations off, no pre-release skip.
3. `tests/test_distribution_pinning.py`: H3, with planted pinned-other and bare lines.
4. Docs: SEC-SC-13 row → the `release_shape` test and `ci: Release`; SEC-GV-07 criterion "by an unpinned name";
   `releasing.md` PyPI setup and the first-upload follow-up (H2); README differentiator sentence; 431 "Why" corrected;
   CHANGELOG *Unreleased*.

**Rejected:** a placeholder upload — PEP 541 reclaims an empty name; an API token secret — SEC-SC-13 says Trusted
Publishing only; `pypi` needing only `build` — a PyPI upload before the attested Release exists would invert W3.

**Change list:** `.github/workflows/release.yml`, `tests/test_release_discipline.py`, `tests/test_distribution_pinning.py`,
`docs/SECURITY_STANDARD.md`, `docs/runbooks/releasing.md`, `README.md`, `docs/tasks/431_release-pipeline.md`, `CHANGELOG.md`;
bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file).

**Proving tests:** `tests/test_release_discipline.py::test_the_release_workflow_has_the_shape_the_standard_names` and its
planted variants; `tests/test_distribution_pinning.py` install-lint arms.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **AC4 — expired 2026-11-04, falsified:** PyPI refused the pending publisher (Resolution). Was: expiry the first stable signed tag after this merge. `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/code-atlas/json` returns 200 and the maintainer is the owner.

## Phase 3 — execute

Main loop, no `implementer` dispatch (SCOPE S). Landed Approach 1–4 in `1156dbb0`, `d96253cc`; ticket and backlog in
`1bace62f`. **Verification sweep.** File axis: `git diff --stat 8c7f7a12..HEAD` names 10 files, every one on the change
list; no deviation. Behaviour axis: Approach 1–4 as approved; the README sentence is "no graph-database server (SQLite
only); not the `code-atlas-mcp` package" and keeps "not published on PyPI" (H2); `ci: Publish with Trusted Publishing`
joins SEC-SC-13's guard.

**Seen failing (R6.5).** `pypi_shape` stubbed out of `release_shape` → the 7 new variants red (7 failed, 13 passed);
restored, all pass. The `==` pin allowance removed from `install_violations` → the 2 new allowed lines red (2 failed,
15 passed); restored. Targeted suite 490 passed, 1 deselected (the baseline exclusion); `ruff check` and `ruff format`
clean on the changed tests; `mypy` reports the 3 errors `main` already has, none in changed lines.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The rule-book reviewer was waived by the run's argument; no
reviewer step ran (no `reviewer`, no `reviewer-max`, no native `/code-review`).

- **`challenger` round 1** (ticket-blind, 54,946 tokens, at `8312687a`): 4 met · 1 partly met (3b: README names the
  look-alikes but keeps "not published on PyPI" — H2, by design) · 1 not met (2b) · 1 can't tell (AC4, the exclusion).
  - **Important, taken** in `2e548bb5`: 431's call-site line and C1 row still said "no PyPI".
  - **Minors taken** in `2e548bb5`: the `pypi` job now has a job-level `if: needs.build.outputs.prerelease != 'yes'`
    (from a `build` output), so a pre-release never waits on the environment reviewer; `pypi_shape` compares that `if`
    and `packages-dir: dist/` exactly, with two new planted variants. **Not taken:** the pin — `v1.14.3` is an
    annotated tag, dereferenced to commit `7245906f…` before pinning; `publish`'s scopes — unchanged by this diff.
  - Seen failing after the fix: `pypi_shape` stubbed → 8 failed, 13 passed; restored, 267 passed.

Verdict: clean (challenger only — REVIEWER: OFF), the Important landed.
`Ph3/4 proven by`: AC1 → `release_shape`/`pypi_shape` and its 8 planted variants, `tests/test_ci_hardening.py` over
`release.yml`; AC2 → `tests/test_security_standard.py` (SEC-SC-13 guard names resolve); AC3 → the install-lint arms in
`tests/test_distribution_pinning.py`, README read; AC4 → exclusion; G1 → AC4; C1 → `docs/runbooks/releasing.md` step 5.

Reviewed at 2e548bb5

## Phase 5 — finalise

**Durable lesson.** 433-C1 `a-shape-guard-pins-the-wiring` (new, type 2); 433-C2 `symbol:pypi-json-api` (new, type 1).

`CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=1 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate.** `scripts/gate.sh` on the host at `2e548bb5`: 24 passed · 1 failed · 1 skipped — pytest 5729 passed,
2 failed, 4 skipped. Both failures (`test_the_plugin_hook_names_a_skew_against_the_installed_package`,
`test_a_checkout_behind_the_core_is_named_with_its_fix`) fail identically on `main` at `8c7f7a12`: the host's PATH
`code-atlas` is 0.9.1. Docker before the re-scope (`0b87f7e9`, with the `pypi` job): 5727 passed, 8 skipped. Docker on
the re-scoped final tree, delta-green (the exclusion's route):

Ran at e68e45fd

```
$ scripts/docker-test.sh
5715 passed, 8 skipped in 699.55s (0:11:39)
```

### Re-scope after the PR opened (maintainer, 2026-11-04)

PyPI refused `code-atlas` (Resolution). On the maintainer's pick — drop PyPI — the branch reverts
`release.yml`, `tests/test_release_discipline.py`, `tests/test_distribution_pinning.py`, `docs/runbooks/releasing.md` and
`CHANGELOG.md` to `main`, and keeps only the true record: SEC-SC-13's `n/a` reason, 431's "Why", the README's install
sentence and differentiator, this ticket, the lesson and the ledger. W1–W3 are moot. The challenger's review covered
the reverted job; the remaining diff is docs only.

### Outward actions

Under the handover: push `chore/433-claim-pypi-name`; open its PR against `main` (#157), then update it after the
re-scope. Deferred to the maintainer: merge. Nothing on PyPI or in GitHub settings is needed.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker `challenger` | 1 | 44,629 |
| 4 review | ticket-blind `challenger` | 1 | 54,946 |

`LEDGER TOTAL: 99,575 · top cost driver: 4 review / challenger` — main loop unmeasured.
