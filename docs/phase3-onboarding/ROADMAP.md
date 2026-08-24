# Phase 3 — Onboarding: roadmap & brainstorm

> **Status: delivered.** Ratified 2026-08-12, folded into [`PLAN.md`](../PLAN.md) §14/§15 and registered
> in [`BACKLOG.md`](../BACKLOG.md) (tasks **083–091**, superseding the old placeholders 022/023).
> **M10, M11 and M12 are all complete**, and the roadmap below is now a record of what was decided
> rather than a set of open questions — every M11/M12 decision point is resolved in place. The plan was
> also **reshaped mid-flight** by tasks **108–117** after a human read the emitted artifact: the page
> dump became one navigable system map (see [`ONBOARDING_MOCKUP.md`](ONBOARDING_MOCKUP.md)).
> **This file does not track status** — [`BACKLOG.md`](../BACKLOG.md) does, under *Open work —
> Pillar 2*. The two quality defects field measurement found on 2026-08-21 were **118** (module
> summaries starved at the seam) and **119** (the reachability split not saying which signal produced
> each count); 119 closed inside 127 on 2026-08-23, which is exactly why a delivered record should
> not carry a live status line.
> **Companion:** [`phase3-roadmap.html`](phase3-roadmap.html) — the same roadmap as a visual
> brainstorming surface (open in a browser). This markdown is the version-controllable source of truth
> and additionally records the architecture-vs-rules placement.
> **Decisions taken 2026-08-11:** audience = human **and** agent · output = markdown-in-repo then a
> static viewer · LLM = deterministic-first, added later. **M10 decisions locked 2026-08-11** (see §4).

## 1. What Phase 3 is

- **Premise.** Search speed was measured false as the selling point (PLAN §19). What the graph
  uniquely holds is *relationships* — and "explain this codebase / where do I start / what are the
  layers" is exactly the relationship question `grep` cannot answer. Onboarding is where that value
  should finally pay off.
- **Not a fork of Understand-Anything** — a *consumer* of the graph you already have, at higher
  fidelity than tree-sitter. Multi-language "for free" later; validated on **PHP now** (the only
  adapter today).
- **Done means:** onboarding tools + committable markdown + a viewer work on a real PHP repo; the core
  stays deterministic (LLM out of core **and** CI, proven by a stub); no PHP-specific logic; and the
  onboarding question-class beats hand-mapping on tokens-to-answer — or we narrow the scope in writing
  (same §19 discipline that recorded the founding premise as false).

## 2. The mechanism — one clean split

```
 [core · deterministic]      [enrichment · deterministic default]     [presentation]
 SQLite symbol graph  ──▶  metrics · layers · summaries (one seam)  ──▶  tools (JSON) · markdown · viewer
 (ships today)                        │
                                      ▼
                          [M12 · opt-in · OUT of core + CI]
                          LLM summarizer behind the seam
```

The core computes, enrichment interprets, presentation renders. The only stage that may touch an LLM
is the last-added one (M12), and it lives **outside** the core. The deterministic path (M10/M11) stands
alone with zero LLM.

## 3. Architecture placement vs the rules

| Rule | How Phase 3 honours it |
|---|---|
| **R4 / R4.1** — core deterministic, no LLM/network | Deterministic enrichment (`metrics`, `layers`, structural `summary`) may live under `code_atlas/onboarding/` — same precedent as `enrichment.py` (optional, off by default, no LLM). The **LLM** summarizer is a separate impl injected through one `Summarizer` Protocol seam and lives **outside** `code_atlas/` (proposed `onboarding_llm/`, mirroring `adapters/`). CI stubs the seam. |
| **R1.1** — zero language branches | No `if language == …`; layering is driven by graph shape + generic namespace/dir strings. The existing CI grep-gate (`tests/test_core_is_language_agnostic.py`) already covers any new file under `code_atlas/`. |
| **R1.2** — one seam, YAGNI | Two enrichment seams, each forced by the same hard rule (R4.1 pushes the LLM out of core), not speculation: the `Summarizer` Protocol (085/090) and the `LayerRefiner` Protocol (091). Each has a deterministic in-core default (structural summarizer; identity refiner) **and** an LLM implementer shipping with it, so neither is a dead abstraction (R7.4); no registry — the entry point injects them with one `if opted-in` each. |
| **R1.4 / SQL confinement** | All SQL stays in `store.py` (guarded by `tests/test_sql_confinement.py`); onboarding modules call the store's read API, never embed SQL, never parse, never write. |
| **R4.3** — never load the whole graph | Metrics are SQL `GROUP BY` aggregates (one row per node, not per edge). Whole-graph work (SCC) is node-budgeted, the pattern `impact`/`reach` already use. |

