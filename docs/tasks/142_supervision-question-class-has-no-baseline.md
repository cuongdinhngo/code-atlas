---
id: 142
slug: supervision-question-class-has-no-baseline
title: The supervision question class was never put through the harness — 121's lesson, one phase later
phase: 3
milestone: Measure
status: done
depends_on: [034, 055, 121, 135]
---

## Why this exists

[121](121_onboarding-question-class-never-measured.md) exists because **Phase 3 shipped without its own
cost gate**, and its split verdict is what narrowed the phase: cheap and correct where the question is a
lookup (12/12, recall 1.0), wrong where it is a reading order — `guided_tour` opened `symfony/demo` with
a lint config and put the front controller fifth
([benchmark](../benchmarks/121_onboarding-question-class.md)).

[138](138_architecture-rules-are-never-asked-of-the-graph.md),
[139](139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md),
[140](140_impact-answers-in-symbols-not-modules.md) and
[141](141_extractability-cut-edges-and-the-cycles-that-block-it.md) propose four answers to a **question
class the harness has never seen**: *does this rule still hold*, *what changed architecturally*, *which
modules does this reach*, *can this be split*. 034/045/055 and 135's precision axis carry no such class.

**This ticket runs first, not last.** Done first it produces the baseline the other three are measured
against; done last it repeats 121 exactly — which is the one mistake this set already knows about.

Provenance: the architecture review of 2026-08-23, applying 121's lesson forward. **No tool is built
here.**

## Scope

- A fixture question set for the class: **≥6 questions** on the committed public pins, each with a
  hand-verified expected answer.
- The grep+`Read` baseline cost per question, recorded in a benchmark file — the same baseline 034
  defines.
- The class run under the existing harness on **both** axes: recall (055) and precision (135).
- Where no tool among the 17 can answer, that is recorded as **no tool answers this**, not scored as a
  miss — the two are different findings and 121's split verdict is what proves it.

## Acceptance criteria

