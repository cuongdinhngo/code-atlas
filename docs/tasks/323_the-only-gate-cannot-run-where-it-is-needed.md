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
