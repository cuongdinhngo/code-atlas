---
id: 114
slug: business-module-table
title: Onboarding — nothing bridges "fix screen X" to a file path (M11)
phase: 3
milestone: M11
status: done
depends_on: [112]
---

## Why this exists

A first-day developer's only real question is *"I was told to fix the X screen — which file do I open?"*
The current artifact is organised by structure (files, symbols, edges) while the newcomer's head is
organised by business capability. Nothing connects the two, and the reviewer standing in as that
developer named this the single reason the page failed them.

The mockup added a table derived from **module directories in the code** — the segment after
`application/` or `modules/` — giving 24 modules on the anchor repo with, per module: file count, class
count, which top-level trees it appears under, and its highest-fan-in file. Examples measured:
`admin` (394 files, both region trees), `roster` (257, both), `reports` (252, both), `api` (205, both
regions plus the namespaced tree), `care` (111, all three), `catering` (106, one region only).

The single-tree rows are the finding: **a module present under one region tree and not the other is where
the two markets have diverged**, which is exactly what a newcomer must not assume away.

## The limit that must ship with it

Testing the reviewer's own example exposed the boundary: the screen they named is a **flat file directly
under the web root** and belongs to no module directory, so it is absent from the table. The table
therefore must state its own coverage — what fraction of indexed files it accounts for — and point at
search for the remainder. A table that looks exhaustive and isn't is worse than a smaller honest one.

## Scope

- Derive module candidates structurally: a directory one level under a `application`/`modules`-style
  container segment, with a minimum file count, excluding role words already claimed by 110's vocabulary
  and excluding region/container names.
- Per module: files, classes, which top-level trees contain it, its directories, and its top hub.
- Report **coverage**: files accounted for vs total indexed, in the dataset and in every renderer.
- Rank single-tree modules as a distinct signal (divergence), not just as a row.
- R2.2: no repo-specific module names in code — the names are *read from the tree*, never listed.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with `app/application/billing/…` and `app/application/audit/…` yields two
   modules with correct counts — observed red against today's code, which has no such concept.
2. **AC2.** Coverage is reported and correct: a fixture where half the files sit outside any module
   directory reports ~50 %, and the renderer shows it.
3. **AC3.** A module present under one tree and absent under a sibling tree is flagged; a module present
   under both is not.
4. **AC4.** Role words (`controller`, `model`, `view`, …) and container/region names never become modules.
5. **AC5.** Measured on the anchor repo and two pinned public repos: module count, coverage percentage,
   and single-tree count. A repo with no module-style layout reports zero modules and says so rather than
   inventing groups.
6. **AC6.** No module name is hard-coded anywhere in `code_atlas/`; R2.2 grep-gate covers the new code.

## Out of scope

