---
id: 115
slug: mirror-subtree-detection
title: Onboarding — sibling subtrees duplicating 62% of their paths, and nothing says so (M11)
phase: 3
milestone: M11
status: done
depends_on: [112]
# 115 FEEDS 098 (it produces that ticket's evidence); 098 was never a blocker for it.
feeds: [098]
---

## Why this exists (measured, anchor monorepo)

Two sibling subtrees hold near-copies of the same application. Counted from the index by relative path:

| | Count |
|---|---:|
| relative paths present under **both** subtrees | **4,244** (62 %) |
| present under the first only | 1,522 |
| present under the second only | 1,134 |

Corroborating signals from the same index: the DB-access file exists three times with 4,050 / 4,041 /
3,926 dependents; the largest class in the repo is a vendored PDF library present in **four** copies;
the tour's SCC lines are dominated by pairs of same-named files across the two trees.

This is the highest-value fact the map produces, and the current artifact never states it. The reviewer's
verdict was that seeing it as three numbers is not enough — they need it **as a lookup**: paste a path,
get the parallel path, or get told there isn't one. The mockup does exactly that, and the absence case
(`no counterpart`) is the more useful answer, because it marks divergence.

## Relationship to task 098

[098](098_correspondence-relation-seam.md) asks whether the *graph* should hold a "this file is a copy or
port of that one" relation, and is **deferred pending evidence**. This ticket is that evidence: it
produces the correspondence set structurally, without a new edge kind, and measures how large and how
useful it is. If it proves out, 098 can decide about a real relation with numbers in hand. If it does not
generalise past one repo, 098 stays deferred and this stays a presentation-layer fact.

## Scope

- Detect candidate mirror subtrees structurally: sibling directories at the same depth whose relative
  path sets overlap above a threshold. No repo names, no configured pair (R2.2).
- Report `both / only-A / only-B` counts, the overlap fraction, and a bounded sample.
- Expose counterpart resolution over the dataset's path index (112) so a renderer can answer
  "given this path, what is its sibling?" — including the negative answer.
- Confidence caveat: identical *path* is not identical *content*. The output must say it compares paths,
  not bytes, and must not claim the files are copies.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with `a/x`, `a/y`, `b/x` reports one shared path and one on each side —
   observed red against today's code, which has no such concept.
2. **AC2.** Counterpart resolution is symmetric, and a path outside any mirror subtree returns a clean
   negative rather than a guess.
3. **AC3.** A repo with no mirrored subtrees reports none — proven on a pinned public repo, so the
   detector is not manufacturing structure.
4. **AC4.** The threshold is justified by measurement across the anchor repo plus at least two pinned
   public repos, and the chosen value is recorded with the numbers that chose it.
5. **AC5.** The output states that the comparison is path-based, and never asserts content equality.
6. **AC6.** Findings written into 098 so the deferred decision has evidence attached.

## Out of scope

