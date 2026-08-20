---
id: 110
slug: layers-named-by-responsibility
title: Onboarding — layers are directory names, not architecture; name them by responsibility (M10)
phase: 3
milestone: M10
status: done
depends_on: [084, 105, 109]
---

## Why this exists (measured, anchor monorepo)

084/103/104/105 group modules by directory, so the layer names on a real repo are the top-level
directory names. On the anchor monorepo the emitted layers are the two region directories, the shared
`src`, a vendor directory, `tests`, `scripts`, `public`, `config`, and `(root)`. None of those tell a
newcomer what code in the layer *does*, and two of them are the same application twice.

The mockup instead matched a **responsibility vocabulary** against directory segments and produced 12
layers with plausible mass:

| Layer | Files | Class | Method |
|---|---:|---:|---:|
| Shared Library | 4,950 | 4,114 | 37,542 |
| Views | 3,694 | 734 | 3,058 |
| Uncategorised | 2,740 | 1,363 | 8,719 |
| Domain / Data | 2,478 | 2,461 | 19,223 |
| Vendor / Framework | 1,302 | 795 | 5,817 |
| Integration / Reporting | 1,048 | 1,019 | 2,586 |
| HTTP / Entry | 1,027 | 1,036 | 7,272 |
| Services | 870 | 875 | 5,073 |
| Middleware / Auth | 343 | 351 | 1,808 |
| Tests | 343 | 408 | 4,046 |
| Config / Migration | 97 | 78 | 404 |
| Background Jobs | 37 | 21 | 63 |

The distribution is itself the insight: `Views` holds 3,694 files but only 734 classes — that layer is
procedural script, and a newcomer should know before opening it.

