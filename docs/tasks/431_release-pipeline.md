---
id: 431
slug: release-pipeline
title: "A release is built by a workflow, not a laptop — signed tag, GitHub Release with the wheel, an SBOM and a provenance attestation a user can verify"
phase: 2
milestone: Trust
status: done
depends_on: [424, 425]
---

## Why this exists

0.9.1 was tagged and released by hand: the tag is unsigned, the release carries no artifact, and a
user installing `@v0.9.1` cannot check that what they got is what CI built. code-atlas is not on
PyPI (PyPI refuses `code-atlas` as too similar to `codeatlas`, 433), so the GitHub Release is the distribution point and must carry
the proof itself.

## Acceptance

1. **Signed tags and commits:** release tags are signed (SSH signing); the `v*` ruleset requires
   it; `test_release_discipline` verifies the top release's tag signature where the key is known.
2. **`release.yml`** on a `v*` tag push: builds sdist and wheel from the tag, generates a CycloneDX
   SBOM, attests build provenance (`actions/attest-build-provenance`, SLSA Build L2+), and creates
   the GitHub Release with the CHANGELOG entry and those files. Pinned, least-privilege, write
   scopes in that job only.
3. **Verification documented:** README and SECURITY.md show `gh attestation verify` on the wheel,
   and the install line that uses the verified file.
4. **Dry run:** a pre-release tag in a fork produces attested artifacts; recorded in the
   resolution.
5. **Advisory releases:** `test_release_discipline` fails when a release that fixed an advisory
   (its TOKEN_LEDGER row links a GHSA) has no `Security` section in its CHANGELOG entry (SEC-GV-02).
6. The release steps are written once, as `docs/runbooks/releasing.md` (bump, CHANGELOG, signed
   tag, the workflow does the rest); none exists today, and 0.9.1 was released by hand.

## Call sites

