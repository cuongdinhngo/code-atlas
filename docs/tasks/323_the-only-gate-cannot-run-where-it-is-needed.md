---
id: 323
slug: the-only-gate-cannot-run-where-it-is-needed
title: "The gate is the only gate, yet it needs four runtimes on PATH and has no container route — so on any host missing one it returns exit 2 and there is nothing else to fall back to"
phase: 1.5b
milestone: Measure
status: todo
depends_on: [268]
---

## Why this exists

AGENTS.md states the arrangement plainly: **Actions report `fail` in ~3 s without running (0 steps,
unbillable), so `gh pr checks` is not a second opinion — the local gate is the only gate.** And
`scripts/gate.sh` is honest about what it needs: every check whose tool is absent is `_record SKIP`,
skips turn the summary red, and **exit 2 means a check was skipped, which is not a pass (R6.5)**.

Put together: on a host without `php`, `composer`, `node` **and** a `.venv`, the only gate this
project has cannot return a pass — and there is no second opinion to fall back on, because CI's
failure is unbillable rather than informative. **Eleven** of the twenty checks carry a
missing-tool SKIP arm (`gate.sh:127-219`): both `npm ci`s, the php-adapter dep probe,
`tokens-to-answer`, `composer validate`, `php -l`, `phpstan level max`, both `tsc` runs, and the two
Python-adapter analyser checks. A twelfth (`:274`) is gated on `origin/main` instead of a tool.

`scripts/docker-test.sh` already solves the neighbouring problem — **the test suite** runs in a
container with every adapter present, and AGENTS.md pins the expected counts (4,288 passed /
5 skipped). The gate has no equivalent: `grep -n docker scripts/gate.sh` returns **zero matches**.

**And today's image cannot run the gate even if it were handed to it.** Two gaps, both one line:
- `composer install **--no-dev**` (`docker/Dockerfile:27`) omits **phpstan**, so `gate.sh:180` takes
  its SKIP arm.
- only `npm ci --prefix adapters/typescript` is run (`:29`), never `adapters/sql`, so `gate.sh:199`
  takes its SKIP arm too.

**A third gap decides the design.** `.dockerignore:3` excludes `.git`, with a stated reason (ruff in
the image would otherwise have no gitignore to honour). But `gate.sh:274` skips the R7.3
AI-attribution-trailer check when there is no `origin/main` to compare against — so a container that
only holds a `COPY`'d snapshot **can never reach GATE GREEN**, whatever else is fixed. This is the
decision the ticket must make, not discover during implementation.

## Goal

One command produces the same twenty-check verdict on any host with Docker, so "the only gate" is
actually reachable — and a skip caused by the *host* stops being indistinguishable from a skip caused
by the *tree*.

## Scope / Deliverables

1. **`scripts/gate.sh --docker`** — builds the image and re-runs the same gate inside it. `gate.sh`
   stays the single list of what is checked; `--docker` changes only **where** it runs. The image
   must not grow its own copy of the check list.
2. **Decide the `.git` question, in the ticket's design, with the rejected option written down.**
   Two candidates:
   - **Bind-mount the working tree** (`docker run -v "$root:/repo" -w /repo`) — gates exactly what
     you are about to push, `.git` included, no rebuild per edit. Cost: the mounted tree has no
     `vendor/` or `node_modules`, so the image's pre-installed deps must be reachable from it.
   - **Stop excluding `.git` from the build context** — self-contained, no mount, layer cache keeps
     it cheap. Cost: reverses a deliberate `.dockerignore` decision and its stated ruff side effect.
3. **Close the two image gaps** — `composer install` with dev deps (phpstan), and
   `npm ci --prefix adapters/sql`.
4. **Recursion guard.** The inner run must not re-enter `--docker`. Block it on an **argv flag, not
   an env var** — an env var leaks into every child process and is the harder thing to reason about.