Mapping modules to URLs or menu entries — that needs a repo's own route inventory, which is repo-specific
knowledge the core must not consume.

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 114

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed · **Branch:** `feat/114-business-module-table`
- **CHALLENGER:** OFF (--no-challenger) · **REVIEW (subagent):** WAIVED — inline main-loop review only
- **TIER:** full · **SCOPE:** M (one new pure module + one store aggregate + 3 consumer edits + dataset version bump + tests)
- **change type:** feat

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions`. The ticket states the problem, the per-module fields,
the coverage requirement, the divergence signal and the R2.2 constraint. Everything else is a
how-decision, resolved below and cited.

**Premise check — PASSED.** Every referenced source resolves: the 112 dataset
(`code_atlas/onboarding/dataset.py`, `DATASET_VERSION = 2` after 113), 110's responsibility vocabulary
(`code_atlas/onboarding/layers.py:41`, public `responsibility_layer` since 113), the mockup prototype
(`docs/phase3-onboarding/mockup/extract.py:130-167`), 112's store aggregates
(`file_symbol_counts`/`module_hubs`/`largest_classes`), and R2.2 + its now-core-covering CI gate
(`docs/ENGINEERING_RULES.md:54`, `.github/workflows/ci.yml`).

## Phase 1 — analysis

### Measured problem (ticket)
The artifact is organised by structure; a newcomer's head is organised by business capability, and
nothing bridges them. The reviewer standing in as a first-day developer named this the single reason
the page failed them.

### The prototype cannot be ported — it is R2-tainted in four separate ways
`docs/phase3-onboarding/mockup/extract.py:131-139` derives modules with:
1. a container regex naming `application|modules|Application`,
2. a `SKIP` set holding **region names** (`alpha`, `beta`, `ab`),
3. the same set holding **library names** (`tcpdf`, `mpdf`, `adodb`, `smarty`, `zend`, `saml`,
   `phpexcel`, `phpword`, `log4php`, `fpdf`, `dompdf`, `phpqrcode`),
4. hardcoded tree prefixes `legacy/alpha/`, `legacy/beta/`, `src/`.

Every one is exactly what R2.2 forbids in the core. So this ticket is not a port: the signal must be
**derived structurally**, and the design below does that — no container word list, no region list, no
library list, no tree prefixes.

### Real-repo validation, run BEFORE designing (the `fixture-shape-begs-the-question` retro)
The three pinned repos are already cloned under `artifacts/cross-repo-cache/`, so the candidate rule was
measured against real trees first. Fan-out per directory, `*.php` outside `vendor/`:

| repo | widest container | qualifying children (≥3 files) | 110 role words among them |
|---|---|---|---|
| `laravel/laravel` | `app` (3 child dirs) | **0** (Http/Models/Providers hold 1 file each) | — |
| `symfony/demo` | `src` (12 child dirs) | **7** — Command 3, Controller 4, Entity 4, EventSubscriber 4, Form 7, Repository 3, Twig 3 | **4** (controller, entity, form, repository) |
| `brick/math` | `src` (2 child dirs) | **2** — Exception 10, Internal 7 | 0 |

**This measurement moved the design twice.** A file-count floor alone cannot separate `brick/math`'s
`Exception` (10 files) from a real module, and `symfony/demo`'s widest container is organised **by
responsibility, not by capability** — a table listing `Controller`, `Entity`, `Form`, `Twig` as
"business modules" would be worse than no table. Hence the two gates in H2/H3, which land all four
repos (three pins + the anchor's shape) on the right answer.

### HOW-decisions (resolved on standing approval)
- **H1 — new pure module `code_atlas/onboarding/modules.py` (56th core module).** Holds
  `BusinessModule`, `ModuleMap`, `find_business_modules`. Pure functions over candidate paths + per-file
  counts + 083 degrees: no SQL, no LLM, no language branch (R1.1/R1.4/R4).
- **H2 — a container is DERIVED, never named.** For every directory, count its child directories holding
  at least `MIN_MODULE_FILES = 3` candidate files (recursively). A directory is a **container** when it
  has at least `MIN_CONTAINER_MODULES = 4` such children. This replaces the prototype's
  `application|modules` regex: on the anchor the same rule elects `legacy/alpha/application` and
  `legacy/beta/application` (24 children each) without knowing either word, and it also works on a repo
  that spells its container anything else. Both thresholds are defaulted parameters (112's
  `dir_symbol_threshold` precedent), not config knobs — so tests can drive the boundary from both sides.
- **H3 — a container organised by RESPONSIBILITY yields no modules, and says so.** If at least half its
  qualifying children resolve a 110 responsibility layer, the container is role-organised and produces
  **zero** modules with the reason recorded. `symfony/demo` (4 of 7) is refused; the anchor (2 of 24)
  is not. Reuses 110's already-ratified R2.2 vocabulary as a *negative* filter — no new vocabulary,
  so **no new R2.2 judgment is needed** (the 113 precedent).
- **H4 — the "tree" is the container's parent path, derived.** The prototype hardcoded `legacy/alpha/`,
  `legacy/beta/`, `src/`. Instead, a module found at `<container>/<name>` is attributed to the tree
  `<container's parent>`, so the anchor yields `legacy/alpha`, `legacy/beta` and `src` from the paths
  themselves. Region and container names therefore **cannot** become modules: both sit *above* the
  module level by construction, which satisfies AC4's second half with no list at all.