`enrichment.py` is **not** this seam — it is deterministic framework-indirection rules (tasks 040/062).
The onboarding LLM seam is new and named differently.

## 4. Milestones

Dependency order: **M10 → M11 → M12**.

### M10 — `architecture_overview` + layers (deterministic)

Assign modules to architectural layers and expose them as an agent-facing overview, with zero LLM.

| ID | Task |
|----|------|
| 083 | Graph-metrics foundation — fan-in/out, entry points, dependency direction (read-only SQL in `store.py`). |
| 084 | Layer assignment — namespace/dir heuristic refined by dependency direction; graph-metric fallback for flat legacy trees. |
| 085 | Summarizer **seam** (Protocol) + deterministic default; a CI test proves the graph→enrichment→presentation split with the middle stubbed. |
| 086 | The `architecture_overview` tool — JSON layers + modules + metrics; carries `index_root` and reason codes. |

**Decisions — LOCKED 2026-08-11:**
1. **Module unit = file path** (per-symbol = qname). Matches how `impact`/`include_graph` aggregate;
   flat PSR-0/global legacy namespaces make a namespace-unit unreliable.
2. **SCC / cycle membership deferred to 087** with its own node budget. 083 stays cheap SQL aggregates
   → R4.3-clean.
3. **Entry-point = zero-inbound roots** — pure, deterministic, no config knob. 087 may additionally
   seed from config for a rooted walk.
4. **Layering = namespace/dir prefix refined by dependency direction, with a pure dependency-direction
   fallback** when namespaces are uninformative. Do **not** block on the LLM; 091 is an optional
   refinement. Measure layer quality on the anchor repo before trusting layer names.

### M11 — `guided_tour` + markdown docs + viewer

A dependency-ordered walk and committable onboarding docs, plus a small offline viewer.

| ID | Task |
|----|------|
| 087 | The `guided_tour` tool — topological walk seeded from entry points, cycle-safe via SCC condensation (**SCC lands here**). |
| 088 | `generate_onboarding` — emit committable markdown (overview · tour · per-module) + a `manifest.json`. |
| 089 | Static HTML viewer — one self-contained, theme-aware file reading the manifest; no server, no external deps. **Shipped:** `docs/onboarding/index.html` emitted by `generate_onboarding`; payload embedded (no `file://` fetch). |

**Decision points — M11:**
- **Artifact location** — **locked by 088, versioned by 145:** markdown + `manifest.json` committed under
  `docs/onboarding/`; versioned `artifact.json` under `.code-atlas/onboarding/` (gitignored).
- **Tour granularity & length** — **locked by 087:** file-level stops; walk bounded by
  `CA_IMPACT_MAX_NODES`. 088 reuses that budget for per-module pages.
- **Coherence is not falsifiable** (task-023 note) — CI asserts *structure* only (sections present,
  dependency order respected, deterministic given a fixed stub); coherence = a recorded manual check,
  not a gate.

### M12 — LLM enrichment (opt-in, deferred)

Real prose summaries and layer-name refinement behind the M10 seam — deferred until the deterministic
path is proven and measured.

