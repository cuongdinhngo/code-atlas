---
id: 117
slug: llm-prose-for-map
title: Onboarding — the map's structure is derivable, its prose is not; route prose through the seams (M12)
phase: 3
milestone: M12
status: done
depends_on: [110, 111, 090, 091]
---

## Why this exists (measured, anchor monorepo)

The deterministic summarizer had nothing to read: **500 / 500** emitted pages carried `Summary: (none)`,
because `artifact.py` passed blank `NodeFacts` — the graph carries no doc field, so the seam was
starved on every repo (**118**, done). The anchor repo *does* have docblocks; read-through now feeds
them at build time. Structure is fully derivable;
meaning is not. In the reviewed mockup, exactly three things were written by hand — and they were the
three things the reviewer called the most valuable content on the page:

1. the one-line description per layer (12 of them),
2. the wording of the six headline facts a newcomer must know first,
3. the 12 tour step paragraphs.

Everything else on that page — every count, the matrix, hubs, treemap, mirror figures, reachability split,
module table, and **every number interpolated into the tour text** — came from the index.

The reference tool reaches the same split from the other direction: its per-file `summary`, `tags` and
`complexity` are LLM-produced at analysis time, and its tour is an LLM narrative *over* pre-summarised
nodes. Its structural phase (fan-in/fan-out ranking, entry-point scoring, BFS depth, clusters) is what
code-atlas already does better.

## Scope

Prose only, through the seams that already exist — **no new abstraction** (R1.2), no LLM in the core (R4):

- **Layer descriptions** via the 091 `LayerRefiner` seam, extended from renaming weak layers to also
  producing a one-line responsibility description. Input is structural facts only (member paths, degree
  mix, class/method composition) — never file contents at this stage.
- **Tour step narratives** via a seam on 111's step slot: each step gets 2–4 sentences that reference the
  previous step, given the step's modules, their summaries, layer descriptions, and degrees.
- **Headline facts**: derive the *candidates* deterministically (mirror overlap, hub concentration,
  abstraction ratio, confidence share, reachability split), then let the seam write the sentence. The
  candidate set is structural; only the wording is generated.
- Content-hash caching, sorted-key JSON, no timestamps — same discipline as 090/091, so a rename is a
  cache hit and results can be committed to replay without calling a model.
- Off by default. With both switches unset the map renders with structural defaults and stays complete.

## Acceptance criteria

1. **AC1.** With the seams unset, output is byte-identical to the 116 deterministic map (R4.2) — no
   silent dependency on enrichment.
2. **AC2.** With the seams set, only prose fields differ; every number, ranking and grouping is unchanged.
   Proven by diffing two runs and asserting the numeric fields are equal.
3. **AC3.** Cache hit on a pure rename/reorder; miss on an edit. Cache files are byte-stable.
4. **AC4.** A model failure or timeout degrades to the structural default for that field and the artifact
   still passes 109's gate — never a half-written map.
5. **AC5.** Cost measured on the anchor repo: number of calls and tokens for a cold build and for a warm
   cache, recorded in the working doc. A per-run call ceiling exists and is enforced.
6. **AC6.** Generated prose that merely restates a path or a name fails 109's C1 like any other filler —
   enrichment does not get an exemption from the quality gate.
7. **AC7.** No prompt, no model name and no LLM import appears under `code_atlas/`; it all lives in
   `onboarding_llm/`.

## Out of scope

Per-symbol summaries, and reading file contents to summarise a layer — start with structural inputs and
measure whether that is enough before spending a model on source text.

---

# Working doc — task 117

## Session status

- **Phase:** 5 (finalise) — Gates 1 and 2 ratified; review waived by the run's arguments;
  delta-green proven in Docker. Committing, pushing, opening the PR.
- **Run args:** `/mango:solve 117 with skipped review & challenge`. `CHALLENGER: OFF (--no-challenger)`;
  reviewer subagent waived by the same argument. Standing maintainer approval to suggest and take the
  best option and to finish through commit + push + PR (AGENTS.md, *Maintainer workflow*).
- **`work_doc_mode`:** `embed` (`.harness.json`) — plain local-file ticket, working doc below the
  separator above. Ticket text above the separator is never edited by a phase.