- **H5 — the divergence signal is only computed when there is something to diverge from.** A module in
  exactly one container is flagged `single_tree` **only when the repo has ≥ 2 containers**. With one
  container every module is trivially single-tree, and flagging all 24 as divergence would be noise
  dressed as a finding.
- **H6 — vendored and test code is excluded using 113's signals, not a new list.** A candidate path is
  dropped when it is under a declared `stub_roots`, or when its 110 layer is `Vendor / Framework` or
  `Tests`. This is what keeps a 200-package `vendor/` from being elected the widest container and
  reported as 200 business modules.
- **H7 — one new bounded store aggregate: `file_class_counts()`.** Per-file `kind = 'Class'` count, one
  GROUP BY pass, the same shape and bound as 112's `file_symbol_counts()`. `'Class'` is a contract node
  kind, not a repo name (the `largest_classes` precedent). Per-module **hub** needs no SQL — it is the
  highest `fan_in` among the module's files, already in `metrics.modules`.
- **H8 — coverage is reported *and explained*.** `ModuleMap` carries `covered`, `total`, `percent`, plus
  `excluded` (files skipped as vendored/test) so the gap is accounted for rather than mysterious, and a
  fixed note points at search for the remainder — the ticket's "a table that looks exhaustive and isn't
  is worse than a smaller honest one".
- **H9 — consumers: the dataset, the artifact overview, and the overview tool.** `dataset.py` gains a
  `modules` section (`DATASET_VERSION` **2 → 3**); `artifact.py`'s overview renders the table with its
  coverage line; `architecture_overview` gains `summary.business_modules`. The viewer's HTML stays 116.
- **H10 — SCOPE boundary (surfaced at Gate 1).** Out: mapping modules to URLs or menu entries (ticket's
  own Out of scope), the viewer (116), any config knob, any adapter or contract change.

### ⚠ AC1's fixture conflicts with the shipped threshold — amendment proposed at Gate 1
AC1 names a fixture with **two** module directories (`app/application/billing/…`,
`app/application/audit/…`). Under H2's `MIN_CONTAINER_MODULES = 4` that fixture correctly yields **zero**
modules, so AC1 as literally written can never go green — and lowering the gate to 2 would make
`brick/math` report `Exception` and `Internal` as business modules, breaking AC5 on a real repo.

**Proposed amendment (the 107 precedent):** AC1's fixture gains two more module directories (four total:
`billing`, `audit`, `roster`, `catering`) so it exercises the **shipped default** rather than a threshold
chosen to suit it, and a **separate boundary test** proves a three-module container is refused. AC1's
requirement is unchanged — module directories yield modules with correct counts — and it is now tested
against the code that actually ships. Recorded rather than absorbed.

### Blast radius
- **New:** `code_atlas/onboarding/modules.py`; `scripts/module_report.py`; `tests/test_business_modules.py`.
- **Edited:** `code_atlas/store.py` (+`file_class_counts`); `code_atlas/onboarding/dataset.py`
  (`modules` section, `DATASET_VERSION` → 3); `code_atlas/onboarding/artifact.py` (table + coverage row);
  `code_atlas/tools/architecture_overview.py` (`summary.business_modules`);
  `code_atlas/tools/generate_onboarding.py` (pass the new rows through).
- **Must-fix pins:** `tests/test_sql_confinement.py:32`, `tests/test_core_is_language_agnostic.py:42`
  (`55` → `56`); the `OnboardingDataset` fixture in `tests/test_onboarding_dataset.py`; the exact-equality
  `summary` assertion in `tests/test_architecture_overview.py` (the 113 deviation, now expected).
- **Verify-only green:** 113's reachability split, 109's quality gate, 111's steps, viewer, config.

