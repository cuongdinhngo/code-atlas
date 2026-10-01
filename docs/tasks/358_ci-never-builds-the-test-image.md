---
id: 358
slug: ci-never-builds-the-test-image
title: 'CI never builds the test image docker/Dockerfile, so gate.sh --docker can break unseen'
phase: 2
milestone: Tooling
status: todo
depends_on: [323]
---

## Why this exists

The backlog follow-up said "Docker images are never built by CI". Half of that is stale: CI's
pytest step builds `docker/Dockerfile.runtime` inside
`tests/test_server_build.py::test_runtime_image_reports_server_build` (Docker is on GitHub's
runners; the 2026-10-01 main run reports 4 skips, none of them that test).

`docker/Dockerfile` — the test image behind `scripts/docker-test.sh` and `scripts/gate.sh --docker`
(323) — is built by nothing in CI. It pulls a floating base (`python:3.12-slim-bookworm`), apt's
PHP and composer's installer over `curl`; any of them can drift and break the image. Today the
break surfaces only when the maintainer runs Docker before a PR.

## Scope

1. One CI job that builds `docker/Dockerfile` (build only — the suite already runs in the pytest
   job; running it twice buys nothing).
2. `scripts/gate.sh` mirrors the job, kept in step by `tests/test_ci_and_gate_agree.py`.
3. The job uses buildx's GitHub Actions cache (`type=gha`), so an unchanged image is not rebuilt
   from scratch on every PR.

**Open decision (resolve at design):** `gate.sh --docker` already builds `docker/Dockerfile`
(`scripts/gate.sh:44`), but a plain run does not. Mirroring the job in a plain run means either
every local gate builds the image (slow, needs Docker), or it records a SKIP without Docker, which
is exit 2 and never `GATE GREEN` (R6.5). The other choice is to mirror it only under `--docker`,
with `test_ci_and_gate_agree` taught that one exception.

## Acceptance criteria

- **AC1:** a broken `docker/Dockerfile` (e.g. a missing apt package) fails CI on the PR.
- **AC2:** `test_ci_and_gate_agree` passes with the new job.
- **AC3:** CI wall-clock grows by no more than the job's own build, run in parallel.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 358 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** review. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 360 → 357 → 358 → 359;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `chore/358-ci-never-builds-the-test-image` off `main` (`41ba7996`). Contract `.mango/run-contract-358.txt`,
  written after the first change commit (see DISCLOSURE). RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 3 want-decision asked | 7 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** All six resolve on `41ba7996`: `docker/Dockerfile`, `docker/Dockerfile.runtime`,
`tests/test_server_build.py::test_runtime_image_reports_server_build`, `scripts/docker-test.sh`,
`scripts/gate.sh:44` (the `--docker` build), `tests/test_ci_and_gate_agree.py`.

**Recall.** No claim matches: the change touches CI config and a guard test, none of the three
type-2 shapes (shared vocabulary, new core module, threaded value).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 41,726 tokens) surfaced X1–X6.

| # | Decision | Class | Resolution |
|---|---|---|---|
| W1 | the ticket's open decision: plain-run build vs `--docker` only | want (bar) | **ASSUMED:** mirror under `--docker` only, `test_ci_and_gate_agree` carrying that one row. A plain-run build would make every docker-less host exit 2 (R6.5), and `scripts/docker-test.sh`, which AGENTS.md has the maintainer run before each PR, already builds this image |
| X1 | a warm `type=gha` cache replays the apt and composer layers, so drift waits for eviction | want | **ASSUMED:** `pull: true` — a new base digest rebuilds every layer above it, with no new trigger; a scheduled `--no-cache` run is not added |
| X2 | making `test-image` a required check in branch protection | want (outward) | **ASSUMED:** not done — a repo setting outside the diff and the two authorised actions; a red job already turns the PR's CI red (AC1). Listed as deferred |
| H1 | build tooling | how | `docker/setup-buildx-action` + `docker/build-push-action`, `push: false`, `type=gha` (Scope 3) |
| H2 | permissions | how | `contents: read` — every job in `ci.yml` declares least privilege |
| H3 | triggers | how | the workflow's own (`push`/`pull_request` on `main`) — Scope 1 asks for a job, not a workflow |
| H4 | AC1's proof | how | locally: a missing apt package fails `docker build` (exit 1); the live red-on-PR run is a coverage-gap exclusion (it needs a throwaway broken branch pushed) |
| X3 | `timeout-minutes` | how | none — no job in `ci.yml` sets one (`grep -c timeout-minutes` → 0) |
| X4 | a fork PR's read-only token fails `cache-to` | how | `ignore-error=true` on `cache-to`; the job judges the build only (AC1) |
| X5 | cache scope | how | the default: no other job in the repo writes the gha cache |
| X6 | context and file | how | `context: .`, `file: docker/Dockerfile` — the same as `gate.sh:44`; pinned by the shape test |