- **`TIER: full` · `SCOPE: L`** — 7 ACs, a new seam, a new core module, a `DATASET_VERSION` bump, a
  quality-gate check, viewer rendering, and a committed cost script.
- **Branch:** `feat/117-llm-prose-for-map` (per `branch_strategy`).

## Phase 0 — refine

**Premise check — every source the ticket cites as already existing resolves:**

| Ticket reference | Resolves to |
|---|---|
| 091 `LayerRefiner` seam | `code_atlas/onboarding/layers.py:333` `refine_layers` + the `LayerRefiner` Protocol |
| 090 `Summarizer` seam / cache discipline | `onboarding_llm/summarizer.py`, `onboarding_llm/cache.py` |
| 111's step slot | `code_atlas/onboarding/steps.py:244` `_why` — "117 replaces it with prose" |
| 109's gate, C1 | `code_atlas/onboarding/quality_gate.py:66` |
| `StructuralSummarizer` emits `Summary: (none)` without a docblock | `code_atlas/onboarding/summary.py` |

No `PREMISE FALSIFIED`. Three unresolved decisions were exposed, so this is the **ticket-refine**
path (single deliverable, not an epic).

**Exposure-checker dispatch: not run.** The run's arguments waive review and challenge, and this
session's standing instruction is not to dispatch subagents unrequested. Recorded as a deliberate
waiver, not an omission — 0 dispatches this run, so the cost ledger below carries 0 rows.

## Phase 1 — analysis

### Measured on this host, before any design was chosen

Three pinned public repos (`artifacts/cross-repo-cache/`, already indexed), through the real
deterministic pipeline — `compute_metrics` → `assign_layers` → `ordered_stops` → `build_steps`:

| pin | files | modules | layer method | layers | **weak layers** | stops | **steps** |
|---|---|---|---|---|---|---|---|
| `brick_math` | 32 | 32 | responsibility | 2 | **0** | 32 | 5 |
| `laravel_app` | 26 | 26 | responsibility | 5 | **0** | 26 | 7 |
| `symfony_demo` | 51 | 51 | responsibility | 7 | **0** | 51 | 13 |

**The load-bearing finding: the weak-layer count is zero on every pin.** Task 110 made
`responsibility` the primary method, and it names every layer from the path vocabulary, so
`LLMLayerRefiner._WEAK` (`{source, sink, mixed, isolated, (root)}`, `layer_refiner.py:34`) matches
nothing. The 091 rename seam is *live code that no longer fires on a normally-shaped repo*.

This falsifies the ticket's routing bullet, not its goal. The ticket asks for "the one-line
description per layer (12 of them)" — **every** layer, weak or not. `LayerRefiner` is gated on
weakness by construction, so hanging descriptions off it would deliver them for zero layers on all
three pins. Surfaced, not absorbed (see the HOW-decisions below).

### The prose slot count is already bounded by existing caps — so AC5's ceiling is derived, not invented

| slot | bound | source |
|---|---|---|
| layer descriptions | 12 under `responsibility` | `layers.py` `_VOCABULARY` (11 layers) + `UNCATEGORISED` |
| tour-step narratives | 15 | `quality_gate.MAX_TOUR_STEPS` (109 C4) |
| headline facts | 6 | one per structural candidate family (below) |

`12 + 15 + 6 = 33` calls is the cold-build ceiling for a repo under `responsibility`. Under the
`dominant-subtree` fallback the layer count is **unbounded** (`architecture_overview.py` docstring:
"a monorepo can yield hundreds"), so the ceiling must be enforced by the seam rather than assumed
from the vocabulary. Cold-build calls on the pins: 13 / 18 / 26.

### The six headline candidate families, all already in the 112 dataset

`mirrors.pairs[0].overlap` (115) · hub concentration from `hubs[0].fan_in` against `edge_counts` ·
abstraction ratio from `node_counts` · `confidence` share below `EXACT` · `reachability` buckets
(113) · `modules.coverage` percent (114). Every one is a bounded field of the existing dataset, so
the candidate set needs no new store query — only pure derivation.

