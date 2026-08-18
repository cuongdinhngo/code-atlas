---
id: 085
slug: onboarding-summarizer-seam
title: Onboarding — Summarizer Protocol seam + deterministic default (M10)
phase: 3
milestone: M10
status: done
depends_on: [083]
---

## Goal
The single seam that keeps the LLM out of the core: a `Summarizer` Protocol with a deterministic
default, so later LLM enrichment (090/091) plugs in without the core ever importing an LLM.

## Scope / Deliverables
- `Summarizer` Protocol in `code_atlas/onboarding/`; default impl = **structural** summary (signature,
  docblock first line, role tag derived from 083 metrics). No SQL, no network, no LLM.
- One seam only (R1.2) — no registry/factory until a second summarizer exists.
- A CI test that proves the **graph → enrichment → presentation** split holds with the middle stage
  faked (R4.1 keeps the LLM out of the core; this keeps it out of CI too).

## Acceptance criteria
- Default summarizer is deterministic (R4.2) and language-agnostic (no PHP logic).
- The stubbed-seam test asserts the split and would fail if presentation read the graph directly.
- No dead abstraction (R7.4): exactly one Protocol, one default impl.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §2–§4;
PLAN §14, §15 (M10). Precedent for optional deterministic enrichment: `code_atlas/enrichment.py`.

## Session status
- **Runner:** `/mango:autorun 085` (unattended lifecycle, stops at the PR; **challenger ON** — default).
- **Handover authorisation:** the two outward actions (push branch, open PR) are covered by the
  maintainer's standing durable approval in `AGENTS.md` (*Maintainer workflow*) plus the explicit
  `/mango:autorun 085` invocation. Recorded verbatim in `.mango/run-contract-085.txt`.
- **Envelope:** RUN CONTRACT written + validated at t0 (bound at Gate 2); RECONCILE t0 clean (2 BROKEN
  bound floor conditions, 2 UNBOUND — TREE-COMPARISON + PROVING-TEST, 0 holding → no strikes).
  Merge-strategy: squash-or-rebase (28 first-parent commits since newest merge; narrows not removes).
  Call-ceiling: **unknown** (no ledger history for tier `standard` — recorded, not invented). Windows
  note: floor POSIX checks wrapped in `bash -c`; contract I/O forced UTF-8 (`PYTHONUTF8=1`).