### Acceptance-criteria matrix
| AC | Requirement | Proof | Status |
|----|-------------|-------|--------|
| AC1 (R6.5) | A fixture with module directories under a container yields those modules with correct file/class counts — observed red against today's code, which has no such concept | `test_ac1_container_yields_its_modules_with_counts` (four-module fixture per the amendment) + `test_ac1_boundary_a_three_module_container_is_refused` | ✅ (fixture amended — above) |
| AC2 | Coverage is reported and correct: half the files outside any module dir ⇒ ~50 %, and the renderer shows it | `test_ac2_coverage_is_reported_and_correct` (exact 50 % fixture) + `test_ac2_renderer_prints_the_coverage_line` | ✅ |
| AC3 | A module under one tree but absent under a sibling tree is flagged; one under both is not | `test_ac3_single_tree_module_is_flagged_and_a_shared_one_is_not` (two containers) + `test_ac3_divergence_is_not_claimed_with_one_container` (H5) | ✅ |
| AC4 | Role words never become modules; container/region names never become modules | `test_ac4_a_role_organised_container_yields_no_modules` (the `symfony/demo` shape) + `test_ac4_container_and_tree_names_are_never_modules` (structural, H4) | ✅ |
| AC5 | Measured on the anchor + two pinned public repos: module count, coverage %, single-tree count; a repo with no module layout reports zero and says so | `scripts/module_report.py` (Docker) over the three pins; counts recorded below. **Anchor deferred to the operator** (absent on this dev host — 108/112/113 precedent) | ✅ (anchor deferred) |
| AC6 | No module name hard-coded in `code_atlas/`; the R2.2 grep-gate covers the new code | `test_ac6_no_repo_or_library_name_in_the_module_finder` + the CI gate 113 widened to scan `code_atlas/` | ✅ |

## Phase 2 — design

### Approach
One new pure module derives the map; four existing consumers render it. Nothing is named: the container,
the module names and the trees all come **out of the path set**, and the only vocabulary involved is
110's already-ratified one, used as a *negative* filter.

```
store.file_paths()        ─┐
store.file_class_counts()  ├─▶ find_business_modules ──┬─▶ dataset.modules (DATASET_VERSION 3)
metrics.modules (fan_in)  ─┤   (container → modules    ├─▶ artifact overview table + coverage line
config.stub_roots         ─┘    → trees → coverage)    └─▶ architecture_overview.summary.business_modules
layers.responsibility_layer ── negative filter only (vendor/test paths, role-organised containers)
```

### The algorithm, in five deterministic steps
1. **Candidates.** Every indexed path, minus paths under a declared `stub_roots` and minus paths whose
   110 layer is `Vendor / Framework` or `Tests` (H6 — this is what stops a 200-package `vendor/` being
   elected the widest container).
2. **Fan-out.** For every directory, count child directories holding ≥ `MIN_MODULE_FILES` (3) candidate
   files, counted recursively.
3. **Containers.** Directories with ≥ `MIN_CONTAINER_MODULES` (4) such children. A container that is a
   **descendant of another container is dropped**, so modules never nest inside modules.
4. **Role refusal.** A container where ≥ half its qualifying children resolve a 110 responsibility layer
   is role-organised: it contributes **no** modules and its path + reason go into `refused`.
5. **Union.** Modules keyed by lowercased child segment; `trees` = sorted container **parents**;
   `single_tree` set only when the repo has ≥ 2 containers (H5). Coverage = candidate files under an
   accepted module ÷ every indexed file.

### Rejected alternatives
- **Port the prototype's regex + `SKIP` list.** Rejected: four separate R2.2 violations (analysis §
  "the prototype cannot be ported"). This is the whole reason the ticket exists as core work.
