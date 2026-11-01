---
id: 426
slug: container-hardening
title: "The runtime image runs as a fixed non-root user from digest-pinned bases, and the documented run line drops every privilege it does not need"
phase: 2
milestone: Trust
status: done
depends_on: [425]
---

## Why this exists

Both images build from `python:3.12-slim-bookworm` by tag, fetch composer with
`curl … | php`, and run as root. Running as root is also why 0.9.1 leaves a residual: git refuses
a host-owned `.git` mounted into a root container, so a tracked index cannot be refused there (420,
SECURITY.md *Known limitations*). The README run line passes no hardening flags.

## Acceptance

1. **Non-root:** `docker/Dockerfile.runtime` ends with `USER` at a fixed UID/GID; the README run
   line passes `--user "$(id -u):$(id -g)"` so the mounted repo's owner matches and git answers.
2. **Pinned bases:** every `FROM` names a digest (tag kept as a comment); composer comes from a
   digest-pinned `composer` image by `COPY --from`, never `curl | php`.
3. **Documented run line:** `--read-only --tmpfs /tmp --cap-drop=ALL
   --security-opt=no-new-privileges --network=none`, one writable index mount. A smoke test runs
   the image with exactly those flags and gets an MCP `initialize` answer.
4. **The 420 residual closes in the image:** with `--user`, a tracked index in the mounted repo is
   refused (fixture), and SECURITY.md's limitation narrows to "git cannot run".
5. **Context hygiene:** `.dockerignore` and `.gitignore` cover `.env*`, key files and `.mcp.json`;
   no `.git` credentials reach a layer (a test greps the build context rules).
6. **Scan:** the image is scanned in CI (Trivy or Grype), failing on a fixable critical; images
   stay build-only (not published).

## Call sites

