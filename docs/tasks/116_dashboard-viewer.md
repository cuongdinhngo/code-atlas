---
id: 116
slug: dashboard-viewer
title: Onboarding — replace the 31 MB page dump with a navigable system map (M11)
phase: 3
milestone: M11
status: todo
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
