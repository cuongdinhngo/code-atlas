---
id: 001
slug: project-scaffold
title: Project scaffold & tooling
phase: 1
milestone: Setup
status: in-progress
depends_on: []
---

## Goal
Stand up the Python package and dev tooling so every later task has a home.

## Scope / Deliverables
- `pyproject.toml` (package `code_atlas`, deps: `fastmcp`; dev: `pytest`, `ruff`, `mypy`).
- Package skeleton per §5: `code_atlas/{main,config,contract,adapter,store,indexer,resolver,gitutil,ignore}.py` (stubs) + `code_atlas/tools/`.
- `adapters/` and `tests/{contract,fixtures,}` directories.
- `ruff`/`mypy`/`pytest` configured and runnable; a trivial passing test.
- CI (`.github/workflows/ci.yml`, already in repo) turns green: ruff · mypy · pytest + the R1.1/R2.2 grep-gates run on every PR.
- Token-ledger bootstrap: the **Token usage on PR** rule in `CLAUDE.md` + the Token usage roll-up table in `docs/BACKLOG.md` — seed the token-tracking process at scaffold time so every later task inherits it. *(Folded into this ticket during Phase 4 by approval; originally a same-session governance request.)*

## Acceptance criteria
- `pip install -e .` succeeds; `pytest` runs green; `ruff check` clean.
- Import `code_atlas` works; no per-language code anywhere in the package.
- CI passes on the PR: `test` job runs ruff/mypy/pytest (no longer skipped), `guardrails` job green.

## References
Plan §5 (architecture, repo layout).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 001 — Project scaffold & tooling (working doc)