`docker/Dockerfile`, `docker/Dockerfile.runtime`, `.dockerignore`, `.gitignore`, `README.md`
(container section), `scripts/docker-test.sh`, `.github/workflows/ci.yml` (image job),
`SECURITY.md`; standard rows SEC-CT-01..05, SEC-SC-09 (files).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 426 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** none — the PR is the handover.
- `TRACK: backend` · Run mode: `autorun 426 - 429` — `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: max`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/426-container-hardening` from `main` at `a0c454f2`. Contract `.mango/run-contract-426.txt`.
  RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 0 want-decision asked | 8 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `docker/Dockerfile`, `docker/Dockerfile.runtime`, `.dockerignore`, `.gitignore`, `README.md`
(*In a container*), `scripts/docker-test.sh`, `.github/workflows/ci.yml` (`test-image`), `SECURITY.md`
(*Known limitations*) resolve; rows SEC-CT-01..05 and SEC-SC-09 carry `open: 426`. Both bases resolve by
digest today: `python:3.12-slim-bookworm@sha256:e697c818…d337`, `composer:2@sha256:4ed71c38…e0a`. The runtime
image installs no `git`, so the tracked-index check there cannot run even with `--user` — the residual needs
git in the image as well as a matching owner. The index writes land under `.code-atlas/` (`store.py`,
`index_lock.py`, `onboarding/artifact.py` `CACHE_DIR`); `generate_onboarding` also writes `docs/onboarding/`
(`artifact.py:97`) — missed here, caught by the reviewer (Phase 4).
Recall: the two handles this change meets — `a-subset-reader-must-fail-closed` and
`a-loader-guard-misses-the-entry-that-loads-nothing` — are retired into R6.5 and R6.7 (promoted 2026-11-01), so
they reach this ticket as rules at analysis, not as claims.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the fixed user | how | `USER 10001:10001` (a system user created in the image, no login shell) and `ENV HOME=/tmp`, so git and Python find a writable home under `--read-only`; `--user` overrides both IDs at run time |
| H2 | pinned bases | how | every `FROM` is `<tag>@sha256:<digest>` with the tag kept; composer arrives by `COPY --from=composer:2@sha256:… /usr/bin/composer` in both files — no `curl … \| php`; a `docker` entry in `.github/dependabot.yml` moves the digests, so a pin is not a freeze |
| H3 | the run line | how | `--user "$(id -u):$(id -g)" --read-only --tmpfs /tmp --cap-drop=ALL --security-opt=no-new-privileges --network=none`, the repo mounted `:ro` at `/workspace` and its `.code-atlas/` mounted writable over it — the one writable mount; the flags live once in `scripts/container_smoke.py` and a test holds README to them |
| H4 | closing the 420 residual | how | the runtime image installs `git` (no recommends); with `--user` matching the repo owner git answers, and a fixture repo committing `.code-atlas/graph.db` is refused by the image; SECURITY.md's limitation narrows to "git cannot run" |
| H5 | context hygiene | how | `.dockerignore` and `.gitignore` cover `.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `.mcp.json`; `.dockerignore` also drops `.git/config` (where a remote token or credential helper lives) while keeping the refs the gate's R7.3 check reads |
| H6 | the scan | how | a CI job builds `Dockerfile.runtime`, runs the smoke script, then scans with Grype (`anchore/scan-action`, SHA-pinned, `severity-cutoff: critical`, `only-fixed: true`, `fail-build: true`); nothing is pushed |
| H7 | the smoke test | how | `scripts/container_smoke.py` (stdlib only) runs the image with exactly the documented flags, speaks MCP `initialize` over stdio and asserts an answer, then repeats against a tracked-index fixture and asserts the refusal |
| H8 | gate parity | how | whatever `tests/test_ci_and_gate_agree.py` requires of a new CI job lands in `scripts/gate.sh` (`--docker` route) in the same change |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=6`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/12 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "run as root … a tracked index cannot be refused there" | non-root, pinned, hardened run line, the residual closed | ⚠ |
| AC1 | Acc 1 | "`USER` at a fixed UID/GID; … `--user \"$(id -u):$(id -g)\"`" | H1, H3 | ⚠ |
| AC2 | Acc 2 | "every `FROM` names a digest … composer … by `COPY --from`" | H2 | ⚠ |
| AC3 | Acc 3 | "`--read-only --tmpfs /tmp --cap-drop=ALL …` … A smoke test … gets an MCP `initialize` answer" | H3, H7 | ⚠ |
| AC4 | Acc 4 | "with `--user`, a tracked index in the mounted repo is refused (fixture)" | H4, H7 | ⚠ |
| AC5 | Acc 5 | "`.dockerignore` and `.gitignore` cover `.env*`, key files and `.mcp.json`; no `.git` credentials" | H5 | ⚠ |
| AC6 | Acc 6 | "scanned in CI (Trivy or Grype), failing on a fixable critical; … build-only" | H6 | ⚠ |
| C1 | Call sites | "standard rows SEC-CT-01..05, SEC-SC-09 (files)" | each closes on its test | ⚠ |

`BASELINE: green — the suite on `main` at a0c454f2: 5565 passed, 4 skipped (host Linux, worktree)`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §5 (change-type) ✅ R5.3: a context rule the test cannot classify fails loud · §6 (change-type) ✅ R6.5: each guard seen failing on the base, a sweep fails closed; R6.7: every FROM read, not a named list · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §8 (change-type) ✅ R8.2: no new runtime dependency beyond the image's git · §9 (change-type) ✅ R9.6: workflow actions pinned by SHA, least-privilege permissions`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

R6.5 (widened): the context-rule test classifies every `.dockerignore` line and fails on one it cannot place.
R6.7: the pin test walks every `FROM` and `COPY --from` in both Dockerfiles, so a third stage is read too.

**Approach.**
1. `docker/Dockerfile.runtime`: digest-pinned bases, composer by `COPY --from`, `git` in the runtime stage,
   a system user 10001, `ENV HOME=/tmp`, `USER 10001:10001`; the header comment shows the hardened run line.