5. **Name the host in the verdict.** The summary line says whether this was the host gate or the
   container gate, so a pasted "GATE GREEN" in a PR is attributable.
6. **Resolve the stale header while here.** `gate.sh:4-6` tells the reader *"GitHub Actions DO run
   for this repo … after pushing, read `gh pr checks <n>` too"*. AGENTS.md says the opposite and says
   why. One of the two is wrong; they cannot both stand, and `test_ci_and_gate_agree.py`'s own
   docstring records that this header has already been wrong once before.

## Constraints

- **R6.5** — `--docker` must not become a way to launder a skip into a pass. A check that skips
  inside the container still counts as a skip and still yields exit 2.
- **`tests/test_ci_and_gate_agree.py` stays green** — it matches on the commands each file runs, so a
  docker branch must not disturb the shared-check table.
- The image stays a *test/dev* image; `docker/Dockerfile.runtime` is the shipped server and is out of
  scope.
- No new dependency for the ordinary host path: `scripts/gate.sh` with no flag behaves exactly as
  today, byte-identical summary included.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** On a host with Docker and **none** of `php` / `composer` / `node` on PATH,
  `scripts/gate.sh --docker` reaches **GATE GREEN — 20 passed · 0 failed · 0 skipped** on a clean
  tree.
- **AC2** The same command on a tree with a real failure (e.g. a ruff error) exits non-zero and names
  the failing check — the container path is not a green-stamp machine.
- **AC3** The R7.3 trailer check **runs** inside the container rather than skipping — whichever
  option (2) chose, this is the one that proves it was chosen correctly.
- **AC4** `phpstan level max` and `tsc … (SQL adapter)` both report PASS inside the container, not
  SKIP.
- **AC5** Invoking the inner gate with `--docker` again is refused rather than recursing.
- **AC6** `scripts/gate.sh` with no flag produces the same summary as today on a fully-provisioned
  host; `tests/test_ci_and_gate_agree.py` is green.

## Out of scope