- **Ticket:** 001 · docs/tasks/001_project-scaffold.md · repo https://github.com/cuongdinhngo/code-atlas
- **Type:** enhancement (greenfield scaffold)
- **Repo(s) / Porting:** `app` (`.`) — single repo, no porting
- **SCOPE:** M
- **STRUCTURE:** native (headers map to `ticket_header_schema`; `References` is an unmapped informational pointer)
- **TRACK:** backend (`config.track=backend`; all touched files are Python core + tooling, zero UI)
- **TIER:** full (SCOPE=M, multi-file, universal requirement with N>1 → not lite-eligible)
- **BASELINE:** red (unsatisfiable on fresh checkout — expected for a scaffold task)
  - `pytest` → **no tests collected** (nothing to collect yet); `mypy` → no files → no issues; `ruff` → **not installed locally** (provided by the `[dev]` extra this task adds).
  - baseline exclusions (pre-existing failures outside this change): **none** — the repo has zero `.py` files; every result above is "nothing built yet", not a defect. DoD for later phases = **prove the delta is green** (pytest green after scaffold; ruff/mypy clean once installed).

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=5 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Stand up the Python package and dev tooling so every later task has a home." | Create the `code_atlas` package + dev toolchain so subsequent tasks have a working home. | No `pyproject.toml`, no `code_atlas/` (repo survey) | 7/7 | package + toolchain live; `import code_atlas` ok; pytest green | ✅ |
| R1 | Scope | "`pyproject.toml` (package `code_atlas`, deps: `fastmcp`; dev: `pytest`, `ruff`, `mypy`)." | Author `pyproject.toml`: runtime dep `fastmcp`; `[dev]` optional-deps `pytest`/`ruff`/`mypy`; installable as `code_atlas`. | Absent (survey); CI installs `-e ".[dev]"` (ci.yml:24) | 1/1 | `pyproject.toml` @ 27bc105; `pip install -e ".[dev]"` ok | ✅ |
| R2 | Scope | "Package skeleton per §5: `code_atlas/{main,config,contract,adapter,store,indexer,resolver,gitutil,ignore}.py` (stubs) + `code_atlas/tools/`." | Create 9 named module stubs + `tools/` package (+ enabling `__init__.py`). **Per-item checklist, N=9** — see Inventory. | Layout matches CONVENTION §1 / PLAN §5 (PLAN.md:145-154) | 11/11 | 9 stubs + 2 `__init__` @ 27bc105 (inventory 9/9 ✅); mypy 11 files clean | ✅ |
| R3 | Scope | "`adapters/` and `tests/{contract,fixtures,}` directories." | Create `adapters/`, `tests/contract/`, `tests/fixtures/`, `tests/`. | Absent (survey) | 3/3 | `.gitkeep` @ 27bc105 in adapters/, tests/contract/, tests/fixtures/ | ✅ |
| R4 | Scope | "`ruff`/`mypy`/`pytest` configured and runnable; a trivial passing test." | Add tool config (ruff/mypy/pytest) to `pyproject.toml` + one trivial passing test under `tests/`. | ruff not installed locally (baseline) | 1/1 | `[tool.*]` in pyproject + `tests/test_smoke.py`; ruff/mypy/pytest all green | ✅ |
| R5 | Scope | "CI … turns green: ruff · mypy · pytest + the R1.1/R2.2 grep-gates run on every PR." | The committed `ci.yml` must go green: `test` job (ruff/mypy/pytest) + `guardrails` job (R1.1/R2.2). CI file already exists. | ci.yml present w/ conditional mypy/pytest steps (ci.yml:33,37) | 1/1 | PR #2 CI green: `lint·type·test` pass + `guardrails` pass (run 30444621501) | ✅ |
| R6 | Scope (folded in Ph4) | "Token-ledger bootstrap: Token-usage-on-PR rule + BACKLOG token table." | Add the `Token usage on PR` rule to `CLAUDE.md` and the Token usage roll-up table to `docs/BACKLOG.md`. | Same-session user request; approved to fold in at Gate-4 | 1/1 | `CLAUDE.md:36` + `docs/BACKLOG.md:47-55` @ 5478c5a | ✅ |
| AC1 | AC | "`pip install -e .` succeeds; `pytest` runs green; `ruff check` clean." | 3 command checks all exit 0; pytest green (≥1 passing test, 0 fail). | — | 1/1 | `pip install -e ".[dev]"` ok · `pytest` 1 passed · `ruff check .` clean (re-run by reviewer+challenger) | ✅ |
| AC2 | AC | "Import `code_atlas` works; no per-language code anywhere in the package." | `python -c "import code_atlas"` exits 0; R1.1 grep over `code_atlas/` finds no language branch. | R1.1 gate defined (ci.yml:46-53) | 1/1 | `import code_atlas` ok + R1.1 grep over `code_atlas/` → 0 hits (re-run by both agents) | ✅ |
| AC3 | AC | "CI passes on the PR: `test` job runs ruff/mypy/pytest (no longer skipped), `guardrails` job green." | On the PR: `test` job's mypy+pytest steps execute (not skipped) and pass; `guardrails` green. | Steps gated on `hashFiles('code_atlas/**/*.py')` / `hashFiles('tests/**/*.py')` (ci.yml:33,37) | 1/1 | PR #2: mypy+pytest steps ran (not skipped) & passed; guardrails green | ✅ |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met. (All ❌ pre-implementation — nothing built yet.)

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | `pip install -e .` ok · `pytest` green · `ruff check` clean | 3 processes exit 0; pytest exit 0 with ≥1 passed, 0 failed | Y | ✅ greppable/measurable — exit codes + pytest summary | none |
| AC2 | import works · no per-language code in package | `python -c "import code_atlas"` exit 0; `grep -rEn 'if.*\blanguage\b.*==|match.*\blanguage\b' code_atlas/` → 0 hits (R1.1) | Y | ✅ measurable — import exit code + the exact R1.1 grep (ci.yml:47-52) | none |
| AC3 | CI passes; test job runs ruff/mypy/pytest (no longer skipped); guardrails green | CI run conclusion = success; mypy step runs iff a `.py` exists under `code_atlas/`, pytest step iff a `.py` exists under `tests/` (both satisfied by R2+R4) | Y | ✅ measurable — CI job conclusion + the `hashFiles(...)` step conditions (ci.yml:33,37) | none |