- **AC1** ≥6 questions on pinned public repos, expected answers hand-verified, committed as fixtures.
- **AC2** Baseline (grep+`Read`) tokens-to-answer recorded per question in `docs/benchmarks/`.
- **AC3** The class runs on both axes; an unanswerable question is labelled unanswerable, not zero.
- **AC4** The benchmark names the host, the server build and the index revision that produced it
  (125's rule — a retro must not quote a commit that did not answer).
- **AC5** The existing question classes' numbers are unchanged, asserted — the class was added, the
  metric was not moved.

## Out of scope

- **Building any of 138–141.**
- **Changing the pins or the harness's existing classes.**
- **Deciding whether the class is worth serving.** That is what the numbers this ticket produces are
  for; 141's gate reads them.

<!-- ============================ MANGO WORKING DOC (embed) ============================ -->
---

# Working doc — 142

## Session status
- **work_doc_mode:** embed (harness default; 142 is a tracked task file, not a scaffold stub)
- **branch:** `chore/142-supervision-question-class`
- **CHALLENGER:** OFF (--no-challenger)
- **review:** SKIPPED (run arg: "skipped review")
- **TIER:** full · **SCOPE:** L (new fixtures + snapshots + questions + harness bindings + test + benchmark)
- **phase:** finalise (execute done; review SKIPPED per run arg)
- **run args:** standing approval to choose approach + pass all gates; finish through commit + push + PR.

## Phase 3 — Execute (done) · Phase 4 — Review SKIPPED (run arg)

Built exactly the D1–D7 change list, nothing wider. Verified in **Docker** (Linux, Python 3.12.14,
PHP 8.2.33 — the Windows host cannot run the PHP/POSIX suite):
- **Delta-green:** `ruff` ✅, `mypy` ✅ (71 files), `pytest -q` **2015 passed, 1 skipped, 1 failed**.
  The one failure is environmental, **not this change**: `test_ac2_ci_carries_the_same_step_as_the_gate`
  reads `.github/workflows/ci.yml`, which `.dockerignore` excludes from the image; it fails identically
  on main in Docker and is unrelated (this ticket touches no `.github`/ci/bytecode path). The real gate
  for it is `scripts/gate.sh` on a POSIX host with `.github` present.
- **New test** `tests/test_supervision_question_class.py`: 8 passed, incl. the `@needs_php` both-axes
  proving test (recall 1.0, precision 1.0 on scored rows; unanswerable row labelled).
- **AC5 empirically proven** ([benchmark](../benchmarks/142_supervision-question-class.md)): ratio 0.807
  and every existing row byte-identical with/without the `_TOOL_NAMES` additions.

**proven by (matrix):** G1/C1 — no `code_atlas/` diff (grep-clean); R1/AC1 — 6 `tier: supervision`
questions, fixture proving path green; R2/AC2 — benchmark doc records the per-question baseline (the
documented absence of a fair grep) ; R3/AC3 — `test_the_class_is_measured_on_both_axes`,
`test_the_unanswerable_row_is_labelled_not_scored`; R4 — `sup_can_split_unanswerable` labelled;
AC4 — benchmark provenance block; AC5 — `test_supervision_class_cannot_move_the_cost_ratio` + benchmark
toggle table; C2 — additive-only harness change proven byte-identical; C3 — benchmark defers the
worth-serving call to 141's gate.

## Phase 5 — Finalise (learning loop)

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop (no subagent dispatched)

Lesson `142-C1` written to `docs/LESSONS.md` (type 5, project-ground-truth, seen 142, stays in
lessons_path — a repo fact about the scorer's identity vocabulary, not a cross-ticket heuristic).

## Phase 0 — refine

PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no

`refine ran: 1 unresolved product-decision` (HOW, self-resolved + cited; no WANT for the human).
- **PREMISE check:** PASS. Every source the ticket references resolves — `tour.py` Tarjan, `metrics.py`,
  the four tools (138 `check_architecture_rules`, 139 `diff_architecture`, 140 `impact_modules`,
  120 `subtree_dependencies`) all exist. Not premise-falsified.
- **HOW-1 (tier ambiguity):** AC1 says "pinned public repos" but also "committed as fixtures", and Scope
  says "committed public pins". Resolved: **fixture tier is primary + CI-gated**, because two of the
  class's tools need committed scaffolding a cloned pin cannot host cleanly — `check_architecture_rules`
  needs a rules file on the indexed tree, `diff_architecture` needs two dataset snapshots. Add **one
  sample-tier** supervision question (`impact_modules` on `symfony_demo`) to honour "pinned public repos"
  where a tool applies with no scaffolding. Cited: 121/135 both run fixture-tier as the CI gate and
  sample-tier as the maintainer-run value tier; this class follows that precedent.

## Phase 1 — Analysis (requirements matrix)

Legend: **G** goal · **R** scope/deliverable · **AC** acceptance · **C** constraint. `proven by` filled in Ph3/4.

| # | Requirement | Source | Design row | proven by |
|---|---|---|---|---|
| G1 | Produce the baseline the supervision class (does-rule-hold / what-changed / which-modules-reach / can-split) is measured against; **no tool built** | Why exists | D4, D6 | — |
| R1 | Fixture question set for the class: ≥6 questions, each hand-verified | Scope 1 | D1,D2,D4 | — |
| R2 | grep+`Read` baseline cost per question, recorded in a benchmark file (034's baseline) | Scope 2 | D6 | — |
| R3 | Class run under the existing harness on **both** axes: recall (055) + precision (135) | Scope 3 | D4,D5,D6 | — |
| R4 | Where no tool answers → recorded **no tool answers this**, not scored as a miss | Scope 4 | D4(unans),D5,D6 | — |
| AC1 | ≥6 questions, expected answers hand-verified, committed as fixtures | AC1 | D1,D2,D4 | — |
| AC2 | Baseline tokens-to-answer recorded per question in `docs/benchmarks/` | AC2 | D6 | — |
| AC3 | Class runs on both axes; an unanswerable question is labelled unanswerable, not zero | AC3 | D4(unans),D5 | — |
| AC4 | Benchmark names host, server build, index revision (125's rule) | AC4 | D6 | — |
| AC5 | Existing classes' numbers unchanged, **asserted** | AC5 | D5 | — |
| C1 | Build no tool (138–141 not built) | Out of scope | all — only fixtures/questions/bench/test | — |
| C2 | Don't change the pins or the harness's existing classes | Out of scope | D3 additive-only | — |
| C3 | Don't decide whether the class is worth serving | Out of scope | D6 reports, does not rule | — |

SECTIONS: 4 found (Why this exists, Scope, Acceptance criteria, Out of scope) | 4 decomposed | ROWS: C=3 R=4 G=1 AC=5
CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R4.2 (determinism) ✅, §R2 (standard-over-sample) ✅, §R7.2 (docs+ledger) ✅, §R7.6 (prune) ✅

Clarification tally: **0 open** (HOW-1 self-resolved; no WANT → no Gate 0).

## Phase 2 — Design

HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered
EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor

No coverage excluded. Two design notes (not exclusions — both are delivered): the full acyclic
**cut-edge-set** half of "can this be split" is answered by **no tool** (141 deferred), delivered as the
labelled unanswerable row AC3/R4 require; the sample-tier supervision row runs only under `--samples`
(not CI), the same platform limit 135's sample tier documents.

**Approach.** Add a `supervision` tier to the existing tokens-to-answer harness — the same instrument
121 used for the onboarding class — exercising the four already-shipped supervision tools, plus one row
that is honestly unanswerable (141's acyclic cut-edge set, deferred). No new tool, no core change.

**Rejected alternatives.** (a) *Sample tier only* — rejected: `check_architecture_rules`/`diff_architecture`
can't get their scaffolding into a cloned pin without fragile injection, and the CI gate needs committed
fixtures. (b) *A new bespoke harness* — rejected: 034/055/135 already score recall+precision+cost; a second
harness would duplicate the axes AC3 names. (c) *Skip the unanswerable row* — rejected: AC3/R4 require it.

**Change list (D1–D7):**
- **D1** New PHP fixture `tests/fixtures/php/architecture_rules/` — domain→service→http chain,
  `.code-atlas.toml` (`architecture_rules=["rules.json"]`, `entry_points`), `rules.json` with one
  violated rule (`domain-must-not-reach-http`) and one that holds. [R1/AC1/G1]
- **D2** New snapshot fixture `tests/fixtures/php/architecture_drift/` — two committed dataset snapshots
  (`before.json`/`after.json`, matching `index_root`+`version`, one module/layer/matrix drift) for
  `diff_architecture`. [R1/AC1]
- **D3** `scripts/tokens_to_answer.py` — **additive**: bind `impact_modules` + `subtree_dependencies`
  in `_TOOL_NAMES` + `bind_tools`; add a light `unanswerable` field surfaced into the report row
  (no expected_set, requires `unanswerable_note`). No existing binding/scoring touched. [R3/R4/C2]
- **D4** `scripts/tokens_to_answer_questions.json` — ≥6 `tier: supervision` questions, `ratio_eligible:false`
  + `ratio_note` (no fair grep for a rule-closure/drift/rollup/split): rule-holds(violation),
  rule-holds(clean), arch-drift, modules-reached, can-split(partial subtree_dependencies+guided_tour),
  can-split(**unanswerable** full cut-set), + 1 sample-tier `impact_modules` on `symfony_demo`. Each
  hand-verified `expected`/`expected_set` + `precision_scope`/`precision_note`. [R1/R2/R3/R4/AC1/AC2/AC3]
- **D5** `tests/test_supervision_question_class.py` — mirror of 121's test: class present ≥6, tier present,
  every recipe answers with a tool, exercises the supervision tools, bindable, scored rows declare recall
  ground truth, the unanswerable row is labelled (not scored zero), out-of-ratio states why, **AC5**:
  the supervision class carries **no ratio-eligible** question so the existing cost ratio is unchanged
  by construction (asserted). [R3/R4/AC3/AC5]
- **D6** `docs/benchmarks/142_supervision-question-class.md` — per-question both-axis numbers, the grep
  baseline or its documented absence, the **no-tool-answers-this** recording for the full split question
  (feeds 141's evidence-gate item 3), and AC4 provenance (host, server build/commit, index revision). [R2/R3/R4/AC2/AC3/AC4]
- **D7** Bookkeeping — BACKLOG 142 todo→done + frontmatter status; `docs/TOKEN_LEDGER.md` spend row;
  one-line BACKLOG governance note. Prune, don't retell (R7.6). [R7.2]

**Rule-compliance:** R4/R4.1 (deterministic, no LLM/core change — this is `scripts/` dev tooling);
R2 (standard over sample — the arch-rules fixture encodes a generic layering rule, not a repo's names);
R7.2/R7.6 (docs + ledger, prune). Zero core/`code_atlas/` change → R1.1 untouched.

**Named proving test:** `tests/test_supervision_question_class.py::test_supervision_class_present_and_measured`
plus the `@needs_php` end-to-end row added to `test_tokens_to_answer.py` proving the class runs green on
both axes (recall 1.0 on scored rows, the unanswerable row labelled, cost ratio unchanged). Verified in
Docker (Windows host cannot run PHP/POSIX suite).

## Cost ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| (no subagent dispatched yet — main-loop only) | — | — | n/a |