### HOW-decisions (resolved on standing approval, each cited)

1. **One unified prose seam, not "extend `LayerRefiner` + add a narrator".** The ticket routes layer
   descriptions "via the 091 `LayerRefiner` seam, extended". **Deviation, recorded:** the measurement
   above shows that seam is weakness-gated and fires zero times, and the ticket's own headline
   constraint is *no new abstraction* (R1.2). A single `ProseWriter` Protocol with one method serves
   all three slots — so the filler guard (AC6), the failure degradation (AC4) and the per-run call
   ceiling (AC5) each exist **once** instead of twice. Splitting them would put the ceiling in two
   places, which is the defect R7.1 warns about. `LayerRefiner` is left untouched.
2. **AC1 cannot mean "the same bytes 116 emitted".** The Scope requires that with the switches unset
   "the map renders with structural defaults" — structural default headline sentences are *new
   deterministic content*, so the map's bytes necessarily move. `ASSUMED (awaiting ratification):`
   AC1 is read as **the deterministic path is complete and reproducible** — with the seam unset the
   output is byte-identical run-to-run and identical to explicitly passing the identity impl, and no
   field depends on enrichment. The byte-delta against 116 is intended and versioned by
   `DATASET_VERSION 5 → 6`. **This is the one item that changes what gets built if you read it
   differently** — see Gate 1.
