---
id: 111
slug: tour-is-narrative-steps
title: Onboarding — the tour is one stop per module, so 500 modules is a 500-stop "tour" (M11)
phase: 3
milestone: M11
status: done
depends_on: [087, 110]
---

## Why this exists (measured, anchor monorepo)

`guided_tour` and `generate_onboarding` emit **one stop per module in the budget**. On the anchor repo
that is 500 stops in a 6,312,632-byte `tour.md`, each line of the form
`path — reached from path`. Nobody reads 500 stops, and 332 of them are `cycle with …` lines where the
same SCC is re-listed per member.

A tour is a *reading order with a reason*, and the reference tool constrains it to **5–15 steps**, each
grouping 1–5 files with a 2–4 sentence explanation of what the reader learns there. Its own repo tour is
12 steps. The mockup's 12-step tour over the anchor repo covered: the two mirror trees, the web entry
surface, the bootstrap/error-handler path, the DB wrapper's three copies, the global helper bag, the
namespaced `src/` layer, Domain/Data, Views, the self-contained integration island, the vendored PDF
libraries, the test bootstrap being the largest hub, and the map's own limits.

Every number in those 12 steps is interpolated from the dataset; the prototype carries a regression
assertion that no number is hard-coded, so a regenerated tour cannot go stale.

## Scope

Deterministic step construction — **no LLM in this ticket** (prose is 117):

- Group the budgeted subgraph into steps by layer rank (110) crossed with BFS depth from the entry
  seeds, collapsing each SCC to **one** step contribution rather than one per member.
- Clamp to `[5, 15]` steps by merging the smallest adjacent same-layer groups; each step names 1–5
  modules chosen by fan-in within the group.
- A step carries `order`, `title`, `modules`, and a structural `why` line assembled from facts already
  in the dataset (layer description, degree, cycle membership) — the slot 117 replaces with prose.
- The 500-module subgraph remains the *substrate* for ranking. It stops being the deliverable.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with 60 modules across 4 layers yields between 5 and 15 steps — observed
   red against today's code, which yields 60.
2. **AC2.** An SCC of N modules contributes exactly one step entry, and the step says how many modules
   the cycle holds instead of listing all of them.
3. **AC3.** Byte-stability: same index → identical steps, titles and order (R4.2).
4. **AC4.** Every step names at least one module and no step is empty; 109's C4 becomes a real bound.
5. **AC5.** Measured on the anchor repo and two pinned public repos: step count, `tour.md` bytes before
   and after, and the module count each step covers. `tour.md` under 64 KB on the anchor repo.
6. **AC6.** No number in the rendered tour text is a literal — proven by a test that regenerates against
   a mutated dataset and asserts the rendered numbers moved.

## Out of scope