Every **ASSUMED** row rests on the maintainer's hand-back in the run's invocation ("You have my
approval to choose the best approach, make the necessary decisions … without waiting for further
confirmation"). None reverses a prior decision. Each is surfaced in the PR for ratification.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (title, Why this exists, Scope, Open decision, Acceptance criteria) | 5 decomposed | ROWS: C=1 R=4 G=1 AC=3`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

W1, X1 and X2 cite the maintainer's up-front hand-back; the rest cite the code, so `j = 0`.

### BASELINE

`main` at `41ba7996`: CI run 36876561135 concluded `success`. Ran at 41ba7996.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | title / Why | "gate.sh --docker can break unseen" | a break in `docker/Dockerfile` shows on the PR | ✅ |
| C1 | Scope 1 | "build only" | no `run:` step, no suite in the image | ✅ |
| R1 | Scope 1 | one CI job builds `docker/Dockerfile` | `test-image` | ✅ |
| R2 | Scope 2 | `gate.sh` mirrors it, kept in step | a `SHARED_CHECKS` row; header says `--docker` | ✅ |
| R3 | Scope 3 | `type=gha` cache | `cache-from` / `cache-to` | ✅ |
| R4 | Open decision | resolve at design | W1 | ✅ |
| AC1 | AC | broken Dockerfile fails CI | local broken build + job wiring; live run excluded | ✅ |
| AC2 | AC | `test_ci_and_gate_agree` passes | 25 passed | ✅ |
| AC3 | AC | wall-clock grows by no more than the job, in parallel | no `needs` on or toward it | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `docker build` exit ≠ 0 on a missing apt package; the job runs that build | the PR run itself is the coverage-gap exclusion below |
| AC2 | yes — pytest | |
| AC3 | yes — the job has no `needs:` and nothing `needs: test-image` (shape test) | the measured wall-clock is read from this PR's first CI run |

### Gap analysis (enhancement)

- **Now.** `ci.yml` has three jobs; none builds `docker/Dockerfile`. `gate.sh:44` builds it only under `--docker`.
- **Target.** A fourth, parallel, build-only job; the gate's `--docker` build is its counterpart.

### Blast radius

- `.github/workflows/ci.yml` (a job), `scripts/gate.sh` (header), `tests/test_ci_and_gate_agree.py`
  (a row, a shape test), `AGENTS.md` (the "mirrors every job" line). No runtime code.

### Rule sections

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §R6.5 (change-type) ✅ the shape test was seen red on three mutations (needs, run, cache) and the build red on a broken Dockerfile, §R7.5 (change-type) ✅ every new comment ≤ 3 lines, §R7.6 (change-type) ✅ the AGENTS.md line is replaced (two lines merged into two), under its budget`

## Phase 2 — design

### Approach

1. **`ci.yml`**: job `test-image` — checkout, buildx, `build-push-action` with `context: .`,
   `file: docker/Dockerfile`, `pull: true`, `push: false`, `cache-from: type=gha`,
   `cache-to: type=gha,mode=max,ignore-error=true`; `contents: read`; no `needs`.
2. **`gate.sh`**: the header says the fourth job is mirrored under `--docker` (W1); no new check.
3. **`test_ci_and_gate_agree`**: a `SHARED_CHECKS` row (`file: docker/Dockerfile` ↔
   `docker build -f "$root/docker/Dockerfile"`) and a shape test (parallel, build only, cache,
   pull, context).
4. **`AGENTS.md`**: the gate line names the `--docker` exception.

### Rejected alternatives

- **Build in every plain gate run.** Exit 2 on every host without Docker (W1).
- **Run the suite inside the image in CI.** The test job already runs it; twice buys nothing (Scope 1).
- **A weekly `--no-cache` schedule.** A new trigger the ticket did not ask for (X1).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | the image builds on this tree | verified — `docker build -f docker/Dockerfile .` exit 0, 2m02s |
| S2 | a missing apt package fails the build | verified — exit 1, apt exit 100 |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `test-image` job | `.github/workflows/ci.yml` | CI only | R1, R3, C1, AC1, AC3 | 1/1 |
| 2 | header | `scripts/gate.sh` | — | R2, R4 | 1/1 |
| 3 | row + shape test | `tests/test_ci_and_gate_agree.py` | — | R2, AC2, AC3 | 1/1 |
| 4 | gate line | `AGENTS.md` | `tests/test_doc_size_budget.py` | R2 | 1/1 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (CI) | local `docker build` of a broken copy (exit 1) and of the real file (exit 0); the job runs the same build | n/a | ✅ with the exclusion below |
| AC2 | logic | `pytest tests/test_ci_and_gate_agree.py` | n/a | ✅ |
| AC3 | config | the shape test (no `needs`) | n/a | ✅ |

Coverage-gap exclusions (human hand-back):

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|---|---|---|---|---|---|
| AC1 observed red on a live PR | low | needs pushing a deliberately broken branch, outside the two authorised actions | push a branch with a bad apt package and see `test-image` fail | when a PR run of `test-image` with a broken Dockerfile is recorded | — |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_ci_and_gate_agree.py`. The shape test fails on `41ba7996`
(no `test-image` job) and passes after the change.

### Rollback

`git revert` the branch commits.

## Phase 3 — execute

Commits on `chore/358-ci-never-builds-the-test-image`: `ecd210c8` (the job, the row, the header,
AGENTS.md), `23abcc75` (`pull: true`, `ignore-error=true`, the context pins — X1, X4, X6).

**Sweep.**
- Axis 1 — file set: the change list exactly.
- Axis 2 — design conformance: bullets 1–4 as approved. `ruff check` clean; `ci.yml` parses as YAML.
- `tests/test_ci_and_gate_agree.py`: 25 passed. The shape test, run against three mutated copies
  of `ci.yml` (a `needs:`, a `run:` step, no `cache-from`): red on each.
- `docker build -f docker/Dockerfile .` on the change tree: exit 0 in 2m02s. A copy with
  `php-no-such-package-358` added to the apt line: exit 1 (`apt-get` exit 100).
- `AGENTS.md` first went 2,859 tokens over its 2,850 budget; two gate lines were merged into two
  shorter ones to fit.