| ID | Task |
|----|------|
| 090 | LLM summarizer behind the 085 seam; content-hash cache so runs replay and diffs stay stable; opt-in config; never in the per-PR gate. **Shipped:** `onboarding_llm/` package + `code-atlas-llm` entry point (opt-in via `CA_ONBOARDING_SUMMARIZER`); the core imports no LLM. |
| 091 | LLM layer refinement — better layer names where namespaces are uninformative (optional). **Shipped:** `LLMLayerRefiner` behind a new 091 `LayerRefiner` seam in `layers.py`, injected via `code-atlas-llm` (opt-in `CA_ONBOARDING_LAYER_REFINER`); renames only the weak dependency-direction bands (module *boundaries* left to a follow-up); own content-hash cache; the core imports no LLM. |
| 117 | LLM prose for the map — layer descriptions, tour-step narratives and the wording of the headline facts. **Shipped:** one `ProseWriter` seam (`code_atlas/onboarding/prose.py`) with one method for all three slots, `LLMProseWriter` behind it in `onboarding_llm/` (opt-in `CA_ONBOARDING_PROSE`); headline *candidates* derived in `onboarding/headlines.py` so enrichment words the map and never changes it; filler refused by 109's C1, a failure degrades to the structural sentence, and spend is capped per slot at 33 calls a build. `DATASET_VERSION` 6. |

**Decision points — all resolved as built:**
- **Provider / model — Claude, one tier.** `claude-sonnet-5` is the default for every slot
  (`CA_ONBOARDING_LLM_MODEL` / `_LAYER_MODEL` / `_PROSE_MODEL` override per seam). The "top tier for the
  layer pass" half of the recommendation was dropped with the pass itself: 117 measured that 091's
  rename seam fires on nothing once 110 names layers by responsibility.
- **Determinism & cost — as proposed, and bounded by construction.** Content-hash caches per seam,
  committable, sorted-key JSON, no timestamps; on demand, never in the per-PR gate; the ceiling is
  derived (6 headline families + 12 layers + 15 tour steps = **33 calls a build**) and enforced per slot.
- **Seam shape — in-process Protocol, no sidecar.** Three seams, each with a deterministic in-core
  default and one implementer in `onboarding_llm/`; the core imports no LLM (CI grep-gate R4.1).

## 5. How we'll know it earned its cost

> **Measured on 2026-08-23 (task 121), and it is a split verdict.** This section specified the gate —
> an **onboarding question-class** in the tokens-to-answer harness (034/045) plus the recall gate
> (055), baselined against `grep`+`Read` — and for three milestones it was never added. It now holds
> **twelve** questions (`tier: onboarding`): ten on the committed fixture
> `tests/fixtures/php/onboarding`, two on the pinned `symfony/demo`, every ground truth read out of
> the source by hand before the tools ran. Numbers, both halves:
> [`../benchmarks/121_onboarding-question-class.md`](../benchmarks/121_onboarding-question-class.md).
>
> **Earned:** 12/12 correct, recall 1.0, `confidently_wrong` 0; **1.58 / 1.34 / 1.01** on the fixture
> and **4.66** on `symfony/demo` for the three questions a grep baseline can fairly answer, moving the
> fixture aggregate 0.29 → **0.789**. Nine questions have no fair baseline and each states why rather
> than carrying an invented one.
>
> **Not earned — and this section promised to say so:** on a canonical real repo the **reading order
> was wrong** — lint and bootstrap opened the tour. ~~`guided_tour`'s first five were a lint config,
> two bootstrap configs and an importmap; front controller fifth.~~ **131 closed** — re-measured first
> five open on controllers and include `public/index.php`. ~~The
> `web_entry` count calls 8 files the web surface when 4 are test controllers.~~ **130 closed.**
> Tickets
> [131](../tasks/131_tour-ranks-configuration-ahead-of-the-front-controller.md),
> [130](../tasks/130_web-entry-bucket-counts-test-controllers.md), and
> [129](../tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) (a silent zero
> found while establishing ground truth).
>
> **Scope narrowed accordingly**, per this section's own instruction: the onboarding layer is measured
> as a **navigation and provenance aid — which files, which layer, what depends on this, which
> declaration claimed that count — not as a curated syllabus.** A dependency walk still is not the
> hand reading order (kernel / entity / repository). **143** put a mermaid layer graph in the
> committed markdown (a lookup); auto-generated *syllabi* stay behind that line. Class diagrams are
> [144](../tasks/144_class-diagram-is-a-projection-minus-the-return-type.md).

