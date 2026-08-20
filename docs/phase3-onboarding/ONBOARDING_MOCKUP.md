# Onboarding mockup — a system map for humans (design note, 2026-08-19)

**Status:** design accepted by the maintainer; tasks 108–117 filed from it.
**Prototype:** [`mockup/`](mockup/) — regenerates the reviewed artifact from any indexed repo.
**Reviewed artifact:** `artifacts/onboarding-mockup/index.html` (gitignored; rebuild with `mockup/build.sh`).

This note records *why* the Phase-3 onboarding output is being reshaped, what the mockup proves, and
which parts of it are deterministic versus prose. Every number below was measured on the anchor
monorepo (private PHP, 18,929 indexed files, commit `767a2ec7a4b4`, default knobs) — not estimated.

---

## 1. The problem the mockup answers

`generate_onboarding` (088/089) currently emits **one markdown page per module in the tour budget**,
plus a tour file, a manifest, and a viewer. On the anchor repo that is:

| Artifact | Bytes | Verdict |
|---|---:|---|
| `overview.md` | 2,683 | the only part anyone can use |
| `tour.md` | 6,312,632 | 500 lines of `path — reached from path` |
| `manifest.json` | 6,507,331 | machine-only, and no machine reads it |
| `index.html` | 31,057,609 | a paginated data dump, not a map |
| 500 module pages | 24,643,326 | see below |
| **total** | **≈ 43 MB** | |

Median module page is **82,218 bytes** (≈ 20.5k tokens) and **261 of 500** exceed 80 KB. Where those
bytes go, on the median page:

```
## Role            13 bytes     (one of two values: connector | entry-point)
## Layer            6 bytes     (a directory name)
## Summary         10 bytes     ("(none)" — 500/500 pages)
## In the tour  23,893 bytes    (SCC member list, repeated identically per member)
## Neighbours   58,196 bytes    (644 flat paths, uncapped)
```

**99.96 % of a page is two flat path lists.** Reading one page costs more than reading the entire
knowledge graph of the reference tool this design borrows from (100 KB for a whole project). And every
fact on the page is one MCP tool call away, live and precise — so the artifact competes with
code-atlas's own tools and loses on every axis.

The conclusion the maintainer drew, and this note adopts:

> **The MCP tools are the product for AI. The onboarding artifact is the product for humans.**
> It must be a *map* — something a person can look at and see where the system's classes, modules and
> models sit — not a paginated dump of the graph.

Scope boundary set with it: **the map answers only what the codebase says.** How to run the app,
environment setup, and deployment are the repo's own documentation and deliberately out of scope
(they are also the kind of repo-specific knowledge R2.2 keeps out of the core).

---

## 2. What the mockup is

One self-contained HTML file, **891 KB**, no build step, no network reference, offline, theme-aware,
commit-stamped. Of that, ~800 KB is a front-coded index of all 18,929 file paths (5,399 unique
directories + filenames) that powers search; the **aggregate dataset is ~50 KB**.

Eleven sections, ordered the way a newcomer needs them:

| # | Section | What it answers | Source |
|---|---|---|---|
| 00 | Overview | six headline numbers, each with what it *means* | derived |
| 01 | Six things to know first | the traps you cannot read off a directory tree | prose over derived numbers |
| 02 | Business → directory | *"I was told to fix screen X — which file?"* | derived |
| 03 | Sitemap (treemap) | where the code volume actually is | derived |
| 04 | Layers & class distribution | is this layer OOP or procedural script? | derived + prose descriptions |
| 05 | Dependency matrix | who calls whom, all layers, nothing cut | derived |
| 06 | Hubs | change here and you touch everything | derived |
| 07 | Duplication (mirror trees) | the repo's biggest trap, as a *lookup tool* | derived |
| 08 | Nothing calls this | four different populations, not one number | derived |
| 09 | Largest classes | vendored libraries inflating every count | derived |
| 10 | 12-step tour | a reading order where each step builds on the last | prose over derived numbers |
| 11 | Where these numbers come from | provenance: derived vs written | — |