- **work_doc_mode:** embed. **Branch:** `feat/085-onboarding-summarizer-seam`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: S` · `TIER: full`.
- **Outcome — `done`, PR opened.** All 7 matrix rows green (G1/R1/R2/R3/AC1/AC2/AC3); reviewer
  conditional-LGTM with both Important findings landed; challenger 9/9; Docker full gate **1317 passed,
  0 failed** (delta-green, +9). Ticket `status: done`.
- **Next action (maintainer):** review & merge **PR #124** (squash). Then confirm the two `proposed`
  lessons (085-C1/C2) in `docs/LESSONS.md` — both are `count-pin-in-blast-radius` / `ac-failure-mode-needs-the-right-guard`,
  type-2 seen-once; run `/mango:promote` only if either recurs (seen ≥ 2). **086 (`architecture_overview`)
  can start — it depends on 084/085/104; 085 is now done.**
- **Revert path:** unmerged → close the PR + `git push origin --delete feat/085-onboarding-summarizer-seam`.
  Merged → revert the single squash-merge commit on `main` (no schema/contract/tool change to undo; the
  new module has no importer yet — 086 is the first).

## Phase 0 — refine (self-skipped)
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**Premise.** All four referenced-as-existing sources resolve: `code_atlas/onboarding/` (exists;
`metrics.py` = the 083 metrics), `code_atlas/enrichment.py` (the named deterministic-enrichment
precedent), `docs/phase3-onboarding/PHASE3_ONBOARDING.md` §2–§4. The `Summarizer` Protocol itself is
to-be-created (not missing). `m = 0` → continue.

**Recall (advisory, blocks nothing).** `093-C3 prove-the-guard-fails` (type 2, confirmed, seen
093/096/099/100/101; promoted to R6.5) matches by handle — the change introduces a CI guard test, and
085's AC requires it "would fail if presentation read the graph directly", i.e. the guard must be
*made to fail*, not merely pass. Carried into design/execute as a constraint on the stubbed-seam test.

**Skip rationale.** 085 is fully locked: the scope names the seam (`Summarizer` Protocol), the default
impl (structural: signature + docblock first line + role tag from 083 metrics; no SQL/network/LLM), the
one-seam-YAGNI constraint (R1.2), and the CI split-proof test. Every remaining choice (exact role-tag
vocabulary, module layout, Protocol method shape) is a HOW/design decision the later phases own, and it
is derivable from `metrics.py` + the PHASE3 doc + the `enrichment.py` precedent — none is an
acceptance-bar decision the user owns. No want-decision survives, so refine self-skips and `j` is
untouched (Gate 0 clear). Exposure-checker not dispatched (self-skip).

## Phase 1 — analysis
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)` (carried from Phase 0)
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` (carried from Phase 0)
`SECTIONS: 4 found (Goal, Scope/Deliverables, Acceptance criteria, References) | 4 decomposed (References informational → 0 rows) | ROWS: C=0 R=3 G=1 AC=3`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Status |
|---|---|---|---|---|
| G1 | Goal | One seam that keeps the LLM out of the core: a `Summarizer` Protocol + deterministic default, so 090/091 plug in without the core importing an LLM | Ship the Protocol seam + default impl in `code_atlas/onboarding/`; nothing in core imports an LLM | ✅ done |
| R1 | Scope | `Summarizer` Protocol in `code_atlas/onboarding/`; default impl = **structural** summary (signature, docblock first line, role tag from 083 metrics). No SQL, no network, no LLM | New `summary.py`: `Summarizer` Protocol + `StructuralSummarizer`; role tag derived from `NodeMetric.direction` | ✅ done |
| R2 | Scope | One seam only (R1.2) — no registry/factory until a second summarizer exists | Exactly one Protocol; no registry/base-class/DI | ✅ done |
| R3 | Scope | A CI test proving the **graph → enrichment → presentation** split with the middle stage **faked** | `test_onboarding_summary.py`: inject a fake `Summarizer`; presentation reflects the seam's output, made-to-fail if it read the graph | ✅ done |
| AC1 | AC | Default summarizer deterministic (R4.2) and language-agnostic (no PHP logic) | Byte-stable `to_json`; role from generic direction strings; grep-gates clean | ✅ done |
| AC2 | AC | Stubbed-seam test asserts the split and **would fail if presentation read the graph directly** | Two complementary guards: (a) presentation *structurally* cannot reach the graph (signature test); (b) enrichment routes through the injected seam — a hardcoded default flips it red (093-C3, **recorded sabotage run** in Phase 4) | ✅ done |
| AC3 | AC | No dead abstraction (R7.4): exactly one Protocol, one default impl | One `Protocol`, one impl; DTOs (`NodeFacts`/`Summary`) are data-carriers, not seams | ✅ done |

### AC validation (falsifiability)
- **AC1** falsifiable — determinism: same input → byte-identical `Summary.to_json` (asserted); language-agnostic: `test_core_is_language_agnostic.py` grep-gate + no PHP strings in `summary.py`.
- **AC2** falsifiable — the fake summarizer returns role/docline that *diverge* from the structural default; presentation asserts it shows the fake's value, and a companion assertion shows the structural default would have produced a different value → the guard is proven made-to-fail (093-C3 `prove-the-guard-fails`).
- **AC3** falsifiable — grep/count: exactly one `Protocol` subclass and one concrete default impl in `summary.py`; no registry symbol.
No numeric thresholds to re-derive; no ticket/computed mismatch.

### Clarification
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision` — `j = 0`. Gate 0 already cleared at Phase 0 (refine self-skip, no unresolved want-decision). autorun proceeds.

### Universal inventory
Universal negatives only ("no SQL / no network / no LLM"; "exactly one Protocol, one default impl") — verified by grep-gates + count, not a "for-each-of-N>1" list. N(Protocol)=1, N(default impl)=1. No per-item checklist needed.