2. `docker/Dockerfile`: digest-pinned base, composer by `COPY --from`, no `curl | php` (the test image stays root:
   it is a build-and-test image, not shipped).
3. `.dockerignore`, `.gitignore`: H5. `.github/dependabot.yml`: a `docker` ecosystem entry for `/docker`.
4. `scripts/container_smoke.py`: `RUN_FLAGS`, the `initialize` arm, the tracked-index arm.
5. `.github/workflows/ci.yml`: a `runtime-image` job — build, smoke, Grype; `push: false`. `scripts/gate.sh` and
   `tests/test_ci_and_gate_agree.py` as parity requires.
6. `tests/test_container_hardening.py`: USER fixed and last; every `FROM`/`COPY --from` digest-pinned; no piped
   installer; README's run line carries every `RUN_FLAGS` flag; planted secret names excluded by both ignore
   files; the CI job scans with a fail-on-fixable-critical setting and pushes nothing.
7. Docs: README (*In a container*), SECURITY.md (the two limitations), SEC-CT-01..05 and SEC-SC-09 rows,
   CHANGELOG *Unreleased*.

**Rejected:** a separate index volume through `CA_DB_PATH` — `generate_onboarding` writes `.code-atlas/onboarding`
under the repo root, so the index directory has to be that path anyway; Trivy — either meets the ticket, and
Grype is one pinned action with nothing else to install.

