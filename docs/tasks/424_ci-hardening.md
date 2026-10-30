---
id: 424
slug: ci-hardening
title: "CI cannot be steered by a moved tag or a leaked token — actions pinned by SHA, least-privilege tokens, Dependabot, CodeQL, Scorecard and a settings-drift check"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

Every `uses:` in `.github/workflows/` names a moving tag (`actions/checkout@v4`,
`shivammathur/setup-php@v2`, …): whoever moves the tag runs code in CI. Checkouts keep the token in
`.git/config`, no Dependabot config exists, and nothing scans the code or scores the repo. The
repository settings that do guard `main` (rulesets, private reporting, secret scanning) were set
by hand and are checked by nothing.

## Acceptance

1. **Pinned actions:** every `uses:` names a full commit SHA with the version as a comment. A test
   fails on any `uses:` that is not a 40-hex SHA. Then the repo setting `sha_pinning_required` is
   turned on (maintainer, read back by AC6).
2. **Least privilege:** each workflow declares `permissions: contents: read` at the top; a write
   scope appears only in a job that runs no pull-request code. `persist-credentials: false` on
   every checkout. No `pull_request_target`, no `workflow_run` with a PR checkout, no
   `${{ github.event.* }}` inside `run:`. One test reads the workflows and asserts all of it.
3. **`.github/dependabot.yml`** for pip, both npm adapters, composer, GitHub Actions and Docker,
   grouped weekly.
4. **CodeQL** (Python, JavaScript/TypeScript) and **OpenSSF Scorecard** (weekly, results to code
   scanning) workflows, themselves pinned and least-privilege.
5. **R2.4 sweep on ref names:** the identity grep also covers branch names and PR head refs.
6. **Settings drift:** a scheduled workflow reads, through `gh api`, the `main` and `v*` rulesets,
   private vulnerability reporting, secret scanning with push protection, Dependabot security
   updates and `sha_pinning_required`, and fails (opening an issue) when one has drifted from the
   values written in `docs/SECURITY_STANDARD.md`.
7. `scripts/gate.sh` keeps parity with `ci.yml` (`test_ci_and_gate_agree`); the new workflows
   are scheduled or analysis-only and say why they have no gate counterpart.

## Call sites

`.github/workflows/ci.yml`, `cross-repo.yml`, `tokens-to-answer-sample.yml`; new
`.github/dependabot.yml`, `codeql.yml`, `scorecard.yml`, `settings-drift.yml`;
`tests/test_ci_and_gate_agree.py`; the R2.4 grep in `ci.yml`; `docs/SECURITY_STANDARD.md` rows
SEC-SC-01..05, 08, 10, 15, 16.
