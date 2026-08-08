---
id: 055
slug: recall-benchmark
title: Nothing measures what the tools fail to find — a recall gate above the cost metric
phase: 1.5b
milestone: Measure
status: done
depends_on: [034, 045]
---

## Goal
The project's metric is **tokens-to-correct-answer vs a grep+`Read` baseline** (PLAN §19, task 034).
That is a *cost* metric. It checks each question's `expected` answer, but every question in the set was
written by someone who already knew the tool could answer it — so nothing in the harness ever asks
**what the tool missed**.

That gap is not theoretical. Field retro round 2 recorded `find_callers` returning `total_count: 0` for
a method with six live call sites ([054](054_bare-name-callers-silent-drop.md)). Run through the
existing harness, that answer scores as a **cheap success**: few tokens, and the missing callers are
not in anyone's `expected` list. The metric we build the project around cannot see the worst failure
the project has had.

Task 046's outcome already recorded the same shortcoming from the other side — *"this benchmark
measures cost, never what a payload carries"* — and nothing was done about it.

**Both retros also measured the wrong shape.** Every question they timed handed the agent the symbol's
name up front (`who calls \Foo::save`). That is grep's best case, not the case the project exists for.
The founding claim — that native tools flounder on a large repo — is about starting from a *symptom*
with no name in hand.

**Updated 2026-08-08: that claim has now been measured once, externally, and it lost** (PLAN §19). Five
symptom-first questions, hand-graded: native tools 5/5, code-atlas 3 correct · 1 partial · 1 wrong. That
round was n=1 per cell, not blind, and lives outside this repo — so it is evidence, **not** the gate this
ticket builds. Two of its findings change what this ticket must measure, and both are now deliverables
below: no question in that set needed a whole-graph query, and the agent used the index in only 19% of
its tool calls. A recall gate that never exercises the tools an agent does not reach for measures the
wrong half of the problem.

## Scope / Deliverables
- **A recall measure, reported next to the cost ratio.** For a question with known ground truth: what
  fraction of the true result set the tool returned, and — counted separately, because it is the one
  that destroys trust — how often it returned a confident empty or a confident wrong answer.
- **`confidently_wrong` is its own metric, not a recall miss.** "I don't know" and "there is nothing"
  are different answers; the harness must score them differently or the number hides the only failure
  mode that makes an agent stop using the tool.
- **Symptom-first questions.** A question tier whose prompt names no file, class, or method — the agent
  must find the name before it can use it. This is the only shape that can test the founding claim.
- **Session-level accounting for that tier**: tokens to the answer, files read, whether the answer was
  reached at all — not per-call cost, which is what the current harness measures.
- **Whole-graph questions, which no benchmark has ever posed.** At least two questions answerable only
  by `impact`, `reachable_from`, `find_orphans`, `include_graph` or an edge-health aggregate — the tools
  the project exists for, and the ones the 2026-08-08 round never touched. Add one whose answer is a
  *relationship* rather than a location: text search finds locations, and nothing has yet forced the
  distinction the index's whole claim rests on.
- **Report index-use share per question** — MCP calls as a fraction of all tool calls. A tool that is
  correct and never chosen is a fit failure, and it is invisible to both recall and cost. The external
  round measured 19% for code-atlas and 0% for a language server on the same questions; without this
  number in the harness, that finding cannot be tracked or moved.
- **A recall floor in CI, on the fixture tier**, alongside the existing `--min-ratio` gate: a change
  that halves tokens while losing results must fail, and today it passes.