### Interactions that changed its nature from poster to tool

- **`Ctrl+K` search** over all 18,929 paths, plus module and class names.
- **Counterpart lookup.** Paste `legacy/<A>/…` and the parallel path under the sibling tree comes back
  inline; a legacy path with *no* counterpart is called out, which is the more valuable signal.
- **Treemap drill-down** with breadcrumb, coloured by the dominant responsibility layer inside each
  directory (computed, not keyword-guessed at render time).
- **Clickable module rows** that open pre-filled in search.

---

## 3. What the mockup proved on real data

Findings a newcomer cannot get from `ls`, all derived:

- **4,244 relative paths exist under *both* sibling trees** (62 % of the legacy tree); 1,522 exist only
  under one, 1,134 only under the other. Editing one side and forgetting the other is the repo's most
  likely first bug.
- **The DB-access layer has three copies**, with 4,050 / 4,041 / 3,926 dependent files.
- **13,255 classes, 95 interfaces, 8 traits.** There is almost nothing to mock against.
- **The largest hub in the repo is a test bootstrap** (5,425 dependents) — above every production file.
- **64 % of edges are `HEURISTIC`**, not `RESOLVED` (1,141,330 vs 647,549). The map states this itself.
- **The largest class is a vendored PDF library with 416 methods, present in 4 copies.**

### The claim the mockup had to retract

An earlier draft reported *"45 % of files are entry points"* from `fan_in == 0`. That conflates four
populations. Split honestly:

| Zero-inbound population | Count |
|---|---:|
| web entry points (under a web root, a controller dir, or an `index`/`main` file) | 1,000 |
| vendored libraries | 1,967 |
| tests and fixtures | 1,776 |
| **not statically resolvable** | **3,732** |
| ⤷ of which view/template files (dynamic `include`) | 2,254 |
| ⤷ no inbound *and* no outbound edge — worth investigating | 512 |

Calling 8,475 files "entry points" would have made a newcomer panic; calling 3,732 of them "dead code"
would have been a false accusation. The map now reports the split and names the 512 as *a list worth
checking, not a conclusion*.

---

## 4. Deterministic vs prose — the seam this design depends on

**Derived from the index (reproducible, no opinion):** every count; layer assignment; the dependency
matrix; hubs; the treemap and its per-directory dominant layer; mirror-tree detection; the
reachability split; the module table; and **every number interpolated into the tour text** (the
prototype has a regression assertion that no such number is hard-coded).

**Written by a human in the mockup — in the shipped version this is the LLM's job:** the one-line
description per layer, the wording of the six headline facts, and the 12 tour paragraphs. These go
through the existing 085 `Summarizer` / 091 `LayerRefiner` seams (090/091), not a new abstraction.

This split is what makes the design implementable under R4: the deterministic core produces the whole
map, and enrichment only replaces prose.

---

## 5. Design decisions that need a rule judgment

Two items are flagged rather than assumed, because they touch **R2.2 (standard over sample)**:

