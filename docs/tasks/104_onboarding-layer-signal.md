---
id: 104
slug: onboarding-layer-signal
title: Onboarding — fix the layer collapse (F1): group beneath the dominant subtree (M10)
phase: 3
milestone: M10
status: todo
depends_on: [103]
---

## Why this exists (the shipped defect, not a fresh guess)

Two iterations have now inferred "architectural layer" from the **shape of the file path**, and each
failed on real repos in the *opposite* direction:

- **084** grouped by the **deepest** parent dir → `app/Http/Controllers/Api/UserController.php` became a
  near-singleton layer `.../Api`. **Over-fragmentation.**
- **103** (PR #122, **merged 2026-08-18**) grouped by the **first segment past the longest common dir
  prefix**. Run against a real Laravel tree (8 classes under `app/**` **plus one** `routes/web.php`) it
  collapses the *entire application* into one layer `app`:

  ```
  layers: ('routes', 'app')
    app/Http/Controllers/Api/UserController.php -> 'app'
    app/Models/User.php                         -> 'app'
    app/Services/Billing.php                    -> 'app'   ← Http/Models/Services/Providers all == 'app'
    routes/web.php                              -> 'routes'
  ```
  A single top-level file outside `app/` (every real repo has `routes/`, `config/`, `public/`,
  `bootstrap/`, `database/`, `tests/`) empties the common prefix and flattens the architecture.
  **Under-fragmentation.** Drop the one outlier and it splits correctly — so the output is decided by an
  incidental file, not by architecture.

103 shipped this deliberately as **deterministic-but-limited scaffolding**: `assign_layers` has **no
consumer until 086** (`architecture_overview`, still `todo`), so the defect reaches nothing yet. This
ticket must land **before 086** (086 now depends on 104).

Full evidence + runnable reproduction: `today-i-learned/ai/how-to-create-mango-plugin/Retrospective/2026-08-18_mango-autorun-output-quality-1.md`
(finding F1).

## The signal is decided — this ticket implements it (not "decide again")

The earlier 104 draft asked *which signal a layer should come from at all*. That question has now been
answered empirically by a bake-off over 6 real-shape layouts (Laravel, deep-root `src/App/**`, a
`packages/*/src/**` monorepo, and the flat/2-deep cases 084/103 already covered). Do not re-open it
without new evidence — record the result as the design decision and implement it:

**Chosen — C1, "dominant-subtree".** Group modules **beneath the top-level directory that holds the most
modules** (the *dominant* subtree): strip the common prefix **within** that subtree and layer by its
first remaining segment; every **other** top-level directory becomes its **own** layer. This is the only
candidate that survived all 6 shapes — it splits `app/Http` · `app/Models` · `app/Services` while keeping
`routes/` as its own layer, and it does not collapse the deep `src/App/**` tree.

**Rejected (record in the design doc with these reasons):**
- **C0 — common-prefix + first segment (the shipped 103).** Collapses Laravel `app/**` the moment one
  top-level outlier file exists. This is the defect being fixed.
- **C2 — first-two-segments.** Collapses the deep `src/App/**` layout (everything becomes `src/App`).
- **Namespace declaration (PSR-4 `App\Http\…` from the qname).** Closer to the language's own structure,
  **but** qnames are language-specific, so the derivation would have to live in the adapter/contract,
  never a core branch (R1.1). Deferred: heavier, and C1 already produces the architectural grain from the
  path alone. Revisit only if C1 proves insufficient on the anchor repo (AC2).
- **Dependency topology (condensation / longest-path rank).** Most principled, heaviest; makes "layer"
  mean depends-on depth rather than lives-in dir. Deferred as a possible successor, not this ticket.

## Known residual to handle in this ticket
C1 leaves a **root-level file** (e.g. a top-level `config.php` whose directory prefix is empty) with an
empty-string layer name. Assign it an explicit `"(root)"` layer rather than emitting `""`. Add a fixture
for it.

## Acceptance criteria
- **AC1 (design gate)** — the signal decision above is recorded in the design phase (chosen C1 + the four
  rejected alternatives with why), consistent with R1.1 (no language branch in the core) and R4.2
  (determinism). No grouping code changes before the design gate closes.
- **AC2 (the real-input gate — this is the point)** — the C1 implementation is proven on a **real indexed
  repo** (the anchor PHP monorepo the plan already names), **not** a hand-built fixture. Record the actual
  layer assignment produced and a human judgement that it is architecturally sensible. A green unit suite
  over authored fixtures is **explicitly insufficient** — that is exactly what hid both 084's and 103's
  defects (retro F1). **If the anchor repo is unavailable this session, AC2 is a recorded manual-check
  exclusion and the ticket is `blocked`, not silently passed.**
- **AC3 (regression fixtures)** — add, as unit fixtures *in addition to* AC2, the bake-off shapes that
  broke C0/C2: (a) real Laravel `app/**` + `routes/web.php` does **not** collapse into one `app` layer;
  (b) the deep `src/App/**` tree still splits into Http/Domain/Infra; (c) a `packages/*/src/**` monorepo
  keeps each package distinct; (d) the root-level-file `"(root)"` rule. Fixture coverage alone never
  closes AC2.
- **AC4 (invariants preserved)** — determinism / byte-stability (R4.2), language-agnostic core
  (R1.1/R1.5/R2), the derived-not-listed `LAYER_METHODS` guard (R6.7), comments ≤3 lines, lines ≤100
  chars. The direction-fallback path (flat namespaces) is unchanged.

## Relationship to 103 / PR #122
PR #122 is **merged**. 103 is `done` with a documented known-limitation note pointing here. 104 **replaces
`assign_layers`'s grouping** (the dominant-subtree derivation) rather than extending the direction
fallback. There is no production urgency — nothing calls `assign_layers` until 086 — but 104 is a hard
dependency of 086 so the collapse is fixed before any consumer exists.

## Out of scope
- LLM layer-name refinement (091). 083 metrics substrate (unchanged). The Summarizer seam (085).
- Namespace-declaration and dependency-topology signals (recorded as deferred alternatives above).

## References
- Retro F1 (runnable repro): `.../Retrospective/2026-08-18_mango-autorun-output-quality-1.md`.
- `code_atlas/onboarding/layers.py` (`assign_layers`, `_common_dir_prefix`, `_group_key`, `_by_prefix`).
- 084 `docs/tasks/084_onboarding-layer-assignment.md`; 103 `docs/tasks/103_onboarding-layer-granularity.md`;
  086 `docs/tasks/086_architecture-overview-tool.md` (the gated consumer).
- PLAN §14, §15 (M10). R1.1/R1.5/R2 (language-agnostic core), R4.2 (determinism), R6.7 (derived-not-listed).