No acceptance **values** (numbers/thresholds/formats) appear in this ticket, so there is nothing to re-derive for mismatch; all three ACs are falsifiable. No manual-check exclusions needed. No uncodified-standard gate items — the R1.1/R2.2 gates are already codified in `ci.yml` and ENGINEERING_RULES §1–2.

## Inventory (universal "all/every/no" requirements)

**R2 "Package skeleton per §5" is a counted "do X for each of N" requirement → per-item checklist.**

- **Denominator / total N:** 9 (ticket-named module stubs)
- Enabling files that ride with R2 (not counted in N, but required for AC2 "import works"): `code_atlas/__init__.py`, `code_atlas/tools/__init__.py`.

| # | Item | Ph3/4 proven by (`path:line` / test) | Status |
|---|------|--------------------------------------|--------|
| 1 | `code_atlas/main.py` | created @ 27bc105; mypy 11 files clean; `import code_atlas` ok | ✅ |
| 2 | `code_atlas/config.py` | created @ 27bc105; mypy clean | ✅ |
| 3 | `code_atlas/contract.py` | created @ 27bc105; mypy clean; ruff clean | ✅ |
| 4 | `code_atlas/adapter.py` | created @ 27bc105; mypy clean | ✅ |
| 5 | `code_atlas/store.py` | created @ 27bc105; mypy clean | ✅ |
| 6 | `code_atlas/indexer.py` | created @ 27bc105; mypy clean | ✅ |
| 7 | `code_atlas/resolver.py` | created @ 27bc105; mypy clean | ✅ |
| 8 | `code_atlas/gitutil.py` | created @ 27bc105; mypy clean | ✅ |
| 9 | `code_atlas/ignore.py` | created @ 27bc105; mypy clean | ✅ |

Review must confirm **every** row, not a `k/9` total. Directory deliverable R3 (adapters/, tests/contract/, tests/fixtures/, tests/) is a small fixed set proven the same way. AC2's "no per-language code" is a whole-package grep assertion (R1.1), effectively N=1 proof over `code_atlas/`.

### Surface inventory

n/a — TRACK=backend, no frontend surfaces.

## Clarifications

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

- Self-resolved (cited):
  1. **`requires-python` version?** → target `>=3.12`; CI's only tested interpreter is `python-version: "3.12"` (ci.yml:18) and CONVENTION §4 says "modern Python".
  2. **What is the `[dev]` group called?** → the extra must be named `dev`; CI runs `pip install -e ".[dev]"` (ci.yml:24).
  3. **`__init__.py` needed?** → yes; AC2 requires `import code_atlas` to work, so `code_atlas/__init__.py` (+ `tools/__init__.py`) are required even though the skeleton bullet doesn't list them.
  4. **What un-skips the conditional CI steps (AC3)?** → mypy runs iff `hashFiles('code_atlas/**/*.py') != ''`; pytest iff `hashFiles('tests/**/*.py') != ''` (ci.yml:33,37). R2's stubs + R4's test satisfy both.
- For human decision: **none** → j=0, Gate 0 not triggered.
- Deferred to Phase 2 (design choices, not blockers): build backend (setuptools vs hatchling), mypy strictness level, ruff rule selection. Analysis does not pre-pick these.

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement, per goal G1):** current = repo has docs + `.harness.json` + CI + PR template only, **zero Python** (`find . -name '*.py'` → empty). Target = installable `code_atlas` package, dev toolchain, green CI. Gaps: (a) no `pyproject.toml` → R1; (b) no package/module stubs → R2; (c) no `adapters/`/`tests/` tree → R3; (d) no tool config or test → R4; (e) CI's mypy/pytest steps skipped for lack of `.py` files → R5/AC3. Root files: PLAN.md:139-165 (layout), ci.yml:23-38 (install/steps), CONVENTION.md:9-38.
- **Handler / entry point + blast radius:** greenfield — no existing code depends on anything. Only pre-existing coupling is `ci.yml` (its conditional steps activate once `.py` files land) and `.harness.json`/docs (unchanged). Touched repo: `app` only. No callers/dependents.
- **Self-audit:** every section decomposed (4/4) ✅ · AC table complete, all 3 ACs falsifiable, none carrying a bare `✅`, no manual-check exclusions needed ✅ · BASELINE captured (red/unsatisfiable, no exclusions) ✅ · j=0 (Gate 0 not triggered) ✅ · inventory N=9 set with per-item checklist ✅ · matrix Status filled ✅ · STRUCTURE=native, TRACK=backend, TIER=full declared ✅ · SURFACES n/a (backend) ✅.
- **Gate 1 status:** **cleared** (user approved; proceeding to design)