**The deepest segment must win.** Matching *any* segment (the reference tool's order) let one container
directory absorb **11,540 files** into a single layer. Deepest-wins puts
`…/asset/controller/x` in HTTP and `…/asset/model/x` in Domain/Data, which is the useful answer.

## The rule judgment this ticket needs (✋ maintainer)

The vocabulary is `controller · handler · route · endpoint · api · service · usecase · model · entity ·
repository · view · template · page · form · middleware · filter · auth · session · job · cron · queue ·
worker · report · export · integration · lib · util · helper · common · system · test · spec · mock ·
config · migration · vendor`.

**Is that a standard or a sample (R2.2)?** This ticket argues **standard**: every word is an industry
architectural convention, none names a repo, product or framework, and the same table would apply
unchanged to a Laravel, Rails or Spring tree. The maintainer decides before implementation; if the
judgment is *sample*, the fallback is to keep directory names and carry only the mandatory
`description` field, and this ticket shrinks accordingly.

## Scope

- A responsibility vocabulary in `onboarding/layers.py`, deepest-segment-wins, with a documented
  `Uncategorised` fallback that is **reported, not hidden** (2,740 files is a naming-debt signal worth
  surfacing).
- Every layer carries a mandatory `description` (structural default now, LLM prose in 117).
- Keep 105's graph-mass ordering for layer *rank*; this ticket changes naming and grouping only.
- `architecture_overview` and the artifact both read the new names; no language branch (R1.1).

## Acceptance criteria

1. **AC1.** A fixture with `app/x/controller/a`, `app/x/model/b`, `app/x/view/c` yields three layers,
   not one — observed red against today's code (R6.5).
2. **AC2.** Deepest-wins is proven by a fixture where an outer segment also matches the vocabulary, and
   the outer match loses.
3. **AC3.** Every layer has a non-empty description; 109's C3 becomes green for real rather than by
   default.
4. **AC4.** Re-measured on the anchor repo and on at least two pinned public repos: layer counts and the
   `Uncategorised` share reported in the working doc. A pinned repo whose layer set changes shape is
   discussed, not silently accepted.
5. **AC5.** R2.2 grep-gate still passes; the vocabulary contains no repo, product or framework name.

## Out of scope

Re-grouping *modules* across layers (091 already refuses to), and the tour's use of layers (111).

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 110

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed · **Branch:** `feat/110-layers-named-by-responsibility`
- **CHALLENGER:** OFF (--no-challenger) · **REVIEW (subagent):** WAIVED — inline main-loop review only
- **TIER:** full · **SCOPE:** L (declared, not grown — algorithm + data-model + all renderers + test churn)
- **change type:** feat

## Gate 0 — the R2.2 judgment ✋ (maintainer-decided)
**Ratified: STANDARD — build full 110.** The 36-word vocabulary is industry-general (controller,
service, model, repository, view, job, report, config, vendor, …); none names a repo, product or
framework, and the R2.2 grep-gate denylist (laravel|symfony|wordpress|drupal|magento) still passes.
The same table applies unchanged to a Laravel/Rails/Spring tree. (If it had been *sample*, the ticket
shrank to directory-names + a description field only.)

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions` after Gate 0. The one product-decision (standard vs
sample) was the maintainer's and is resolved above; everything else is a HOW-decision resolved in
design. No premise falsified — `assign_layers`, `LayerRow`, `architecture_overview` all resolve.

## Phase 1 — analysis

### HOW-decisions (resolved on standing approval)
- **H1 — responsibility is the PRIMARY grouping; dominant-subtree/direction stay as FALLBACK.**
  `assign_layers` groups each module by its deepest vocabulary-matching segment. If that yields **≥ 2
  distinct layers** → `method="responsibility"`. Otherwise fall back to today's dominant-subtree
  (105), then dependency-direction (084). This keeps 104/105's code and the tests whose fixtures use
  non-vocabulary directory names, and confines the churn to fixtures whose segments *do* match.
- **H2 — deepest-segment-wins** (ticket): iterate a module's directory segments from the leaf up and
  take the first match, so `…/service/controller/x` is HTTP/Entry, not Services (AC2).
- **H3 — matching is case-insensitive and simple-plural aware** (`Controllers`→controller,
  `Repositories`→repository via -ies→-y, `models`→model). A general English-morphology normalisation,
  not a repo name (R2.2). Deterministic (R4.2).
- **H4 — every layer carries a `description`, non-empty by construction.** `layer_description(name)`
  returns the ratified prose for a known layer/direction band, else a structural default
  `Modules grouped under "<name>"`. So 091-refined names and fallback bands are never blank.
- **H5 — 109's C3 strengthens from name → description** (ticket AC3). `LayerRow` gains
  `description`; the gate's C3 checks `row.description`. This is 109's planned hand-off, not scope
  creep (109 shipped C3 as "non-empty name" precisely to enable this).
- **H6 — anchor + pinned-repo re-measure (AC4).** The anchor monorepo is absent on this host (108
  pattern), so AC4's anchor numbers are **deferred to an operator run**; the two pinned public repos
  (`scripts/layer_report.py`, added by 105) are re-measured here and their layer sets discussed.

### Blast radius
`layers.py` (new vocabulary + matching + descriptions; grouping now responsibility-first),
`artifact.py` (`LayerRow.description`, overview render, manifest, cache), `viewer.py` (payload),
`architecture_overview.py` (`_layer_rows` + summary), `quality_gate.py` (C3 → description). Tests:
`test_onboarding_layers.py` (fixtures with vocab segments shift to responsibility), plus any
byte/string pin over layer output, and the C3 fixture in `test_onboarding_quality_gate.py`. No store,
adapter, or contract change. R1.1 (no language branch — generic segment matching), R4.2 (deterministic)
hold.

### Acceptance matrix
| AC | Requirement | Approach | Verification |
|---|---|---|---|
| AC1 | `controller`/`model`/`view` under one dir → 3 layers, not 1 (R6.5 red) | responsibility grouping, deepest-wins | fixture test, observed red vs today's dominant-subtree (1 layer `app`) |
| AC2 | deepest-wins: an outer vocab segment loses to an inner one | `…/service/controller/x` → HTTP/Entry | fixture test |
| AC3 | every layer has a non-empty description; C3 green for real | `layer_description` + `LayerRow.description`; C3 → description | gate + layer tests |
| AC4 | re-measure anchor + 2 pinned repos; report counts + Uncategorised share | `layer_report.py` on pinned repos; anchor deferred (H6) | ledger/working-doc note |
| AC5 | R2.2 grep-gate passes; vocabulary names no repo/product/framework | keywords are conventions only | CI guardrails job + a test |

### Gate 1 — analysis ✋ (surfaced; proceeding on standing approval). TIER full, SCOPE **L** (declared).

## Phase 2 — design

### The ratified vocabulary → layer map (the "standard")
| Layer | Keywords | Description |
|---|---|---|
| HTTP / Entry | controller, handler, route, endpoint, api | Request entry points: controllers, routes and API handlers that receive external calls. |
| Services | service, usecase | Application services and use-cases that coordinate domain logic. |
| Domain / Data | model, entity, repository | Domain models, entities and repositories — the data layer and its persistence. |
| Views | view, template, page, form | Presentation: views, templates, pages and forms rendered to the user. |
| Middleware / Auth | middleware, filter, auth, session | Request middleware, filters, authentication and session handling. |
| Background Jobs | job, cron, queue, worker | Asynchronous work: jobs, cron tasks, queues and workers. |
| Integration / Reporting | report, export, integration | Outbound integration, reporting and data export. |
| Shared Library | lib, util, helper, common, system | Shared libraries, utilities and helpers reused across the codebase. |
| Tests | test, spec, mock | Automated tests, specs and mocks. |
| Config / Migration | config, migration | Configuration and database migrations. |
| Vendor / Framework | vendor | Third-party vendor and framework code. |
| Uncategorised | (no keyword matched) | Modules whose path matched no responsibility keyword — a naming-debt signal worth surfacing. |

Direction-band + root descriptions (fallback path, so C3 is real there too): `source`, `sink`,
`mixed`, `isolated`, `(root)` each get a one-line description; any other name falls to the structural
default.

### Change list (approved scope — do not widen)
1. `layers.py` — `RESPONSIBILITY_KEYWORDS`, `LAYER_DESCRIPTIONS`, `UNCATEGORISED`,
   `_match_keyword`, `_responsibility_layer`, `layer_description`; `assign_layers` responsibility-first
   (H1); `LAYER_METHODS` gains `"responsibility"`.
2. `artifact.py` — `LayerRow.description`; `_layer_rows` fills it; `render_overview` prints it;
   `manifest_dict`/`as_dict` layer rows carry it.
3. `viewer.py` — `viewer_payload` layer rows carry `description`.
4. `architecture_overview.py` — `_layer_rows` rows carry `description`.
5. `quality_gate.py` — C3 checks `row.description` (was `row.layer`).
6. Tests — new AC1/AC2/AC3/AC5 tests in `test_onboarding_layers.py`; update fixtures/pins that shift
   from directory to responsibility names; update the C3 fixture in `test_onboarding_quality_gate.py`
   to an empty-description row; `layer_report.py` pinned-repo re-measure (AC4).
7. Docs — this working doc, `docs/BACKLOG.md` (status + token row), frontmatter.

### Rejected alternatives
- **Replace dominant-subtree entirely** — rejected (H1): keeping it as fallback confines test churn
  and preserves 104/105 for repos the vocabulary can't name (R7.1).
- **Substring matching** — rejected: `cron`⊂`scronch` false-positives. Exact segment match with
  explicit plural normalisation is deterministic and safe.
- **Description as a separate side-table keyed elsewhere** — rejected: the field belongs on the layer
  row every renderer already iterates (one field, no new abstraction — R1.2).

### Gate 2 — design ✋ (surfaced; proceeding on standing approval).

## Phase 3 — execute (results)
- **`layers.py`** — responsibility vocabulary + `_match_keyword`/`_responsibility_layer`/
  `layer_description`; `assign_layers` responsibility-first, dominant-subtree/direction as fallback;
  `LAYER_METHODS` now three. **`artifact.py`** — `LayerRow.description`, filled + rendered +
  serialized. **`viewer.py`**, **`architecture_overview.py`** — layer rows carry `description`.
  **`quality_gate.py`** — C3 now checks `row.description`. No new file → core count-pins stay 52.
- **Directory-segments-only** matching (not filename stems), so the flip is confined to the six
  dominant-subtree fixtures whose *dirs* matched the vocab; renamed those to non-vocab tokens to keep
  105/104/103's fallback coverage intact. **`description` derives from the layer name** at each
  renderer, so `LayerAssignment`/`refine_layers` are unchanged.
- **AC1 (R6.5):** `test_responsibility_groups_controller_model_view_into_three_layers` — three layers
  where pre-110 dominant-subtree collapsed them under `app`/`x` (method flips `dominant-subtree` →
  `responsibility`). **AC2:** deepest-wins (`service/controller/x` → HTTP/Entry, not Services).
  **AC3:** every emitted layer + direction band + refiner rename resolves to a non-empty description;
  C3 checks it. **AC5:** vocabulary contains no R2.2-denylisted name, all lowercase.
- **AC4 — pinned public repos** (anchor deferred, H6/108), via `scripts/layer_report.py` in Docker:
  | repo | method | layers | Uncategorised |
  |---|---|---|---|
  | laravel/laravel `app` | responsibility | 5 | 6/26 (23%) |
  | symfony/demo | responsibility | 7 | 18/51 (35%) |
  | brick/math | responsibility | 2 | 24/32 (75%) |
  All flip to responsibility. laravel `app/**` now splits into HTTP/Entry + Domain/Data (never a
  collapsed `app`); symfony adds Views. **brick/math is 75% Uncategorised — discussed:** a pure math
  library has no controller/model/service roles, so Uncategorised legitimately dominates. This is the
  "reported, not hidden" signal working as designed, not a defect; `layer_report.py`'s invariant for
  brick is `{Tests, Uncategorised}` accordingly.
- **Delta-green (Docker CI gate):** ruff clean · mypy clean · **1514 passed, 0 failed, 0 skipped**
  (106.72 s). `layer_report.py` passes on all three pinned repos.

## Phase 4 — review (inline, main-loop)
Reviewer subagent + ticket-blind challenger **WAIVED** by run arg. Verdict: **clean (reviewer only —
CHALLENGER: OFF).** R1.1 (generic segment matching — the language-agnostic guard test passes), R1.2
(no new abstraction — `layer_description` is a plain function; description derives from the name),
R1.4 (`layers.py` imports no store), R2.2 (vocabulary is architectural conventions in the *core*,
ratified standard at Gate 0; a unit test denylists framework names), R4.2 (deterministic; byte-stable
tests pass), R7.1 (dominant-subtree kept as fallback, byte-stable test reused for C7), R7.5 (comments
≤ 1 line) all hold. Diff ⊆ approved change list; SCOPE stayed L; branch type `feat` matches.

## Phase 5 — finalise
Docs updated before PR: this working doc, `docs/BACKLOG.md` (status + token row), frontmatter.
Outward actions on standing approval. `/mango:promote` not triggered (no claim's `seen:` crosses 2
ticket keys). Unblocks 111 (tour narrative) and 112 (dataset contract).

### Lesson (durable)
A quality gate's pre-cursor invariant (109's C3 = non-empty layer *name*) is a seam a later ticket
fills: 110 added the `description` field and moved C3 onto it with a one-line change, because 109
shipped C3 pointing at the field 110 would introduce. Writing the gate to the *current* model and
naming its future strengthening in a comment (`110 strengthens to a description`) made the hand-off a
rename, not a redesign.

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| analysis | Explore — layer test/byte-stability surface map | 1 | 95,257 (subagent) |

Main-loop token spend: `unmeasured (host does not surface usage)`. One dispatch, one row.

## Decision log
- Gate 0: R2.2 vocabulary ratified **standard** by the maintainer → full 110.
- H1: responsibility grouping primary, dominant-subtree/direction as fallback.
- AC4 anchor re-measure deferred to an operator run (108 precedent); pinned repos measured here.
