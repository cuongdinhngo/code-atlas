---
id: 143
slug: the-system-map-has-no-diagram
title: The system map has no diagram — every relation is a table, and PILLAR 2 promised diagrams
phase: 3
milestone: Presentation
status: todo
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
