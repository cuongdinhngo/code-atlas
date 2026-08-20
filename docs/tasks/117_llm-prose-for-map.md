---
id: 117
slug: llm-prose-for-map
title: Onboarding — the map's structure is derivable, its prose is not; route prose through the seams (M12)
phase: 3
milestone: M12
status: todo
depends_on: [110, 111, 090, 091]
---

## Why this exists (measured, anchor monorepo)

The deterministic summarizer has nothing to read: **500 / 500** emitted pages carry `Summary: (none)`,
because `StructuralSummarizer` needs a docblock and this codebase has none. Structure is fully derivable;
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