- **A new *container* vocabulary** (`application`, `modules`, `apps`, `packages`, `features`, …) as a
  ratified R2.2 standard, mirroring 110. Rejected as **unnecessary**, which is stronger than rejecting it
  as wrong: the structural rule elects the anchor's `legacy/{alpha,beta}/application` without knowing the
  word, so a new ratified vocabulary would buy nothing and would need a maintainer judgment (the 113
  precedent — don't spend an R2.2 judgment you can derive around).
- **A file-count floor as the only gate** (the prototype's `files >= 8`). Rejected on measured evidence:
  `brick/math`'s `Exception` holds 10 files and is not a business module. The peer-count gate is what
  separates a capability layout from a library's internal split.
- **Excluding every role-named child individually** (AC4's literal reading). Rejected: the anchor's own
  measured module list includes `api` (205 files) and `reports` (252 files), both 110 role words, and
  both genuine capabilities there. The container is classified **once** and its classification governs
  its children, so a role-*organised* container yields nothing while a capability-organised container
  keeps a role-named member. AC4's intent is met; its literal per-word reading is not, and that is
  recorded here rather than silently reinterpreted.
- **Flagging `single_tree` unconditionally.** Rejected: with one container every module is trivially
  single-tree, so the divergence "finding" would fire on every row of a single-tree repo.
- **A `business_modules` field on `OnboardingArtifact`.** Rejected: `summary` is already
  `dict[str, object]` and already serialised, so the map rides there — the artifact shape, its cache
  round-trip and 109's gate stay untouched (the 113 precedent).

### Change list (traced to matrix rows)
| # | File | Change | Traces to |
|---|------|--------|-----------|
| 1 | `code_atlas/onboarding/modules.py` | **NEW** — `BusinessModule`, `ModuleMap`, `find_business_modules`, the two thresholds | AC1 AC2 AC3 AC4 AC6 |
| 2 | `code_atlas/store.py` | **+** `file_class_counts()` — one bounded GROUP BY pass | AC1 |
| 3 | `code_atlas/onboarding/dataset.py` | `modules` section; `DATASET_VERSION` 2 → 3; `as_dict`; `render_dataset_overview` | AC1 AC2 |
| 4 | `code_atlas/onboarding/artifact.py` | overview gains the module table + coverage line | AC2 |
| 5 | `code_atlas/tools/architecture_overview.py` | `summary.business_modules` | AC1 AC2 |
| 6 | `code_atlas/tools/generate_onboarding.py` | pull `file_class_counts`, pass declarations through | AC1 |
| 7 | `scripts/module_report.py` | **NEW** — per-pin module count, coverage %, single-tree count | AC5 |
| 8 | `tests/test_business_modules.py` | **NEW** — the AC tests + boundary + determinism | AC1–AC6 |
| 9 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` | core-module pin `55` → `56` | — |
| 10 | `tests/test_onboarding_dataset.py`, `tests/test_architecture_overview.py` | fixture + exact-equality `summary` assertion | — |
| 11 | `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, mockup note, this ticket | docs + token ledger before PR | — |

### Rule compliance
- **R1.1** no language branch — the finder sees paths, counts and degrees; never a language.
- **R1.2** one seam — no new abstraction; the 085/091 seams are untouched.
- **R1.4** SRP — pure module, no SQL; the one new query lives in `store.py`.
- **R2.2** nothing named — no container word, no region, no library, no tree prefix. Enforced by the CI
  gate 113 widened to `code_atlas/` plus a unit twin.
- **R3** untouched — `DATASET_VERSION` is the dataset's own version, not `contract_version`.
- **R4.2** deterministic — sorted containers, sorted trees, sorted modules, stable tie-breaks.
- **R4.3** bounded — `file_class_counts` is one GROUP BY pass; the module list is capped at `max_results`.
- **R7.1** smallest useful change — reuses 113's exclusion signals and 112's aggregate shape rather than
  inventing either.

### Named proving test
`tests/test_business_modules.py::test_ac1_container_yields_its_modules_with_counts` — a four-module
container fixture yielding those four modules with correct file and class counts. Red before change 1
exists (there is no such concept today); green after.

### Verification plan
`scripts/docker-test.sh` (ruff · mypy · pytest) green with the new tests counted, then
`scripts/docker-test.sh python scripts/module_report.py` for AC5's three pinned repos — where the
expected answer is **zero modules on all three**, each with its reason, which is precisely AC5's
"reports zero modules and says so rather than inventing groups".

## Phase 3 — execute

Branch `feat/114-business-module-table`. The approved change list landed as approved. Three findings the
gates caught, one of them a real bug in shipped code from the previous ticket's seam.

### Findings the gates caught (3)
1. **`responsibility_layer` cannot answer for a bare directory name — it drops the last segment.**
   `_is_role_organised` needed the role check on a *segment* (`"controller"`), but
   `responsibility_layer` treats its argument as a module path and drops the final segment as a
   filename, so `responsibility_layer("controller")` returns `None`. Every role-organised container
   would have passed the gate and its role directories shipped as business modules. Fixed by adding a
   public `responsibility_of_segment` to `layers.py` over the existing `_match_keyword` — the same
   shape 113 added `responsibility_layer` in, for the same reason.
2. **The R2.2 CI gate 113 widened caught this ticket's own prose.** `_is_role_organised`'s docstring
   named a pinned public repo to explain the 4-of-7 measurement, which the gate correctly rejects
   (`LESSONS.md` 003 — a grep-gate reads comments as inputs). Reworded to "a pinned sample: 4 of 7";
   the number survives, the name does not. The gate earned its widening on its first ticket.
3. **mypy caught a loop-variable shadow in `render_dataset_overview`.** The new module loop reused
   `row`, already bound to `LayerStat` earlier in the same function; renamed to `mod`.

### Ownership lookup was O(files × modules) and is now O(depth)
The first cut scanned every module's directory list per file — 40k files × 24 modules ≈ 1M prefix
checks on the anchor. Replaced with a `directory → module` map walked over each path's own ancestors,
so cost is path depth, not module count. Caught in review of my own draft, before the gate.

### Verification sweep — the diff against the approved list
| Approved item | File | In diff |
|---|---|---|
| 1 | `code_atlas/onboarding/modules.py` (new, 56th core module) | ✅ |
| 2 | `code_atlas/store.py` (`file_class_counts`) | ✅ |
| 3 | `code_atlas/onboarding/dataset.py` (`modules`, `DATASET_VERSION` 2 → 3) | ✅ |
| 4 | `code_atlas/onboarding/artifact.py` (table + coverage line) | ✅ |
| 5 | `code_atlas/tools/architecture_overview.py` (`summary.business_modules`) | ✅ |
| 6 | `code_atlas/tools/generate_onboarding.py` | ✅ |
| 7 | `scripts/module_report.py` (new) | ✅ |
| 8 | `tests/test_business_modules.py` (new, 19 tests) | ✅ |
| 9 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` (`55` → `56`) | ✅ |
| 10 | `tests/test_onboarding_dataset.py`, `tests/test_architecture_overview.py` | ✅ |
| 11 | `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, mockup note, this ticket | ✅ |
| — | `code_atlas/onboarding/layers.py` (`responsibility_of_segment`) | ⚠ **addition** — finding 1 |

**One addition beyond the approved list**, recorded rather than absorbed: `layers.py` gains
`responsibility_of_segment`. It is not scope growth — it is the correct home for a lookup the approved
change list assumed already existed, and putting it anywhere else would have duplicated
`_match_keyword` or reached into a private (the same argument 113 made for `responsibility_layer`).
Nothing else outside the list is in the diff: no config knob, no viewer change (116), no URL/menu
mapping (ticket's own Out of scope), no adapter or contract change (R3 untouched).

### Delta-green (Docker — the authoritative gate)
`scripts/docker-test.sh`: **ruff clean · mypy clean over 56 source files · 1581 passed, 0 failed.**
Baseline on `main`, measured by stashing this branch: **1559 passed**. Delta **+22** = 19 new tests in
`test_business_modules.py` + 2 in `test_core_is_language_agnostic.py` and 1 in `test_onboarding_llm.py`,
both parametrized over the core-module list, which grew by one module. Every added test is accounted for.

## Phase 4 — review

**REVIEW (subagent) WAIVED · CHALLENGER OFF** per the run args. Inline main-loop review only; recorded
so a later reader does not mistake this for a reviewed diff.

Inline checks that did run:
- **R1.1** — no language branch; the finder sees paths, counts and degrees. CI gate green.
- **R2.2** — nothing named: no container word, no region, no library, no tree prefix. Enforced by the
  widened CI gate (which **did** fire on a draft comment — finding 2) plus
  `test_ac6_no_repo_or_library_name_in_the_module_finder`, whose denylist also covers every library
  name the prototype listed. The test additionally asserts the prototype's container word is absent.
- **R1.4** — pure module, no SQL; the one new query lives in `store.py`. The SQL-confinement gate covers it.
- **R3** — the adapter contract is untouched; only the dataset's own `DATASET_VERSION` moved.
- **R4.2** — byte-stability pinned by `test_output_is_byte_stable_regardless_of_input_order`.
- **R4.3** — `file_class_counts` is one GROUP BY pass; the module list is capped and says so
  (`test_the_module_list_is_capped_and_says_so`).

### AC5 — measured on the pinned repos (Docker, indexed)
| repo | modules | containers | single-tree | coverage | refused |
|---|--:|--:|--:|---|---|
| `laravel/laravel` @ `ff031db` | **0** | 0 | 0 | 0/26 files (0.0 %), 3 excluded | — (no capability layout) |
| `symfony/demo` @ `03fe256` | **0** | 0 | 0 | 0/51 files (0.0 %), 6 excluded | `src` — groups by responsibility, not capability |
| `brick/math` @ `b61d8e6` | **0** | 0 | 0 | 0/32 files (0.0 %), 8 excluded | — (no capability layout) |

**Zero on all three is the correct answer, not a gap** — none of the pins uses a capability layout, and
AC5 asks precisely for an honest zero with the reason rather than invented groups. `symfony/demo` is the
interesting row: its `src` *does* fan out into 7 peer directories, and it is refused because 4 of them
name responsibilities. A table listing `Controller`, `Entity`, `Form` and `Twig` as business modules
would have been worse than no table.

**Anchor deferred to the operator** — absent on this dev host (the 108/112/113 pattern). The report
script is committed, and its `check()` asserts the invariants that hold on any repo (coverage never
exceeds the total; no coverage claimed without modules; no divergence claimed with fewer than two
containers; every refusal carries a reason), so the anchor run is a measurement, not a hoped-for pass.

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| — | (no subagent dispatched — inline analysis; challenger + reviewer waived by run args) | — | n/a |

**Summary:** 0 dispatches, so 0 ledger rows — the mechanical rule holds (N dispatches ⇒ N rows).
Main-loop spend is not measured by mango. Docker gate: **1581 passed, 0 failed** (main 1559, +22 net);
ruff clean, mypy clean over 56 source files.

## Decision log
- CHALLENGER OFF + REVIEW subagent WAIVED per run args ("with skipped review & challenge"); inline review only.
- Standing maintainer approval to resolve HOW-decisions and pass gates; finishing steps (commit → push → PR) proceed on the AGENTS.md standing approval.
- **The prototype is not portable** — four distinct R2.2 violations (container word list, region list, library list, hardcoded tree prefixes). The signal is re-derived structurally instead.
- **AC1's fixture amended at Gate 1** (two modules → four, plus a boundary test), because the literal fixture cannot pass a threshold that AC5 requires on real repos. Requirement unchanged.
- **Real-repo measurement ran BEFORE the design**, against the already-cached pinned clones. It moved the design twice (the peer-count gate and the role-majority refusal) — the `fixture-shape-begs-the-question` retro applied rather than cited.
- **One addition beyond the approved change list:** `layers.py` gains `responsibility_of_segment`, the correct home for a lookup the change list assumed existed (finding 1).