Content hashing or similarity scoring, and any new edge kind or `contract_version` bump (that is 098's
question, not this ticket's).

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 115

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed · **Branch:** `feat/115-mirror-subtree-detection`
- **CHALLENGER:** OFF (--no-challenger) · **REVIEW (subagent):** WAIVED — inline main-loop review only
- **TIER:** full · **SCOPE:** M (one new pure module + 3 consumer edits + dataset version bump + 098 evidence + tests)
- **change type:** feat

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions`. The ticket states the measured problem, the detection
rule, the required outputs, the confidence caveat and the R2.2 constraint. Everything else is a
how-decision, resolved below and cited.

**Premise check — PASSED.** Every referenced source resolves: the 112 dataset and its `PathIndex`
(`code_atlas/onboarding/dataset.py:122`, `DATASET_VERSION = 3` after 114), the mockup mirror prototype
(`docs/phase3-onboarding/mockup/extract.py:203-211`), 113's exclusion signals
(`responsibility_layer` + `stub_roots`), task 098 (`docs/tasks/098_correspondence-relation-seam.md`,
`status: deferred`), and R2.2 with its now-core-covering CI gate.

**`depends_on: [112, 098]` is misleading and the arrow points the other way.** 098 is not a blocker:
115 *produces* 098's evidence, and AC6 requires writing findings **into** 098. 098's own gate needs a
second repo and a written rejection of a cheaper alternative — which is exactly what this ticket
supplies. Recorded here; the frontmatter is corrected to `depends_on: [112]` with a `feeds: [098]` note
so a later reader is not told to wait for a deferred ticket.

## Phase 1 — analysis

### Measured problem (ticket)
Two sibling subtrees hold near-copies of the same application: **4,244 shared relative paths (62 %)**,
1,522 on one side only, 1,134 on the other. The reviewer's verdict was that three numbers are not
enough — they need a **lookup**, and the **absence** answer (`no counterpart`) is the more useful one
because it marks divergence.

### The prototype cannot be ported — same R2.2 class as 114's
`docs/phase3-onboarding/mockup/extract.py:206` is `re.match(r"legacy/(alpha|beta)/(.*)$", p)` — a hardcoded
tree prefix plus two region names, and the output keys are literally `alpha_only`/`beta_only`. So the pair
must be **discovered**, not configured, and the sides must be named from the paths.

### Real-repo measurement, run BEFORE choosing the threshold (AC4)
The three pinned clones are cached, so every sibling-directory pair was scored before any constant was
picked. Overlap is **Jaccard** (shared ÷ union), which is what reproduces the ticket's own 62 %:
`4244 / (4244 + 1522 + 1134) = 0.615`.

| repo | highest-overlap sibling pair | Jaccard | shared paths |
|---|---|--:|--:|
| anchor monorepo (from the ticket) | the two application subtrees | **0.615** | **4,244** |
| `laravel/laravel` | `tests/Feature` ↔ `tests/Unit` | **1.000** | **1** |
| `laravel/laravel` (after 113's exclusions) | `bootstrap` ↔ `config` | 0.091 | 1 |
| `symfony/demo` | — no sibling pair shares any relative path | — | 0 |
| `brick/math` | — no sibling pair shares any relative path | — | 0 |

**This measurement is the whole reason the design has two gates rather than one.** A Jaccard threshold
alone is worthless: `laravel/laravel` scores a **perfect 1.000** on a pair sharing exactly **one** file.
Overlap fraction says *how alike* two subtrees are; it says nothing about whether there is enough there
to call a mirror. So the shared-path **count** is the gate that rejects noise, and the fraction is the
gate that rejects two large but merely-adjacent trees. Both are needed, and the pins prove it.

### HOW-decisions (resolved on standing approval)
- **H1 — new pure module `code_atlas/onboarding/mirrors.py` (57th core module).** Holds `MirrorPair`,
  `MirrorReport`, `Counterpart`, `find_mirror_subtrees`, `resolve_counterpart`, the two thresholds and
  the path-not-content caveat. Pure functions over a path list: no SQL, no LLM, no language branch
  (R1.1/R1.4/R4).
- **H2 — candidates are sibling directories (same parent), scored by Jaccard over their relative path
  sets.** Sibling-only is the ticket's own rule and it also bounds the search: a pair must share a
  parent, so this is per-parent combinations, not all-pairs over every directory.
- **H3 — two gates, both justified by the table above.** `MIN_SHARED_PATHS = 25` and
  `MIN_OVERLAP = 0.30`. The anchor clears both (4,244 / 0.615); every pin fails both. 25 is an order of
  magnitude above the noise observed (1) and two orders below the real signal (4,244); 0.30 is the point
  below which "mirror" overstates the relationship. Both are defaulted parameters (112's
  `dir_symbol_threshold` precedent), so a test can drive each boundary independently.
- **H4 — 113's exclusion signals are reused, and they earn their place here immediately.** Paths under a
  declared `stub_roots`, or whose 110 layer is `Vendor / Framework` or `Tests`, are not candidates.
  This alone removes `laravel/laravel`'s Jaccard-1.000 pair, because it is mirrored *test scaffolding*,
  not a mirrored application. Consistent with 113 and 114 rather than a fourth exclusion mechanism.
- **H5 — counterpart resolution is a pure function of (path, pairs, known-path membership), with THREE
  outcomes.** `counterpart` (the sibling path exists), `no_counterpart` (inside a mirror subtree, the
  parallel path is absent — the divergence marker the ticket calls the more useful answer), and
  `outside_mirror` (the path is in no detected pair — a clean negative, never a guess). Symmetry is
  structural: swapping the pair's two prefixes is its own inverse (AC2).
- **H6 — the truncation honesty problem, stated rather than hidden.** The ticket asks for resolution
  "over the dataset's path index (112)", but that index is **capped** at `path_index_max` and carries
  `truncated`. Resolving a negative against a truncated index could report `no_counterpart` for a file
  that exists but was trimmed. So `resolve_counterpart` takes an explicit `complete: bool` and a
  `no_counterpart` result carries `qualified=True` when the membership set was incomplete — the answer
  says *"absent from the paths I can see"*, not *"absent"*. The dataset resolves against the **full**
  path list at build time, so its recorded samples are unqualified.
- **H7 — AC5's caveat is a constant on the report, not renderer prose.** `PATH_NOT_CONTENT` ships in
  `MirrorReport.caveat` and every renderer prints it, so no consumer can show the counts without the
  statement that this compares **paths, not bytes**, and asserts no copy relationship.
- **H8 — consumers: the dataset, the artifact overview, the overview tool.** `dataset.py` gains a
  `mirrors` section (`DATASET_VERSION` **3 → 4**); `artifact.py`'s overview renders the pair table with
  the caveat; `architecture_overview` gains `summary.mirrors`. The viewer's HTML stays 116.
- **H9 — AC6 is a docs deliverable with numbers, not a pointer.** An `## Evidence from task 115` section
  is written into `docs/tasks/098_correspondence-relation-seam.md` recording the measured pairs on every
  repo tested, what generalised and what did not, and whether 098's own gate is met.
- **H10 — SCOPE boundary (surfaced at Gate 1).** Out: content hashing or similarity scoring, any new
  edge kind or `contract_version` bump (all three are the ticket's own Out of scope, and the last two are
  098's question), the viewer (116), and any config knob.

### Blast radius
- **New:** `code_atlas/onboarding/mirrors.py`; `scripts/mirror_report.py`; `tests/test_mirror_subtrees.py`.
- **Edited:** `code_atlas/onboarding/dataset.py` (`mirrors`, `DATASET_VERSION` → 4);
  `code_atlas/onboarding/artifact.py` (pair table + caveat);
  `code_atlas/tools/architecture_overview.py` (`summary.mirrors`);
  `code_atlas/tools/generate_onboarding.py` (pass the path list through).
- **Must-fix pins:** `tests/test_sql_confinement.py:32`, `tests/test_core_is_language_agnostic.py:42`
  (`56` → `57`); the `OnboardingDataset` fixture in `tests/test_onboarding_dataset.py`; the
  exact-equality `summary` assertion in `tests/test_architecture_overview.py` (now a known pattern).
- **Docs:** `docs/tasks/098_…` (AC6 evidence), PLAN, README, mockup note, BACKLOG + token ledger, this ticket.
- **Verify-only green:** 114's module table, 113's split, 109's gate, 111's steps, viewer, config.

### Acceptance-criteria matrix
| AC | Requirement | Proof | Status |
|----|-------------|-------|--------|
| AC1 (R6.5) | A fixture with `a/x`, `a/y`, `b/x` reports one shared path and one on each side — red against today's code | `test_ac1_reports_shared_and_each_side` (the ticket's exact fixture, thresholds lowered to expose the arithmetic) | ✅ |
| AC2 | Counterpart resolution is symmetric; a path outside any mirror returns a clean negative, not a guess | `test_ac2_resolution_is_symmetric` + `test_ac2_a_path_outside_any_mirror_is_a_clean_negative` (asserts the `outside_mirror` status, and that no path is invented) | ✅ |
| AC3 | A repo with no mirrored subtrees reports none — proven on a pinned public repo | `test_ac3_a_repo_with_no_mirror_reports_none` + `scripts/mirror_report.py` over all three pins (measured: 0 pairs each) | ✅ |
| AC4 | The threshold is justified by measurement across the anchor + ≥2 pinned repos, and the chosen value recorded with the numbers that chose it | The table above (anchor 0.615/4,244; laravel 1.000/**1**; symfony 0; brick 0) + `test_ac4_thresholds_reject_the_measured_false_positive`, which encodes the laravel shape as a regression | ✅ |
| AC5 | The output states the comparison is path-based and never asserts content equality | `test_ac5_the_caveat_ships_with_the_report` + `test_ac5_no_renderer_can_print_counts_without_the_caveat` | ✅ |
| AC6 | Findings written into 098 so the deferred decision has evidence attached | `## Evidence from task 115` section in `docs/tasks/098_correspondence-relation-seam.md`, with the per-repo numbers and an explicit verdict on 098's gate | ✅ |

## Phase 2 — design

### Approach
One new pure module discovers the pairs and answers the lookup; three existing consumers render them.
The pair is **discovered**, both sides are named from the paths, and every answer carries what it is
allowed to claim.

```
store.file_paths() ─┐                            ┌─▶ dataset.mirrors (DATASET_VERSION 4)
config.stub_roots  ─┼─▶ find_mirror_subtrees ────┼─▶ artifact overview: pair table + caveat
layers.responsibility_layer (negative filter) ─┘  └─▶ architecture_overview.summary.mirrors
                              │
                              └─▶ resolve_counterpart(path, pairs, known, complete=…)
                                    → counterpart | no_counterpart | outside_mirror
```

### The algorithm, in four deterministic steps
1. **Candidates.** Every indexed path, minus paths under a declared `stub_roots` and minus paths whose
   110 layer is `Vendor / Framework` or `Tests` (H4 — this removes the measured false positive).
2. **Sibling pairs.** For each parent directory, every unordered pair of its child directories. The
   relative path set under each child is compared: `shared`, `left_only`, `right_only`.
3. **Two gates.** Keep a pair only when `shared >= MIN_SHARED_PATHS` **and**
   `shared / union >= MIN_OVERLAP`. Ranked by shared count descending, then by name.
4. **Lookup.** `resolve_counterpart` finds the pair whose left or right prefix the path starts under,
   swaps the prefix, and reports whether the swapped path is in the known set — qualifying the negative
   when that set was incomplete.

### Rejected alternatives
- **Port the prototype's `legacy/(alpha|beta)` regex.** Rejected: a hardcoded tree prefix and two region
  names, with the region names in the output keys (`alpha_only`/`beta_only`). Same R2.2 class 114 hit.
- **A configured mirror pair** (an operator knob naming the two trees). Rejected: the ticket's Scope
  says "no configured pair (R2.2)" explicitly, and the whole value is that the map *finds* the trap
  rather than being told about it. Note the operator's `stub_roots` is still honoured — as an
  *exclusion*, which is a statement about dependencies, not about which trees mirror.
- **Overlap fraction as the only gate.** Rejected on measured evidence: a pinned repo scores Jaccard
  **1.000** on a pair sharing one file. Encoded as a regression test, not just a note.
- **Shared count as the only gate.** Rejected symmetrically: two large unrelated trees can share many
  incidental paths while overlapping barely at all, and calling those a mirror is the same error in the
  other direction.
- **Content hashing to prove the files really are copies.** Rejected: the ticket's Out of scope, and it
  would turn a bounded path comparison into an IO-bound read of every candidate file. The honest move is
  to state the limit (AC5) rather than overclaim — which is why `PATH_NOT_CONTENT` is a constant on the
  report rather than optional renderer prose.
- **Resolving counterparts against the capped path index without saying so.** Rejected: it makes
  `no_counterpart` — the answer the ticket calls the most useful one — indistinguishable from a cap
  artifact. Hence the explicit `complete` flag and the `qualified` negative (H6).
- **A new edge kind for the correspondence.** Rejected: that is 098's question, deferred, and this
  ticket exists to give 098 numbers rather than to pre-empt it. No `contract_version` bump (R3).

### Change list (traced to matrix rows)
| # | File | Change | Traces to |
|---|------|--------|-----------|
| 1 | `code_atlas/onboarding/mirrors.py` | **NEW** — `MirrorPair`, `MirrorReport`, `Counterpart`, `find_mirror_subtrees`, `resolve_counterpart`, thresholds, caveat | AC1 AC2 AC3 AC4 AC5 |
| 2 | `code_atlas/onboarding/dataset.py` | `mirrors` section; `DATASET_VERSION` 3 → 4; `as_dict`; `render_dataset_overview` | AC1 AC5 |
| 3 | `code_atlas/onboarding/artifact.py` | overview gains the pair table + the caveat line | AC1 AC5 |
| 4 | `code_atlas/tools/architecture_overview.py` | `summary.mirrors` | AC1 AC5 |
| 5 | `code_atlas/tools/generate_onboarding.py` | pass the full path list + declarations through | AC1 |
| 6 | `scripts/mirror_report.py` | **NEW** — per-pin pair table, overlap and shared counts | AC3 AC4 |
| 7 | `tests/test_mirror_subtrees.py` | **NEW** — the AC tests, both threshold boundaries, the measured-false-positive regression | AC1–AC5 |
| 8 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` | core-module pin `56` → `57` | — |
| 9 | `tests/test_onboarding_dataset.py`, `tests/test_architecture_overview.py` | fixture + exact-equality `summary` assertion | — |
| 10 | `docs/tasks/098_correspondence-relation-seam.md` | **`## Evidence from task 115`** — the per-repo numbers and a verdict on 098's gate | AC6 |
| 11 | `docs/tasks/115_…` frontmatter | `depends_on: [112]` + `feeds: [098]` (the corrected arrow) | — |
| 12 | `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, mockup note | docs + token ledger before PR | — |

### Rule compliance
- **R1.1** no language branch — the finder sees only paths.
- **R1.2** one seam — no new abstraction; existing seams untouched.
- **R1.4** SRP — pure module, no SQL, no store import; paths arrive from the caller.
- **R2.2** nothing named — no tree prefix, no region, no configured pair. Enforced by the CI gate 113
  widened to `code_atlas/` plus a unit twin.
- **R3** untouched — no edge kind, no `contract_version` bump; `DATASET_VERSION` is the dataset's own.
- **R4.2** deterministic — sorted candidates, sorted pairs, stable tie-breaks, sorted samples.
- **R4.3** bounded — per-parent sibling combinations over a path list already in memory; samples capped.
- **R7.1** smallest useful change — reuses 113's exclusions and 112's dataset shape rather than adding
  a third mechanism for either.

### Named proving test
`tests/test_mirror_subtrees.py::test_ac1_reports_shared_and_each_side` — the ticket's own `a/x`, `a/y`,
`b/x` fixture reporting one shared path and one on each side. Red before change 1 exists; green after.

### Verification plan
`scripts/docker-test.sh` (ruff · mypy · pytest) green with the new tests counted, then
`scripts/docker-test.sh python scripts/mirror_report.py` for AC3/AC4 — where the expected answer is
**zero pairs on all three pins**, which is precisely AC3's "the detector is not manufacturing structure".

## Phase 3 — execute

Branch `feat/115-mirror-subtree-detection`. The approved change list landed as approved. Two findings,
one of them the same self-trip 114 recorded — now a recurrence worth promoting.

### Findings the gates caught (2)
1. **The R2.2 unit twin caught this ticket's own docstring quoting the prototype's literals.** The
   module docstring explained the prototype by reproducing its regex, tree prefix and region names.
   Reworded to describe the shape without the literals. **This is the second consecutive ticket with
   exactly this failure** (114 finding 2 was the same class): explaining an R2-tainted prototype in a
   comment reintroduces the taint the code carefully avoided. Flagged for `/mango:promote` — the claim
   now has `seen: [114, 115]`, which crosses the two-ticket threshold.
2. **AC1's listed fixture cannot produce the result AC1's own sentence claims.** AC1 says "`a/x`,
   `a/y`, `b/x` reports one shared path and one on each side", but those three paths give one shared,
   one on the *left*, and **none** on the right. Both shapes are now asserted: the four-path fixture
   (`+ b/z`) proves the sentence, and the literal three-path fixture proves the asymmetric case. No
   amendment was needed — the requirement is satisfied, and the listing was illustrative.

### Verification sweep — the diff against the approved list
| Approved item | File | In diff |
|---|---|---|
| 1 | `code_atlas/onboarding/mirrors.py` (new, 57th core module) | ✅ |
| 2 | `code_atlas/onboarding/dataset.py` (`mirrors`, `DATASET_VERSION` 3 → 4) | ✅ |
| 3 | `code_atlas/onboarding/artifact.py` (pair table + caveat) | ✅ |
| 4 | `code_atlas/tools/architecture_overview.py` (`summary.mirrors`) | ✅ |
| 5 | `code_atlas/tools/generate_onboarding.py` | ✅ |
| 6 | `scripts/mirror_report.py` (new) | ✅ |
| 7 | `tests/test_mirror_subtrees.py` (new, 17 tests) | ✅ |
| 8 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` (`56` → `57`) | ✅ |
| 9 | `tests/test_onboarding_dataset.py`, `tests/test_architecture_overview.py` | ✅ |
| 10 | `docs/tasks/098_correspondence-relation-seam.md` (`## Evidence from task 115`) | ✅ |
| 11 | this ticket's frontmatter (`depends_on: [112]` + `feeds: [098]`) | ✅ |
| 12 | `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, mockup note | ✅ |

**Nothing outside that list is in the diff.** No content hashing, no similarity scoring, no new edge
kind, no `contract_version` bump, no config knob, no viewer change (116) — the first four are the
ticket's own Out of scope and the last two were the design's declared boundary.

### Delta-green (Docker — the authoritative gate)
`scripts/docker-test.sh`: **ruff clean · mypy clean over 57 source files · 1601 passed, 0 failed.**
Baseline on `main`, measured by stashing this branch: **1581 passed**. Delta **+20** = 17 new tests in
`test_mirror_subtrees.py` + 2 in `test_core_is_language_agnostic.py` and 1 in `test_onboarding_llm.py`,
both parametrized over the core-module list, which grew by one module. Every added test is accounted for.

## Phase 4 — review

**REVIEW (subagent) WAIVED · CHALLENGER OFF** per the run args. Inline main-loop review only; recorded
so a later reader does not mistake this for a reviewed diff.

Inline checks that did run:
- **R1.1** — no language branch; the detector sees only paths. CI gate green.
- **R2.2** — no tree prefix, no region, no configured pair; enforced by the widened CI gate (which
  **did** fire on a draft docstring — finding 1) plus a unit twin whose denylist covers the
  prototype's own literals.
- **R1.4** — pure module, no SQL, no store import. The SQL-confinement gate covers it.
- **R3** — no edge kind and no `contract_version` bump; only the dataset's own version moved.
- **R4.2** — byte-stability and pair ranking pinned by
  `test_pairs_are_ranked_by_shared_count_and_output_is_byte_stable`.
- **AC5 structurally** — the caveat is a field on the report, and
  `test_ac5_no_renderer_can_print_counts_without_the_caveat` asserts the serialised shape is exactly
  `{caveat, pairs}`, so the counts cannot travel without it.

### AC3/AC4 — measured on the pinned repos (Docker, indexed)
`gates: MIN_SHARED_PATHS=25  MIN_OVERLAP=0.3`

| repo | accepted pairs | best sibling pair, ungated | verdict |
|---|--:|---|---|
| `laravel/laravel` @ `ff031db` | **0** | `tests/Feature` ↔ `tests/Unit`, overlap **1.000**, shared **1** | `shared 1 < 25` |
| `symfony/demo` @ `03fe256` | **0** | none shares any relative path | — |
| `brick/math` @ `b61d8e6` | **0** | none shares any relative path | — |

**The laravel row is AC4's justification, printed by the script rather than asserted in prose.** A
perfect overlap on a single shared file is exactly the false positive a fraction-only threshold accepts,
and it is why the detector gates on the shared count too. The script prints the best *ungated* pair on
every repo precisely so the constant can be re-justified whenever a pin moves.

**Anchor deferred to the operator** — absent on this dev host (the 108/112/113/114 pattern). The
arithmetic is pinned instead by `test_ac1_counts_reproduce_the_anchor_numbers`, which reproduces the
ticket's measured 4,244 / 1,522 / 1,134 and its 0.615 overlap exactly.

### AC6 — the evidence is written into 098, and it argues AGAINST opening it
`docs/tasks/098_correspondence-relation-seam.md` gains `## Evidence from task 115`, answering 098's
three gate items with numbers:
- **Gate 1 (a second, independent repository): still NOT met, and now further from met** — a structural
  detector found the shape in **none** of three independent public repos. `n` is still 1. Measured
  absence is stronger evidence than no evidence.
- **Gate 2 (cost to everyone else): answered** — on a repo without the shape the cost is one bounded
  pass producing an empty list. No table, no column, no build cost, nothing to configure. 115 achieves
  that profile *by not being in the schema*.
- **Gate 3 (a cheaper alternative rejected in writing): the alternative was NOT rejected — it works.**
  The presentation-layer answer delivers the lookup the user asked for, including the negative that
  marks divergence, with no relation in the graph.

**Verdict recorded in 098: stays `deferred`, and 115 is the reason it can afford to.** What 115 cannot
do is stated there too — it compares paths not contents (so it cannot notice drift, which remains the
strongest argument for a real relation), it only finds *sibling* subtrees, and it cannot represent a
hand-asserted many-to-many mapping. Reopening 098 now needs a second repo with the shape **plus** a
demand path comparison provably cannot serve.

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| — | (no subagent dispatched — inline analysis; challenger + reviewer waived by run args) | — | n/a |

**Summary:** 0 dispatches, so 0 ledger rows — the mechanical rule holds (N dispatches ⇒ N rows).
Main-loop spend is not measured by mango. Docker gate: **1601 passed, 0 failed** (main 1581, +20 net);
ruff clean, mypy clean over 57 source files.

## Decision log
- CHALLENGER OFF + REVIEW subagent WAIVED per run args ("with skipped review & challenge"); inline review only.
- Standing maintainer approval to resolve HOW-decisions and pass gates; finishing steps (commit → push → PR) proceed on the AGENTS.md standing approval.
- **`depends_on` corrected:** 098 was listed as a dependency but 115 *feeds* 098. Frontmatter becomes `depends_on: [112]` plus a `feeds: [098]` note, so nobody waits on a deferred ticket for this one.
- **The prototype is not portable** — a hardcoded tree prefix plus two region names, with the region names in the output keys. The pair is discovered instead.
- **Two gates, not one, on measured evidence:** a Jaccard threshold alone accepts a pinned repo's pair that scores 1.000 on a single shared file.
- **Recurrence flagged for `/mango:promote`:** "explaining an R2-tainted prototype in a comment reintroduces the taint the code avoided" now has `seen: [114, 115]` — two ticket keys, so it crosses the cross-ticket promotion threshold. The maintainer runs `/mango:promote` between tickets; this run does not.
- **AC6's verdict is negative and that is the finding:** 115's evidence keeps 098 deferred rather than opening it, because measured absence on three independent repos is stronger than no evidence.
