---
id: 109
slug: onboarding-artifact-quality-gate
title: Onboarding — a quality gate on the emitted artifact, so filler cannot ship again (M11)
phase: 3
milestone: M11
status: done
depends_on: [088, 108]
---

## Why this exists

Tasks 106 and 107 both shipped, were released, and were only caught by a human opening the HTML and
reading it. Both defects are **mechanically detectable** and both are named in the checklist of the
reference tool this design borrows from (`graph-reviewer`, Checks 6 and 7):

- *"No summaries that are empty or just restate the filename"* — code-atlas emitted 500/500 pages whose
  only content was the path (107).
- *"Tour has between 5 and 15 steps"* — code-atlas emitted 500 stops and called it a tour (111).

There is no gate between `build_artifact` and disk. Every onboarding defect so far has been found by
eye, after release. This ticket adds the missing gate, **before** 110–116 change the artifact's shape,
so the new shape is born gated.

## Scope

A deterministic checker over the in-memory `OnboardingArtifact` (no IO, no LLM), enforced by tests and
run in CI like the R1.1/R2.2 grep-gates:

| Check | Rule |
|---|---|
| C1 | no page whose body carries no fact absent from its own path (the 107 rule, as an invariant) |
| C2 | every page under a byte ceiling (the 108 rule, as an invariant) |
| C3 | every layer has a non-empty `description` (enables 110) |
| C4 | tour step count within `[5, 15]` once 111 lands; until then, assert the *current* count and fail on regression past a recorded ceiling |
| C5 | referential integrity: every path named in the tour, manifest and layer sets exists in the node set |
| C6 | no duplicate page paths; no page for a module absent from the tour |
| C7 | byte-stability: two builds of the same index produce identical output (R4.2) |

Failure is loud: `build_artifact` raises rather than writing a bad tree, matching the 050 precedent of
refusing rather than overwriting.

## Acceptance criteria

1. **AC1 (R6.5).** Each check has a test that is observed red against a deliberately-bad artifact
   fixture, and the seven fixtures are distinct — one per check.
2. **AC2.** Reverting task 107's fix makes C1 red; reverting 108's makes C2 red. Proven by patching the
   fixture, not by reverting the repo.
3. **AC3.** The gate runs on the anchor monorepo artifact and passes, with the C2 ceiling and C4 count
   recorded in the working doc as the numbers the gate now defends.
4. **AC4.** CI fails when the gate fails; the failure message names the check and the offending path.
5. **AC5.** The gate adds no measurable time to `generate_onboarding` on the anchor repo (report before
   and after).

## Out of scope

