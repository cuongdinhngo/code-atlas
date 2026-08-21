---
id: 116
slug: dashboard-viewer
title: Onboarding — replace the 31 MB page dump with a navigable system map (M11)
phase: 3
milestone: M11
status: done
depends_on: [112, 114, 115]
---

## Why this exists (measured, anchor monorepo)

089's viewer embeds the whole artifact, producing a **31,057,609-byte `index.html`** that renders 500
module pages as a paginated list. It is a data dump, not a map: a human cannot see from it where the
system's classes and modules sit.

The reviewed mockup is **891 KB** — a single self-contained file, no build step, no network reference,
offline, theme-aware, commit-stamped — and answers the spatial question directly. It was validated
headlessly against the real dataset with 12 assertions (mirror lookup, search, per-layer legend
completeness, matrix completeness, no hard-coded tour numbers, provenance section present).

## Scope

Render the 112 dataset as the reviewed map. Presentation only — no SQL, no LLM, no language branch
(R1.1/R1.4/R4):

- **Sitemap treemap** sized by symbol count, coloured by each directory's dominant layer (computed in
  112, not guessed at render time), with drill-down and breadcrumb.
- **Layer table** with description and a class/method/function/property composition bar per layer, so a
  procedural layer is visible as procedural.
- **Dependency matrix** over **every** layer. The mockup's first draft silently cut to the top 10 and the
  reviewer caught it: a section titled "who calls whom" that omits participants is a trust bug.
- **Hub list**, **largest classes**, **module table** (114), **reachability split** (113),
  **mirror panel** (115).
- **Search palette** over the dataset's path index with counterpart lookup inline; when the index is
  capped, search states its own incompleteness.
- **Provenance section** naming, explicitly, which parts are derived and which are prose. The draft's
  "MOCKUP" badge next to the words "real data" was itself a trust bug — a reader cannot tell a display
  bug from a data bug, so the artifact must say where each number came from.
- Every displayed number interpolated from the dataset; **no literal numbers in the template** (the
  draft had five, and a regenerated page would have contradicted itself).

## Acceptance criteria

1. **AC1.** Self-contained: no external stylesheet, script, font or image; opens from `file://` with no
   server. Proven by a test asserting zero external references.
2. **AC2.** Size measured on the anchor repo and two pinned public repos, with and without the path
   index; under 1 MB on the anchor repo with the index and under 150 KB without it.
3. **AC3.** Byte-stable given the same dataset (R4.2).
4. **AC4.** A regression test asserts no literal number in the template, by rendering a mutated dataset
   and checking every displayed figure moved.
5. **AC5.** Layer legend and dependency matrix each cover every layer in the dataset — no silent cut.
   A section that does cap says so in the section.
6. **AC6.** Counterpart lookup and search exercised headlessly against a real dataset, including the
   negative cases (no counterpart; no match).
7. **AC7.** 089's viewer is replaced, not duplicated — one viewer, and `generate_onboarding` writes it.

## Out of scope

Prose content (117), and any interactive feature needing a server or a network call — the artifact must
survive being emailed.

---

# mango working doc — 116

## Session status

- phase: **Gate 1 (analysis) — awaiting ratification**
- SCOPE: **L** · TIER: **full**
- work_doc_mode: `embed` (plain tracked ticket, 113–115 precedent) · path: this file, below the separator
- CHALLENGER: **OFF (--no-challenger)** — waived by the run's arguments
- REVIEW: **skipped** — waived by the run's arguments
- branch: `feat/116-dashboard-viewer`

## Phase 0 — refine

**Premise check: PASSES.** Every source the ticket cites as already existing resolves:

| Cited | Resolves to | Note |
|---|---|---|
| 089's viewer, 31,057,609 B | `code_atlas/onboarding/viewer.py` + `tests/test_onboarding_viewer.py` | embeds `render_module()` for **every** page — that is the 31 MB |
| the reviewed mockup, 891 KB | `docs/phase3-onboarding/mockup/{template.html,extract.py,build.sh,dom-stub.js}` (tracked) | built output at `artifacts/onboarding-mockup/` (untracked) — **present on this host** |
| the 112 dataset | `code_atlas/onboarding/dataset.py`, `DATASET_VERSION = 4` | `render_dataset_overview`'s docstring names 116 as its consumer |
| 113 / 114 / 115 | `reachability.py` · `modules.py` · `mirrors.py` | all three merged; all three already dataset fields |
| "validated headlessly … 12 assertions" | `mockup/dom-stub.js` | the ticket's own premise is that headless JS execution **is** the validation method |