- **Runbook section** in [`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) stating the
  ordering plainly: recall is a gate, cost is the win. A cheaper answer that finds less is a regression.

## Constraints
- **Correctness is a gate, cost is what is maximised.** Not a ranking — a tool that is merely as
  correct as grep and no cheaper has no reason to exist, and a tool that is cheaper and wrong loses the
  user. Both halves must be expressible in the harness.
- **Ground truth is written before the run, by hand.** Truth decided after seeing a tool's answer
  measures nothing.
- **Determinism (R4)** — no LLM in the harness; recipes stay fixed data, as they are today.
- **Nothing about a private repo enters this repository** (as [045](045_tokens-to-answer-local-repo.md)):
  the symptom-first question set for the anchor repo lives outside, and the local report is not the
  artifact CI uploads.
- **The existing fixture gate must not move** — `--min-ratio 0.24` on the fixture tier stays green and
  byte-identical unless the recall work deliberately changes it.
- **No language branch in the core (R1.1)**; this is `scripts/`-side.

## Acceptance criteria
- A question can declare a **complete** expected set, and the harness reports recall against it.
- A tool that returns an empty result where ground truth is non-empty is scored `confidently_wrong`,
  reported separately from a partial-recall miss, and a test asserts the two are not conflated.
- A symptom-first question runs end to end and reports session-level tokens and whether the answer was
  reached.
- CI gates a recall floor on the fixture tier; a deliberately-broken resolver fails that gate in a test.
- The runbook states the gate-vs-win ordering.
- Existing fixture-tier output is unchanged; `pytest`, `ruff`, `mypy` green.

## References
`scripts/tokens_to_answer.py` — `evaluate_question` `:173-191`, `run_grep_path` `:139-170`, the CLI at
`:380+`; [`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) (fixture / sample / local
tiers, and the "What this metric cannot see" section this ticket extends).
PLAN §19 (the metric, and the founding claim this ticket makes falsifiable).
[046](046_resolver-qname-candidate-dedupe.md) outcome — the same shortcoming, recorded and not acted on.
[054](054_bare-name-callers-silent-drop.md) — the failure this metric must be able to see; its Part B
is what lets a miss be reported honestly rather than as an empty answer.
Origin: field retro round 2, and the priority decision of 2026-08-07 (correctness gates, cost wins).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 055 — recall-benchmark (working doc)

- **Ticket:** 055 · local `docs/tasks/055_recall-benchmark.md`
- **Type:** enhancement (scripts/ harness + fixture questions + CI/runbook)
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI paths (`config.track=backend`)
- **TIER:** full
- **BASELINE:** green — `891 passed` at session start; post-change `895 passed` (+4 recall tests)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/055_recall-benchmark.md` (below separator)

---

## Phase 0 — Refine

`REFINE: 2 want-decision asked | 6 ASSUMED (exposure) | skip: no`

**Want-decisions (standing approval 2026-08-08 → recommended):**

| ID | Choice | Meaning |
|----|--------|---------|
| W1 | A | CI `--min-recall 1.0` on fixtures |
| W2 | A | Index-use share only on `session_path` / symptom tier |

**ASSUMED under standing approval (exposure-checker):**

1. Session = fixed recipes with native `grep` / `read_file` (no LLM)
2. `confidently_wrong` = empty `results` when `expected_set` non-empty
3. Optional `expected_set`; substring match; recall-gated fixtures declare it
4. Whole-graph questions on fixture/CI
5. No fair grep → `ratio_eligible: false`, excluded from ratio aggregate
6. One committed synthetic symptom-first question (private anchor sets stay outside)

**Exposure-checker:** [Challenger](0c65c05b-1f1a-4822-ac56-2566b8c9806e) — additional decisions folded into ASSUMED above.

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=4 R=8 G=2 AC=6`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| C1 | Constraints | Correctness gates, cost maximised | Both expressible in harness | runbook + assert_benchmark | ✅ |
| C2 | Constraints | Ground truth before run | Hand-written `expected`/`expected_set` | questions.json | ✅ |
| C3 | Constraints | Determinism R4; no LLM | Fixed recipes | session_path native only | ✅ |
| C4 | Constraints | No private repo in-repo; R1.1 scripts-only | fixture/synthetic only | reach fixture; no core | ✅ |
| R1 | Scope | Recall next to cost ratio | score_recall + aggregate.recall | tokens_to_answer.py | ✅ |
| R2 | Scope | confidently_wrong separate | empty results ≠ partial miss | score_recall + test | ✅ |
| R3 | Scope | Symptom-first + session accounting | session_path + session stats | symptom_persist_via_put | ✅ |
| R4 | Scope | ≥2 whole-graph questions | impact + reachable + orphans | 3 questions | ✅ |
| R5 | Scope | Index-use share | session index_use_share | W2 | ✅ |
| R6 | Scope | CI recall floor + min-ratio 0.24 | `--min-recall 1.0` | ci.yml | ✅ |
| R7 | Scope | Runbook gate-vs-win | "Recall gates, cost wins" | runbook | ✅ |
| R8 | Constraints | min-ratio 0.24 stays green | ratio 0.269 measured | assert_benchmark | ✅ |
| G1 | Goal | Metric must see empty misses | confidently_wrong gate | assert_benchmark | ✅ |
| G2 | Goal | Founding claim falsifiable shape | symptom tier | session_path | ✅ |
| AC1 | AC | expected_set → recall | score_recall | tests | ✅ |
| AC2 | AC | empty ≠ partial; test | test_score_recall_separates… | ✅ |
| AC3 | AC | symptom e2e session tokens | e2e asserts session | ✅ |
| AC4 | AC | CI recall floor; broken fails test | test_recall_gate_fails… | ✅ |
| AC5 | AC | Runbook ordering | runbook section | ✅ |
| AC6 | AC | pytest/ruff/mypy green; floor holds | 895; ruff; mypy; bench | ✅ |