1. **Responsibility-vocabulary layer names.** The mockup names layers `HTTP / Entry`, `Services`,
   `Domain / Data`, `Views`, `Middleware / Auth`, `Background Jobs`, `Integration / Reporting`,
   `Shared Library`, `Tests`, `Config / Migration`, `Vendor / Framework`, `Uncategorised` — matched
   from directory-segment words (`controller`, `service`, `model`, `view`, `job`, …) with **the deepest
   segment winning**. Deepest-wins matters: matching any segment let one container directory swallow
   11,540 files into a single layer. The judgment: is a generic architectural vocabulary a *standard*
   (industry convention, like PSR naming) or a *sample* (this repo's names)? This note argues
   **standard** — none of those words names a repo, product or framework — but it is the maintainer's
   call, recorded in task 110.

2. **Vendor detection.** The prototype recognises vendored libraries by library name
   (`tcpdf`, `mpdf`, `adodb`, …). That **is** framework naming and would violate R2.2 inside the core.
   **Resolved in task 113 (landed), and it needed no new signal:** 110's responsibility vocabulary was
   already ratified as an R2.2 standard and already carries `vendor`, so the bucket is filled by the
   path signal, with the operator's own `stub_roots` declaration outranking it where set. No
   `composer.json` parsing was built — it stays the documented upgrade path for a repo that declares
   neither. Where no indexed path names any responsibility, the vocabulary buckets are **dropped with
   the reason stated** rather than reported as a misleading zero.

---

## 6. Known limits of the mockup, stated up front

- **The module table does not cover the repo.** It only sees what exists as a module *directory*; many
  legacy screens are flat files directly under the web root and belong to no module. The table states
  its own coverage percentage and points at search for the rest. This was found by testing the
  reviewer's own scenario — the screen they named has no module directory.
- **Prose is hand-written** (§4) and will differ once the LLM produces it.
- **Search embeds every path**, which is what takes the file from ~50 KB to 891 KB. Acceptable against
  43 MB, but it is a real cost and the cap should be a knob.
- **No per-symbol detail.** The map stops at file grain deliberately; symbol-level questions are what
  the MCP tools are for.
- **Not measured on a second repo.** Every number here is one monorepo. Layer vocabulary and mirror
  detection especially need a second and third shape before they are called general.

---

## 7. Task breakdown

Ordered by dependency. Wave 1 is independently shippable and needed regardless of the reshape; Wave 2
is the reshape; Wave 3 is enrichment and the new viewer.

| Wave | # | Task | Why now | Depends on |
|---|---|---|---|---|
| 1 | 108 | [Module page neighbour lists are unbounded](../tasks/108_module-page-neighbour-list-is-unbounded.md) | 82 KB pages, and the only place in the repo that ignores `CA_MAX_RESULTS` | 088, 107 |
| 1 | 109 | [Onboarding artifact quality gate](../tasks/109_onboarding-artifact-quality-gate.md) | the gate that would have stopped 106 and 107 from shipping | 088, 108 |
| 2 | 110 | [Layers named by responsibility, deepest segment wins](../tasks/110_layers-named-by-responsibility.md) | directory names are not architecture; needs the R2.2 judgment | 084, 105, 109 |
| 2 | 111 | [The tour is 5–15 narrative steps, not one stop per module](../tasks/111_tour-is-narrative-steps.md) | biggest single value change: 500 stops → a readable reading order | 087, 110 |
| 2 | 112 | [One compact onboarding dataset, aggregates in `store.py`](../tasks/112_onboarding-dataset-contract.md) | the contract both renderers consume; keeps SQL in `store.py` (R1.4) | 083, 086, 110 |
| 2 | 113 | [Zero-inbound is four populations, not one number](../tasks/113_reachability-split.md) | **done** — retracts the "45 % entry points" claim; five buckets from 110's ratified vocabulary + structure | 083, 112 |
| 3 | 114 | [Business modules from directory structure](../tasks/114_business-module-table.md) | the bridge from "fix screen X" to a file; must state its own coverage | 112 |
| 3 | 115 | [Mirror-subtree detection — evidence for 098](../tasks/115_mirror-subtree-detection.md) | turns the duplication trap into a lookup; feeds the deferred 098 decision | 112, 098 |
| 3 | 116 | [Dashboard viewer: sitemap, matrix, search](../tasks/116_dashboard-viewer.md) | replaces the 31 MB dump with the reviewed map | 112, 114, 115 |
| 3 | 117 | [LLM prose for layer descriptions and tour steps](../tasks/117_llm-prose-for-map.md) | the §4 prose half, through the existing seams | 110, 111, 090, 091 |

**Not in scope, deliberately:** run-the-app / environment / deployment documentation (§2); symbol-grain
pages (§6); a second-repo generalisation pass, which should follow 116 rather than gate it.
