---
id: 143
slug: the-system-map-has-no-diagram
title: The system map has no diagram — every relation is a table, and PILLAR 2 promised diagrams
phase: 3
milestone: Presentation
status: done
depends_on: [112, 116, 110, 130]
---

## Why this exists

[PLAN §1](../PLAN.md#1-goals--non-goals) PILLAR 2 says the rendering is built *"as diagrams and
documents"*. There is no diagram. `grep -i 'mermaid|graphviz|<svg'` over `code_atlas/` returns
**nothing**, and the 116 map renders a sitemap treemap, a layer table, the full layer × layer matrix,
hubs, the 114 capability table, the 113 split and the 115 mirror panel — **all tabular**.

The cheap part: **the layer × layer matrix already is an adjacency matrix.** A boxes-and-arrows diagram
is a second *rendering* of numbers 112 has already computed, not new graph work. Nothing about the
graph, the store or the enrichment changes.

**The form is decided by a constraint the viewer states about itself** (`onboarding/viewer.py`
docstring): one self-contained offline HTML page, `connect-src 'none'`, *no external stylesheet,
script, font or image*, so a `fetch` cannot be added later. Mermaid from a CDN is impossible **by
construction**, and bundling it into the page breaks the invariant that page advertises. So the diagram
is emitted as **mermaid source text into the markdown `generate_onboarding` already writes** under
`docs/onboarding/`: GitHub, VS Code and JetBrains render it, the artifact stays committable, and a
diagram **diffs** in review — which is more than the HTML page can do.

Provenance: the architecture review of 2026-08-23. BACKLOG's standing note — *"Auto-generated docs and
diagrams stay unscheduled: that verdict licenses neither"* — is what this ticket asks to revisit, for
**this** diagram only: a layer graph is a lookup, not a reading order, and 121's split verdict was
positive on lookups (12/12, recall 1.0) and negative on ordering.

## Scope

- A deterministic mermaid `flowchart` from the layer × layer matrix and 110's layer names. No literal
  number in the template — same rule as the viewer (116 AC4).
- Edge labels are the matrix counts, and **the arrows reconcile to the cells** — the same arithmetic
  guard 127 put on the artifact.
- **Tier partition (136).** An arrow whose evidence is HEURISTIC-only is either dashed **and** labelled,
  or omitted **and** counted. It is never drawn identically to a confirmed arrow: a diagram has no
  column to print a tier in, which is exactly why the distinction has to be in the ink.
- A node cap, with the cut disclosed (108/124's rule: a capped list says it was capped).
- No repo, framework, directory or language name in the generator (R2.2 — the prototype 116 replaced
  named nine).

## Acceptance criteria

- **AC1** Red first (R6.5): a fixture matrix renders a known mermaid body, byte-identical (R4.2).
- **AC2** Arrow labels sum to the matrix cells they came from, asserted.
- **AC3** A HEURISTIC-only relation is visually distinguishable in the emitted text, asserted on a
  fixture that has one.
- **AC4** A capped diagram says so in the rendered output, and the cap is not silent.
- **AC5** The mermaid text is validated **without adding Node**: a golden fixture plus a Python-side
  syntax-subset check. No npm on the core's build path.
- **AC6** Committed diagrams for the pinned public repos, so a reviewer can see what it looks like on a
  real layout rather than a fixture.

## Out of scope

- **Bundling mermaid into the HTML viewer.** That is the invariant this ticket routes around, not a
  cost it pays.
- **Class diagrams** — [144](144_class-diagram-is-a-projection-minus-the-return-type.md).
- **Sequence diagrams.** Two blockers, neither about rendering: participants are receiver types, and 136
  measured ≥99 % of the HEURISTIC share as missing local type information (`brick/math` 1,659 edges);
  and no `EDGE_KINDS` member carries a branch or a loop, so `alt`/`loop` frames have no source. Line
  order (`edges.line`) is not execution order.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `feat/143-the-system-map-has-no-diagram`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M

## PREMISE / REFINE

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`refine skipped: 0 unresolved product-decisions`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

## Design

- Pure `code_atlas/onboarding/layer_diagram.py` mermaid `flowchart LR` from layer names + crossings
- HEURISTIC-only arrows dashed (`-.->`); DYNAMIC-only omitted and counted
- `GraphStore.dependency_edges_with_tier` — same pair set as `dependency_edges`, winning tier for AC3
- Injected into `overview.md` via `render_overview`; HTML viewer unchanged
- Node cap = `CA_MAX_RESULTS`, disclosed as "N shown of M; the graph is capped"
- AC6: `docs/benchmarks/143_layer_diagrams.md` from pinned indexes

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | golden mermaid body |
| AC2 | ✅ | waived | label sum == cell counts |
| AC3 | ✅ | waived | `-.->` on HEURISTIC-only |
| AC4 | ✅ | waived | cap disclosure |
| AC5 | ✅ | waived | `validate_mermaid_flowchart` |
| AC6 | ✅ | waived | pinned-repo mermaid in benchmarks |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| explore | diagram surface | unmeasured (host does not surface usage) |

## Review of PR #168 — two gaps fixed in-branch

1. **The node cap dropped arrows silently.** `render_layer_flowchart` truncates layers, then keeps
   only edges whose both endpoints survived — and disclosed the layer count alone. `## Cross-layer
   edges` right below the diagram still lists every crossing, so a reader sees a crossing in the
   table with no arrow above it and nothing saying why. AC4's own test watched it happen: at
   `node_cap=1` it asserted `"N1" not in mermaid` and then called the layer-count sentence the
   disclosure. `LayerDiagram.omitted_capped` now counts the arrows the cap cost and `render_overview`
   says so, naming the table that still lists them (108/124).
2. **AC5's validator never ran on the artifact.** `validate_mermaid_flowchart` was called from the
   benchmark script and the tests, never from the write path, so `generate_onboarding` could commit
   an unvalidated diagram. `render_overview` now validates what it is about to write. That also
   exposed that `_label` stripped `"` but not newlines — a dominant-subtree layer name is a directory
   name, not a vetted vocabulary word, and a newline in one breaks the line-structured diagram
   outright (the added test fails with `ValueError` from the validator without the strip).

Three tests added; all three are red without the fixes above.

**Checked and correct:** `dependency_edges_with_tier` really is the same pair set as
`dependency_edges` — identical `WHERE` / `GROUP BY` / `ORDER BY` — so routing `generate_onboarding`'s
`edges` through it changes nothing for metrics, layers or the tour. It has its own tests in
`test_onboarding_metrics.py`.

**Not fixed, noted:** the pin script (`scripts/layer_diagram_report.py`) hardcodes `node_cap=50` and
does not print `omitted_capped`. With ≤ 13 layers it is always 0, so the pins are unaffected; if a
sample ever exceeds the cap the report would omit arrows without saying so.