**Unresolved product-decisions: 1** → ticket-refine path (not epic, not skip).

- **W1 (want-decision, ASSUMED — awaiting ratification at Gate 1).** 089's viewer had a **Tour tab**
  showing 111's reading order and the per-module page bodies. The ticket's Scope lists ten sections and
  the tour is not among them; Out of scope says "Prose content (117)". Dropping it is a **functional
  regression against 089**, which the ticket neither asks for nor forbids.
  **Assumption taken: drop it — the map is rendered from the dataset ALONE.** Reasons, cited:
  (a) `dataset.py:369` already declares the intent — *"Proves the contract: a renderer needs nothing
  but the dataset to draw the map. The full renderer migration (viewer, per-module pages) is 116"*;
  (b) **AC3 is only meaningful under it** — "byte-stable given the same dataset" presumes the dataset
  is the sole input; (c) the embedded page bodies **are** the 31 MB defect, and the Tour tab is what
  displayed them; (d) nothing is lost from the tree — `tour.md`, `overview.md` and `modules/*.md` are
  still written by `generate_onboarding`, and the provenance section names them.
  Consequence: `render_viewer(dataset, …)` no longer takes an `OnboardingArtifact` at all.

HOW-decisions were resolved from the repo rather than asked (each cited under Phase 1).

## Phase 1 — analysis

### Measured, on this host, before any design was chosen

Both premises were measurable here — php 8.3 and node 22 are present, the three pins are already
indexed, and the anchor's own extracted dataset survives at `artifacts/onboarding-mockup/dataset.json`.
So AC2's thresholds are re-derived rather than trusted.

**The anchor dataset, by key (870,878 B total; `index.html` 911,959 B):**

| key | bytes | card | share |
|---|---:|---:|---:|
| `files_idx` | 577,321 | 18,929 | 66.3 % |
| `dirs` | 266,118 | 5,399 | 30.6 % |
| **path index subtotal** | **843,439** | | **96.9 %** |
| everything else combined | 27,439 | | 3.1 % |

- **AC2's two thresholds are exactly calibrated to this split.** With the index: 843 KB + 27 KB + a
  ~41 KB template ≈ **912 KB < 1 MB**. Without it: 27 KB + 41 KB ≈ **68 KB < 150 KB**. The ACs are
  not arbitrary — they are this measurement, and the margin under each is thin enough to matter.
- **"Without the index" needs no new knob.** `CA_PATH_INDEX_MAX=0` already empties it
  (`config.py:54`, `DEFAULT_PATH_INDEX_MAX = 20000`); the anchor's 18,929 paths are **under** that
  default, so the 912 KB figure is the untruncated case.
- Anchor `tree` at `DIR_SYMBOL_THRESHOLD = 400`: **76 directories, max depth 3** — the treemap is a
  few dozen cells, as intended.

**The 089 viewer and the dataset on the three pins (measured, this host):**

| pin | files | paths | 089 `index.html` | `dataset.json` | layers | **tree rows** |
|---|---:|---:|---:|---:|---:|---:|
| `laravel_app` | 26 | 26 | 12,273 B | 9,814 B | 5 | **0** |
| `symfony_demo` | 51 | 51 | 34,294 B | 21,650 B | 7 | **0** |
| `brick_math` | 32 | 32 | 37,873 B | 14,843 B | 2 | **1** |

Two findings that moved the design:

1. **The pins cannot falsify AC2.** At 26–51 files every pin is already two orders of magnitude
   under both thresholds. Measuring there and reporting green would be a **vacuous pass**. AC2's
   thresholds are therefore proven by a **synthetic dataset at the anchor's measured cardinality**
   (18,929 paths / 5,399 dirs / 76 tree rows / 12 layers) — repo-agnostic, and a real test — with the
   pins recorded as a smoke run and the anchor itself deferred to the operator (108/112/113/114/115
   precedent).
2. **The sitemap is EMPTY on two of three pins.** `DIR_SYMBOL_THRESHOLD = 400` prunes every
   directory on a small repo. A treemap that renders a blank 440 px box is a display bug
   indistinguishable from a data bug — precisely the trust failure the ticket's provenance paragraph
   is about. **The section must state "no directory holds ≥ 400 symbols" instead of drawing nothing.**