## Phase 2 — Design ✋ Gate 2

**Approach.** Author a single `pyproject.toml` (PEP 621 `[project]` + `[build-system]` + `[tool.*]`)
using the **setuptools** backend — bundled, zero extra build dep (R8.2). Runtime dep `fastmcp>=2`;
`[project.optional-dependencies].dev = [pytest, ruff, mypy]` (name `dev` per ci.yml:24). Create the
9 module stubs + `code_atlas/__init__.py` + `code_atlas/tools/__init__.py`, each **empty but for a
one-line module docstring** (no imports, no code → no language branch, nothing for ruff/mypy to flag).
Create `adapters/`, `tests/contract/`, `tests/fixtures/` (empty dirs tracked via `.gitkeep`). Add one
smoke test `tests/test_smoke.py` that imports the package. ruff/mypy/pytest configured inline in
`[tool.*]`. The committed `ci.yml` needs no edits — landing `.py` under `code_atlas/` and `tests/`
auto-satisfies its `hashFiles(...)` step conditions (AC3).

**Rejected alternatives.**
- **hatchling / flit build backend** — rejected: adds a build-time dependency for zero benefit on a
  plain pure-Python package; setuptools is bundled and standard (R8.2 minimal deps).
- **Rich stubs (Protocol sketches, placeholder classes) now** — rejected: violates R1.2/R7.4 (no
  abstraction before adapter #2) and R7.1 (smallest useful thing); stubs stay docstring-only until
  their own tasks (002+) fill them.

**Assumptions.**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| `fastmcp>=2` installs on py3.12 with no dep conflict | **verified (spike)** | `pip install fastmcp --dry-run` resolved fastmcp 3.4.5 + full tree cleanly on py3.12 (Phase-2 spike) |
| CI's `test` job un-skips mypy/pytest once `.py` files exist under `code_atlas/` & `tests/` | verified | Step conditions `hashFiles('code_atlas/**/*.py')` / `hashFiles('tests/**/*.py')` (ci.yml:33,37) |
| setuptools auto-discovers `code_atlas` + `code_atlas.tools` | verified | Standard flat-layout discovery; made explicit via `[tool.setuptools.packages.find]` include=`code_atlas*` |

**Smallest change-list.** Every item traces to a matrix row.

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | `[project]` (name `code-atlas`, `requires-python>=3.12`, `dependencies=["fastmcp>=2"]`, `[dev]` extra) + `[build-system]` setuptools + `[tool.setuptools.packages.find]` | `pyproject.toml` | R1, AC1 | 1/1 |
| 2 | `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` config | `pyproject.toml` | R4, R5, AC1, AC3 | 1/1 |
| 3 | Package init (docstring; makes `import code_atlas` work) | `code_atlas/__init__.py` | R2, AC2 | 1/11 |
| 4 | 9 module stubs (docstring-only) | `code_atlas/{main,config,contract,adapter,store,indexer,resolver,gitutil,ignore}.py` | R2 | 9/11 (inventory 1–9) |
| 5 | Tools sub-package init | `code_atlas/tools/__init__.py` | R2 | 11/11 |
| 6 | Empty-dir placeholders | `adapters/.gitkeep`, `tests/contract/.gitkeep`, `tests/fixtures/.gitkeep` | R3 | 1/1 |
| 7 | Smoke test (the proving test) | `tests/test_smoke.py` | R4, AC1, AC2 | 1/1 |
| 8 | Token-usage-on-PR rule + BACKLOG roll-up table (folded in at Gate 4 by approval; committed as `5478c5a`) | `CLAUDE.md`, `docs/BACKLOG.md` | R6 | 1/1 |

**Test blast-radius (mechanical).** Grep for existing tests/specs/snapshots referencing anything this
change touches → **zero** (`find . -name '*.py'` is empty; no existing assertions to invalidate). No
proof-collateral items.

**Rule compliance.**
- **R1.1 / R1.2 / R7.4** — stubs are docstring-only: no language branch, no registry/base-class/DI, no
  dead abstraction. R1.1 grep over `code_atlas/` stays clean.
- **R8.1 / R8.2** — core runtime dep = `fastmcp` only; setuptools is the bundled build backend; no
  adapter deps leak in.
- **R7.5** — every stub comment is a single-line docstring (≤3 lines).
- **CONVENTION §2/§4** — package `code_atlas` (underscore), project `code-atlas` (hyphen); ruff+mypy
  configured; no public functions yet so "type hints on all public functions" is vacuously met.

**Verification plan** (one row per AC; proof at the layer where the AC can fail).

| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 | integration/runtime (packaging + tool invocation) | CI + local run of `pip install -e .` → `pytest` → `ruff check .` (all exit 0; pytest ≥1 passed) | ✅ |
| AC2 | integration (module import) + logic (static grep) | `tests/test_smoke.py::test_import_code_atlas` (real import) + R1.1 grep gate over `code_atlas/` | ✅ |
| AC3 | e2e (the CI pipeline itself) | actual CI run on the PR: `test` job's mypy+pytest steps execute & pass, `guardrails` green | ✅ |

No `❌` rows → no coverage-gap exclusions needed. `SURFACES` n/a (backend).

**Coverage-gap exclusions:** none.

**Proving test.** `tests/test_smoke.py::test_import_code_atlas` — asserts `import code_atlas` succeeds
and `code_atlas.__name__ == "code_atlas"` (references the import so no ruff F401). **Fails pre-change**
(no package → `ModuleNotFoundError`), **passes post-change**. Sits at AC2's import/integration risk
layer. Invocation: `pytest tests/test_smoke.py::test_import_code_atlas` (or plain `pytest`).

**Rollback + porting plan.** Rollback = delete the branch / revert the single scaffold commit; no
runtime, data, or schema state is created, so revert is clean. Single repo (`app`); no shared code, no
porting.

**SCOPE confirmed:** **M** — unchanged from analysis. Change-list (7 items over ~15 new files) matches
the M baseline; no tier drift, no branch/PR-type drift (this is a `chore`/`feat` scaffold).

- **Gate 2 status:** **cleared** (user approved: "implement task-001")

## Phase 3 — Execute

- **Branch:** `chore/001-project-scaffold` (off latest `main` @ d742c37).
- **Commits (logical units; no AI co-author trailer):**
  1. `27bc105` — Add project scaffold: package skeleton, tooling, and smoke test (approved change-list items 1–7).
  2. `5478c5a` — Add token-usage-on-PR rule and BACKLOG token table (governance; docs-before-PR).
  3. `b5880b8` — Embed task 001 working doc; set work_doc_mode=embed.
- **Proving test added:** `tests/test_smoke.py::test_import_code_atlas`. Red pre-package (no `code_atlas` on the branch → `ModuleNotFoundError`); **green post-build** (`1 passed`).
- **Verification sweep (DoD = prove the delta is green; BASELINE was red/unsatisfiable):**
  - `pip install -e ".[dev]"` → success (`code-atlas-0.0.1` + fastmcp 3.4.5 + dev tools) — AC1 ✅
  - `python -c "import code_atlas"` → `code_atlas` — AC2 ✅
  - `pytest -q` → `1 passed` — AC1 ✅
  - `ruff check .` → `All checks passed!` — AC1 ✅
  - `mypy code_atlas` → `Success: no issues found in 11 source files` — CI parity ✅
  - R1.1 grep over `code_atlas/` → no language branch — AC2 ✅
- **Verification sweep — Axis 1 (file set):** zero stray refs ✅ · diff ⊆ approved list ✅ (code files = Gate-2 items 1–7; `ci.yml` untouched as designed; the 4 modified docs are the working-doc + governance edits required by docs-before-PR, committed separately) · each hunk maps to a matrix row ✅.
- **Verification sweep — Axis 2 (design-conformance):** every Gate-2 Approach bullet `implemented-as-approved` — setuptools + `fastmcp>=2` + `[dev]` extra, docstring-only stubs, `.gitkeep` dirs, smoke test, inline `[tool.*]`, `ci.yml` un-edited. **No deviations.**
- **Design-invalidation / re-gate:** none.
- **Stuck-detector:** 1 signature encountered (ruff E501 on the `contract.py` docstring) → fixed on first retry by shortening the line; counter never reached K=3.

## Phase 4 — Review ✋ (stop only if not clean)

- **reviewer verdict:** round 1 = CHANGES REQUESTED / conditional LGTM (`mango:reviewer`, Sonnet) — one Important finding, everything else clean with independent re-verification (ruff/mypy/pytest/import/`pip show`/R1.1 grep all re-run by the agent, not trusted from the doc).
- **Re-review path:** **verify-only, main-loop, no re-dispatch** — Finding 1's fix touched only the exempt working-doc file (docs/bookkeeping carve-out), so round 2 is inspection + no proof change.
- **Finding 1 (scope creep: token-rule untraceable to ticket) → RESOLVED** via the reviewer's option 2: folded into Scope/Deliverables (R6) + Gate-2 change-list item 8 with rationale; commit `5478c5a` now traces to a matrix row. Traceability claim in Phase 3 is now true, not asserted.
- **challenger (ticket-blind) result:** 11/11 reconstructed requirements **MET**, 0 not met, 0 can't tell. Independently re-ran every AC command in a clean venv. Caveat on AC3/CI: only a live GitHub Actions run certifies "CI green"; every command/condition it depends on was reproduced locally with matching results. Also flagged the same out-of-ticket items (now folded in / accounted as process artifacts).
- **security agent:** n/a (none defined; not security-tagged).
- **Scope reconciliation — both axes.** *File axis:* diff ⊆ approved list ✅ (code = items 1–7; token-rule = item 8 folded in; `.harness.json` + embedded working doc = task-001 process artifacts; `ci.yml` untouched). *Behaviour axis:* every Gate-2 Approach bullet `implemented-as-approved`; no behavioural deviation. No tier drift (SCOPE=M).
- **Regression on Phase-1 callers:** none — greenfield, no pre-existing dependents.
- **Proving test result + "would it fail without the change?":** `pytest` → `1 passed`; yes, red without the package (`ModuleNotFoundError`). Judged vs BASELINE=red/unsatisfiable → **delta is green** (no new failure; the "no tests / no package" baseline is now satisfied). No baseline exclusions outstanding.
- **Layer-match re-confirmation:** all three AC proofs sit at their risk layer (AC1 runtime/integration, AC2 import+static, AC3 e2e-CI); no layer-match ❌.
- **`Ph3/4 proven by` filled:** matrix + inventory (9/9 stubs ✅) filled item-by-item.
- **Clean?** reviewer no Critical (the one Important finding resolved) AND challenger every item met AND no layer-match ❌ AND k=N AND proving test green → **YES** (with the standing note that AC3's final CI-green is confirmed only after the PR run in finalise).
- **Reviewed at:** `b5880b8` + the three Phase-4 working-doc edits (folding R6 / item 8). Reviewed files: `pyproject.toml`, `code_atlas/**` (11 modules), `tests/test_smoke.py`, `adapters/.gitkeep`, `tests/{contract,fixtures}/.gitkeep`, `CLAUDE.md`, `docs/BACKLOG.md`. Working-doc path `docs/tasks/001_project-scaffold.md` (embedded) + `.harness.json` are staleness-exempt bookkeeping.

## Phase 5 — Finalise ✋ final gate

- **PR draft:** `scratchpad/pr-001.md` (rendered from the repo `pull_request_template.md`).
- **Stale-review guard:** passed — only the exempt embedded working doc changed since `b5880b8`.
- **Planned outward actions (each approved individually):**
  - [x] push branch `chore/001-project-scaffold` (carries all commits incl. lesson + token ledger) — **approved**
  - [x] open PR via `gh` against `main` — **approved**
  - [ ] tracker comment — **N/A** (GitHub repo, no separate issue; status tracked in BACKLOG + frontmatter)
  - [ ] tracker transition — **N/A** (status synced to `in-progress` in BACKLOG + frontmatter)
- **Follow-up tickets for deferred (⚠) rows:** none — no deferred rows.
- **Durable lesson:** recorded → `docs/LESSONS.md` entry "001 — Fold a mid-task governance request into the ticket's scope"; lands on the shared ref via the branch push.
- **Cost ledger:** `LEDGER TOTAL: 113,628 dispatch tokens · top cost driver: Phase 4 / reviewer` (dispatch-only; main-loop via `rtk gain`).
- **Revert path:** pre-merge — `git push origin --delete chore/001-project-scaffold` + close PR. Post-merge — revert the squash/merge commit on `main`; no runtime/data/schema state was created, so revert is clean.
- **AC3 (CI green):** confirmed by the PR's Actions run after push.

---

## Cost ledger (descriptive — dispatch-only)

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 4 — Review | `mango:reviewer` (Sonnet) | 1 | 70,944 | RTK live on main loop (see `rtk gain`); dispatch not shaped |
| 4 — Review | `mango:challenger` (Sonnet) | 1 | 42,684 | RTK live on main loop (see `rtk gain`); dispatch not shaped |

`LEDGER TOTAL: 113,628 dispatch tokens · top cost driver: Phase 4 / reviewer.` Scope = **subagent dispatch only** (2 dispatches this run: reviewer + challenger; no extractor/Explore fan-out). Main-loop output noise is **not** measured by mango — consult `rtk gain` for that layer.

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 1 | TIER=full | SCOPE=M, multi-file, universal req (R2) with N=9>1 → lite ineligible |
| Phase 1 | BASELINE=red (no exclusions) | Fresh checkout has no `.py`; pytest collects nothing, ruff absent — expected pre-scaffold, not a defect |
| Phase 2 | Build backend = setuptools | Bundled, zero extra build dep (R8.2); hatchling/flit add cost for no benefit on a pure-Python package |
| Phase 2 | `fastmcp` assumption resolved via spike | `pip install fastmcp --dry-run` → fastmcp 3.4.5 + full tree resolves on py3.12; assumption now verified, not novel-untested |
| Phase 2 | Stubs docstring-only | R1.2/R7.4 (no abstraction before adapter #2) + R7.1 (smallest thing); stubs fill in tasks 002+ |
| Phase 4 | Fold token-rule into task 001 (R6 + change-list item 8) | Reviewer flagged commit 5478c5a as untraceable scope creep; user chose "fold in" over split → made it traceable to a matrix row per reviewer's option 2 |

## Session status

- **Last updated:** Phase 5 (finalise) complete — PR #2 open, CI green
- **Current phase:** 5 — done pending merge
- **Work-doc mode / path:** embed · this file (`docs/tasks/001_project-scaffold.md`, below the separator)
- **Next action:** merge PR #2 (your call) → then set status `done` in BACKLOG + frontmatter
- **Blocked on:** human merge of PR #2
