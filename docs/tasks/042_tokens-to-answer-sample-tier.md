---
id: 042
slug: tokens-to-answer-sample-tier
title: Tokens-to-answer sample tier — populate pinned public repos (ratio ≫ 1)
phase: 1.5
milestone: Measure
status: done
depends_on: [034, 018]
---

## Goal
Prove the value claim the fixtures cannot. Task 034 shipped the harness and a per-PR gate, but the
committed questions run against 4-file toy fixtures where `get_index_status` overhead makes
code-atlas *cost more* than reading one tiny file — observed ratio ≈ **0.302** (1409 vs 425 tokens,
9/9 correct). That is a behaviour-lock, not evidence code-atlas saves tokens. The token win
(ratio ≫ 1) only appears on realistic repos, where a grep pattern matches many files an agent must
read whole while code-atlas returns the one resolved answer. This ticket populates the **sample
tier** so we have a real, defensible number (§19 agent-first pivot; "a guard that cannot fail is
not evidence").

## Scope / Deliverables
- Add `source: sample` questions to `scripts/tokens_to_answer_questions.json` against the pinned
  public repos in `scripts/cross_repo_samples.json` (laravel/laravel, symfony/demo, brick/math) —
  a spread of the query kinds where grep over-reads: callers of a widely-used method, references to
  a class, implementations of an interface, "who includes X".
- Verify each answer **by running the harness in a PHP+clone environment** (not by eyeballing) — the
  `expected` must be the real resolved answer, `grep_evidence` the real raw-text hit.
- Wire the sample tier so it runs on schedule / `workflow_dispatch` (like cross-repo validation),
  not per-PR — it needs a clone and is slower. Record the observed aggregate ratio.
- Report the real ratio (expected ≫ 1) in the runbook, replacing "measured on schedule, not yet
  populated".

## Constraints
- Sample questions' answers must be **verified by execution**, never committed unverified — the
  whole point of 034 is falsifiability.
- Harness stays dev tooling under `scripts/` (SRP); no core change; deterministic recipes, no LLM
  (R4). Framework/repo names stay out of `adapters/` (R2.2) — sample pins live in the manifest.
- The per-PR fixture gate (`--min-ratio 0.24`) is unaffected; the sample tier is a separate,
  scheduled run with its own floor.

## Acceptance criteria
- `scripts/tokens_to_answer_questions.json` carries `source: sample` questions whose answers were
  produced (not guessed) by the harness against the pinned checkouts.
- A scheduled / dispatch job runs the sample tier and reports an aggregate ratio; the observed
  number is ≫ 1 (or, if not, that surprising result is investigated and written up — the metric is
  falsifiable both ways).
- The runbook states the real sample-tier ratio and how to reproduce it.

## References
`scripts/tokens_to_answer.py` (harness; `source: sample` path already wired via
`cross_repo_validate`), `scripts/tokens_to_answer_questions.json`,
`scripts/cross_repo_samples.json` (pins), `docs/runbooks/tokens-to-answer.md`,
`docs/runbooks/cross-repo-validation.md` (schedule/dispatch pattern to mirror). Origin: task 034
observed fixture ratio 0.302 — fixtures favour grep; the win is only visible on real repos.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status
- **Phase:** DONE — PR [#48](https://github.com/cuongdinhngo/code-atlas/pull/48) opened at `c67ef3f`.
  **Next action:** wait for CI on PR #48, then merge. **Revert:** close PR #48 and delete branch
  `feat/042-tokens-to-answer-sample-tier` (no merge yet); all work is on that branch, `main` untouched.
- **Durable lesson:** recorded in `docs/LESSONS.md` (042 — stale ticket References; local env provisioning).
- **work_doc_mode:** embed (this file, below separator).
- **Branch:** `feat/042-tokens-to-answer-sample-tier`.
- **TIER:** full · **TRACK:** backend · **SCOPE:** L (re-scoped — accepted).
- **Gate 0/1 resolution:**
  1. Verify env — **run locally.** A portable PHP 8.3.33 + Composer env was stood up (scratchpad);
     `nikic/php-parser` installed; the real adapter builds fixtures end-to-end (10/10, ratio 0.284).
     Blocker removed — R2/C1/AC1 are satisfiable here with real runs.
  2. Scope — **do it all in 042 (L).** Build the sample-run harness path + new workflow + verified
     questions + runbook + tests. Outgrew-its-ticket accepted, not split.
  3. AC2 floor — **report the observed ratio, set scheduled floor = round(0.8 × observed)**, mirroring
     the fixture-floor recalibration convention (`tokens-to-answer.md`).
- **BASELINE:** area-green — `tests/test_tokens_to_answer.py` 13 passed / 1 skipped (`@needs_php`
  end-to-end skips: no PHP locally). Full suite is **red locally** (56 Windows-only PHP-adapter
  subprocess failures, `WinError 2`) but **green in Linux CI** (PR #47 = 753 passed) — recorded as a
  baseline exclusion; this task adds no code that runs in that failing local path.

## Phase 1 — Analysis

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=3 R=4 G=1 AC=3`
`STRUCTURE: native`
`TRACK: backend — 0/N UI files; touches scripts/, .github/workflows/, docs/`
`SCOPE: L` · `TIER: full`
`CLARIFICATION: 3 raised | 0 self-resolved | 3 for human decision`
`BASELINE: red locally (Windows-only PHP-adapter subprocess, WinError 2; green in Linux CI per PR #47). Change-area green (tokens-to-answer pure-Python 13/13).`

### Requirements matrix

| ID | Src | Verbatim (abbrev) | Interpretation | Ph1 evidence | Status |
|----|-----|-------------------|----------------|--------------|--------|
| G1 | Goal | "Prove the value claim the fixtures cannot" — real defensible ratio ≫ 1 | Ship a real sample-tier token-win number, not a behaviour-lock | fixtures ratio 0.302 < 1 (`tokens-to-answer.md:52`) | open |
| R1 | R | Add `source: sample` questions vs pinned repos; spread of grep-over-read query kinds | ≥1 question per query kind (callers / references / implementations / include) across laravel, symfony/demo, brick/math | questions.json has 0 sample rows; 4 tool kinds exist | open |
| R2 | R | Verify each answer by running the harness in a PHP+clone env | `expected`/`grep_evidence` = real resolved/raw-text hits, produced by a run | **blocked — no PHP locally** (`php: not found`, no `adapters/php/vendor`) | **blocked** |
| R3 | R | Wire sample tier to run on schedule / `workflow_dispatch`, not per-PR; record aggregate ratio | New `tokens_to_answer.py` sample-run code path + new workflow mirroring `cross-repo.yml` | harness skips samples today (`tokens_to_answer.py:309,352`) | open |
| R4 | R | Report the real ratio in the runbook, replacing "not yet populated" | Update `tokens-to-answer.md` §Sample tier with number + repro | current text = "not populated" (`tokens-to-answer.md:101-105`) | open |
| C1 | C | Answers verified by execution, never committed unverified | No placeholder `expected` may land; falsifiability is the point | ↳ depends on R2 env | open |
| C2 | C | Dev tooling under `scripts/`; no core change; deterministic, no LLM (R4); repo names out of `adapters/` (R2.2) | Sample-run logic lives in `tokens_to_answer.py`; pins in manifest | matches existing pattern | open |
| C3 | C | Per-PR fixture gate (`--min-ratio 0.24`) unaffected; sample tier separate scheduled run, own floor | Do not touch `ci.yml` fixture step; add separate floor | `ci.yml` fixture gate independent | open |
| AC1 | AC | questions file carries `source: sample` whose answers were produced (not guessed) by the harness | greppable + run-produced | falsifiable ✅ (pending R2) | open |
| AC2 | AC | Scheduled/dispatch job runs sample tier, reports aggregate ratio; number ≫ 1 (or write up if not) | **"≫ 1" needs a concrete floor to gate on** | vague threshold — Gate-1 pin needed | open |
| AC3 | AC | Runbook states real ratio + how to reproduce | falsifiable ✅ | text check | open |

### Universal inventory (R1 query-kind coverage)
`INVENTORY N=4 query kinds — find_callers (callers of a widely-used method), find_references (references to a class), find_implementations (implementations of an interface), include_graph (who includes X).`
Repos in play: laravel/laravel, symfony/demo, brick/math (3). Review confirms ≥1 sample question per
query kind, not just an aggregate count.

### AC validation / falsifiability
- **AC2 "≫ 1" is not falsifiable as written** — no numeric floor. Raised as Gate-1 pin (Q3).
- AC1, AC3 falsifiable as written.

### Outgrew-its-ticket flag
Ticket References state the `source: sample` path is "already wired via `cross_repo_validate`". It is
**not**: `tokens_to_answer.py` has no sample-run path — `run_fixture_questions` skips non-fixture
rows (`:309`) and `main()` only lists sample IDs as skipped (`:352,362`). So R1–R3 require **building**
a clone→build→evaluate→aggregate sample path in the harness **plus a new workflow** — real code, not a
JSON edit. This moves realized SCOPE to **L** (was framed ~M). Surfaced for re-scope/split at the gate.

### Gate 0 + Gate 1 questions (j = 3) — RESOLVED (see Session status)
1. Verify env → run locally (portable PHP env stood up; adapter verified).
2. Scope → do it all in 042 (L).
3. AC2 floor → report observed, set scheduled floor = round(0.8 × observed).

## Phase 2 — Design

### Approach
The `source: sample` execution path does not exist; build it in `tokens_to_answer.py` by **reusing**
`cross_repo_validate`'s already-proven clone-at-SHA + PHP-cmd machinery (the ticket's stated intent —
"via cross_repo_validate"). Add `run_sample_questions(questions, cache_root, php_cmd, skip_clone)`:
group `source: sample` rows by a new `sample: <pin-id>` field, clone/checkout each pin, `full_build`
it (reuse existing `build_index`), then `evaluate_question` per row (unchanged). A new `--samples`
flag switches `main()` to the sample tier (clone+build+gate) with its own `--cache-dir`/`--skip-clone`
and `--min-ratio` floor; **default behaviour is byte-for-byte unchanged** (fixture-only, samples still
listed as skipped) so the per-PR gate is untouched (C3). A new scheduled/dispatch workflow mirrors
`cross-repo.yml`. Sample questions are authored and their `expected`/`grep_evidence` **produced by
running the new path locally** against the warmed clone cache, then committed (C1/AC1).

### Rejected alternatives
- **Duplicate a checkout helper inside `tokens_to_answer.py`** — rejected: re-implements subtle
  git init/fetch-depth/checkout logic already correct in `cross_repo_validate`; reuse is DRY and the
  ticket points at it.
- **Split (engine now, populate later)** — rejected: env now supports real runs, so the full ticket
  (all ACs) ships in one PR; no operator-run deferral needed.
- **Run the sample tier per-PR** — rejected by C3 (needs clone+PHP, slow) — scheduled/dispatch only.

### Assumptions
- A1 `verified` — portable PHP 8.3.33 + `nikic/php-parser` v5.8 builds real indexes here (fixture run
  10/10 correct, ratio 0.284).
- A2 `verified` (was novel-untested) — all three pinned repos clone at their SHAs and build without
  mass-parse failure on this env. **Spike:** `cross_repo_validate.py --public-only` → `public_ok: 3,
  public_failed: 0`. Clone cache warmed at scratchpad `xrepo-cache/` for execute (`--skip-clone`).
- A3 `verified` — `run_grep_path`'s `rglob("*.php")` over the clones reads app source only (no
  committed `vendor/` in laravel/laravel, symfony/demo, brick/math) — so the grep over-read is real
  and bounded by `max_read_files`.

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | `run_sample_questions` + `--samples`/`--cache-dir`/`--skip-clone` wiring; import `cross_repo_validate` for `_ensure_checkout`/`load_manifest`/`_php_cmd` | `scripts/tokens_to_answer.py` | R3, C2 | 1/1 |
| 2 | Add `source: sample` questions (`sample:` pin id) covering all 4 query kinds; `expected`/`grep_evidence` produced by the local run | `scripts/tokens_to_answer_questions.json` | R1, R2, C1, AC1 | 4/4 kinds |
| 3 | New scheduled + `workflow_dispatch` workflow (setup-php, composer, `--samples --min-ratio <floor>`, upload artifact, issue-on-failure) | `.github/workflows/tokens-to-answer-sample.yml` | R3, AC2, C3 | 1/1 |
| 4 | Update §Sample tier with real ratio + repro, replacing "not yet populated" | `docs/runbooks/tokens-to-answer.md` | R4, AC3 | 1/1 |
| 5 | **Proving test** (logic routing) + opportunistic `@needs_php`+cache e2e; extend `test_questions_file_is_well_formed` to validate `sample:` rows name a known pin | `tests/test_tokens_to_answer.py` | proving, R1 | 1/1 |
| 6 | *Proof collateral:* `test_questions_file_is_well_formed` currently asserts a fixture `root` per row — sample rows have none; fold the `sample:`-field assertion in as a planned edit | `tests/test_tokens_to_answer.py` | R1 | 1/1 |
| 7 | Bookkeeping: BACKLOG status→done + token row; task frontmatter status→done | `docs/BACKLOG.md`, this file | AC1–3 | — |

### Rule compliance
- **R1.1 / R2.2 / R4** — no core change; all logic stays in `scripts/` dev tooling; pins stay in the
  manifest (no repo/framework names in `adapters/`); recipes deterministic, no LLM/network in core.
- **R1.2 (one seam, YAGNI)** — reuse existing functions; no new abstraction/registry.
- **R1.4 (SRP)** — script-to-script reuse only; adapters/store untouched.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 (questions produced by harness, not guessed) | runtime/3p (clone+PHP) | manual-recorded local run (this session) + logic test that sample rows are well-formed & routed | ✅ |
| AC2 (scheduled job runs, reports ratio; ≫1 or write-up) | e2e (CI) | new workflow (e2e) + manual-recorded local full-tier ratio | ✅ |
| AC3 (runbook states real ratio + repro) | doc/logic | text present in runbook (manual-recorded) | ✅ |
| R3 sample-run routing | logic | **proving test** (below), no PHP | ✅ |

No ❌ rows. AC1/AC2 runtime/e2e risk is proven by the actual local run recorded in execute **plus**
the scheduled workflow; the logic proving test covers the routing that can fail without PHP.

### Proving test
`test_run_sample_questions_selects_and_routes_by_pin` in `tests/test_tokens_to_answer.py`: with
`build_index`/`evaluate_question` monkeypatched (no PHP), assert `run_sample_questions` evaluates
**only** `source: sample` rows, groups them by `sample:` pin, and builds each pin's clone exactly
once. **Fails pre-change** (`run_sample_questions` does not exist); **passes post-change**.
Invocation: `pytest tests/test_tokens_to_answer.py -q`.

### Rollback + porting
Single repo (`app`). Rollback = revert the branch; the new workflow and sample questions are additive
(default fixture path unchanged), so reverting cannot affect the per-PR gate. No cross-repo port.

### SCOPE
`SCOPE: L` (re-affirmed; outgrew-its-ticket accepted at Gate 0). Branch type `feat` matches the
`feat/042-...` strategy — no branch/PR-type drift.

## Phase 3 — Execute

**Branch:** `feat/042-tokens-to-answer-sample-tier`.

### What landed (all 5 sample answers produced by the harness, not guessed)
Ran `tokens_to_answer.py --samples --skip-clone` against the warm clone cache with portable PHP
8.3.33: **5/5 correct, aggregate ratio 98.204** (grep 435,338 / atlas 4,433 tokens). Per question:
`impls_bignumber` 108.3 · `refs_biginteger` 147.4 · `callers_bignumber_iszero` 94.8 ·
`refs_tag_entity` 28.0 · `callers_post_getid` 19.3. Gate at floor 78 → exit 0 (pass).

### Verification sweep
- **Axis 1 (file set):** diff = exactly the 6 approved paths (harness, questions, workflow, runbook,
  test, working doc); no stray file, no untouched-line reformatting (ruff `--fix` touched only lines
  in the two files this change authored). `diff ⊆ approved list ✅`.
- **Axis 2 (design-conformance):** every Gate-2 Approach bullet `implemented-as-approved` **except**
  one deviation below.
- Change-area tests: `pytest tests/test_tokens_to_answer.py` → 14 passed, 1 skipped (`@needs_php`).
  Lint + mypy clean on changed files. Baseline unchanged (Windows-only PHP-subprocess failures are
  pre-existing, outside this diff).

### Deviation (for review adjudication)
- **Dropped the "opportunistic `@needs_php`+cache e2e" test** named in change-list item 5. It would
  **always skip in CI** (no warm clone cache there) and add a network/cache dependency for zero CI
  signal. The runtime proof of AC1/AC2 is instead the **recorded local run** (above) plus the
  **scheduled workflow**; the committed proving test covers the routing that can fail without PHP.
  Net: strictly smaller diff, same proof coverage.

### Coverage-gap exclusion (recorded, from analysis inventory N=4)
- `include_graph` ("who includes X") — **excluded** from the sample tier: all three pinned repos are
  PSR-4/autoloaded, so `INCLUDES` edges are dynamic with no resolved target (no verifiable answer).
  Fixture tier already covers `include_graph`. Covered kinds M=3 + excluded X=1 = N=4. Documented in
  the runbook.

### Ph3/4 proven by
- Proving test `test_run_sample_questions_selects_and_routes_by_pin` (logic routing).
- Local sample-tier run (AC1/AC2 runtime) + scheduled workflow (AC2 e2e).

## Phase 4 — Review

### Dispatches
- **`mango:reviewer`** (Sonnet): **CHANGES REQUESTED → conditional LGTM**, no Critical. Two Important
  findings, both fixed in commit `c67ef3f`:
  1. `verdict_markdown` + report `note` reused the fixture boilerplate ("toy repos / behaviour-lock,
     not the value claim") — false and self-undercutting on a `--samples` run. → both made mode-aware.
  2. Reaching into `cross_repo_validate`'s underscore-private `_ensure_checkout`/`_php_cmd`. →
     promoted to public `checkout_pinned`/`resolve_php_cmd` (internal callers + test updated).
  **Reviewer-directed scope addition:** `scripts/cross_repo_validate.py` joins the approved change
  list (rename refactor only, no behaviour change). Re-review was **verify-only** (main loop, no
  re-dispatch), per the conditional-LGTM path.
- **`mango:challenger`** (ticket-blind): **10 met / 2 not-met / 2 can't-tell** of 14 rebuilt reqs.
  - The 2 "not met" = the **recorded coverage-gap exclusions**: laravel/laravel has no sample
    (skeleton — index confirms 0 resolved CALLS, 0 inbound `App\` refs) and `include_graph` (autoloaded
    repos have no resolved INCLUDES). Both documented in the runbook. **Surfaced to the human at the
    finalise gate for ratification** (below).
  - The 2 "can't-tell" = execution-verification (challenger had no PHP), but it **independently
    corroborated all 5 answers against the real pinned SHAs** and noted the ratio 98.2 is an exact
    quotient of the raw token counts — strong evidence of a real run, not guessing.

### Verify-only re-review result (post-fix, commit c67ef3f)
Both findings landed as described. `pytest tests/test_tokens_to_answer.py` → 14 passed / 1 skipped;
sample-tier e2e re-run → 5/5, ratio 98.2, gate floor 78 pass; cross-repo tests 8 passed (regression
scan clean — no dangling old symbol names). Lint + mypy clean. **Verdict: clean.**

### Ph3/4 proven-by (k/N)
| Row | Proven by | k/N |
|-----|-----------|-----|
| G1, AC2, AC3 (ratio ≫1 reported) | sample run 98.2 + runbook + workflow | 1/1 |
| R1 (sample questions, query-kind spread) | 5 questions, 3 of 4 kinds; `include_graph` excluded (recorded) | 3/4 covered + 1/1 excluded = 4/4 |
| R2/C1/AC1 (verified by execution) | harness run 5/5 correct; challenger corroborated vs pinned SHAs | 1/1 |
| R3 (scheduled, separate from per-PR) | new workflow; `ci.yml` untouched; `--samples` opt-in | 1/1 |
| R4 (runbook real ratio) | runbook §Sample tier | 1/1 |
| C2/C3 (dev tooling, gate unaffected) | diff under `scripts/`+`.github/`+`docs/`; `ci.yml` untouched | 1/1 |
| Repo spread (laravel) | excluded — skeleton, no nav target (recorded) | exclusion |

### Coverage-gap exclusions (for human ratification at finalise)
1. **`include_graph` ("who includes X")** — not sampled: pinned repos are PSR-4/autoloaded, so
   `INCLUDES` edges are dynamic with no resolved target. Fixture tier already covers it.
2. **laravel/laravel** — no sample question: at the pinned SHA it is the app skeleton with no
   resolvable nav graph (0 resolved CALLS, 0 inbound `App\` refs). Stays a cross-repo *build* sample.

### Cost ledger (subagent dispatch only)
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Review | `mango:reviewer` (Sonnet) | 1 | 85,579 (22 tool uses / 266 s) |
| Review | `mango:challenger` (ticket-blind) | 1 | 48,792 (25 tool uses / 234 s) |
| **Total** | 2 dispatches | | **134,371** |
Top driver: reviewer round 1. Both retrieved via task-notification (usage blocks present). Phases 1–3
and the verify-only re-review dispatched nothing (all main-loop). Main-loop spend is unmeasured (host
does not surface per-task usage), as for prior tasks.

### Reviewed at c67ef3fc99d62d8ae7b6d27b3495c1ce5051d84c
Reviewed files: `scripts/tokens_to_answer.py`, `scripts/cross_repo_validate.py`,
`scripts/tokens_to_answer_questions.json`, `.github/workflows/tokens-to-answer-sample.yml`,
`docs/runbooks/tokens-to-answer.md`, `tests/test_tokens_to_answer.py`.
Working doc (exempt from staleness): `docs/tasks/042_tokens-to-answer-sample-tier.md`.