### Cause / gap (enhancement)
Current: `code_atlas/onboarding/` has `metrics.py` (083) + `layers.py` (084) but **no enrichment→summary stage and no split-proof** — presentation (086) would otherwise read the graph directly. Target: a `Summarizer` seam + deterministic `StructuralSummarizer` default + a CI test proving the graph→enrichment→presentation split with the middle faked. Gap closed by new `code_atlas/onboarding/summary.py` + `tests/test_onboarding_summary.py`.

### Blast radius
- **New:** `code_atlas/onboarding/summary.py` (`Summarizer` Protocol, `NodeFacts`, `Summary`, `StructuralSummarizer`, `summarize_modules`, `summaries_as_dict`, `ROLE_LABELS`); `tests/test_onboarding_summary.py`.
- **Modified (docs/bookkeeping):** `docs/BACKLOG.md` (status + token row); `docs/tasks/085_...md` (this working doc + frontmatter). PLAN/CONVENTION/README unaffected (no new tool, contract, or schema — that is 086).
- **Untouched:** `store.py`, `main.py`, `contract.py`, `metrics.py`, `layers.py`, adapters, resolver. **No contract/schema change** (no `contract_version` bump). No count-pin change.

`BASELINE: green` — onboarding subset (`test_onboarding_metrics/layers/core_is_language_agnostic/sql_confinement`) **123 passed** on the Windows dev host; the authoritative full-suite baseline is Docker (~1308 at 104's merge, per BACKLOG) and is confirmed **delta-green in Docker** at execute before the PR (bare `pytest` on Windows is red at collection — `fcntl` — the known platform exclusion, not a regression).

`TRACK: backend — 0/N touched files under UI paths` (pure core Python module + test).
`SCOPE: S` (one new module + one new test file; no universal N>1, not security-tagged).
`TIER: full` (no `TIER: lite` marker; keep the full gates + challenger).
`STRUCTURE: native` (ticket uses the header schema).

### RULE SECTIONS
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ | §R1.2 (change-type) ✅ | §R4/R4.1 (change-type) ✅ | §R4.2 (change-type) ✅ | §R7.4 (change-type) ✅ | §R6.5 (recalled handle prove-the-guard-fails) ✅`
- **R1.1** (zero language branches) ✅ — `summary.py` has no `if language ==`; role derived from generic `NodeMetric.direction` strings; `test_core_is_language_agnostic.py` grep-gate covers the new file.
- **R1.2** (one seam, YAGNI) ✅ — exactly one new seam (`Summarizer` Protocol), forced by R4.1; no registry/factory/base-class (R2 above).
- **R4 / R4.1** (core deterministic, no LLM/network) ✅ — `StructuralSummarizer` is pure structural arithmetic over strings; no LLM/network/SQL import; the LLM impl (090) stays outside `code_atlas/` behind this seam.
- **R4.2** (byte-stability) ✅ — `Summary.to_json` sorted-keys; determinism asserted (AC1).
- **R7.4** (no dead abstraction) ✅ — exactly one Protocol + one impl (AC3); DTOs are data-carriers matching the `NodeMetric`/`ModuleLayer` sibling convention, not speculative seams.
- **R6.5** (a guard is not a guard until made to fail — recalled handle `prove-the-guard-fails`, 093-C3) ✅ — the split test is constructed to fail if presentation bypasses the seam (AC2).
No migration/UI/schema change → DB-conventions and design-token/a11y sections **N/A** (no such change in the change-list). No uncodified standard applied (role-tag vocabulary is a design choice recorded in Phase 2, not gated as a rule).

## Phase 2 — design

### Approach
One new pure module `code_atlas/onboarding/summary.py`, mirroring the `metrics.py`/`layers.py` sibling
shape (frozen dataclasses + `as_dict`/`to_json`, a derived-not-listed pin, no SQL/LLM/network):

- **`Summarizer` (typing.Protocol)** — the one seam: `summarize(self, facts: NodeFacts) -> Summary`.
  Structural, so the later LLM impl (090, outside `code_atlas/`) matches the shape **without importing
  any core base-class** — the seam stays zero-coupling.
- **`NodeFacts` (frozen)** — the enrichment input DTO: `signature: str`, `doc: str`, `metric: NodeMetric`.
  A data-carrier like `NodeMetric`, not a seam. `key` is `metric.key` (no redundant field).
- **`Summary` (frozen)** — the enrichment output DTO: `key`, `signature`, `docline`, `role`; `as_dict` +
  sorted-keys `to_json` (the byte-stability surface, R4.2), exactly the sibling convention 086 consumes.
- **`StructuralSummarizer`** — the deterministic default impl: `docline` = first non-empty stripped line
  of `doc`; `role` = `_ROLE_BY_DIRECTION[metric.direction]`. No SQL/LLM/network.
- **`ROLE_LABELS` + `_ROLE_BY_DIRECTION`** — role tag derived from 083 metrics: `source→entry-point`,
  `sink→foundation`, `mixed→connector`, `isolated→standalone`. A pin test asserts
  `set(_ROLE_BY_DIRECTION) == set(DIRECTION_LABELS)` so a new metrics label can't ship unmapped (R6.7 /
  `derived-not-listed-invariant`, matching 083/084).
- **The split, as two callables** — `summarize_modules(facts, summarizer) -> tuple[Summary, ...]` is the
  **enrichment** stage (the only thing that touches graph facts / the seam); `summaries_as_dict(summaries)
  -> dict` is the **presentation** stage (consumes only `Summary`, never `NodeFacts`/`NodeMetric`). Their
  separateness is exactly what R3/AC2 prove.

### Rejected alternatives
1. **Registry/factory now** so 090's LLM summarizer self-registers → rejected: R1.2 YAGNI + AC3 (no dead
   abstraction); there is no second summarizer yet. A registry is justified when adapter/impl #2 exists.
2. **ABC base class** instead of `Protocol` → rejected: an ABC forces the out-of-core LLM impl to import
   a `code_atlas/` base (coupling the seam back into core, against the R4.1 intent). `Protocol` is
   structural — the seam is a pure shape.
3. **Fuse enrichment + presentation into one function** → rejected: then R3/AC2 cannot prove presentation
   doesn't read the graph. The separable seam **is** the deliverable.
4. **Role tag via a new SQL/graph query** → rejected: R1.4/R4.3; the role derives purely from the 083
   `NodeMetric` already in hand — no store round-trip.

### Assumptions
- `NodeMetric.direction ∈ DIRECTION_LABELS` — **verified** (`metrics.py:16`, `direction()` range).
- 085 does **not** wire to the store; `NodeFacts` is constructed by the caller (086 / the test), so no
  runtime/third-party assumption about store shape is introduced here — **verified** (no store import).
- Pure stdlib, no network/LLM → **no `novel-untested` third-party/runtime assumption**. Gate 2 unblocked.

### Smallest change-list
| change | file/area | blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| New `summary.py` (Protocol, `NodeFacts`, `Summary`, `StructuralSummarizer`, `summarize_modules`, `summaries_as_dict`, `ROLE_LABELS`, `_ROLE_BY_DIRECTION`) | `code_atlas/onboarding/summary.py` | consumed by 086 (**not yet built** — traced: no existing consumer); auto-covered by `test_core_is_language_agnostic.py` + `test_sql_confinement.py` (`CORE.rglob("*.py")`) | G1, R1, R2, AC1, AC3 | 1/1 |
| New split-proof + determinism + role-pin tests | `tests/test_onboarding_summary.py` | none (new test file) | R3, AC2, AC1, AC3 | 1/1 |
| Status + token row | `docs/BACKLOG.md` | `test_backlog_bookkeeping.py` (TASK_ROW regex + token table) — keep the status cell a bare word | (bookkeeping) | — |
| Working doc + frontmatter `status` | `docs/tasks/085_...md` | none | (bookkeeping) | — |

**Test blast-radius (mechanical trace).** `grep -rn "Summarizer|summary|summaries|NodeFacts|StructuralSummarizer" code_atlas/ tests/` → the only hit is an unrelated docstring (`test_tool_descriptions.py:43`); **no existing consumer** imports these symbols, so the new module invalidates no existing assertion. `summary.py` *consumes* `NodeMetric` (shared type) but does not modify it, so no metrics/layers test is disturbed. Both R1.1 and R4/SQL grep-gates glob `CORE.rglob("*.py")` → the new file is in-scope automatically (folded in above as proof collateral).

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- **`prove-the-guard-fails` (093-C3 → R6.5)** — **traced.** Command:
  `grep -rn "Summarizer\|split\|presentation.*graph" tests/` → **no existing split-guard test** (0 hits),
  so 085 introduces the guard. Folded into the AC2 verification row: the split test is built *made to
  fail* — the fake summarizer returns a role/docline that **diverges** from the structural default,
  presentation asserts it shows the **fake's** value. **R6.5 requires the guard be *observed* failing,
  not argued:** the recorded sabotage run in Phase 4 flips it red against the forbidden shape.

### Rule compliance
R1.1 (no language branch — role from generic direction strings), R1.2 (one Protocol seam, no registry),
R1.4 (no SQL; store untouched), R4/R4.1 (deterministic, no LLM/network; LLM stays outside core behind
this seam), R4.2 (sorted-keys `to_json`), R6.7 (role pin cross-checks `DIRECTION_LABELS`), R7.4 (one
Protocol + one impl), comments ≤3 lines. CONVENTION: module docstring cites the task + rules, sibling
naming (`as_dict`/`to_json`).

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 determinism + language-agnostic | logic | unit — byte-stable `to_json` on reordered input + `test_core_is_language_agnostic` grep-gate | ✅ |
| AC2 split guard, made-to-fail if presentation reads the graph | logic | unit — fake-summarizer split test + companion structural-divergence assertion (prove-the-guard-fails) | ✅ |
| AC3 exactly one Protocol, one default impl | logic | unit/grep — structural count assertion; no registry symbol | ✅ |
| R3 CI split-proof (graph→enrichment→presentation, middle faked) | logic | unit — same test as AC2 | ✅ |

All risk layers are **logic**: this is a pure in-process deterministic core module — no integration,
runtime, or e2e surface. Proofs sit at the matching layer. No layer-match `❌`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Proving test
`tests/test_onboarding_summary.py::test_presentation_reflects_the_seam_not_the_graph` — with a fake
`Summarizer` injected, `summaries_as_dict(summarize_modules(facts, fake))` reflects the fake's diverging
role/docline; the companion assertion shows the structural default would have produced different values,
so the test fails if presentation bypasses the seam. Invocation (bound into the contract at Gate 2):
`python -m pytest tests/test_onboarding_summary.py -k presentation_reflects_the_seam_not_the_graph -q`.

### Rollback + porting
Single-repo (`app`). Revert = delete `summary.py` + `test_onboarding_summary.py` and the BACKLOG/doc
edits (no schema/contract/tool change to undo). Unmerged → close PR + delete the remote branch. No
cross-repo porting (no shared code touched).

### Scope
`SCOPE: S` — unchanged from analysis. One new module + one new test file; no tier crossing, no
change-list growth beyond the traced bookkeeping edits.

## Phase 3 — execute
Branch `feat/085-onboarding-summarizer-seam` off `main`. Implemented the approved change list:
`code_atlas/onboarding/summary.py` + `tests/test_onboarding_summary.py` (9 tests).

### Deviation from the approved change list (surfaced to review)
**Count-pin bump — 2 files outside the Gate-2 list.** `tests/test_core_is_language_agnostic.py:42`
and `tests/test_sql_confinement.py:32` each pin `len(core_modules()) == 44`; a new core module makes
it **45**, so both were bumped 44→45. My Gate-2 blast-radius trace noted these gates *glob*
`CORE.rglob("*.py")` (auto-covering the new file) but **missed that they also count-pin** the module
total — a real blast-radius miss in the estimate, not a behaviour change. The bump is the *intended*
consequence of adding a core module (traced to R1/AC1: the new module is deliberate) — not a golden
silently re-recorded to hide a regression. Recorded here per execute step 5; review to adjudicate.
Realized diff = approved list + this 2-file count-pin deviation. `SCOPE: S` unchanged (no tier cross).

### Verification sweep
**Axis 1 — file set.** `git diff --stat main` + untracked: new `summary.py`, new
`test_onboarding_summary.py`, doc `085_...md`, and the 2 count-pin files (deviation above). No stray
symbols/imports; each hunk maps to a matrix row. `diff ⊆ approved list + 1 recorded deviation`.

**Axis 2 — design-conformance (per Approach bullet).** All `implemented-as-approved`: `Summarizer`
Protocol (structural, no base-class import) ✅ · `NodeFacts`/`Summary` frozen DTOs ✅ ·
`StructuralSummarizer` default (docline = first non-empty line; role from `_ROLE_BY_DIRECTION`) ✅ ·
`ROLE_LABELS` derived + R6.7 pin ✅ · split as two callables `summarize_modules` (enrichment) /
`summaries_as_dict` (presentation, only-Summary input) ✅. No `deviated` bullet.

**Empirical output (Windows dev host):**
```
$ ruff check code_atlas/onboarding/summary.py tests/test_onboarding_summary.py
All checks passed!
$ mypy code_atlas/onboarding/summary.py tests/test_onboarding_summary.py
mypy: No issues found
$ pytest tests/test_onboarding_summary.py tests/test_core_is_language_agnostic.py \
    tests/test_sql_confinement.py tests/test_onboarding_metrics.py tests/test_onboarding_layers.py -q
132 passed
$ pytest tests/test_onboarding_summary.py -k presentation_reflects_the_seam_not_the_graph -q
1 passed
```
Full-suite delta-green is proven in **Docker** (the Windows `fcntl` exclusion) before the PR — see the
Docker gate result recorded below.

`Ph3 proven by:` the 9 authored tests pass; ruff + mypy clean on both files.

## Phase 4 — review
`CHALLENGER: ON` (default). `cost_tier: standard`, diff touches no auth/access/schema → `reviewer`
(Sonnet), not `reviewer-max`. Both agents inspected ref-based, read-only, in place (tree at the
reviewed SHA).

- **Reviewer (Sonnet):** **CHANGES REQUESTED → conditional LGTM**, no Critical. Module rule-compliant
  (no language branch, no SQL, no LLM/network, deterministic, one Protocol + one impl, comments ≤3,
  count-pin bump verified correct: `main` 44 → HEAD 45). Two Important findings — both landed (below).
- **Challenger (ticket-blind):** **9 met / 0 not-met / 0 can't-tell** — independently rebuilt every
  requirement from the raw ticket and confirmed the split proof is non-vacuous, no registry/factory,
  no LLM/SQL/network, deterministic, language-agnostic; flagged the count-pin bump as necessary, not
  scope creep. Payload was raw ticket + diff only (working doc withheld — independence procedural).

### Finding resolutions (verify-only re-review, main-loop, no re-dispatch — fixes stayed in the named findings)
- **F1 — Docs-before-PR (AGENTS.md / R7.2).** Landed: frontmatter `status: todo → done`, `BACKLOG.md:24`
  status `todo → done`, and the 085 Token-usage row added; this Phase-4 cost ledger below.
- **F2 — split-guard made-to-fail had no recorded red run (R6.5) + framing mismatch.** Landed:
  - **(a) Recorded sabotage run (R6.5 — the guard *observed* failing against the forbidden shape):**
    ```
    # SABOTAGE: summarize_modules ignores the injected summarizer, hardcodes the default
    #   summaries = [StructuralSummarizer().summarize(fact) for fact in facts]
    $ pytest tests/test_onboarding_summary.py -k presentation_reflects_the_seam_not_the_graph -q
    E   Extra items in the right set: 'fake-role'
    E   (got {'connector','standalone','foundation','entry-point'}, expected {'fake-role'})
    tests\test_onboarding_summary.py:88: AssertionError
    FAILED ... 1 failed, 6 deselected
    $ git checkout -- code_atlas/onboarding/summary.py   # restore
    $ pytest ... -k presentation_reflects_the_seam_not_the_graph -q   →  1 passed
    ```
  - **(b) Framing corrected** to state what each guard actually proves — AC2 is proven by **two
    complementary guards**: `test_presentation_signature_cannot_reach_the_graph` (presentation
    *structurally* cannot reach the graph — the failure mode AC2 names) and
    `test_presentation_reflects_the_seam_not_the_graph` (enrichment routes through the injected seam; a
    hardcoded default flips it red). Docstrings + the AC2 matrix row + the HANDLES trace updated.

### Scope reconciliation (both axes)
- **File axis:** diff = approved list + the 2-file count-pin deviation (recorded in Phase 3), which the
  reviewer + challenger both independently adjudicated **necessary, not creep**. No untouched-line
  reformat (formatter scoped to authored files). **Clean.**
- **Behaviour axis:** every Gate-2 Approach bullet `implemented-as-approved` (Phase-3 self-check); no
  bullet diverged. **Clean.**

### Proving test + baseline
`test_presentation_reflects_the_seam_not_the_graph` — green post-change, **red under sabotage** (above),
so it fails without the seam. `BASELINE: green` → bar is delta-green: **Docker full gate 1317 passed,
0 failed** (mypy 45 files, ruff clean); `main` 1308 → branch 1317, **+9** (7 authored + 2 per-module
parametrized guard cases for the new core module; none removed). No new failure introduced.

### k/N + layer-match
Every matrix row `k = N` (G1, R1, R2, R3, AC1, AC2, AC3 all ✅). Layer-match re-confirm: all four
verification-plan rows are logic-layer with unit proofs — no `❌`, no coverage-gap exclusion needed.

**Verdict: clean** (conditional LGTM, both named findings landed; challenger 9/9). No Critical/Important
outstanding.

`Reviewed at f66d970` — reviewed set: `code_atlas/onboarding/summary.py`,
`tests/test_onboarding_summary.py`, `tests/test_core_is_language_agnostic.py`,
`tests/test_sql_confinement.py`, `docs/BACKLOG.md`, `docs/tasks/085_onboarding-summarizer-seam.md`
(this working-doc file is exempt from the staleness comparison; BACKLOG carried in scope as review-fix
bookkeeping). Docker full gate green at this SHA (1317 passed).

### Cost ledger (subagent dispatch only — main-loop unmeasured on this host)
| Dispatch | Tokens | Tool-uses | Duration | Outcome |
|---|---|---|---|---|
| `mango:reviewer` r1 | 88.6k | 24 | 262 s | CHANGES REQUESTED → conditional LGTM; 2 Important, both landed |
| `mango:challenger` (ticket-blind) | 47.9k | 10 | 78 s | 9 met / 0 not-met / 0 can't-tell |
| **Total dispatch** | **136.5k** | 34 | — | — |

Not dispatched (disclosed): refine exposure-checker (refine self-skipped, 0 unresolved); analysis
Explore fan-out (done in the main loop); no `extractor`. **Main-loop spend unmeasured** — the host
surfaces no usage block; `rtk gain` is global and not attributable to one task, so nothing is invented.

## Phase 5 — finalise
Stale-review guard: `git diff --name-only f66d970..HEAD` non-exempt = ∅ (only the working doc +
`LESSONS.md`, both exempt) → **not stale**. `pr_checklist_path` unset → skipped. Ledger-completeness:
2 dispatch rows, both carry real token counts → complete.

### Learning loop
`CLAIMS: 2 claim(s) from 1 lesson entry | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true | 0 falsified | 0 not cheaply checkable`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed | 0 cannot promote | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Two durable lessons recorded to `docs/LESSONS.md` as `proposed (awaiting human confirm)` — both type-2,
seen once, so they legitimately stay in lessons (no promotion; the RECURRING-T2 rule bites only at
seen ≥ 2). Under autorun nobody is awake to ratify a classification, so nothing is promoted into a rule
and **0 mango files written**; the maintainer confirms/promotes at review:
- **085-C1 `count-pin-in-blast-radius`** — a count-pinned guard is a blast-radius hit for any file
  added to its globbed set (my Gate-2 trace missed it; execute caught the 44→45 bump as a deviation).
- **085-C2 `ac-failure-mode-needs-the-right-guard`** — an AC phrased as a failure mode needs the guard
  that can actually exhibit that failure; R6.5 wants it observed failing (the recorded sabotage), not argued.

Positive note (not a defect): **084-C1** was applied correctly — the piped Docker gate was judged by
content (`1317 passed`, `All checks passed!`), not the `tail` exit, so no false-green.

### Outward actions (autorun handover covers exactly these two)
1. **Push `feat/085-onboarding-summarizer-seam`** (carries the code + the bookkeeping commit with
   `LESSONS.md` + BACKLOG + working doc, so the durable lesson reaches a shared ref, not an orphan branch).
2. **Open the PR** from `.github/pull_request_template.md` (body drafted).

Every other outward action (merge, tracker transition, delete branch) is **deferred to the maintainer**.