`CLARIFICATION: j=0` (wants ratified by standing approval)

- **Gate 1 status:** cleared — standing approval 2026-08-08

---

## Phase 2 — Design

**Approach.** Extend `scripts/tokens_to_answer.py` only: recall scoring, optional `expected_set`, `session_path` (native+MCP), `ratio_eligible`, CLI `--min-recall`, CI dual gate. Add planted `tests/fixtures/php/reach/` + questions (whole-graph + one synthetic symptom). Runbook states recall-gates/cost-wins. No `code_atlas/` / adapter changes (R1.1).

**Rejected.** LLM session runner (R4). Private IDs in-repo (045). Index-use on MCP-only recipes (W2). Soft recall floor &lt;1.0 on fixtures (W1).

**Approved change list:**

| # | Change | Path | Matrix |
|---|--------|------|--------|
| 1 | Recall/session/ratio_eligible + `--min-recall` | `scripts/tokens_to_answer.py` | R1–R6, AC1–4 |
| 2 | expected_set + whole-graph + symptom questions | `scripts/tokens_to_answer_questions.json` | R3–R4, C2 |
| 3 | Planted reach fixture + entry_points toml | `tests/fixtures/php/reach/` | R4, C4 |
| 4 | Recall/session proving tests | `tests/test_tokens_to_answer.py` | AC2–4, proving |
| 5 | CI `--min-recall 1.0` keep `--min-ratio 0.24` | `.github/workflows/ci.yml` | R6, R8 |
| 6 | Runbook recall-gates section | `docs/runbooks/tokens-to-answer.md` | R7, AC5 |
| 7 | BACKLOG + frontmatter in-progress→done | `docs/BACKLOG.md`, task | R7.2 |

**Proving test:** `test_score_recall_separates_confidently_wrong_from_partial_miss` + `@needs_php` e2e with `assert_benchmark(..., min_ratio=0.24, min_recall=1.0)`.

- **Gate 2 status:** cleared — standing approval 2026-08-08 (best options; pass all gates)

---

## Phase 3 — Execute

- Branch: `feat/055-recall-benchmark`
- Commits: `4ef87ce` (feat), `8749f93` (review fixes)
- Proving tests: recall separation + session CW + empty-nav gate + `@needs_php` e2e
- Verification: fixture bench `ratio=0.269 recall=1.0 confidently_wrong=0` / 14 Q; **896 passed**; ruff/mypy clean
- Diff ⊆ approved list ✅; review findings 1–3 fixed in `8749f93`

## Phase 4 — Review ✋

- reviewer: **CHANGES REQUESTED** → verify-only **LGTM** ([Reviewer](afb8fa8b-1807-44f0-9cf8-461acf1f883c) → [Reviewer](3dd35d04-02f2-440f-b9df-ca99c91d3b28)) @ `8749f93`
- challenger (ticket-blind): prior gaps closed under AC; Goal-only residual = no abstain channel ([Challenger](a819ecca-7538-4bd5-be05-097118380078) → [Challenger](bcebf7cb-27cf-4f60-9bf7-ffd05c8d3a93))
- Scope reconciliation: diff ⊆ approved list ✅ (scripts/tests/docs/ci/fixtures; no `code_atlas/` / `adapters/`)
- Proving test: 32 harness tests + full suite **896 passed**
- **Clean?** yes
- **Reviewed at:** `8749f93` · reviewed files: `scripts/tokens_to_answer.py`, `scripts/tokens_to_answer_questions.json`, `tests/test_tokens_to_answer.py`, `tests/fixtures/php/reach/*`, `.github/workflows/ci.yml`, `docs/runbooks/tokens-to-answer.md`, `docs/BACKLOG.md`, `docs/tasks/055_recall-benchmark.md`
- **Exclusion (Goal-only):** tools have no “I don’t know” abstain payload; AC only requires empty→`confidently_wrong`

### Reviewer detail — round 1 ([Reviewer](afb8fa8b-1807-44f0-9cf8-461acf1f883c)) @ `4ef87ce`

**Verdict: CHANGES REQUESTED** (conditional LGTM once Important 1–3 land). Critical: none.

