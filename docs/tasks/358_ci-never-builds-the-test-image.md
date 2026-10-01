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
