---
id: 424
slug: ci-hardening
title: "CI cannot be steered by a moved tag or a leaked token — actions pinned by SHA, least-privilege tokens, Dependabot, CodeQL, Scorecard and a settings-drift check"
phase: 2
milestone: Trust
status: done
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
7. **Guards for rows held without one:** a CI grep gate refuses `eval`, `exec`, `pickle`,
   `yaml.load` and `importlib` on repo content under `code_atlas/` and `adapters/` (SEC-IN-07); a
   test refuses a committed binary outside a named allow-list (SEC-SC-14); an AST test refuses SQL
   built by f-string, `%` or `.format` in `store.py` outside named identifiers (SEC-IN-06); `claude plugin validate
   --strict` runs in CI where the CLI installs (SEC-PL-06). The drift check (AC6) also reads the
   repo's admins (SEC-GV-04), and adds the standard's repo-setting item kind with its reader.
8. `scripts/gate.sh` keeps parity with `ci.yml` (`test_ci_and_gate_agree`); the new workflows
   are scheduled or analysis-only and say why they have no gate counterpart.

## Call sites

`.github/workflows/ci.yml`, `cross-repo.yml`, `tokens-to-answer-sample.yml`; new
`.github/dependabot.yml`, `codeql.yml`, `scorecard.yml`, `settings-drift.yml`;
`tests/test_ci_and_gate_agree.py`; the R2.4 grep in `ci.yml`; `docs/SECURITY_STANDARD.md` rows
SEC-SC-01..05, 08..10, 14..16, SEC-IN-06, 07, SEC-PL-06, SEC-GV-01, SEC-GV-04.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 424 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer creates `SETTINGS_READ_TOKEN`, ratifies W1–W2, merges after #124, then turns on `sha_pinning_required`.
- `TRACK: backend` · Run mode: `autorun 427 - 430 - 424 - 425 - 428 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/424-ci-hardening`, **stacked on `feat/430-limits-and-containment`** (#124).
  Contract `.mango/run-contract-424.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 2 want-decision asked | 8 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `.github/workflows/ci.yml`, `cross-repo.yml`, `tokens-to-answer-sample.yml`, `scripts/gate.sh`,
`scripts/identity_markers.py`, `tests/test_ci_and_gate_agree.py`, `adapters/{php,typescript,sql}` manifests and
`docker/` resolve; `dependabot.yml`, `codeql.yml`, `scorecard.yml`, `settings-drift.yml` are to be created.
The repo's settings were read back (read-only `gh api`, 2026-10-31): rulesets *Protect main* (deletion,
non-fast-forward, pull request, five required checks) and *Protect release tags* (deletion, update,
non-fast-forward, no bypass); private reporting on; secret scanning and push protection on; Dependabot security
updates on; `sha_pinning_required: false`; one collaborator, `admin`.
Recall (type 2, by handle): 423-C1 `a-cited-guard-must-hold-its-row` (each new guard is read against its row);
427-C1 `a-loader-guard-misses-the-entry-that-loads-nothing` (the workflow checks enumerate every workflow file,
not the ones a helper loads).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | how a SHA is chosen | how | each tag resolved through `gh api …/commits/<tag>` (an annotated tag dereferenced); the comment names the exact version |
| H2 | the PR ratio comment | how | the one write scope in a job that runs PR code (`ci.yml:149`, `pull-requests: write`); AC2 forbids it, so the ratio goes to the job summary (`$GITHUB_STEP_SUMMARY`) and the uploaded report, which carry the same numbers |
| H3 | `${{ github.event.* }}` in `run:` | how | `ci.yml:155, 348, 355` move to `env:` and are read as shell variables |
| H4 | CodeQL's trigger | how | push to `main` and a weekly schedule, not `pull_request` — its `security-events: write` then sits in a job that runs no PR code (AC2) |
| H5 | the R2.4 ref sweep | how | `identity_markers.py` also reads the PR head ref and the branch name (`GITHUB_HEAD_REF` / `GITHUB_REF_NAME`, or `git branch --show-current` in the gate) |
| H6 | the repo-setting item kind | how | `set: <name> = <value>` in SECURITY_STANDARD rows; `tests/test_security_standard.py` checks every `set:` name is one `scripts/settings_drift.py` reads, and the drift script reads its expected values from those items (R6.7, one source) |
| H7 | guard placement | how | SEC-IN-07 grep and SEC-SC-14 binary sweep as tests (they run in `pytest`, so the gate mirrors them for free); SEC-IN-06 an AST test over `store.py`; SEC-PL-06 a CI job installing the pinned Claude Code CLI, with no gate counterpart (a network install), named in `test_ci_and_gate_agree`'s exemption with its reason |
| H8 | Dependabot scope | how | `pip` (`/`), `npm` (`/adapters/typescript`, `/adapters/sql`), `composer` (`/adapters/php`), `github-actions` (`/`), `docker` (`/docker`); weekly, one group per ecosystem |
| W1 | the drift check's credential | want | **ASSUMED (awaiting ratification):** the settings endpoints need an admin-read token, which `GITHUB_TOKEN` lacks; the workflow reads `secrets.SETTINGS_READ_TOKEN` (a fine-grained token, *Administration: read*) and fails loudly naming it when absent. Creating it is the maintainer's |
| W2 | `sha_pinning_required` | want | **ASSUMED (awaiting ratification):** the standard records `true`; until the maintainer turns it on (a settings write, outside this run's authorisation) the drift check reports that one drift |

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
| G1 | Why | "CI cannot be steered by a moved tag or a leaked token" | pinned actions, least privilege, scanners, settings read back | ⚠ |
| AC1 | Acc 1 | "every `uses:` names a full commit SHA" | H1; test over every workflow file | ⚠ |
| AC2 | Acc 2 | "`permissions: contents: read` … `persist-credentials: false` … no `${{ github.event.* }}` inside `run:`" | H2, H3, H4; one test reads every workflow | ⚠ |
| AC3 | Acc 3 | "`.github/dependabot.yml` … grouped weekly" | H8 | ⚠ |
| AC4 | Acc 4 | "CodeQL … Scorecard … pinned and least-privilege" | H4; both covered by the AC1/AC2 test | ⚠ |
| AC5 | Acc 5 | "the identity grep also covers branch names and PR head refs" | H5 | ⚠ |
| AC6 | Acc 6 | "a scheduled workflow reads … fails (opening an issue)" | H6, W1, W2 | ⚠ |
| AC7 | Acc 7 | "Guards for rows held without one" | H7 | ⚠ |
| AC8 | Acc 8 | "`scripts/gate.sh` keeps parity with `ci.yml`" | new workflows scheduled or analysis-only, each named with its reason | ⚠ |
| C1 | Call sites | "rows SEC-SC-01..05, 08..10, 14..16, SEC-IN-06, 07, SEC-PL-06, SEC-GV-01, SEC-GV-04" | each closes on its guard; a setting row on `set:` + the drift job | ⚠ |

`BASELINE: green — Docker on feat/430-limits-and-containment at 38f019d6 (5299 passed, 8 skipped)`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §2 (change-type) ✅ R2.4: the ref sweep extends the identity guard · §6 (change-type) ✅ R6.4: the new grep gates fail the build; R6.5: each guard seen failing on a planted workflow or file; R6.7: drift values derived from the standard · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §8 (change-type) ✅ R8.3: actions pinned like a lock · §9 (change-type) ✅ R9.6: each closed MUST names a test or a CI step`

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 423-C1: each guard's test is read against its row's criterion before the row cites it (the SEC-IN-06 AST test
  guards binding in `store.py`, the row's subject).
- 427-C1: the workflow tests glob `.github/workflows/*.yml`, every file, not the three named today.

**Approach.**
1. Pin every `uses:` (H1); `permissions: contents: read` at each workflow's top; `persist-credentials: false` on
   every checkout; the ratio comment becomes a job summary (H2); event values move to `env:` (H3).
2. `.github/dependabot.yml` (H8); `codeql.yml` (H4) and `scorecard.yml` (weekly, SARIF to code scanning), pinned
   and least-privilege.
3. `identity_markers.py` reads the branch and head ref (H5).
4. `scripts/settings_drift.py` + `settings-drift.yml` (weekly; opens an issue on drift) reading the expected values
   from the standard's `set:` items (H6, W1, W2); the admins check (SEC-GV-04) is one of them.
5. Guards (H7): `tests/test_ci_hardening.py` (pins, permissions, credentials, triggers, event interpolation),
   `tests/test_no_code_execution_on_repo_content.py`, `tests/test_no_committed_binaries.py`,
   `tests/test_store_binds_sql.py`; a `plugin validate --strict` CI job.
6. Docs: SECURITY_STANDARD rows and grammar (`set:`), CONTRIBUTING/README note if any, CHANGELOG.

**Rejected:** keeping the PR comment under `pull_request_target` (the pattern AC2 forbids); CodeQL on
`pull_request` with a write token (a write scope beside PR code).

**Change list:** `.github/workflows/{ci,cross-repo,tokens-to-answer-sample}.yml`, new
`.github/dependabot.yml`, `.github/workflows/{codeql,scorecard,settings-drift}.yml`, `scripts/identity_markers.py`,
new `scripts/settings_drift.py`, `scripts/gate.sh` (parity only), `tests/test_ci_and_gate_agree.py`,
`tests/test_security_standard.py`, new tests above, `docs/SECURITY_STANDARD.md`, `SECURITY.md`, `CHANGELOG.md`;
bookkeeping.

**Proving tests:** `tests/test_ci_hardening.py` and the three guard tests — each seen red on a planted violation.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- The drift workflow, CodeQL and Scorecard cannot run before merge (scheduled / `main` only); their logic is
  tested offline (`settings_drift.py` on fixtures) and the workflows are proven by their first scheduled run
  (expiry: the first run after merge, read by the maintainer).

## Phase 3 — execute

`implementer` landed Approach 1–6 in `2279cd59`…`2b4d543d` (7 commits). **Verification sweep.** File axis: the
change list plus recorded deviations — `tests/test_commit_identity.py` (the ref arms), `docs/runbooks/tokens-to-answer.md`
and `scripts/tokens_to_answer.py` (the PR comment became the job summary). Behaviour axis as approved: eleven
actions pinned (each SHA read from `gh api …/commits/<tag>`); CodeQL on push and schedule only; the Claude Code CLI
installed at an exact version for `plugin validate --strict`, the one `CI_ONLY` check; `adapters/typescript/src/imports.js`
allow-listed by the binary sweep (one literal NUL inside a cache key — a follow-up could spell it `\0`).

**Seen failing (R6.5).** `tests/test_ci_hardening.py` on a worktree of the base: 15 failed, 25 passed (unpinned
`uses:`, no top-level `permissions`, no `persist-credentials: false`, `pull-requests: write` beside a checkout,
no `codeql.yml` / `dependabot.yml`); the plugin-job pin red with `@latest`; `test_store_binds_sql.py` accepted an
early planted interpolation until its allow-list became (function, name) pairs. A read-only `settings_drift.py
--local` against the live repo reported exactly one drift — `actions.sha_pinning_required` (W2), as designed.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 85,705 tokens): 6 met · 2 partly met · 0 not met; five SHAs re-checked
  against their tags. Taken in `046611c9`:
  - **Important 1** — the workflow reader passed flow-style steps, an event expression in `with: script:`, and a
    reusable-workflow job with a write scope under a PR trigger: it now fails closed on any flow mapping, anchor,
    alias or merge key, scans every `with:` value, refuses (c), and also reads `.github/actions/**`; each with a
    planted case. ci.yml, codeql.yml and scorecard.yml were rewritten to block style.
  - **Important 2** — SEC-GV-04 claimed 2FA, which no API reads for a user-owned repo: the row now holds the
    single admin only, and the new SHOULD row SEC-GV-08 (2FA) is `deferred:` with the maintainer's attestation.
  - Minor, taken: the issue step guards a missing report; the ref sweep's scope is stated (SEC-SC-16); the
    execution guard resolves aliases and refuses `compile` / `runpy`; the Dependabot directories are derived from
    the adapters' manifests.
- **Round 2: verify-only, main loop.**

```
# review-time record (an earlier tree by design; the final-tree run is in Phase 5)
$ .venv/bin/python -m pytest -q tests/test_ci_hardening.py tests/test_settings_drift.py tests/test_no_code_execution_on_repo_content.py tests/test_no_committed_binaries.py tests/test_store_binds_sql.py tests/test_security_standard.py tests/test_ci_and_gate_agree.py tests/test_commit_identity.py
231 passed in 2.16s
```

Verdict: clean (challenger only — REVIEWER: OFF), W1–W2 standing for ratification.
`Ph3/4 proven by`: AC1, AC2, AC4 → `tests/test_ci_hardening.py`; AC3 →
`test_dependabot_covers_every_ecosystem_and_directory`; AC5 → `tests/test_commit_identity.py` ref arms +
`test_ci_and_gate_agree`; AC6 → `tests/test_settings_drift.py`; AC7 → `tests/test_no_code_execution_on_repo_content.py`,
`tests/test_no_committed_binaries.py`, `tests/test_store_binds_sql.py`, the plugin job; AC8 → `test_ci_and_gate_agree`;
C1 → `tests/test_security_standard.py`.

Reviewed at 046611c9.

## Phase 5 — finalise

**Durable lesson.** 424-C1 `a-subset-reader-must-fail-closed` (new, type 2). Sightings (P1): 423-C1 +424 (each
guard read against its row: SEC-GV-04 overclaimed), 427-C1 +424 (the workflow test reads every file, and `.github/actions/`).

`CLAIMS: 3 claim(s) from 3 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 2 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 2 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md, docs/ENGINEERING_RULES.md | mango files written: 0`

**The final gate:** __DOCKER__

### Outward actions

Under the handover: push `feat/424-ci-hardening`; open its PR against `feat/430-limits-and-containment`.
Deferred to the maintainer: create the `SETTINGS_READ_TOKEN` secret (W1); ratify W1–W2; merge after #124; then turn
on `sha_pinning_required` (W2) and add the plugin-validate job to the ruleset's required checks if wanted.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 3 execute | `implementer` | 1 | 227,526 |
| 4 review | ticket-blind `challenger` | 1 | 85,705 |
| 4 review | `implementer` (review fixes, resumed) | 2 | 256,778 |

`LEDGER TOTAL: 570,009 · top cost driver: 4 review / implementer` — main loop unmeasured.