3. **AC5's anchor number, measured here rather than deferred.** Precedent 113–116: a committed
   re-runnable `scripts/*_report.py`. Calls and tokens are countable **without a model** — a counting
   fake client over an anchor-scale synthetic dataset gives an exact call count and an exact prompt
   token estimate (`scripts/viewer_report.py`'s synthetic-anchor trick, 116). So AC5 lands as a real
   number now, with the live-model row still available to the maintainer behind an env switch.
4. **Filler is rejected twice, and the two are not redundant.** AC6 wants filler to fail 109's C1;
   AC4 wants a bad model response to degrade, not brick the build. Both: the seam discards filler and
   falls back (normal operation), *and* the gate independently enforces it, so no impl can smuggle
   filler past (R6.5 — the gate is the backstop, not the happy path).

### Blast radius

| touched | why |
|---|---|
| `code_atlas/onboarding/prose.py` (new) | the `ProseWriter` Protocol, the request shape, the filler predicate, the ceiling |
| `code_atlas/onboarding/headlines.py` (new) | deterministic headline candidates + their structural sentences |
| `code_atlas/onboarding/layers.py` | `layer_descriptions()` helper beside `refine_layers` |
| `code_atlas/onboarding/steps.py` | `build_steps` takes the writer; `_why` becomes the default |
| `code_atlas/onboarding/dataset.py` | `headlines` field, `DATASET_VERSION` 5 → 6, writer wired |
| `code_atlas/onboarding/artifact.py` | descriptions + step prose flow into the markdown renderers |
| `code_atlas/onboarding/quality_gate.py` | C1 extended over layer/step/headline prose |
| `code_atlas/onboarding/viewer.py` | the headline strip in the overview section |
| `code_atlas/main.py`, `tools/generate_onboarding.py`, `tools/architecture_overview.py` | the third injection point |
| `onboarding_llm/prose.py` (new), `__init__.py`, `server.py` | the LLM impl + its own switch |
| `scripts/prose_cost_report.py` (new) | AC5's evidence |
| tests, docs, CI | below |

Out of scope, per the ticket: per-symbol summaries; reading file contents to describe a layer.

### Acceptance-criteria matrix

| AC | claim | proof | risk if wrong |
|---|---|---|---|
| AC1 | seam unset ⇒ complete, reproducible deterministic output | two-run byte equality + identity-impl equality over dataset JSON, viewer HTML, `overview.md`, `tour.md` | silent LLM dependency |
| AC2 | seam set ⇒ only prose differs | diff two runs, assert every non-prose field of `as_dict()` equal | enrichment moves a number |
| AC3 | rename/reorder ⇒ hit; edit ⇒ miss; cache byte-stable | raising client on the second run; key-change test; JSON re-read | non-replayable builds |
| AC4 | failure/timeout ⇒ structural default, gate still passes | raising / timing-out / empty client; `check_artifact` green | half-written map |
| AC5 | cold + warm call and token counts recorded; ceiling enforced | `scripts/prose_cost_report.py` + a ceiling test over an over-budget dataset | unbounded spend |
| AC6 | generated filler fails C1 | writer returning a path ⇒ discarded; gate raises when fed directly | prose exemption |
| AC7 | no prompt / model name / LLM import under `code_atlas/` | filesystem sweep test + CI grep-gate | confinement breach |

**Gate 1 — analysis. ✋ Awaiting your approval.** One item genuinely needs your call: HOW-decision 2
(AC1's reading). HOW-decision 1 is a recorded deviation from the ticket's routing bullet, justified by
the zero-weak-layer measurement.

**Gate 1: ratified** ("approve"). HOW-decision 2's `ASSUMED` tag is discharged — AC1 is the
reproducibility claim, and the byte-delta against 116 is intended and versioned.

## Phase 2 — design

### Approach — one seam, one request, one budget

```
                      ┌─ layers.layer_descriptions() ──┐
generate_onboarding ──┤  steps.build_steps()           ├─→ ProseRun ──→ ProseWriter (Protocol)
  (one ProseRun)      └─ headlines.headline_candidates()┘      │              │
                                                              │              └─ onboarding_llm/prose.py
                                          memoised per request│                 (the only impl)
                                          + counted + capped ─┘
```

`ProseRun` is the **one** place that (a) memoises a request so the artifact and the dataset building
the same layer table cost one call, not two, (b) counts calls, (c) enforces the ceiling, (d) catches
a seam failure, and (e) rejects filler. Every one of AC3–AC6 therefore has exactly one home.

### `code_atlas/onboarding/prose.py` (new) — the seam and its guards

| name | role |
|---|---|
| `SLOT_HEADLINE` / `SLOT_LAYER` / `SLOT_STEP` | the three slots, as constants |
| `ProseRequest(slot, key, default, facts, previous)` | frozen; `default` is the complete structural sentence, `facts` is `(label, value)` pairs, `previous` chains the step narrative |
| `ProseWriter` Protocol — `write(request) -> str` | returns `""` to decline; an impl lives outside `code_atlas/` (R4.1) |
| `is_filler(text, *names)` | true when blank, or when **every** alphanumeric token of `text` already appears in `names` (path/camel/underscore-split) — 109 C1's "no fact beyond its own path", applied to prose |
| `ProseRun(writer, limit=MAX_PROSE_CALLS)` | `.text(request)`, `.calls`, `.declined` |
| `MAX_PROSE_CALLS = 33` | pinned by a **derived** test, not re-listed: `len(_VOCABULARY)+1 + MAX_TOUR_STEPS + len(HEADLINE_FAMILIES)` (R6.7) |

`ProseRun(None)` returns `request.default` for every request, makes zero calls, and is what the
deterministic path uses — so AC1's off path is identity by construction, not by discipline.

`prose.py` imports nothing from `code_atlas.onboarding`, so it can be imported anywhere without a
cycle. It holds **no prompt and no model name** (AC7).

### `code_atlas/onboarding/headlines.py` (new) — candidates are derived, only wording is written

`headline_candidates(*, node_counts, confidence, edges_total, layers, hubs, reachability, modules,
mirrors) -> tuple[Headline, ...]`, taking primitives and returning a frozen report — the same shape
`mirrors.py`, `modules.py` and `reachability.py` already use. Six families, each emitted **only when
its structural precondition holds**, so an absent fact yields no sentence rather than a hollow one:

| key | precondition | the number it states |
|---|---|---|
| `duplication` | a mirror pair exists | shared relative paths + Jaccard overlap (115) |
| `concentration` | a hub exists | top hub's dependents as a share of all dependencies |
| `abstraction` | both type- and callable-kind counts > 0 | type-declaring vs callable symbols |
| `confidence` | any tier below `EXACT` | share of dependencies resolved heuristically |
| `reachability` | a zero-inbound bucket exists | total + the largest population (113) |
| `coverage` | `modules.total > 0` | files under a named capability (114) |

The type/callable split comes from two **new named subsets in `contract.py`** — `TYPE_KINDS`,
`CALLABLE_KINDS` — beside the existing `CALLER_KINDS`/`IMPL_KINDS`, whose comment already says
"consumers import these; do not re-list kinds". A named subset of existing kinds is not a vocabulary
change, so `CONTRACT_VERSION` stays at 5 (R3).

### Where each slot's prose enters

| slot | producer | default | consumers |
|---|---|---|---|
| layer description | `layers.layer_descriptions(assignment, metrics, run)` | `layer_description()` (110) | `artifact._layer_rows`, `dataset._layer_stats`, `architecture_overview` |
| step narrative | `steps.build_steps(..., prose=run, docline_of=...)` | `_why()` (111) | `render_tour`, the artifact cache |
| headline | `dataset.build_dataset` via `headline_candidates` | the structural sentence | `index.html`, `render_dataset_overview` |

Step prose is applied in step order with the **previous step's final prose** as `ProseRequest.previous`,
so the narrative can reference it — which also makes step N's cache key depend on step N−1's, a chain
that still replays byte-for-byte from a committed cache.

### `DATASET_VERSION` 5 → 6 — one field

`headlines: tuple[Headline, ...]`, serialised as `[{"key", "label", "text"}]`. Nothing else in the
shape moves. The call counters deliberately do **not** go in the dataset: AC2 requires that with the
seam on *only prose fields differ*, and a `calls: 17` field would be a number that moved. They surface
on `generate_onboarding`'s `standard` payload (`prose_calls`, `prose_declined`) instead, which is
where an operator looks, and in AC5's script.

### 109's gate covers all three slots (AC6) — and the seam rejects filler first (AC4)

- `check_artifact` C1 gains: a layer description that only restates its layer name, and a step
  narrative that only restates its title and modules, each raise `QualityGateError("C1", …)`.
- `check_dataset(dataset)` is added for the headline slot, called from `build_dataset` by a deferred
  import (the same cycle-break `artifact.py` already uses for `check_artifact`).
- The structural defaults were checked against `is_filler` by hand for every case, including the
  `f'Modules grouped under "{layer}"'` fallback and an empty layer name: each carries at least one
  token outside its own name, so the gate is not vacuous and cannot trip on the off path.
- **The two are not redundant.** `ProseRun` discards filler and falls back, so a bad model response
  degrades (AC4). The gate then independently refuses filler from *any* impl, including one nobody
  here wrote (R6.5 — the gate is the backstop, never the happy path).

### `onboarding_llm/prose.py` (new) — the only impl

`LLMProseWriter` mirrors 090/091 exactly: lazy `anthropic` in the factory, a per-slot system prompt,
`MAX_TOKENS = 2048`, `PROMPT_VERSION`, and a `ContentHashCache` keyed on
`(slot, key, default, facts, previous, model, prompt_version, system, max_tokens)` — the full facts
fold into the key while the prompt shows a capped list (091's pattern), so two slots differing past
the cap get distinct entries. Switch `CA_ONBOARDING_PROSE=llm|claude`; model
`CA_ONBOARDING_LLM_PROSE_MODEL` (default `claude-opus-5` — prose is the highest-judgment slot, PHASE3
§4's top tier); cache `CA_ONBOARDING_LLM_PROSE_CACHE` (default
`.code-atlas/onboarding-llm-prose.json`, point it at a tracked path to commit and replay).

`build_server(config, summarizer, layer_refiner, prose_writer)` gains the third injection point,
threaded to `architecture_overview.create` and `generate_onboarding.create`.

### AC5 — the ceiling is structural, so the cost is bounded independently of repo size

| slot | cap | source |
|---|---|---|
| layers | 12 | 110's `_VOCABULARY` (11) + `UNCATEGORISED` |
| steps | 15 | `quality_gate.MAX_TOUR_STEPS` (109 C4) |
| headlines | 6 | the six families above |

A repo falling back to `dominant-subtree` can emit hundreds of layers, so the ceiling is **enforced**
by `ProseRun`, not assumed: requests are served in a fixed order (headlines → layers by rank → steps
by order) until `limit`, after which every remaining slot keeps its structural default. Deterministic
given the limit. `scripts/prose_cost_report.py` records cold and warm calls, prompt bytes, and a
labelled char/4 token estimate for each pin and for an anchor-scale synthetic; a live-model row is
available behind an env switch so the estimate is never mistaken for a measurement.

### Rejected alternatives

| rejected | why |
|---|---|
| extend `LayerRefiner` with `describe_layers` (the ticket's routing) | weakness-gated — 0 of 14 pin layers qualify; and it puts the ceiling and the filler guard in two places |
| three Protocols, one per slot | three copies of AC4/AC5/AC6's guards; R1.2/R7.1 |
| `headlines` derived in the browser from the dataset | the LLM must be able to rewrite the sentence, so it has to be in the payload |
| put `calls`/`declined` in the dataset | a number that moves when the seam turns on — breaks AC2 |
| a wall-clock timeout in the core | no network in the core (R4); a timeout surfaces as the exception AC4 already degrades |

### Change list (traced to matrix rows)

| # | file | AC |
|---|---|---|
| 1 | `code_atlas/onboarding/prose.py` (new) | AC1, AC4, AC5, AC6, AC7 |
| 2 | `code_atlas/onboarding/headlines.py` (new) | AC2, AC6 |
| 3 | `code_atlas/contract.py` — `TYPE_KINDS`, `CALLABLE_KINDS` | AC2 |
| 4 | `code_atlas/onboarding/layers.py` — `layer_descriptions()` | AC1, AC2 |
| 5 | `code_atlas/onboarding/steps.py` — prose pass | AC1, AC2 |
| 6 | `code_atlas/onboarding/dataset.py` — `headlines`, version 6 | AC1, AC2 |
| 7 | `code_atlas/onboarding/artifact.py` — descriptions + step prose | AC1, AC2 |
| 8 | `code_atlas/onboarding/quality_gate.py` — C1 over prose, `check_dataset` | AC6 |
| 9 | `code_atlas/onboarding/viewer.py` — the headline strip | AC2 |
| 10 | `code_atlas/main.py`, `tools/generate_onboarding.py`, `tools/architecture_overview.py` | AC1, AC5 |
| 11 | `onboarding_llm/prose.py` (new), `__init__.py`, `server.py` | AC3, AC4, AC7 |
| 12 | `scripts/prose_cost_report.py` (new) | AC5 |
| 13 | `tests/test_onboarding_prose.py`, `test_onboarding_headlines.py`, `test_onboarding_llm_prose.py` (new) | all |
| 14 | `tests/test_onboarding_quality_gate.py`, `test_onboarding_dataset.py`, `test_onboarding_viewer.py`, `test_onboarding_steps.py` | AC1, AC2, AC6 |
| 15 | `.github/workflows/ci.yml` — AC7 grep-gate | AC7 |
| 16 | docs: PLAN, BACKLOG, CONVENTION, README, LESSONS, ONBOARDING_MOCKUP, this ticket | docs-before-PR |

### Rule compliance

R1.1 no language branch — the new modules read contract kinds, never a language. R1.2 one seam —
one Protocol, one method, and `LayerRefiner`/`Summarizer` untouched. R1.4 SRP — no SQL in the new
modules; `headline_candidates` takes primitives. R2.2 — nothing names a repo, framework or language;
the denylist twin test is written before the module (114/115/116's lesson). R3 — no contract
vocabulary change, `CONTRACT_VERSION` stays 5. R4/R4.1 — no LLM under `code_atlas/`, proven by the
existing filesystem sweep plus AC7's. R4.2 — sorted throughout, cache is sorted-key JSON, no
timestamps. R4.3 — every prose list is already a capped list. R6.5 — the proving test is below.
R6.7 — `MAX_PROSE_CALLS` and the headline family set are derived in their pin tests. R7.1 — the
smallest change that gives each AC one home.

### Verification plan

- **Proving test (R6.5, observed red first):** with a `ProseWriter` that returns a distinct sentence
  per slot, `dataset.headlines`, every `LayerStat.description` and every `TourStep.why` carry it —
  and with the writer unset every one of them is the structural default, byte-identical to a second
  run. Red before the seam exists (no `headlines` field, `why` unreachable).
- AC1: two-run byte equality **and** equality against an explicitly-passed `ProseRun(None)`, over
  `dataset_json`, `render_viewer`, `render_overview`, `render_tour`.
- AC2: build twice, once with a writer; assert `as_dict()` equal after blanking prose fields only.
- AC3: second run against a client that raises if called; a changed fact ⇒ a call; cache file
  re-reads byte-identical.
- AC4: clients that raise, time out (`TimeoutError`) and return empty ⇒ defaults everywhere,
  `check_artifact`/`check_dataset` green.
- AC5: `scripts/prose_cost_report.py` numbers recorded below; a ceiling test with `limit=2` proving
  the third slot keeps its default and `declined` counts it.
- AC6: a writer returning a bare path ⇒ discarded by the seam; the same text injected straight into
  the gate ⇒ `QualityGateError("C1", …)`.
- AC7: filesystem sweep over `code_atlas/` for `anthropic`, `onboarding_llm`, `claude-`, and
  prompt markers; plus a CI grep-gate.
- Full suite in Docker (`scripts/docker-test.sh`) — the authoritative gate.

**Gate 2 — design. ✋ Awaiting your approval.**

**Gate 2: ratified** ("approve").

## Phase 3 — execute

### One refinement of the approved design, made during execute

**Per-slot ceilings instead of one pooled 33-call ceiling.** The approved design served requests in
a fixed priority order (headlines → layers → steps) until the pool ran out. Two problems surfaced
while wiring it: the natural composition order is layers → steps → headlines (the artifact builds
before the dataset), so headlines would have been starved first; and with a `dominant-subtree`
fallback the layer count is unbounded, so layers would eat the whole pool and leave the tour and the
headlines with nothing. `SLOT_LIMITS = {headline: 6, layer: 12, step: 15}` makes starvation
impossible and makes the ceiling independent of call order. `MAX_PROSE_CALLS` is still 33 — their
sum — and each cap is still derived from its own source. Recorded as a refinement, not a re-scope:
same ceiling, same change list.

### What the measurement said, and where the ticket was wrong

| claim | measured |
|---|---|
| layer descriptions belong on 091's seam | **falsified** — 0 weak layers on 3 of 3 pins, so that seam would describe 0 of 14 layers |
| AC1 = "byte-identical to the 116 map" | **impossible** — the Scope's own structural-default headlines are new deterministic content |
| the ceiling needs a number | **derived** — 6 + 12 + 15 = 33, each from an existing cap |
| the ceiling is enforced | **shown biting** — 1,176 requested, 12 served, 1,164 refused |

### AC5 — the cost, measured (`scripts/prose_cost_report.py`)

```
per-slot ceilings: {'headline': 6, 'layer': 12, 'step': 15}  total 33

### pinned public repos
  laravel_app  @ ff031db: cold 17 (headline 5, layer 5, step  7); warm 0;  7,797 prompt bytes
  symfony_demo @ 03fe256: cold 25 (headline 5, layer 7, step 13); warm 0; 13,389 prompt bytes
  brick_math   @ b61d8e6: cold 12 (headline 5, layer 2, step  5); warm 0;  6,398 prompt bytes

### anchor-scale synthetic — the ceiling is structural, so size does not move it
  18,929 files, named layers:        cold 24; warm 0; 26,261 prompt bytes; declined 0
### the unbounded case the ceiling exists for
  18,929 files, per-directory layers: cold 32; warm 0; 29,495 prompt bytes; declined 1,164
```

Prompt **bytes** are exact; the token figure the script prints is a labelled `char/4` **estimate**,
not a measurement — a live-model row is available to the maintainer behind `CA_PROSE_LIVE`. Warm is
0 on every row: a second identical build through the same run is entirely memo hits. Five of six
headline families fire on the pins — the sixth needs a mirror pair, and 115 measured that none of
these three repos has one.

### Delta-green (authoritative gate: `scripts/docker-test.sh`)

**1671 passed, 0 failed** · ruff clean · mypy clean over **59 source files**. Main baseline 1618, so
**+53 net**, accounted exactly: 43 in the three new test files, +2 in the viewer suite, +2 in the
dataset suite (47 authored), and +6 from tests parametrized over the core-module list (090's
confinement sweep +2, `test_core_is_language_agnostic`'s two sweeps +4, for the two new core
modules). Nothing removed.

### The three findings the gates caught

1. **An AC6 test asserted something false.** It fed a writer returning `"Services"` and expected
   every layer's description to fall back. `"Services"` is filler only for the layer *named*
   Services — for `HTTP / Entry` it adds a word of its own, and C1's rule is "restates what it was
   handed", not "is correct". No mechanical rule can catch a wrong-but-original sentence. The
   fixture became an echo-the-key writer, which is filler in every slot by construction; the
   predicate was kept as written.
2. **The cost report was green without the ceiling ever engaging** (LESSONS 117c). Every realistic
   shape lands under 33, so the report proved the arithmetic and not the enforcement until a row was
   added on the other side of the bound.
3. **The synthetic row understated the headline cost 2/6** because the first version of the report
   handed `build_dataset` empty censuses, and a family only fires when its precondition holds. Fixed
   by passing the store's real rows — the `fixture-shape-begs-the-question` class again.

### Deviations from the approved change list

| # | deviation | disposition |
|---|---|---|
| 1 | `scripts/cross_repo_samples_util.py` was written to share the pin-loading loop, then **deleted** | the three existing report scripts wrap that loop in a per-repo `try/except`, so migrating them changes their error semantics — not mechanical, and out of this ticket's scope. The loop is inlined in the new script instead. |
| 2 | per-slot ceilings replaced the pooled one | design refinement, recorded above; same total, same files |
| 3 | `tests/viewer_dom_stub.js` gained `heads` in the overview section map | required for the new headline strip to be visible to the headless harness at all |

### Verification sweep

| AC | proof | result |
|---|---|---|
| AC1 | `test_ac1_*` — 4 renderers × (`None`, identity run) | green |
| AC2 | `test_ac2_only_prose_differs*` — blank the 3 prose fields, compare | green |
| AC3 | `test_ac3_*` (seam) + `test_ac3_*` (impl: exploding client, edit-is-a-miss, sorted-key file) | green |
| AC4 | `test_ac4_*` parametrized over error / timeout / empty | green |
| AC5 | `test_ac5_*` + the report above | green, ceiling shown biting |
| AC6 | `test_ac6_*` — 7 filler shapes, seam falls back, both gates raise C1 | green |
| AC7 | `test_ac7_*` filesystem sweep + new CI `R4.1` grep-gate | green |

### Cost ledger

| phase | dispatch | round | tokens |
|---|---|---|---|
| — | none | — | 0 dispatches this run (review waived, challenger `OFF (--no-challenger)`, no subagent dispatched) |

Main-loop spend: **unmeasured (host does not surface usage)**. Total dispatch: **0**.

### Decision log

| # | decision | why |
|---|---|---|
| D1 | one `ProseWriter` seam, not two routes | 091's seam fires on nothing (measured); and four guards × two routes is four duplicated guards, with a split budget that is not a budget (LESSONS 117b) |
| D2 | AC1 read as reproducibility, not byte-equality with 116 | the Scope's structural-default headlines are new deterministic content; ratified at Gate 1 |
| D3 | `headlines` in the dataset, counters **not** in it | the LLM must be able to reword the sentence, so it must be in the payload; a `calls:` field would be a number that moved when the seam turned on, breaking AC2 |
| D4 | per-slot ceilings | starvation-proof and order-independent; same derived total |
| D5 | filler rejected at the seam **and** at the gate | the seam gives AC4's graceful degradation, the gate gives AC6's backstop against any impl — including one nobody here wrote |
| D6 | `TYPE_KINDS`/`CALLABLE_KINDS` in `contract.py` | a named subset of an existing vocabulary, exactly what the neighbouring `CALLER_KINDS` comment sanctions; no `CONTRACT_VERSION` bump (R3) |
| D7 | tokens reported as bytes + a labelled estimate | no tokenizer here, and an estimate printed as a measurement is a false green |