New `.github/workflows/release.yml`, `docs/runbooks/releasing.md`;
`tests/test_release_discipline.py`, `README.md`, `SECURITY.md`; standard rows SEC-SC-11..13
(13 recorded N/A: no PyPI), SEC-GV-02.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 431 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer's merge.
- `TRACK: backend` · Run mode: `autorun 431 --no-reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` ·
  `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/431-release-pipeline` from `main` at `bd242e59`, in its own worktree from t0. Contract
  `.mango/run-contract-431.txt`. RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`.
- Doctor preflight: 6 pass, 0 warn, 0 fail (mango 1.17.3, path and manifest agree). Budget: unknown — no
  fresh-token split in `docs/TOKEN_LEDGER.md`; comparable no-reviewer runs (424, 425, 428) took 3 dispatches.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 3 want-decision asked | 10 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise** (main loop, no dispatch). `tests/test_release_discipline.py`, `README.md`, `SECURITY.md`,
`docs/SECURITY_STANDARD.md` (SEC-SC-11..13, SEC-GV-02) and `docs/runbooks/` resolve; `release.yml` and
`releasing.md` are to-be-created. **Ambiguous:** GitHub documents *Require signed commits* for branches only, and
says nothing on whether a tag ruleset checks the tag object's signature, so the ruleset cannot be the guarantee;
the workflow itself verifies the tag. Every workflow is already held by `tests/test_ci_hardening.py` (pins,
`contents: read` at the top, no write scope beside pull-request code, no kept checkout token), so `release.yml` is
judged by the same arms with no new list. The test image (`docker/Dockerfile`) has no `ssh-keygen`.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | workflow shape | how | two jobs. `build` (`contents: read`, no write) checks out the tag, re-fetches the annotated tag object, verifies its SSH signature against the committed signers file, checks tag = `v` + pyproject version = CHANGELOG top entry, builds sdist and wheel with `SOURCE_DATE_EPOCH` from the tagged commit, and writes the SBOM. `publish` (`contents`, `id-token`, `attestations: write`; no checkout, so it runs no repo code) downloads the digest-checked artifact, attests provenance and the SBOM, and creates the Release |
| H2 | the SBOM | how | CycloneDX JSON of what a user installs: a fresh venv from the hashed `uv.lock` (`uv export --frozen --no-dev`) plus the wheel `--no-deps`, scanned by `anchore/sbom-action` (pinned; the 426 scan already uses Anchore); `actions/attest-sbom` binds it to the wheel |
| H3 | provenance | how | `actions/attest-build-provenance` over `dist/*` — GitHub-hosted, signed by Sigstore, SLSA Build L2; `gh attestation verify <file> --repo cuongdinhngo/code-atlas` checks it |
| H4 | release notes | how | new `scripts/release_notes.py`: the CHANGELOG entry for a version, and the agreement check of tag, pyproject and CHANGELOG; stdlib only, tested offline |
| H5 | signed-tag discipline | how | `test_release_discipline` verifies every `v*` tag from `SIGNED_FROM = 0.10.0` against `.github/allowed_signers` with `git verify-tag`; 0.9.1 and earlier are unsigned history, named in the runbook; a planted repo with an ephemeral key proves an unsigned or foreign-key tag goes red |
| H6 | advisory releases | how | derived from git, never a list: each GHSA a `TOKEN_LEDGER` row links → the commit that added it → the earliest release tag containing that commit → that release's CHANGELOG entry must carry `### Security` naming the GHSA; an advisory not yet released checks nothing |
| H7 | pre-release | how | a PEP 440 pre-release version (`a`, `b`, `rc`, `dev`) is created as a GitHub pre-release, so a fork dry run never reads as the latest release |
| H8 | the ruleset setting | how | a `rulesets.tags.required_signatures` reader in `scripts/settings_drift.py`; SEC-SC-11 carries it as a `set:` item, so the weekly drift job reports it until it is switched on |
| H9 | `ssh-keygen` in the test image | how | `openssh-client` joins the test image's apt line, so the planted signing arms run in Docker as on the host; the runtime image is unchanged |
| H10 | the standard rows | how | SEC-SC-11 and SEC-SC-12 lose `open: 431` and name their tests and `ci: Release`; SEC-SC-13 stays `n/a`; SEC-GV-02 names its test |
| W1 | commit signing | want | **RATIFIED 2026-11-02 (maintainer):** release tags are signed and verified; commits on `main` are not required to be signed — with merge commits, a required-signature rule on `main` refuses every PR whose branch commits are unsigned, which is a workflow change for the maintainer to choose |
| W2 | the signing key | want | **RATIFIED 2026-11-02 (maintainer):** `.github/allowed_signers` is the maintainer's to commit (which key signs is theirs to choose); until it exists the workflow refuses every tag and the runbook says why — fail closed, no release without a verifiable signature |
| W3 | the tag ruleset | want | **RATIFIED 2026-11-02 (maintainer):** `rulesets.tags.required_signatures = true` is the expected value; switching it on is a settings write outside this run, so the drift job reports that one drift until the maintainer does (as 424-W2) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=6`
`CLARIFICATION: 13 raised | 13 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W3 count as self-resolved because the handover handed them back; each stood `ASSUMED` until the maintainer ratified all three on 2026-11-02.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a user installing `@v0.9.1` cannot check that what they got is what CI built" | the Release carries attested files a user verifies | ⚠ |
| AC1 | Acc 1 | "release tags are signed (SSH signing); the `v*` ruleset requires it; `test_release_discipline` verifies the top release's tag signature where the key is known" | H5, H8, W1–W3 | ⚠ |
| AC2 | Acc 2 | "`release.yml` on a `v*` tag push: builds sdist and wheel … CycloneDX SBOM, attests build provenance … creates the GitHub Release" | H1–H4, H7 | ⚠ |
| AC3 | Acc 3 | "README and SECURITY.md show `gh attestation verify` on the wheel, and the install line that uses the verified file" | docs | ⚠ |
| AC4 | Acc 4 | "a pre-release tag in a fork produces attested artifacts; recorded in the resolution" | met 2026-11-02 in a throwaway public copy: [run](https://github.com/cuongdinhngo/code-atlas-release-dryrun/actions/runs/41379616572) | ✅ |
| AC5 | Acc 5 | "fails when a release that fixed an advisory … has no `Security` section" | H6 | ⚠ |
| AC6 | Acc 6 | "The release steps are written once, as `docs/runbooks/releasing.md`" | the runbook | ⚠ |
| C1 | Call sites | "standard rows SEC-SC-11..13 (13 recorded N/A: no PyPI), SEC-GV-02" | H10 | ⚠ |

`BASELINE: green — the suite on main at bd242e59: 5674 passed, 4 skipped (host Linux, this worktree; the working-doc lines above were already appended, no source change)`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5: each new arm seen failing on a planted repo; R6.7: the advisory check reads the ledger and git, never a list · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §9 (change-type) ✅ R9.5: SEC-GV-02 is now a test; R9.6: no MUST row held by a document alone · §1 (change-type) ✅ R1.1: no core change`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

R6.5: each new guard is seen failing on a planted input before it is trusted — an unsigned tag, a tag signed by a
key not in the file, a release that names a GHSA without `### Security`, a workflow with a write scope in `build`.

**Approach.**
1. New `.github/workflows/release.yml` (H1–H3, H7); the existing `tests/test_ci_hardening.py` arms judge it.
2. New `scripts/release_notes.py` (H4).
3. `tests/test_release_discipline.py`: the signed-tag arm (H5), the advisory arm (H6), the release workflow's
   shape (tag-only trigger, verify before build, writes only in `publish`, `publish` has no checkout, provenance
   and SBOM attested) and `release_notes` — each with a planted red case.
4. `scripts/settings_drift.py` reader (H8); `tests/test_settings_drift.py` fixture gains the rule.
5. `docker/Dockerfile`: `openssh-client` (H9).
6. Docs: new `docs/runbooks/releasing.md` (AC6); README (verify, then install the verified wheel); SECURITY.md
   *Supply chain*; SEC-SC-11/12, SEC-GV-02 rows (H10); CHANGELOG *Unreleased*.

**Rejected:** one job holding every write scope — the build runs the repo's build backend, so it gets none;
trusting the tag ruleset for the signature — GitHub does not document that it checks a tag object; a
hand-kept list of advisory releases — R6.7, the ledger and the tags already say it; `slsa-github-generator`'s
reusable workflow (Build L3) — a second toolchain for a level the ticket does not ask for.

**Change list:** new `.github/workflows/release.yml`, new `scripts/release_notes.py`,
`tests/test_release_discipline.py`, `scripts/settings_drift.py`, `tests/test_settings_drift.py`,
`docker/Dockerfile`, new `docs/runbooks/releasing.md`, `README.md`, `SECURITY.md`, `docs/SECURITY_STANDARD.md`,
`CHANGELOG.md`; bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file).

**Proving tests:** the new `tests/test_release_discipline.py` arms — each seen red on a planted input.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **AC4 — expired 2026-11-02.** Signed `v0.10.0rc1` in a throwaway public copy (attestations need a public repo):
  [run 41379616572](https://github.com/cuongdinhngo/code-atlas-release-dryrun/actions/runs/41379616572) green, a pre-release with wheel, sdist, SBOM; `gh attestation verify` exit 0
  for both artifacts and the SBOM, 1 against another repo. An unsigned tag: [run 41379796826](https://github.com/cuongdinhngo/code-atlas-release-dryrun/actions/runs/41379796826) red.

## Phase 3 — execute

`implementer` landed Approach 1–6 in `4af0438d`…`42d2fc49` (3 commits); the main loop wrapped one SECURITY.md line
in `23d596c4`. **Verification sweep.** File axis: `git diff --stat bd242e59..HEAD` names 11 files, every one on the
change list; no deviation. Behaviour axis: Approach 1–6 as approved, with three choices recorded — SEC-SC-11's
criterion now says what W1 decided (tags signed and verified, `main` commits not required to be); the `build` job
also refuses a tag that no longer points at the triggering commit; a `release/PRERELEASE` marker carries H7 to the
checkout-less `publish` job. The implementer ran `ruff format` over `tests/` by mistake and restored every
unrelated file (`git status` clean of them; its test diff removes no line).

**Seen failing (R6.5).** With `advisory_drift`, `unverified_tags` and `release_shape` stubbed to `[]`,
`tests/test_release_discipline.py` went 14 failed · 29 passed (the planted signed-tag repo, 3 advisory cases, 10
workflow-shape variants); restored, 43 passed. `### Security` renamed in CHANGELOG → the real advisory arm red on
GHSA-66g7-7jr3-j5rc / 0.9.1. The settings-drift planted case is red with the rule removed. Targeted suite 305 passed;
`ruff check`, `mypy` clean; `gate.sh --fast` 21 passed · 0 failed · 2 skipped (pytest and tokens-to-answer, by
`--fast` — not a green gate).

**Offline dry run of the workflow's steps** (main loop, at `42d2fc49`): `uv build` with `SOURCE_DATE_EPOCH` gives
`code_atlas-0.9.1-py3-none-any.whl` and the sdist; `release_notes.py check v0.9.1` rc 0, `notes 0.9.1` prints the
entry, `prerelease 0.10.0rc1` rc 0 and `0.10.0` rc 1; the hashed-lock venv plus the wheel `--no-deps` installs and
`code-atlas-build --help` runs. Not run: `verify-tag` on GitHub, the SBOM scan, both attestations and
`gh release create` — AC4's exclusion.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The rule-book reviewer was waived by the run's argument; no
reviewer step ran (no `reviewer`, no `reviewer-max`, no native `/code-review`).

- **`challenger` round 1** (ticket-blind, 74,314 tokens, at `23d596c4`): 10 met · 2 partly met (1a signing, 1c the
  ruleset) · 2 not met (1b commit signing, AC4). Its 234-test run green.
  - **Important 1, taken** in `fb83b0c3`: the workflow read `.github/allowed_signers` from the tagged tree, so a
    commit could add its own key and sign with it. The signers file now comes from `main`, the tagged commit must be
    on `main` (`merge-base --is-ancestor`), and checkout fetches full history. `release_shape` names both, and the
    planted variants "signers read from the tag's tree" and "a tag off main" are red — seen failing with the two new
    rules disabled (3 failed, 10 passed), green restored (46 passed).
  - **Important 2, not taken**: commit signing — W1, ratified 2026-11-02 (not required).
  - **Important 3, not taken**: AC4 — the recorded exclusion; the first real tag also needs W2's signers file.
  - **Important 4, partly taken**: SECURITY.md now says the trust root is `main`'s file; the ruleset setting stays
    W3's drift until the maintainer switches it on.
  - Minor 6, taken: provenance must cover both the wheel and the sdist ("provenance misses the sdist" red).
    Minor 5 (the real signed-tag arm checks zero tags until 0.10.0), 7 (`setuptools>=68` unpinned in the build
    backend) and 8 (the verify lines name this repository; a fork adjusts `--repo`), not taken: disclosed.
- **Round 2: verify-only, main loop**, at `fb83b0c3`: the `Verify the tag signature` step, extracted from
  `release.yml`, run against a throwaway origin — no signers on `main` rc 1; a good signed tag on `main` rc 0
  ("Good \"git\" signature"); an unsigned tag rc 1; a key added on a side branch and tagged there rc 1 ("the tagged
  commit is not on main"); that key's tag on `main` whose file lacks it rc 1 ("No principal matched").

Verdict: clean (challenger only — REVIEWER: OFF), Important 1 landed, Importants 2–4 are the ASSUMED decisions and
the AC4 exclusion.
`Ph3/4 proven by` (all `tests/test_release_discipline.py`): AC1 → the planted signed-tag repo and the real arm
from `SIGNED_FROM`, plus `tests/test_settings_drift.py` for the ruleset reader; AC2 → `release_shape` and its 13
planted variants, `tests/test_ci_hardening.py` over `release.yml`, the release-notes arms and the offline dry run;
AC3 → doc review (README, SECURITY.md, the runbook); AC4 → exclusion; AC5 → the real advisory arm and its planted
cases; AC6 → `docs/runbooks/releasing.md`; C1 → `tests/test_security_standard.py`.

**The final gate caught two repo-wide guards** the targeted run never reached, on the host and in Docker alike
(5713 passed · 2 failed at `2f0b6a7b`): `test_dependency_lock` refused the SBOM venv's two `uv pip install` lines,
and `test_no_client_identifiers` refused the tests' `@example.test` identities. Fixed in `38f00146`: the SBOM
environment is `uv sync --frozen --no-dev --no-editable` into a temp venv (the lock plus code-atlas built from the tag,
the install the CI install job already checks — a recorded deviation from H2's "wheel `--no-deps`"; checked offline:
`code_atlas-0.9.1.dist-info` and the locked `fastmcp` land in it), and the identities use `example.com`. Same files as
the reviewed set; verified in the main loop.

Reviewed at 2f0b6a7b; gate fix at 38f00146.

## Phase 5 — finalise

**Durable lesson.** 431-C1 `a-trust-root-never-rides-in-the-input` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate:** the full suite on the host and in Docker from a clean clone, on the final tree.

Ran at 38f00146

```
$ .venv/bin/python -m pytest -q
5715 passed, 4 skipped in 850.91s (0:14:10)
$ scripts/docker-test.sh
5711 passed, 8 skipped in 857.72s (0:14:17)
```

### Outward actions

Under the handover: push `feat/431-release-pipeline`; open its PR against `main`.
Deferred to the maintainer: ratify W1–W3 (ratified 2026-11-02); commit `.github/allowed_signers` to `main` (W2); switch on the `v*` tag
ruleset's signature rule (W3); run a pre-release tag in a fork and record its run URL here (AC4, done 2026-11-02); merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 3 execute | `implementer` | 1 | 143,604 |
| 4 review | ticket-blind `challenger` | 1 | 74,314 |

`LEDGER TOTAL: 217,918 · top cost driver: 3 execute / implementer` — main loop unmeasured.