| # | Finding | Path | Fix |
|---|---------|------|-----|
| 1 | Incomplete `expected_set` for `reachable_from_entry` (2 of 5 measured qnames) | `scripts/tokens_to_answer_questions.json` | Full set: `entry.php`, `\Entry`, `\Entry\main`, `\Lib\Helper`, `\Lib\Service` |
| 2 | Incomplete `expected_set` for `orphans_dead_unused` (missing `\Dead`) | same | `["\\Dead", "\\Dead\\Unused"]` |
| 3 | Native grep hits masked session `confidently_wrong` | `scripts/tokens_to_answer.py` `result_bearing_responses_empty` | Ignore `_NATIVE_TOOLS`; session-shaped test |
| note | `files_read=0` on grep session steps | `run_native_step` | Return `len(bodies)` |

**Scope check:** all 7 approved change-list paths present; R1.1/R4/min-ratio 0.24/no private IDs ✅.

### Reviewer detail — verify-only ([Reviewer](3dd35d04-02f2-440f-b9df-ca99c91d3b28)) @ `8749f93`

**Verdict: LGTM.** Findings 1–3 + files_read + symptom wording + broken-empty gate test verified fixed. Critical/Important remaining: none.

### Challenger detail — round 1 ([Challenger](a819ecca-7538-4bd5-be05-097118380078)) — ticket-blind @ `4ef87ce`

Rebuilt from raw ticket + `main...feat/055-recall-benchmark` only.

**Summary: 14 met · 5 not met · 0 can’t-tell**

| # | Requirement | Verdict |
|---|-------------|---------|
| 1–3, 7–10, 12–17 | Recall/CW/CI/runbook/whole-graph/R4/R1.1/private-repo/`min-ratio` | **met** |
| 4 | “I don’t know” vs empty | **not met** (no abstain channel) |
| 5 | Symptom prompt names no method | **not met** (`put()` in question text) |
| 6 | Session `files_read` for grep | **not met** (hard-coded 0) |
| 11 | Deliberately-broken empty-nav fails recall gate in a test | **not met** (synthetic ratio only) |
| 18 | Fixture-tier output unchanged | **not met** (recall columns added) |

### Challenger detail — re-check ([Challenger](bcebf7cb-27cf-4f60-9bf7-ffd05c8d3a93)) — ticket-blind @ `8749f93`

Prior five not-mets re-judged:

| # | Verdict | Evidence |
|---|---------|----------|
| 4 | **met (AC)**; Goal-only residual | AC requires empty→CW; no abstain channel remains Goal/Scope prose only |
| 5 | **met** | Symptom question no longer names `put()` / file / class |
| 6 | **met** | Grep returns `len(bodies)`; e2e asserts `files_read > 0` |
| 11 | **met** | `test_recall_gate_fails_when_nav_returns_empty_for_known_set` |
| 18 | **met** (deliberate-deliverable reading) | `--min-ratio 0.24` kept; recall columns are the ticket |

**Five-item counts: 5 met · 0 not met.** Full-ticket AC/Scope: satisfied; only Goal abstain residual remains.

## Phase 5 — Finalise ✋

- Outward actions (approved 2026-08-08): push · open PR · status→done + token row
- Follow-up deferred: Goal abstain/“I don’t know” channel (needs tool surface)
- Revert path: revert branch commits; close the PR

## Session status

- **Last updated:** 2026-08-08
- **Current phase:** Phase 5 — Finalise (push + PR)
- **Next action:** push + `gh pr create`

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 0 | exposure-checker Challenger ([Challenger](0c65c05b-1f1a-4822-ac56-2566b8c9806e)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:reviewer ([Reviewer](afb8fa8b-1807-44f0-9cf8-461acf1f883c)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:challenger ([Challenger](a819ecca-7538-4bd5-be05-097118380078)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:reviewer verify ([Reviewer](3dd35d04-02f2-440f-b9df-ca99c91d3b28)) | 2 | unmeasured (blocking retrieval) | — |
| 4 | mango:challenger re-check ([Challenger](bcebf7cb-27cf-4f60-9bf7-ffd05c8d3a93)) | 2 | unmeasured (blocking retrieval) | — |

`LEDGER TOTAL: 5 dispatch rows · all unmeasured (blocking retrieval) · top cost driver: review rounds`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-08 | W1=A, W2=A | Standing approval recommended |
| 2026-08-08 | ASSUMED 1–6 | Standing approval after exposure-checker |
| 2026-08-08 | ratio_eligible false for whole-graph/symptom | Preserve fixture cost floor semantics |
| 2026-08-08 | CW = empty MCP results only | AC; no abstain channel in tools (Goal residual) |
| 2026-08-08 | Gate 4 clean | reviewer LGTM @ `8749f93` after Important 1–3 fixed |
| 2026-08-08 | Finalise push+PR approved | user: add review detail, commit, push, open PR |