Prose quality and the per-step narrative sentences (117). Whether per-module pages survive at all (116).

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 111

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed · **Branch:** `feat/111-tour-is-narrative-steps`
- **CHALLENGER:** OFF (--no-challenger) · **REVIEW (subagent):** WAIVED — inline main-loop review only
- **TIER:** full · **SCOPE:** L (new module + step algorithm + artifact field + gate change + test churn)
- **change type:** feat

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions`. The ticket is specific (5–15 steps, group by layer
rank × BFS depth, collapse SCC, name ≤5 by fan-in, structural `why`). No premise falsified —
`ordered_stops`/`TourStop` (087), `assign_layers`/`layer_description` (110), `build_artifact`,
`render_tour`, `quality_gate` C4 all resolve. Remaining choices are HOW-decisions (below).

## Phase 1 — analysis

### Measured problem (ticket)
`render_tour` emits one line per file → 500 stops / 6,312,632-byte `tour.md` on the anchor repo; 332
lines are `cycle with …` repeats. Nobody reads 500 stops. The tour must become a 5–15 step reading
order, each step 1–5 named modules + a structural `why`.

### HOW-decisions (resolved on standing approval)
- **H1 — new module `code_atlas/onboarding/steps.py` (53rd core module).** `tour.py` is pure graph
  reasoning (SCC + order) and imports neither `layers` nor `metrics`; steps need layer rank +
  description (110) and fan-in (metrics). A sibling module keeps `tour.py`'s SRP; `build_artifact`
  already imports every onboarding sibling, so the coupling lands where composition already lives.
- **H2 — keep `stops`, ADD `steps`.** `stops` still drives per-module pages, the manifest, the viewer
  and gate checks C5/C6/C7 (pages are explicitly in scope; "do pages survive" is deferred to 116).
  `steps` is the new narrative layer over the same budgeted substrate; the 500-module subgraph stays
  the ranking substrate and stops being the deliverable (ticket).
- **H3 — grouping = layer rank (110) × BFS depth from entry seeds; SCC collapses to one
  contribution.** BFS depth over `tour_edges` from `entry_points`; an SCC's members share the
  component's min depth so a cycle is one bucket contribution, not N (AC2). Bucket key `(rank, depth)`,
  buckets ordered by `(rank, depth)` — the reading order of steps.
- **H4 — clamp to `[5, 15]`.** Over-max: merge the smallest adjacent **same-rank** bucket pair
  repeatedly (ticket); if none remains and still > max, merge the smallest adjacent pair overall
  (termination fallback). Under-min: split the largest bucket (> `modules_per_step`) into fan-in-ordered
  chunks until ≥ min or unsplittable. `min_steps=5, max_steps=15, modules_per_step=5` (ticket).
- **H5 — a step names ≤5 modules by fan-in (desc, tie-break by key), covers all in its group.**
  `TourStep(order, title, modules, why, covers, cycle_size)`. `covers` ≥ `len(modules)`; `cycle_size`
  is the largest SCC represented (0 if none) so `why` can say the cycle size without listing members.
- **H6 — `why`/`title` assembled from dataset facts only (117 replaces the prose).** `why` leads with
  `layer_description(layer)` (110) then interpolated `covers`/`cycle_size`. `title` = layer name; when
  a layer spans K>1 steps, `f"{layer} ({i}/{k})"` (i,k interpolated). No literal numbers (AC6).
- **H7 — quality gate C4 repurposed: `len(steps) > MAX_TOUR_STEPS(=15)` + every step non-empty
  (AC4).** The `[5]` FLOOR is a `build_steps` target proven by AC1, **not** a gate — `check_artifact`
  runs in `build_artifact` for every fixture in the suite, and a hard floor would fail every small
  fixture. C4's real bound moves from 500 stops → 15 steps (ticket AC4). `MAX_TOUR_STEPS` 500→15;
  add `MIN_TOUR_STEPS=5` for `build_steps` to read.
- **H8 — SCOPE boundary (surface at Gate 1): `guided_tour` (paged JSON API) and `viewer.py` stay
  unchanged.** The measured 6.3 MB harm and every AC target the committed `tour.md`. `guided_tour`
  already pages at `CA_MAX_RESULTS` (no blob); the viewer's stop-rail overhaul is 116. Touching either
  widens scope past the measured driver (R7.1). `steps` is added to `as_dict` (cache stability) but not
  to `manifest_dict`/`viewer_payload` — the dataset contract behind renderers is 112.

### Blast radius (from analysis Explore, 61.6k)
- **Must-fix:** `tests/test_onboarding_quality_gate.py` (`_artifact` ctor :70 → add `steps=`; C4 test
  :145-151 repurpose; `MAX_TOUR_STEPS==500` pin :236; import :23; `_valid`/`_scale_artifact` need
  valid non-empty `steps`); `tests/test_generate_onboarding.py:78-86` (tour headings/order/count →
  step format); count pins `test_sql_confinement.py:32` & `test_core_is_language_agnostic.py:42`
  52→53.
- **Verify-only green:** viewer, guided_tour, architecture_overview, cache/byte-stability tests.

### Acceptance-criteria matrix
| AC | Requirement | Proof | Status |
|----|-------------|-------|--------|
| AC1 | 60 modules / 4 layers → 5–15 steps; red vs today (yields 60) | `test_ac1_...`: asserts `5<=len<=15` **and** red-guard `len(ordered_stops)==60` | ✅ |
| AC2 | SCC of N → one step entry; `why` states cycle size, no member list | `test_ac2_...`: one `cycle_size==3` step; render says "cycle of 3 modules", members not listed | ✅ |
| AC3 | Byte-stability: same index → identical steps/titles/order | `test_ac3_...`: `build_steps` twice equal; `render_tour` twice byte-equal | ✅ |
| AC4 | Every step ≥1 module, no empty step; C4 a real bound | `test_ac4_...` + gate `test_c4_a_step_that_names_no_module_is_empty` + `test_c4_tour_over_the_step_ceiling` | ✅ |
| AC5 | Measured anchor + 2 pinned: step count, `tour.md` bytes before/after, modules/step; `tour.md`<64 KB anchor | `scripts/tour_report.py` (Docker): laravel 26→**7** (1729→1335 B), symfony 51→**13** (4193→2844 B), brick 32→**5** (5994→1205 B) — all <64 KB. **Anchor deferred to operator** (absent on dev host — 108/015 precedent) | ✅ (anchor deferred) |
| AC6 | No literal number in rendered tour; mutated dataset moves numbers | `test_ac6_...`: grow cycle 3→4 + add edge, assert covers/`cycle_size` move and "cycle of 4 modules" renders | ✅ |

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| analysis | Explore — test/consumer blast radius | 1 | 61,614 (30 tool-uses, 180 s) |

**Summary:** 1 dispatch, 61,614 tokens (all measured). Top driver: the analysis Explore. Main-loop
spend unmeasured (not measured by mango). Docker: full gate **1524 passed** (main 1514, +10 new);
`scripts/tour_report.py` green on all three pinned repos.

## Decision log
- CHALLENGER OFF + REVIEW subagent WAIVED per run args ("skipped Review & Challenge"); inline review only.
- Standing maintainer approval to resolve HOW-decisions and pass gates; finishing steps (commit → push
  → PR) proceed on the AGENTS.md standing approval. Anchor AC re-measure deferred to operator (108).