- Making CI build the images. That is the standing follow-up in
  [`BACKLOG.md`](../BACKLOG.md#follow-ups-not-yet-ticketed) — but note this ticket **raises its
  stakes**: once the gate runs through `docker/Dockerfile`, that file rotting silently stops being a
  cosmetic risk. Worth re-reading that follow-up when this lands, not folding it in here.
- `scripts/setup.py`'s silent degradation — it sets up "every adapter whose runtime is present" and
  reports success either way. A real but separate defect, and a smaller one.
- Windows/macOS parity beyond "Docker is present"; the container is Linux and that is the point.
- Any change to what the twenty checks verify.

## References
`scripts/gate.sh:4-6` (the stale header), `:14-16` (exit-2 contract), `:127-219` (the eleven
runtime-gated SKIP arms), `:180` (phpstan), `:199` (SQL tsc), `:274` (R7.3 needs `origin/main`);
`docker/Dockerfile:27` (`--no-dev`), `:29` (typescript-only `npm ci`); `.dockerignore:3` (`.git`);
`scripts/docker-test.sh`; `tests/test_ci_and_gate_agree.py`; AGENTS.md — *"Before a PR or a push"*
and *"Running the full test suite"*; ENGINEERING_RULES R6.5.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 323 — gate.sh --docker (working doc)

- **Ticket:** 323 · local
- **Type:** enhancement (tooling)
- **Repo(s) / Porting:** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/323_the-only-gate-cannot-run-where-it-is-needed.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** design

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — the ticket hands the `.git` question to design (Scope 2) and fixes every other shape.

## Requirements matrix

`SECTIONS: 7 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope · References) | 7 decomposed | ROWS: C=5 R=6 G=1 AC=6`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | one command, same twenty-check verdict on any host with Docker | `gate.sh --docker` | D1–D3 | AC1 | ✅ |
| R1 | Scope 1 | `--docker` builds the image and re-runs the same gate inside it | outer branch → `docker build` + `docker run … scripts/gate.sh --in-container` | D1 | AC1 proving | ✅ |
| R2 | Scope 2 | decide the `.git` question with the rejected option written | stop excluding `.git` (Phase 2) | D2 | AC3 | ✅ |
| R3 | Scope 3 | composer with dev deps; `npm ci --prefix adapters/sql` | Dockerfile edits | D3 | AC4 | ✅ |
| R4 | Scope 4 | recursion guard on an argv flag | `--in-container` + `--docker` refused | D1 | AC5 | ✅ |
| R5 | Scope 5 | summary names host vs container | container summary suffixed; host unchanged (AC6) | D1 | AC1 AC6 | ✅ |
| R6 | Scope 6 | resolve the stale header | header follows AGENTS.md (Actions: 0 steps) | D1 D4 | review | ✅ |
| C1 | Constraints | R6.5 — container skip still exit 2 | same `_record`/exit logic runs inside | D1 | AC1 AC2 | ✅ |
| C2 | Constraints | `test_ci_and_gate_agree.py` green | shared-check commands untouched | D1 | AC6 | ✅ |
| C3 | Constraints | test/dev image only; runtime out of scope | Dockerfile.runtime untouched (explicit COPYs) | D2 D3 | sweep | ✅ |
| C4 | Constraints | no-flag path byte-identical summary | arg parse only; summary text untouched on host | D1 | AC6 | ✅ |
| C5 | Constraints | comments ≤ 3 lines | R7.5 | D1–D3 | review | ✅ |
| AC1 | AC | no php/composer/node on PATH → GATE GREEN 20/0/0 | stripped-PATH e2e run | D1–D3 | e2e record | ✅ |
| AC2 | AC | real failure → non-zero, names the check | injected ruff error | D1 | e2e record | ✅ |
| AC3 | AC | R7.3 runs inside, not SKIP | from AC1 log | D2 | e2e record | ✅ |
| AC4 | AC | phpstan + SQL tsc PASS inside | from AC1 log | D3 | e2e record | ✅ |
| AC5 | AC | inner `--docker` refused | `--in-container --docker` exits 64 | D1 | proving | ✅ |
| AC6 | AC | no-flag summary unchanged; agree test green | host gate summary vs 313's host run | D1 | e2e + test | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

- Q1 (self-resolved): Scope 5 (summary names the host) vs Constraint "byte-identical summary" on the no-flag path → the host summary stays exactly as today (Constraints bullet 4, AC6) and only the container run carries the label; absence of the label is the host gate.

## Phase 1 — Analysis

- Gap: `grep -n docker scripts/gate.sh` → 0 matches; `docker/Dockerfile:27` `--no-dev` (no phpstan → `gate.sh` phpstan SKIP); `:29` only the TS `npm ci` (SQL tsc SKIP); `.dockerignore:3` `.git` (R7.3 SKIP: no `origin/main`); `gate.sh:4-6` claims Actions run, while `gh run view 35948207877` shows every job `failure steps=0` (AGENTS.md is right).
- Blast radius: `docker/Dockerfile` is also `scripts/docker-test.sh`'s image — `.git` in context changes that image (ruff now honours `.gitignore`; git-aware tests see a repo); `Dockerfile.runtime` COPYs explicit paths, so its image is unchanged though its context grows by `.git` (25M). `tests/test_ci_and_gate_agree.py` matches command substrings in `gate.sh`. AGENTS.md "Before a PR" names `gate.sh`.

`TRACK: backend — 0/6 touched files under UI paths`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R6.5 (change-type) ✅ the inner run is the same gate and docker run returns its exit status (skip is still 2) · R7.5 (change-type) ✅ new comments ≤ 3 lines · R7.2 (change-type) ✅ ledger row + BACKLOG removal`

Baseline record — tree `660281a140e52a4ccd0a71f1e43bfd9b639c79bc` (historical, shared with 313's run; re-run on the reviewed tree in Phase 4). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider`, output tail:

```
4376 passed, 4 skipped in 362.21s (0:06:02)
```

`BASELINE: green`

## Phase 2 — Design

- Approach:
  - A1 `gate.sh` parses `--fast` / `--docker` / `--in-container` from any position. `--docker` without `--in-container`: needs `docker` on PATH (else a named refusal, exit 2), builds `docker/Dockerfile` as `code-atlas-test`, then `exec docker run --rm code-atlas-test sh scripts/gate.sh --in-container [--fast]` — the image never holds its own check list.
  - A2 `--in-container` with `--docker` → refused before any check, exit 64. Guard is argv, never env.
  - A3 `--in-container` suffixes the two verdict lines with `(container gate)`; the no-flag path prints today's bytes.
  - A4 `.git` is no longer excluded from the build context, so the copied tree carries `origin/main` and R7.3 runs; `.mango` stays excluded, comment updated.
  - A5 Dockerfile: `composer install` with dev deps; `npm ci --prefix adapters/sql` beside the TS one, keyed on its lock file.
  - A6 header lines 4-6 say what AGENTS.md says: Actions report `fail` with 0 steps, so this script is the only gate; `test_ci_and_gate_agree.py`'s docstring stops calling that claim false.
- Rejected: **bind-mounting the working tree** (`-v "$root:/repo"`) — the inner gate's `compileall -f`, `pytest` and `npm ci` then write root-owned `.pyc` and `node_modules` into the host tree, and the host venv's interpreter symlink does not resolve inside the image; self-contained copy is cheaper to reason about. An env-var recursion guard — rejected by the ticket (leaks into children).

**Assumptions:** the copied `.git` resolves `origin/main` inside the image — novel-untested → proven by AC3 (the e2e run shows R7.3 PASS with a commit count, not SKIP). `docker run`'s exit status is the inner gate's — verified (docker propagates the container's exit code).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | arg parse, `--docker` route, recursion guard, container label, header | scripts/gate.sh | `test_ci_and_gate_agree.py` substrings; AGENTS.md gate section | R1 R4 R5 R6 C1 C2 C4 | 1/1 |
| D2 | keep `.git` in the context | .dockerignore | docker-test.sh image; Dockerfile.runtime context size | R2 C3 | 1/1 |
| D3 | dev composer deps; SQL `npm ci` | docker/Dockerfile | docker-test.sh image and its pinned counts | R3 | 1/1 |
| D4 | proving test; agree-test docstring | tests/test_gate_docker_route.py · tests/test_ci_and_gate_agree.py | new file; docstring only | AC5 R6 | 1/1 |
| D5 | AGENTS.md gate line; ticket; BACKLOG; TOKEN_LEDGER | AGENTS.md · docs/tasks/323_… · docs/BACKLOG.md · docs/TOKEN_LEDGER.md | agent chain budget; doc budget; bookkeeping test | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | e2e | e2e (recorded `gate.sh --docker` run, php/composer/node stripped from PATH) | n/a | ✅ |
| AC2 | e2e | e2e (recorded run with an injected ruff error) | n/a | ✅ |
| AC3 | e2e | e2e (R7.3 line of the AC1 run) | n/a | ✅ |
| AC4 | e2e | e2e (phpstan + SQL tsc lines of the AC1 run) | n/a | ✅ |
| AC5 | integration | integration (subprocess `sh scripts/gate.sh`) | n/a | ✅ |
| AC6 | e2e | e2e (host gate summary) + integration (`test_ci_and_gate_agree.py`) | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_gate_docker_route.py -q` (AC5 + the route, with a stub `docker` on PATH); AC1–AC4/AC6 are the recorded e2e runs in Phase 3/4.

Rollback: revert the branch; the image rebuilds from the previous Dockerfile. Porting: single repo.

`SCOPE: M` (unchanged)