### The prototype cannot be ported — the same R2.2 class as 114's and 115's

`mockup/template.html` is a **repo-specific** artifact. Carrying it across would import, in one file:
the repo's own name; `legacy/`, two region segments, `web/`, `application/`, `modules/`, `src/`,
`public/`; the file and class names `DatabaseWrapper`, `error_handler.php`, `helper_functions`,
`TCPDF`, `mPDF`, `LedgerReport.php`, `assessments`, `WSDL`; the framework names `Zend`, `SimpleSAML`,
`log4php`, `PHPUnit`, `PSR-4`, and the language itself; a hand-keyed `LDESC` table of layer
descriptions that `layers.layer_description()` already derives; a hand-keyed 5-entry `KINDS` list
duplicating `contract.NODE_KINDS`; and Vietnamese prose (this repo's on-disk language is English).

**Only the mechanisms port**: the squarify treemap, the matrix builder, the palette, the front-coded
path expansion, the DOM stub. Every label, description, threshold and section note is re-derived from
the dataset. This is the **third consecutive ticket** in which the R2.2 gate's live risk is my own
prose rather than my code, so the denylist unit twin is written **first**, not last, and its list is
widened to the prototype's own literals.

### HOW-decisions (resolved on standing approval, each cited)

- **H1 — rewrite `viewer.py` in place; do not add a module.** AC7 says "one viewer". A rewritten
  `render_viewer` keeps the core-module pin at **57** (no `test_sql_confinement` / `test_core_is_language_agnostic`
  bump) and is the smallest useful change (R7.1). The template stays an inline constant — 089's
  precedent, and no packaging-data machinery.
- **H2 — the commit stamp goes IN the dataset (`DATASET_VERSION` 4 → 5).** `store.get_meta("last_commit")`
  exists and is populated on all three pins. Putting it in the dataset keeps AC3 literally true
  ("same dataset → same bytes") and keeps the dataset the sole renderer input per W1. The objection
  that it churns the committed `manifest.json` on every regeneration is **void**: `index.html` is
  committed too, so any stamp anywhere churns identically. Absent repo/commit → `""`, which
  `gitutil.py:4` calls a normal state, and the page says "no commit recorded".
- **H3 — the per-layer composition bar needs a new bounded store query.** The ticket's Scope
  requires "a class/method/function/property composition bar per layer, so a procedural layer is
  visible as procedural"; `LayerStat` carries no kind breakdown. Add
  `store.file_kind_counts() -> ((file, kind, count), …)` — one `GROUP BY file_path, kind` pass,
  bounded by files × `contract.NODE_KINDS`, the exact shape and bound of the existing
  `file_class_counts` (R1.4/R4.3). Module grain **is** file grain (`metrics.py:128`), so a layer's
  composition is the sum over its files, and `LayerStat.modules` is already its file count.
  The bar iterates the dataset's **own** kind vocabulary — no 5-entry hardcode.
- **H4 — AC4, AC5 and AC6 are all only provable headlessly, so node is not optional.** The page
  builds its content in the browser; a static scan of the HTML cannot see a single displayed figure,
  so "check every displayed figure moved" (AC4), "the legend covers every layer" (AC5) and "search
  and counterpart exercised" (AC6) have no static formulation. The ticket's own premise already
  names the method. Therefore: `tests/viewer_dom_stub.js` is committed (evolved from the prototype's
  stub, which is pure DOM and R2-clean), it prints a JSON report of what the page actually rendered,
  **all assertions stay in Python**, and node joins `docker/Dockerfile` + the CI test job. Guarded
  by a `needs_node` skipif — the `needs_php` pattern (`tests/php_adapter_cli.py:23`) — so the gate
  runs everywhere it matters and still reports **0 skipped** in Docker.
- **H5 — the page exposes its query functions on one namespace.** The harness must call search and
  counterpart, so the script assigns `globalThis.CA_MAP = {…}` instead of hiding in an IIFE. A page
  that cannot be driven cannot be tested; the surface is documented as exactly that.
- **H6 — every capped or empty section states its own condition.** Not just search (AC6 names it) but
  the sitemap (`0` tree rows), the module table (114's `COVERAGE_NOTE`), the mirror panel (115's
  `PATH_NOT_CONTENT`), the reachability split (113's per-bucket notes) and the matrix. AC5's "a
  section that does cap says so in the section" is applied uniformly, not only where an AC names it.

### Blast radius

| Path | Change |
|---|---|
| `code_atlas/onboarding/viewer.py` | **rewritten** — dataset-only payload + the map template |
| `code_atlas/onboarding/dataset.py` | `+commit`, `+LayerStat.kinds`; `DATASET_VERSION` 4 → **5** |
| `code_atlas/store.py` | `+file_kind_counts()` |
| `code_atlas/tools/generate_onboarding.py` | pass `commit` + `file_kind_counts`; call `render_viewer(dataset, …)` |
| `tests/test_onboarding_viewer.py` | **rewritten** — static shape + the headless report |
| `tests/viewer_dom_stub.js` | **new** — the committed headless harness |
| `scripts/viewer_report.py` | **new** — AC2 sizes: pins, synthetic anchor-scale, operator's anchor |
| `tests/test_onboarding_dataset.py`, `tests/test_generate_onboarding.py`, `tests/test_store.py`, `tests/test_architecture_overview.py` | consequence + the new query's own test |
| `docker/Dockerfile`, `.github/workflows/ci.yml` | node for the headless gate |
| `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, `docs/phase3-onboarding/ONBOARDING_MOCKUP.md`, `docs/LESSONS.md` | docs-before-PR |

Core-module pin stays **57**. Contract untouched (R3) — `DATASET_VERSION` is the dataset's own version.

### Acceptance-criteria matrix

| AC | Claim | Proven by | Risk |
|---|---|---|---|
| AC1 | self-contained, opens from `file://` | static assertions (no `<script src`, no `http`/`https`, no `fetch(`, CSP `default-src 'none'` retained from 089) + the headless run needing no network | low |
| AC2 | < 1 MB with index, < 150 KB without, on the anchor + two pins | **synthetic anchor-scale dataset** (18,929 paths / 5,399 dirs / 76 dirs / 12 layers) asserted against both thresholds; pins measured as smoke; `scripts/viewer_report.py` for the operator's anchor | **the pins are vacuous here — named, not hidden** |
| AC3 | byte-stable given the same dataset | render twice, assert identical; `commit` is inside the dataset (H2) so the claim holds literally | low |
| AC4 | no literal number in the template | headless: render dataset A and a **mutated** A, diff every rendered figure | needs node (H4) |
| AC5 | legend + matrix cover **every** layer | headless: rendered legend entries == `len(dataset.layers)`; matrix is n×n | needs node (H4) |
| AC6 | search + counterpart exercised, negatives included | headless: hit, no-match, counterpart, no-counterpart, and the truncated-index statement | needs node (H4) |
| AC7 | 089's viewer replaced, not duplicated | one `render_viewer`, one `VIEWER_NAME`; `grep` twin asserting no second viewer module and no `render_module` import in the viewer | low |

## Phase 2 — design

### Approach

**The dataset *is* the payload.** `render_viewer(dataset, max_results)` embeds `dataset.as_dict()`
verbatim and the page reads it directly. `viewer_payload()` is **deleted**, not ported: 089 had a
second hand-written payload shape that re-walked the artifact, and keeping it would mean two
serialisations of the same facts drifting apart. One shape, declared once in `dataset.py`, is what
112 built. This is also what makes AC3 literally checkable — same dataset in, same bytes out.

Ten sections, every label and every figure read out of that one blob:

| § | Section | Reads | States its own limit |
|---|---|---|---|
| 1 | Overview + commit stamp | `files` `parsed` `method` `node_counts` `edge_counts` `confidence` `commit` `version` | heuristic share of edges |
| 2 | Capability → directory | `modules` (114) | `COVERAGE_NOTE` + every refusal |
| 3 | Sitemap treemap | `tree` `dir_symbol_threshold` | **"no directory clears the threshold"** when `tree` is empty |
| 4 | Layers + composition | `layers` incl. new `kinds` | — (covers every layer) |
| 5 | Dependency matrix | `layers` × `matrix` | n×n, no cut (AC5) |
| 6 | Hubs | `hubs` | "a ranking, not an inventory", length derived |
| 7 | Mirror subtrees | `mirrors` (115) | `PATH_NOT_CONTENT`, always |
| 8 | Zero-inbound split | `reachability` (113) | per-bucket `note`, `sample_truncated`, `dropped` |
| 9 | Largest classes | `classes` | as §6 |
| 10 | Provenance | all of the above | which parts are derived; **that no prose exists yet** |
| — | Search palette (Ctrl-K) | `path_index` `mirrors` `modules` `classes` | `truncated` ⇒ search says it is incomplete |

### Two design consequences of AC4 that are easy to miss

AC4 forbids a literal number in the template. Taken literally — which is the only way it bites — two
things follow that the mockup gets wrong:

1. **The numeric section badges (`01`…`11`) are deleted.** They are literal numbers in the template,
   they carry no information, and they are the one thing that would make AC4's assertion fuzzy: they
   would appear unchanged in both renders of the mutation test and force the assertion to become
   "most figures moved". Without them, AC4 is exact and total — **no digit-run in any data section's
   rendered text survives a mutation of the dataset.**
2. **An empty matrix cell renders blank, not `0`.** A constant `0` would otherwise survive the
   mutation, for the same reason. (The mockup already does this; here it is load-bearing.)

The same rule forces `dir_symbol_threshold` into the dataset: §3's empty-state sentence must name the
threshold it was pruned at, and that number cannot be a template literal.

### `DATASET_VERSION` 4 → 5 — three fields, each forced by an AC

| Field | Forced by | Source |
|---|---|---|
| `commit: str` | "commit-stamped" + AC3 (sole input) | `store.get_meta("last_commit")`, `""` when absent |
| `LayerStat.kinds: (KindCount, …)` | Scope's composition bar | new `store.file_kind_counts()`, summed per layer |
| `dir_symbol_threshold: int` | AC4 (no literal numbers) + §3's empty state | the `build_dataset` parameter already in hand |

`contract_version` is untouched (R3) — this is the dataset's own version, as `dataset.py:37` records.

### The new store query

```
file_kind_counts() -> tuple[tuple[str, str, int], ...]
  SELECT file_path, COALESCE(kind,''), COUNT(*) FROM nodes
   WHERE file_path IS NOT NULL GROUP BY file_path, kind ORDER BY file_path, kind
```

One GROUP BY pass; rows bounded by files × `contract.NODE_KINDS`, the exact shape and bound of the
adjacent `file_class_counts` (R4.3). Module grain is file grain (`metrics.py:128`), so a layer's
composition is the sum over the files assigned to it, and `LayerStat.modules` is already its file count.

### The headless harness

`tests/viewer_dom_stub.js` — committed, ~120 lines, evolved from `mockup/dom-stub.js` (pure DOM, no
repo names). Invoked as `node tests/viewer_dom_stub.js <index.html>`; it extracts the payload and the
page script, runs the script against a minimal DOM, then drives `globalThis.CA_MAP` and prints **one
JSON report** on stdout:

```
{ sections: {<id>: {text, figures[]}}, legend: [...], matrix: {rows, cols},
  search: {<query>: {count, first, incomplete}}, counterpart: {<path>: {status, path, qualified}},
  tree: {roots, nodes, closed_under_parents} }
```

Every assertion lives in Python (`tests/test_onboarding_viewer.py`); the JS only reports. Guarded by
`needs_node = pytest.mark.skipif(shutil.which("node") is None, …)` — the `needs_php` pattern
(`tests/php_adapter_cli.py:23`) — and node is added to `docker/Dockerfile` and the CI test job so the
gate actually runs and Docker still reports **0 skipped**.

### The one duplication this design accepts, stated rather than hidden

The counterpart lookup exists twice: `mirrors.resolve_counterpart` in Python and a prefix swap in the
page's JS. It is **forced** — the lookup must answer inside a page with no server, and precomputing a
counterpart for each of the anchor's 18,929 paths would roughly double the index that already accounts
for 96.9 % of the payload. Mitigation: the headless test drives the JS through the *same four
outcomes* 115's Python tests pin (`counterpart`, `no_counterpart`, `outside_mirror`, and `qualified`
under a truncated index), so a divergence fails a test rather than shipping.

### Rejected alternatives

| Rejected | Why |
|---|---|
| A new `map_page.py` beside `viewer.py` | AC7 says one viewer; a second module is the duplication the AC forbids, and would bump the 57-module pin for nothing (R7.1) |
| Template as package data via `importlib.resources` | adds packaging machinery for one string; 089's inline constant is the precedent |
| Keep `viewer_payload()` as its own shape | two serialisations of one fact set, drifting — the defect 112 was written to end |
| Commit passed to `render_viewer` out of band | weakens AC3 to "same dataset *and* commit"; and the churn objection is void since `index.html` is committed either way |
| Precompute every path's counterpart server-side | ~doubles the payload's dominant term to avoid ~15 lines of JS |
| Prove AC4/5/6 by static grep | the page builds its content client-side; a static scan sees **zero** rendered figures. A green grep here is a false green |
| Reimplement search in Python and test that | tests a copy, not the shipped page |
| Measure AC2 on the pins alone | 26–51 files, two orders of magnitude under both thresholds — a vacuous pass (Phase 1) |

### Change list (traced to matrix rows)

| # | Path | For |
|---|---|---|
| 1 | `code_atlas/store.py` — `file_kind_counts()` | Scope / §4 |
| 2 | `code_atlas/onboarding/dataset.py` — v5, `commit`, `LayerStat.kinds`, `dir_symbol_threshold` | §1 §3 §4, AC3, AC4 |
| 3 | `code_atlas/onboarding/viewer.py` — **rewritten**, dataset-only | AC1 AC2 AC3 AC5 AC6 AC7 |
| 4 | `code_atlas/tools/generate_onboarding.py` — pass commit + kind counts, new call | AC7 |
| 5 | `tests/viewer_dom_stub.js` — **new** | AC4 AC5 AC6 |
| 6 | `tests/test_onboarding_viewer.py` — **rewritten** | AC1–AC7 |
| 7 | `scripts/viewer_report.py` — **new** | AC2 (pins + synthetic + operator's anchor) |
| 8 | `tests/test_store.py`, `tests/test_onboarding_dataset.py`, `tests/test_generate_onboarding.py`, `tests/test_architecture_overview.py` | consequence of 1, 2, 4 |
| 9 | `docker/Dockerfile`, `.github/workflows/ci.yml` — node | AC4 AC5 AC6 |
| 10 | `docs/PLAN.md`, `docs/BACKLOG.md`, `README.md`, `docs/phase3-onboarding/ONBOARDING_MOCKUP.md`, `docs/LESSONS.md` | docs-before-PR |

Nothing outside this list. Core-module pin stays **57**.

### Rule compliance

- **R1.1 / R2.2** — no language branch and no repo name reaches `code_atlas/`. The denylist unit twin
  is written **first** this ticket (third consecutive occurrence), widened to the prototype's own
  literals: the two region segments, `legacy/`, `web`, `DatabaseWrapper`, `TCPDF`, `mPDF`,
  `assessments`, `Zend`, `SimpleSAML`, `log4php`, plus the CI gate's five framework names.
- **R1.4** — the viewer runs no SQL; the one new query is in `store.py`.
- **R3** — adapter contract untouched; `DATASET_VERSION` is the dataset's own.
- **R4 / R4.2** — no LLM, no network, no wall-clock; sorted throughout, rendered twice and diffed.
- **R4.3** — every list on the page is a bounded dataset field; the one unbounded term (`path_index`)
  is already capped and now says so on screen.
- **R7.1** — one module rewritten, none added.

### Named proving test (R6.5 — observed red)

`test_ac2_an_anchor_scale_dataset_renders_under_the_size_budget` — build a synthetic dataset at the
anchor's **measured** cardinality (18,929 paths, 5,399 dirs, 76 tree rows, 12 layers, 500 modules) and
assert `< 1 MB` with the index and `< 150 KB` at `path_index_max=0`. Run against the **current**
viewer first and record the observed red number; it embeds a `render_module()` body per page, which
is the 31 MB defect the ticket opens with.

### Verification plan

1. `scripts/docker-test.sh` — ruff · mypy · pytest. Baseline on `main` is **1601 passed, 0 failed**;
   report the delta and account for every new test.
2. `scripts/docker-test.sh python scripts/viewer_report.py` — AC2 on the three pins **and** the
   synthetic anchor-scale dataset, with and without the path index.
3. Local `awk` line-length pre-check before each Docker run (the 114/115 E501 lesson: ruff only
   exists in the container).
4. The anchor's own re-measure is deferred to the operator; `scripts/viewer_report.py` asserts
   repo-agnostic invariants so a run is a measurement, not a hoped-for pass.

## Phase 3 — execute

### Premise correction found while measuring the proving test (surfaced, not absorbed)

The ticket's *Why this exists* opens on **31,057,609 bytes**. Rendering the **current** viewer against
an anchor-scale artifact (18,929 paths, 500 pages, 12 layers, post-108 neighbour caps) measures
**921,746 B — 0.9 MB**, not 31 MB.

**Task 108 already removed ~97 % of that size.** The 31 MB figure was measured when the median module
page was 82,218 bytes and *99.96 % flat path list* (`BACKLOG.md:98`); 108 capped those lists at
`CA_MAX_RESULTS`, so 500 pages now cost ~1.8 KB each instead of ~82 KB. This is a real correction to
the ticket's stated rationale and it moves the proving test — it does **not** change the deliverable,
because the ticket's second sentence is untouched and is the actual defect:

> *"It is a data dump, not a map: a human cannot see from it where the system's classes and modules sit."*

Consequences, all recorded rather than quietly patched:

- **The proving test is re-chosen.** Size is no longer the honest red. The red is *absence of the
  spatial answer*: today's payload carries `crossings · layers · isolated · method · pages · stops ·
  truncated` and **none** of `tree · matrix · hubs · classes · modules · mirrors · reachability ·
  path_index`. That is the ticket's complaint, structurally checkable.
  → `test_the_map_answers_the_spatial_question_the_page_dump_could_not`.
- **AC2's two halves are no longer both red.** *Under 150 KB without the index* **is** red today
  (921,746 B — 6.1× over), because the 500 page bodies are the whole payload. *Under 1 MB with the
  index* passes today **by luck**, post-108, with 12 % of headroom. Both are still asserted; the
  first is the load-bearing one and the second is recorded as a regression lock, not a discovery.

### Findings the gates caught (6)

The first Docker run was **1611 passed, 6 failed**. Three were real, three were mine:

1. **AC2 measured 2,035,269 B — double the 969 KB I had measured by hand.** The test fixture used
   199 symbols per file, which put **every** one of the 5,399 directories over
   `DIR_SYMBOL_THRESHOLD`, so `tree` grew from 167 rows to ~5,399. The classifier was right and the
   fixture was wrong — and the finding is worth keeping: **the map's size follows `tree`'s
   cardinality, which the threshold bounds only for a repo of ordinary symbol density.** Fixed by
   having the test import `synthetic_dataset` from `scripts/viewer_report.py`, so the number
   asserted is the number the committed report prints. Two copies of a fixture is how this drifted.
2. **The synthetic had 102 layers and a 10,404-cell matrix.** Paths naming no responsibility fall
   through to structural grouping. No real repo looks like that (the anchor has 12), and it inflated
   the without-index page to 152,110 B — **1,490 bytes** under the 150 KB budget, a pass by luck.
   Fixed by building the paths out of 110's ratified vocabulary: 11 layers, 110 matrix entries, and
   the budget now passes at 70.9 %.
3. **AC4 was asserting something false.** "Every displayed figure moved" cannot hold: the layer
   count, the kind count, the bucket count and the prune threshold are all read from the dataset yet
   are *scale-invariant*, and a percentage is a ratio. Reformulated into a pair that is exact:
   **statically**, no digit survives in the template's visible text once style and script are
   stripped; **behaviourally**, every figure of four or more digits is disjoint between a render and
   the same dataset with counts scaled by 1009 — at four digits a figure *is* a count.
4. My figure extractor counted the digits **inside file names** (`CompiledModule00001.aa`), so every
   path looked like a rendered number. Fixed with token boundaries in the regex.
5. AC3 reversed `file_paths` to test order-invariance, but `_path_index` caps a **prefix**, so path
   order is part of the dataset's content, not of its assembly. The claim was wrong, not the code —
   now it reverses `nodes`/`edges`, which is the order-invariance 112 actually asserts.
6. The breakout test compared against `entries[i][1]`, but the index is front-coded and the
   injected path holds a `/` inside its markup — the name alone is only half of it. Reassembled.

### Delta-green (Docker — the authoritative gate)

- `main` baseline: **1601 passed, 0 failed**. This branch: **1618 passed, 0 failed** — `+17`,
  fully accounted: `test_onboarding_viewer.py` net `+13` (6 tests replaced by 19) and
  `test_onboarding_dataset.py` `+4` (the commit/threshold pair, the layer composition, the empty
  composition, and `file_kind_counts`).
- `ruff` clean · `mypy` clean over **57** source files — the count is unchanged, because AC7's
  "one viewer" was met by rewriting `viewer.py` rather than adding a module.

### AC2 — measured (`scripts/viewer_report.py`)

```
budgets: with index < 1,048,576 B   without index < 153,600 B
synthetic-anchor   with index 969,009 B  without 108,940 B  (index alone 860,143 B = 1.020x the
                   anchor's measured 843,439 B; 18,929 paths, 11 layers, 167 mapped dirs)
laravel_app        with index  44,457 B  without  43,632 B   (26 paths)  smoke only
symfony_demo       with index  53,693 B  without  51,799 B   (51 paths)  smoke only
brick_math         with index  48,021 B  without  47,011 B   (32 paths)  smoke only
anchor monorepo    not measured here: set CA_ANCHOR to an indexed repo root
```

**The honest comparison.** 089's viewer at the same cardinality was **921,746 B**; the map is
**108,940 B** without the search index — **8.5x smaller while answering more**. *With* the index it
is slightly larger than 089's page, and that is the trade the ticket asked for: 500 rendered module
bodies are exchanged for an 18,929-path search index with counterpart lookup. Both budgets hold.

**Two of the three pins map zero directories**, so the sitemap is empty there — which is why the
empty state names the threshold instead of drawing a blank box, and why that behaviour has its own
test rather than being left to chance.

### Verification sweep — the diff against the approved change list

17 files, `+1828 / -303`. Fifteen are the approved list. **Two deviations, recorded rather than
absorbed:**

1. **`scripts/dataset_report.py` was not on the list.** It calls `build_dataset` and would have kept
   compiling — the two new parameters default — but it would then report a dataset with no commit and
   no layer composition, and its query-timing sweep would omit `file_kind_counts` and so under-report
   the aggregate cost. Two lines added plus the new query in the sweep. Recorded as a deviation
   because "it still compiles" is not the same as "it is still correct".
2. **The `file_kind_counts` test went into `tests/test_onboarding_dataset.py`, not
   `tests/test_store.py`.** That file is where `node_kind_counts`, `edge_kind_counts`,
   `module_hubs`, `largest_classes` and `file_symbol_counts` are already tested, against a shared
   `_seeded` fixture. `tests/test_generate_onboarding.py` and `tests/test_architecture_overview.py`
   were on the list as *possible* consequences and needed no change — the new dataset fields are
   additive and neither asserts the dataset by exact equality.

CI's grep-gates re-run locally: **R1.1 ok · R2.2 ok** for both `adapters/` and `code_atlas/`. The
R2.2 unit twin inside the suite is wider than the CI gate and passed on the first run this ticket —
the denylist was written before the template, which is the change of habit 115's lesson asked for.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| — | **none** | — | **0 subagents dispatched this run** |
| main loop | — | — | `unmeasured (host does not surface usage)` |

Review and challenger were waived by the run's arguments; refine's exposure-checker and analysis's
Explore fan-out were not dispatched (the session's standing instruction), disclosed rather than
silently skipped.

## Decision log

| # | Decision | Why |
|---|---|---|
| W1 | The map renders the dataset **alone**; 089's Tour tab is dropped | `dataset.py` already named 116 as that renderer; AC3 is only meaningful under it. Ratified at Gate 1 |
| H1 | Rewrite `viewer.py`; add no module | AC7's "one viewer"; keeps the 57-module pin (R7.1) |
| H2 | `commit` goes in the dataset | keeps AC3 literally true; the churn objection is void since `index.html` is committed too |
| H3 | New `store.file_kind_counts()` | the composition bar has no substrate; bounded by files x kinds (R1.4/R4.3) |
| H4 | node becomes a test dependency | AC4/AC5/AC6 have no static formulation |
| H5 | The page exposes `CA_MAP` | a page that cannot be driven cannot be tested |
| H6 | Every empty or capped section states its own condition | AC5 applied uniformly, not only where an AC names it |
| — | `viewer_payload()` deleted, not ported | one payload shape; 089's second one is the drift 112 was written to end |
| — | Numbered section badges deleted | they are literal numbers (AC4) and would have made its assertion inexact |
| — | Proving test re-chosen mid-execute | the ticket's 31 MB was already ~97 % fixed by 108; the red is the missing spatial answer |
| — | AC4 split into a static and a behavioural half | "every figure moved" is false for a cardinality or a ratio |
| — | AC2 asserted on a synthetic at the anchor's measured shape | the pins are two orders of magnitude too small to falsify it |
| — | Anchor re-measure deferred to the operator (`CA_ANCHOR`) | absent on this host; 108/112–115 precedent |