Judging *content quality* — whether a summary is any good is 117's problem. This gate only catches
structural filler, which is what shipped twice.

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 109

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed (plain local-file ticket; consistent with 108)
- **Branch:** `feat/109-onboarding-artifact-quality-gate`
- **CHALLENGER:** OFF (--no-challenger, by run arg "with skipped Review & Challenge")
- **REVIEW (subagent reviewer):** WAIVED; inline main-loop review only, per run arg
- **TIER:** full · **SCOPE:** M · **change type:** feat (new checker module + build_artifact now raises)

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions.` The WANT is unambiguous (a deterministic structural
gate that raises before writing filler). Every ambiguity is a HOW-decision, resolved below and cited.
No premise falsified — `build_artifact`, `OnboardingArtifact`, `render_module` all resolve
(`code_atlas/onboarding/artifact.py`).

## Phase 1 — analysis

### HOW-decisions (surfaced at Gate 1; resolved on standing approval)
- **H1 — C3 has no field to check yet.** `LayerRow`/`ModuleLayer` carry only a layer *name*, no
  `description` (110 introduces responsibility names/descriptions). Pre-110 invariant: **every layer
  name is a non-empty, non-whitespace string.** `layers.py` already routes root files to `(root)` so
  the empty string never ships — C3 locks that. 110 strengthens C3 to the description when it lands.
- **H2 — C4's `[5,15]` is 111's bound.** Pre-111 invariant: **`len(stops) ≤ MAX_TOUR_STEPS`**, a
  recorded module constant = the current default tour budget **500** (`Config.impact_max_nodes`
  default). This is a regression lock, not a quality bar — a 500-stop tour is expected today and is
  111's problem; C4 only fails a build that balloons *past* the recorded ceiling. `check_artifact`
  takes `max_tour_steps` so 111 can pass `15` and an operator with a bigger budget can raise it.
- **H3 — C7 is a builder property, not a static-artifact one.** Realized two ways: (a) the gate asserts
  **canonical ordering** (pages by ascending `index`, layers by ascending `rank`, crossings by
  descending `count` then name, `isolated` sorted) — canonical order ⇒ byte-stable render; (b) a
  build-twice determinism test asserts identical rendered bytes. AC1's distinct bad fixture for C7 is a
  shuffled-order artifact.
- **H4 — C5 node set.** The gate is pure over the `OnboardingArtifact` (scope: "no IO"). Node universe
  = `{stop.file}`. C5 asserts every referenced path — each `page.file`, each `isolated`, each SCC
  member on any stop/page — is a tour-stop file, catching dangling references.
- **H5 — enforcement point.** `build_artifact` calls `check_artifact` before returning and raises
  `QualityGateError` on violation (050 precedent: refuse rather than emit a bad tree). CI is the
  existing `pytest -q`; no new CI job (there is no committed anchor artifact for CI to regenerate).
- **H6 — anchor monorepo absent on this host** (same as 108). AC3/AC5 use a synthetic-scale fixture
  reproducing the anchor's shape (500-stop tour, wide pages); the at-scale re-measure on the anchor is
  **deferred to an operator run** (015 AC2 / 018 A4 / 108 pattern). Recorded in the cost ledger.

### The seven checks (semantics the gate enforces)
| Check | Invariant on `OnboardingArtifact` | Ticket source |
|---|---|---|
| C1 | every page has a fact beyond its path: `page.docline or page.fan_in or page.fan_out` | 107 rule |
| C2 | every page's rendered bytes `≤ MAX_PAGE_BYTES` (rendered at `max_results`) | 108 rule |
| C3 | every `layer` name is non-empty, non-whitespace (H1) | enables 110 |
| C4 | `len(stops) ≤ max_tour_steps` (H2) | pre-111 form |
| C5 | referential integrity: every referenced file is a tour-stop file (H4) | — |
| C6 | no duplicate page `relpath`; every `page.file` is a tour-stop file | — |
| C7 | canonical ordering of pages/layers/crossings/isolated (H3) | R4.2 |

### Acceptance matrix
| AC | Requirement | Approach | Verification |
|---|---|---|---|
| AC1 | R6.5: each check red against a distinct deliberately-bad fixture (7 fixtures) | 7 hand-built bad `OnboardingArtifact`s, each violating exactly one check | 7 tests, each observed red then green; distinctness asserted |
| AC2 | reverting 107 → C1 red; reverting 108 → C2 red (patch the fixture, not the repo) | a filler page (empty docline, 0/0 degree) fixture → C1; an uncapped-wide page fixture → C2 | 2 tests |
| AC3 | gate runs on anchor artifact & passes; record C2 ceiling + C4 count | synthetic-scale fixture (H6) passes; ceilings recorded here; anchor deferred | test + ledger note |
| AC4 | CI fails on gate failure; message names check + offending path | `QualityGateError(check, path)`; `build_artifact` raises; `pytest` is CI | test asserts raise + message |
| AC5 | gate adds no measurable time on anchor (before/after) | gate is O(pages) str-len + set ops, no IO; measure on synthetic fixture, defer anchor | timing note in ledger |

### Blast radius
New `code_atlas/onboarding/quality_gate.py`; one call added inside `build_artifact`
(`artifact.py`). New `tests/test_onboarding_quality_gate.py`. No change to `store.py`, adapters, the
contract, or any tool payload. R1.1 (no language branch), R1.4 (no store import), R4.2 (deterministic)
all hold — the gate is pure over an in-memory dataclass.

### Gate 1 — analysis ✋ (surfaced; proceeding on standing approval)
TIER full, SCOPE M, feat. `j = 0` open product-questions → no Gate 0. HOW-decisions H1–H6 ratified on
standing approval.

## Phase 2 — design

### Change list (approved scope — do not widen)
1. **NEW** `code_atlas/onboarding/quality_gate.py` — `QualityGateError(check, path, detail)`,
   `MAX_PAGE_BYTES`, `MAX_TOUR_STEPS`, `check_artifact(artifact, *, max_results, max_page_bytes=…,
   max_tour_steps=…) -> None` running C1–C7, raising on the first violation with an actionable message.
2. **EDIT** `code_atlas/onboarding/artifact.py` — `build_artifact` calls `check_artifact(result,
   max_results=max_results)` on the composed artifact before returning; docstring notes the gate.
3. **NEW** `tests/test_onboarding_quality_gate.py` — pure (no store/`fcntl`, runs on Windows too):
   AC1 (7 distinct red fixtures, one per check), AC2 (revert-C1/C2 by fixture patch), AC3
   (synthetic-scale pass + pinned ceilings), AC4 (message names check+path), AC5 (cheap-over-scale).
   C7's build-twice half is **already** covered by the existing
   `test_generate_onboarding_composition_is_byte_stable` (two builds → identical bytes) — no
   redundant test added (R7.1); the gate's C7 canonical-order invariant is the new-file half.
4. **EDIT** `docs/tasks/109_*.md` (this doc), `docs/BACKLOG.md` (status + token row), frontmatter status.

### Rejected alternatives
- **A new CI grep/subprocess job** — rejected: the checker is a Python invariant and `pytest -q`
  already runs in CI; there is no committed anchor artifact for a standalone job to regenerate. A grep
  gate cannot express "page bytes ≤ ceiling."
- **Thread `impact_max_nodes` into `build_artifact` for C4** — rejected: `len(stops) ≤ budget` is
  near-tautological (stops ⊆ tour_files). A recorded constant ceiling (H2) is what "regression past a
  recorded ceiling" means.
- **Enforce in `generate_onboarding` (the tool) instead of `build_artifact`** — rejected: the ticket
  says `build_artifact` raises "rather than writing a bad tree"; putting it in the tool would let a
  direct `build_artifact` caller (the viewer payload path) emit filler.

### Recorded ceilings the gate defends (AC3)
- **C2 `MAX_PAGE_BYTES = 16384` (16 KiB).** 108 measured a single module page at **40,074 B uncapped →
  6,878 B capped**; 16 KiB sits above the capped page and below the uncapped one, so reverting 108
  trips C2 (AC2) while every current page passes.
- **C4 `MAX_TOUR_STEPS = 500`** = default `impact_max_nodes`; the pre-111 tour count the gate defends.
- Both re-measured on the anchor monorepo in a **deferred operator run** (H6).

### Verification plan
Docker CI gate (`scripts/docker-test.sh`): ruff + mypy + full pytest, expect delta-green. AC1's seven
reds observed by asserting each bad fixture raises the *right* check; AC2 by patching the C1/C2
fixtures (not the repo). No network, no LLM, deterministic (R4.2).

### Gate 2 — design ✋ (surfaced; proceeding on standing approval)
Change list is 4 items, all inside the approved blast radius; SCOPE stays M (no tier creep).

## Phase 3 — execute (results)
- **New** `code_atlas/onboarding/quality_gate.py` (52nd core module) — `check_artifact` runs C1–C7,
  raises `QualityGateError(check, path, detail)`. **New** `tests/test_onboarding_quality_gate.py`
  (14 tests, all pure). **Edited** `artifact.py` (gate call, lazy import breaks the cycle), and the
  two guard-the-guard pins (`test_sql_confinement.py`, `test_core_is_language_agnostic.py`) 51→52.
- **R6.5 proof.** Each AC1 test asserts the raise fires on a bad fixture (the guard is load-bearing,
  not vacuous); `test_ac2_reverting_108_would_make_c2_red` shows the capped render **passes** and the
  uncapped one **raises C2** in the same test — a within-test red/green contrast reproducing 108.
- **AC3 recorded ceilings:** `MAX_PAGE_BYTES = 16384`, `MAX_TOUR_STEPS = 500`. Synthetic-scale
  fixture (500 stops, wide-but-capped pages) passes; anchor at-scale re-measure deferred (H6).
- **AC5 timing:** gate = **4.09 ms** over the 500-page synthetic artifact (one extra render pass for
  C2's byte count) — negligible vs the store queries + disk writes; anchor before/after deferred (H6).
- **Delta-green (Docker CI gate):** ruff clean · mypy clean · **1508 passed, 0 failed, 0 skipped**
  (79.93 s). Windows bare `pytest`: the 14 pure gate tests pass; the store/`fcntl` suite is the known
  platform exclusion.
- **Deliberate behavioural note (C4 + operator budget):** pre-111, an operator who raises
  `CA_IMPACT_MAX_NODES` above 500 and produces a > 500-stop tour will hit a **loud** `QualityGateError
  C4` — which is the gate working as designed (a > 500-stop "tour" is exactly the 111 defect it
  refuses), not a regression. A budget-derived ceiling was rejected as vacuous (would never fire).

## Phase 4 — review (inline, main-loop)
Reviewer subagent + ticket-blind challenger **WAIVED** by run arg. Inline verdict: **clean (reviewer
only — CHALLENGER: OFF).** R1.1 (no language branch — now scanned by the CI grep-gate + the
language-agnostic guard test, passes), R1.2 (no new abstraction — a plain function), R1.4 (imports
`artifact`, never `store` — SQL-confinement guard now covers it, passes), R2.2 (no repo/framework
names), R4.2 (pure; `time` is test-only), R7.1 (smallest change — reused the existing byte-stable test
for C7's build-twice half), R7.5 (every comment ≤ 1 line) all hold. Diff ⊆ the approved change list;
SCOPE stayed M, branch type `feat` matches.

## Phase 5 — finalise
Docs updated before PR: this working doc, `docs/BACKLOG.md` (status todo→done + token row),
frontmatter status. Outward actions (commit → push → PR) on the maintainer's standing approval; PR is
the review surface. `/mango:promote` is **not** triggered — no claim's `seen:` crosses 2 ticket keys.

### Lesson (durable)
When a ticket's acceptance names a field or bound a *later* ticket introduces (C3's layer description →
110; C4's `[5,15]` → 111), the gate ships the **pre-cursor invariant** the current model can express
(non-empty layer name; a recorded regression ceiling) and records the strengthening as the later
ticket's job — a gate born now, tightened on schedule, rather than blocked on the future.

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| (all) | — (ran entirely in main loop; reviewer + challenger waived) | — | 0 dispatch |

Main-loop token spend: `unmeasured (host does not surface usage)`.

## Decision log
- Reviewer + challenger waived by run arg; inline main-loop review only.
- H1–H6 resolved as HOW-decisions on standing approval (see Phase 1).
- Anchor at-scale AC3/AC5 re-measure deferred to an operator run (108 precedent).