Gate the phase on the harness, not on vibes. Add an **onboarding question-class** to the
tokens-to-answer harness (034/045) and the recall gate (055). Baseline = `grep`+`Read` with an agent
building the map by hand.

Questions: *"top-level layers & their dependencies?"* · *"entry point + first 5 things to read?"* ·
*"what depends on module X?"* If the tools do not beat hand-mapping on this class, say so in writing
and narrow the scope.

**All three shipped as questions, and the middle one is the one that failed** — which is why the
narrowing above is written in this section rather than argued away. The class also runs seven shapes
§5 did not name (dead code, feature files, request entry, declared-entry provenance, the committable
map, naming debt, blast radius); the two shapes no committed tier can measure — mirror subtrees and a
named business screen on a tree nobody can hold in their head — ship as a **local-tier template** in
[`../runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) for an operator with such a repo.

## 6. Risks & sequencing

| Risk | Mitigation |
|---|---|
| Layering on flat-namespace legacy PHP (the anchor repo is the hard case) | Dependency-direction fallback when namespaces are uninformative; consider LLM refinement (091) before trusting layer names. |
| LLM cost & nondeterminism (fights R4) | Deterministic-first; content-hash cache; never in the per-PR gate. |
| SCC is whole-graph vs R4.3 | Node-budgeted traversal in the tour (087), the pattern impact/reach already use. |
| "Multi-language for free" but only PHP exists | Onboarding ships on PHP; enforce language-agnostic by design (no PHP strings, CI grep-gate) even with one adapter. |
| Sequencing vs the Phase 1.5 tail (074–082) | M10 is read-only over the graph → can run **in parallel**. Recommend closing 074 (does the index harm mechanism answers) and 077 (name the revision) first, since narratives inherit any graph-trust defect. |

## 7. Task breakdown

| Task | One-liner | Stage | Depends on |
|------|-----------|-------|-----------|
| 083 | Graph-metrics foundation — fan-in/out, entry points, direction (read-only SQL) | M10 · deterministic | 014, 031, 017 |
| 084 | Layer assignment — heuristic + dependency-direction refine; graph-metric fallback | M10 · deterministic | 083 |
| 085 | Summarizer Protocol seam + deterministic default; CI stub test for the split | M10 · deterministic | 083 |
| 086 | `architecture_overview` tool — JSON layers + modules + metrics | M10 · tool | 084, 085 |
| 087 | `guided_tour` tool — topo, entry-seeded, cycle-safe (carries SCC) | M11 · tool | 083, 086 |
| 088 | `generate_onboarding` — committable markdown + `manifest.json` | M11 · docs | 084, 086, 087 |
| 089 | Static HTML viewer — self-contained, reads the manifest | M11 · viewer | 088 |
| 090 | LLM summarizer behind the 085 seam — Claude; content-hash cache; opt-in; out of core/CI | M12 · opt-in | 085, 088 |
| 091 | LLM layer refinement — better names/boundaries where namespaces are weak | M12 · opt-in | 084, 090 |

## 8. Next steps

1. **Brainstorm the M11 and M12 decision points** (§4) — M10 is locked. *(still open)*
2. ~~**Fold this roadmap into [`PLAN.md`](../PLAN.md) §14/§15** and add 083–091 to
   [`BACKLOG.md`](../BACKLOG.md) once ratified (R7.2).~~ **Done 2026-08-12** — PLAN §14/§15 folded,
   BACKLOG rows 083–091 registered (022/023 removed). The stub tasks in [`docs/tasks/`](../tasks/)
   carry `status: todo` and this proposal is their source.
3. **Then** run each ticket through the mango lifecycle (`/mango:solve 083` …), M10 first.
