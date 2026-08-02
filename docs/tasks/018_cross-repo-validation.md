---
id: 018
slug: cross-repo-validation
title: Cross-repo validation ("works on any repo")
phase: 1
milestone: M4
status: in-progress
depends_on: [015]
---

## Goal
Prove the adapter follows the language standard, not one sample (§2, §16).

## Scope / Deliverables
- Run the PHP adapter against several varied repos: a Laravel app, a Symfony app, a small PSR-4 library, and a large PHP monorepo.
- Assert: no crashes; sane node/edge counts; syntax errors isolated per file.
- Document any construct gaps found (feed back into task 007).
- **CI:** cloning several third-party repos is network-bound and slow, and one sample is not public. This belongs in a scheduled/opt-in workflow, never the per-PR gate; per-PR CI keeps only the spec-driven fixtures (R6.2).

## Acceptance criteria
- All sample repos index without crashing; counts are plausible.
- The large monorepo treated as one sample among several — no repo-specific behavior required.

## References
Plan §2 (standard over sample), §16, §17.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 018 — Cross-repo validation (working doc)

- **Ticket:** 018 · [docs/tasks/018_cross-repo-validation.md](018_cross-repo-validation.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — 549 passed (`.venv/bin/pytest -q`)
- **work_doc_mode:** `embed` → below separator (harness `embed`; sibling `018_*.work.md` would be scooped by `test_backlog_bookkeeping.task_files`)

## Session status

```
phase: 3 execute — verification sweep done; flowing to review
Gate: Gate 1 + Gate 2 cleared (standing approve)
work_doc_mode: embed
working_doc: docs/tasks/018_cross-repo-validation.md (below separator)
branch: feat/018-cross-repo-validation
```

- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — 549 passed in 29.38s (`.venv/bin/pytest -q`)

---

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 6 unresolved surfaced | 4 want-decision asked | 5 how-decision resolved+cited | 6 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

### Premise detail

| # | Reference | Framing | Result |
|---|-----------|---------|--------|
| 1 | Plan §2 / §16 / §17 | referenced-as-existing | `docs/PLAN.md` |
| 2 | Dep 015 | referenced-as-existing | BACKLOG `done` |
| 3 | Task 007 (gap feedback sink) | referenced-as-existing | `docs/tasks/007_…` |
| 4 | R6.2 / R6.3 | referenced-as-existing | `ENGINEERING_RULES.md` |
| 5 | Spec-driven fixtures stay in per-PR CI | referenced-as-existing | `.github/workflows/ci.yml` |
| 6 | Opt-in scale script / runbook from 015 | referenced-as-existing | `scripts/scale_full_build.py`; `docs/runbooks/scale-sample.md` |
| 7 | Scheduled/opt-in GHA workflow | to-be-created | — |
| A1 | “Laravel / Symfony / PSR-4 library / large monorepo” | ambiguous prose | surfaced; not blocking |
| A2 | “one sample is not public” | ambiguous prose | surfaced; not blocking |

### ASSUMED (ratified Gate 1 under standing approve)

| # | Assumed choice | Why ASSUMED | Explicit confirm | Reverses prior? |
|---|----------------|-------------|------------------|-----------------|
| A1 | Public pins: `laravel/laravel`, `symfony/demo`, `brick/math` at SHAs in an in-repo manifest (not under `adapters/`); private large sample via `CODE_ATLAS_SCALE_SAMPLE` (operator-local; not required for GHA public job) | W1 best | Gate 1 standing | no |
| A2 | Plausible = crash-free + `files > 0` + `nodes > 0` + `edges ≥ 0`; no fixed floor vs LOC | W2 best | Gate 1 standing | no |
| A3 | GHA: `workflow_dispatch` + weekly `schedule`; public trio only; `ci.yml` untouched | W3 best (matches “scheduled/opt-in”) | Gate 1 standing | no |
| A4 | Fold 015 timing: when `CODE_ATLAS_SCALE_SAMPLE` set, run `scale_full_build` / capture JSON; when unset, document skip (do not fail public CI) | W4 best | Gate 1 standing | no |
| A5 | Syntax isolation: build must complete; per-file `parsed_ok`/`failed` accounting; do **not** require third-party samples to contain syntax errors — fixture isolation stays in per-PR CI; proving harness uses a tiny local mini-repo with one broken + one good file | exposure #1 | Gate 1 standing | no |
| A6 | Construct gaps → `docs/runbooks/cross-repo-validation.md` + BACKLOG Follow-ups bullets feeding 007 | exposure #2 | Gate 1 standing | no |

### HOW (cited)

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Per-PR CI stays fixture-only | No third-party clones in `ci.yml`; new opt-in/scheduled workflow only | ticket Scope CI; R6.2; task 024 |
| 2 | No sample names in adapter source | Manifest + harness live under `scripts/` / `docs/` / `.github/` — never `adapters/` | R2.2; Plan §2 |
| 3 | Reuse 015 scale plumbing | Private sample via `CODE_ATLAS_SCALE_SAMPLE`; public clones in cross-repo script | `docs/runbooks/scale-sample.md`; R2.3 |
| 4 | Gap documentation sink | Runbook + BACKLOG follow-ups → 007; no adapter branches | ticket Scope; R7.2 |
| 5 | Tooling shape | Script + workflow + assertions; not a core API change | CONVENTION; 015 script pattern |

### Exposure-checker

[challenger](003ebc65-d9af-4974-8e06-4eb5111d41e0): `EXPOSURE: 2` → A5 (syntax isolation verify) + A6 (gap doc sink).

---

## Phase 1 — Analysis

`PREMISE:` / `RECALL:` carried from refine.

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=4 G=1 AC=8`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Prove adapter follows language standard, not one sample (§2, §16) | Multi-repo harness + R6.3 CI opt-in; no adapter sample tuning | Plan §16; R6.3 | Approach | proving + workflow | ❌ |
| R1 | Scope | Run against Laravel / Symfony / PSR-4 lib / large monorepo | A1 sample set | gap | change-list 1–2 | manifest + public run | ❌ |
| R2 | Scope | Assert no crashes; sane counts; syntax errors isolated per file | A2 + A5 | gap | change-list 3–4 | proving harness | ❌ |
| R3 | Scope | Document construct gaps → 007 | A6 | gap | change-list 6 | runbook + BACKLOG | ❌ |
| R4 | Scope | CI scheduled/opt-in; never per-PR; fixtures stay in ci.yml | A3; HOW-1 | gap | change-list 5 | workflow exists; ci.yml untouched | ❌ |
| AC1 | AC | All sample repos index without crashing; counts plausible | A1∪A2; public required in GHA; large optional locally | A2 | proving + script | PASS | ❌ |
| AC2 | AC | Large monorepo one sample among several — no repo-specific behavior | No adapter/core branches on sample names; same harness path | R2.2 | change-list 1–3 | R2.2 gate + harness | ❌ |
| AC-A1 | refine | concrete public pins + private env | as A1 | A1 | manifest | pins present | ❌ |
| AC-A2 | refine | plausible bar | as A2 | A2 | assert helper | tests | ❌ |
| AC-A3 | refine | dispatch + weekly | as A3 | A3 | workflow | yaml | ❌ |
| AC-A4 | refine | fold 015 timing when env set | as A4 | A4 | script/runbook | skip-or-run | ❌ |
| AC-A5 | refine | isolation verify | as A5 | A5 | proving mini-repo | PASS | ❌ |
| AC-A6 | refine | gap doc sink | as A6 | A6 | docs | runbook+BACKLOG | ❌ |

### AC validation

| AC ID | Ticket / ASSUMED | Computed | Match? | Falsifiable? | Gate-1 |
|-------|------------------|----------|--------|--------------|--------|
| AC1 | crash + plausible | A2 measurable | Y under A2 | yes | ratify A2 |
| AC2 | no repo-specific behavior | R2.2 + shared harness | Y | grep/tests | — |
| A1–A6 | ASSUMED | as Phase 0 | Y if ratified | measurable | Gate 1 |

### Inventory

**N = 4 sample kinds** (Laravel, Symfony, PSR-4 lib, large monorepo) — “all sample repos” / R1.

| # | Item | Status |
|---|------|--------|
| S1 | Laravel app pin | ❌ |
| S2 | Symfony app pin | ❌ |
| S3 | Small PSR-4 library pin | ❌ |
| S4 | Large PHP monorepo (operator) | ❌ |

`SURFACES:` N/A — `TRACK: backend`.

### Clarifications

`CLARIFICATION: 6 raised | 5 how self-resolved (Phase 0) | 6 for human (ASSUMED A1–A6)` → Gate 1 ratification only; **j=0** open design Qs after standing approve.

### Gap analysis

| Slice | Current | Target | Evidence |
|-------|---------|--------|----------|
| Cross-repo harness | absent | script + assertions + report | no `cross_repo` script |
| Public sample pins | Plan Q3 open | manifest with pinned SHAs | PLAN §18 Q3 |
| Opt-in GHA | only `ci.yml` | `cross-repo.yml` dispatch+schedule | `.github/workflows/` |
| Gap docs | informal | runbook + BACKLOG → 007 | ticket R3 |
| 015 timing | procedure only | fold when env set (A4) | BACKLOG Follow-ups |

### Blast radius

- **Entry:** new `scripts/cross_repo_validate.py` (+ shared assert helpers); new workflow; runbook; tests; docs/BACKLOG/PLAN Q3; optionally call existing `scale_full_build.py`.
- **Repos:** `app` only. **db-map:** N/A. **ci.yml:** must remain untouched (proof collateral: no diff).

`TRACK: backend — 0/N UI paths`

### Rule sections

`RULE SECTIONS: §1 ✅ R1.1 (no lang branches) · R1.2 N/A · §2 ✅ R2.2/R2.3 (manifest outside adapters; sample via env) · §3 N/A · §4 ✅ R4.1 (script may network only outside core) · §5 ✅ R5.1 isolation · §6 ✅ R6.1–R6.3 · §7 ✅ R7.2 · §8 N/A`

### Scope / Tier

- **SCOPE:** M — harness + workflow + tests + docs; no core API.
- **TIER:** full — N=4; not lite.

**Gate 1:** ASSUMED A1–A6 ratified under standing “best option / pass all gates”. Cleared.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | W1–W4 + exposure → ASSUMED A1–A6 | standing best option |
| Gate 1 | Ratify A1–A6; clear | standing pass all gates |
| Gate 2 | Approve approach + change-list | standing pass all gates |

---

## Phase 2 — Design

### Approach

Ship an **opt-in cross-repo validation harness** (not a core change): a pinned-SHA manifest of three public PHP samples + a shared `full_build` runner that asserts A2/A5, writes a JSON report under `artifacts/`, and documents construct gaps. A new GHA workflow (`workflow_dispatch` + weekly) clones the public trio only. The private monorepo remains operator-provisioned via `CODE_ATLAS_SCALE_SAMPLE`; when set, the harness (or scale script) also captures the 015 timing JSON (A4). Per-PR `ci.yml` stays fixture-only. Proving test uses a **local mini-repo** (good + broken PHP) so CI without network still proves the assertion bar and isolation.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Clone third-party repos in per-PR `ci.yml` | Violates ticket R4 / R6.2 / task 024 |
| Encode Laravel/Symfony strings in `adapters/php` | Violates R2.2 |
| Require private monorepo in GHA | Sample not public; secrets out of scope |
| Hard LOC-based count floors | Over-constrains A2; samples vary |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| Public GitHub clones of pinned SHAs are enough for GHA R6.3 | novel-untested → proving at runtime in workflow; unit proving uses local mini-repo | workflow is the 3p proof; Gate-2 proving test covers assert helpers |
| Existing `full_build` + `parsed_ok` already isolates parse errors | verified | `tests/test_php_adapter_server.py`; contract R5.1 |
| Manifest outside `adapters/` satisfies R2.2 | verified | R2.2 scopes adapters |

### Smallest change-list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | Sample manifest (owner/repo/sha/kind) | `scripts/cross_repo_samples.json` | harness only | R1, AC-A1, S1–S3 | 1 |
| 2 | Cross-repo validate script (clone/cache, build, assert, report; optional scale when env set) | `scripts/cross_repo_validate.py` | artifacts/; calls indexer | R1–R2, AC1–2, A4 | 1 |
| 3 | Assert helpers + proving mini-repo test | `tests/test_cross_repo_validation.py` | none beyond new tests | AC1, AC-A2, AC-A5 | 1 |
| 4 | Opt-in GHA workflow | `.github/workflows/cross-repo.yml` | Actions minutes; not ci.yml | R4, AC-A3 | 1 |
| 5 | Runbook (how to run, gap log template, scale fold-in) | `docs/runbooks/cross-repo-validation.md` | scale-sample.md cross-link | R3, A4, A6 | 1 |
| 6 | Docs/bookkeeping: BACKLOG status + follow-ups; PLAN §18 Q3 note; task frontmatter; README pointer if needed | `docs/BACKLOG.md`, `docs/PLAN.md`, task 018, maybe README | readers | G1, A6, R7.2 | 1 |
| 7 | Proof collateral: ensure `ci.yml` untouched; `.gitignore` artifacts if needed | `.gitignore` (if missing), no `ci.yml` | — | R4 | 1 |

**Test blast-radius:** new tests only; existing scale script callers unchanged. R2.2 grep still excludes vendored; manifest must not live under `adapters/`.

### Rule compliance

R2.2/R2.3 · R5.1 · R6.1–R6.3 · R7.2 — as analysis RULE SECTIONS.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 crash + plausible | integration | mini-repo proving test + script assert helper | ✅ |
| AC2 no repo-specific | logic/integration | R2.2 gate + shared harness path | ✅ |
| AC-A1 pins | integration | manifest present + script loads | ✅ |
| AC-A2 bar | logic | unit asserts on report dict | ✅ |
| AC-A3 workflow | runtime/config | workflow YAML triggers | ✅ (file presence; live schedule is ops) |
| AC-A4 scale fold | integration | env-set branch / documented skip | ✅ |
| AC-A5 isolation | integration | mini-repo with broken+good file | ✅ |
| AC-A6 gaps | docs | runbook + BACKLOG bullets | ✅ manual-recorded |

### Proving test

`tests/test_cross_repo_validation.py::test_harness_plausible_counts_and_parse_isolation` — temp mini-repo with one valid PSR-4 file + one syntax-error file; run assert path used by the script; expect crash-free, `nodes > 0`, `failed >= 1`, build completed. Invocation: `.venv/bin/pytest tests/test_cross_repo_validation.py -q`.

### Rollback / porting

Revert the change-list commit(s). Repos: `app` only.

**Gate 2:** cleared under standing approve.

---

## Phase 3 — Execute

**Branch:** `feat/018-cross-repo-validation`

**Verification sweep**

| Check | Result |
|-------|--------|
| Proving test | `test_harness_plausible_counts_and_parse_isolation` PASS |
| Cross-repo suite | `tests/test_cross_repo_validation.py` — **5 passed** |
| Full suite | **552 passed** (clean env; polluted `CA_PHP_CMD` from smoke run caused a false MCP fail) |
| Public smoke | `cross_repo_validate.py --public-only` — 3/3 ok (laravel 75n, symfony 437n, brick_math 887n) |
| Diff ⊆ change-list | manifest, script, tests, workflow, runbooks, BACKLOG/PLAN/README/task — items 1–7; `ci.yml` untouched |
| Approach bullets | opt-in harness + pins + GHA dispatch/schedule + A4 skip + mini-repo proof — **implemented-as-approved** |

**Deviations:** none.

**Note:** `index_root` always absolutizes `CA_PHP_CMD` because `SubprocessAdapter` uses sample `cwd`.

---

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | exposure-checker challenger | 1 | unmeasured (host does not surface usage) |