**Change list:** `docker/Dockerfile`, `docker/Dockerfile.runtime`, `.dockerignore`, `.gitignore`,
`.github/dependabot.yml`, `.github/workflows/ci.yml`, `scripts/gate.sh`, new `scripts/container_smoke.py`, new
`tests/test_container_hardening.py`, `tests/test_ci_and_gate_agree.py`, `README.md`, `SECURITY.md`,
`docs/SECURITY_STANDARD.md`, `CHANGELOG.md`; bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`,
`docs/LESSONS.md`, this file).

**Proving tests:** `tests/test_container_hardening.py` (each arm seen red on the base) and
`scripts/container_smoke.py` against the built runtime image (red on the base image: it runs as root, and has
no git to refuse the tracked index).

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

`implementer` landed Approach 1–7 in `e4b21153`…`d23e1aa1` (5 commits). **Verification sweep.** File axis: every
changed file is on the change list; `.github/dependabot.yml` and `scripts/gate.sh` did not change — the `docker`
Dependabot entry already existed (424), and `tests/test_gate_docker_route.py` pins `--docker` to one build and one
run, so the smoke and the scan are `CI_ONLY` rows in `tests/test_ci_and_gate_agree.py`, each with its reason.
Behaviour axis: Approach 1–7 as approved, plus one recorded deviation — the first Grype run found a fixable
critical in the image's own `uv` (0.11.28, GHSA-hq85-5cpj-mr62), so the runtime stage installs `uv`, syncs and
uninstalls it in one `RUN`; the image ships no installer. The smoke script also checks the image's configured user.

**Seen failing (R6.5).** `tests/test_container_hardening.py` on a worktree of the base `a0c454f2`: 8 failed, 15
passed (the passes are the parsers' planted-input self-tests and the "ignores no tracked file" guard). The smoke
against an image built from the base: `FAIL image user`, `ok initialize`, `FAIL tracked index refused` (the base
image has no git, so it opened the planted file: `file is not a database`). Against the final image: all three ok.
Grype (`anchore/grype:v0.121.0`, `--only-fixed --fail-on critical`): rc=2 on the first image (the `uv` finding),
rc=0 after the removal.

## Phase 4 — review

`REVIEWER: ON (reviewer-max — cost_tier max, security-tagged)` · `CHALLENGER: ON`. Git isolation held: the
worktree's reflog was identical before and after both review dispatches.

- **`reviewer-max` round 1** (113,301 tokens): CHANGES REQUESTED — 2 Important, 6 Minor/nit. Taken in `83336ab5`
  and the commit before it:
  - **Important 1** — the documented line mounts the repo read-only, and `generate_onboarding` writes
    `docs/onboarding/`, so it failed opaquely (`Read-only file system: '/workspace/docs'`); the design's premise
    missed that writer. The line keeps one writable mount; README and SECURITY.md name the extra mount
    `generate_onboarding` needs; the smoke gains an index-build arm (writes only under `.code-atlas/`) and an
    onboarding arm with the extra mount — each red with its mount removed.
  - **Important 2** (R6.7) — the pin guard read a hand-kept pair of Dockerfiles; the set is now derived from the
    tree, and a planted third Dockerfile with an unpinned `FROM` fails it.
  - Minor, taken: a `.dockerignore` character range is refused, not mis-read; the runtime header is three lines
    and points at README; the job may grant nothing broader than read; `uv sync --no-cache` (74 MB gone).
  - Informational: `runtime-image` is not a required check — a ruleset change, left to the maintainer.
- **`challenger` round 1** (ticket-blind, 62,523 tokens): 13 met · 0 partly · 0 not met. Five planted mutations
  each failed their test. Minor, not taken: `.gitignore` already ignores `.mcp.json` on `main`; `.git/` beyond
  `config` stays (the gate reads the refs). Its Minor 3 (no write arm) is the reviewer's Important 1, taken.
- **Round 2: verify-only, main loop**, at `83336ab5`: the smoke against a rebuilt image — `ok` on all five arms;
  Grype `--only-fixed --fail-on critical` rc=0.

Verdict: clean (reviewer-max and challenger), both rounds' findings landed.
`Ph3/4 proven by` (all `tests/test_container_hardening.py` unless named): AC1 → the fixed-user test and the smoke's
`image user` arm; AC2 → `test_every_from_and_copy_from_is_pinned_by_digest`,
`test_every_dockerfile_that_runs_composer_gets_it_from_its_pinned_image`, the piped-installer walk; AC3 →
`test_the_readme_run_line_carries_every_documented_flag` and the smoke's `initialize` and build arms; AC4 → the smoke's
`tracked index refused` arm, SECURITY.md narrowed; AC5 → the two planted-secret ignore tests; AC6 →
`test_the_ci_job_builds_smokes_and_scans_without_pushing`; C1 → `tests/test_security_standard.py`.

Reviewed at 83336ab5.

## Phase 5 — finalise

**Durable lesson.** 426-C1 `a-sandbox-claim-calls-every-writer` (new, type 2). Sighting: the R6.7 class
`a-loader-guard-misses-the-entry-that-loads-nothing` (+426 — the reviewer's Important 2, a hand-kept Dockerfile
pair, after the design note had cited R6.7).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate:** the suite in Docker on the final tree, from a clean clone (a worktree's `.git` is a file, so
the test image needs a clone to carry the refs).

Ran at 83336ab5

```
$ scripts/docker-test.sh
5587 passed, 8 skipped in 800.30s (0:13:20)
$ python3 scripts/container_smoke.py code-atlas-server
ok   image user · ok initialize · ok tracked index refused · ok index build writes only .code-atlas · ok generate_onboarding with its mount
$ grype code-atlas-server --only-fixed --fail-on critical
rc=0
```

### Outward actions

Under the handover: push `feat/426-container-hardening`; open its PR against `main`.
Deferred to the maintainer: ratify the `uv` removal from the runtime image; add `runtime-image` to the `main`
ruleset's required checks; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 3 execute | `implementer` | 1 | 122,777 |
| 4 review | `reviewer-max` | 1 | 113,301 |
| 4 review | ticket-blind `challenger` | 1 | 62,523 |
| 4 review | `implementer` (review fixes, resumed) | 2 | 145,429 |

`LEDGER TOTAL: 444,030 · top cost driver: 4 review / implementer` — main loop unmeasured.

