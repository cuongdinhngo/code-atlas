---
id: 098
slug: correspondence-relation-seam
title: 'The graph holds neither relation the anchor repo''s work is made of — port-of and variant-of'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [030, 011, 003]
---

## Goal
The anchor repo's dominant activity is *port a legacy file into the unified tree without breaking the
other region*. That chore is made of exactly two relations, and code-atlas holds **neither**:

1. **`legacy file ↔ unified file`** — which legacy source became which unified source.
2. **`region-A file ↔ region-B file`** — the same application, twice, and the two copies drift.

Every question the field session actually struggled with reduces to one of these. It read **1,913
lines** of two legacy sources and counted grid columns by eye to decide whether the port should be
one shared file or two region-specific ones. It answered *"has this been ported, and to what?"* with
a name-similarity search. It shipped a claim about historical route resolution that nothing in the
repo could check.

Meanwhile the index *notices* relation 2 and **refuses** on it: `subject_ambiguous` listing two
definitions of the same qname in two regional trees ([078](078_ambiguous-payload-still-picks-one-definition.md),
correct behaviour and a real improvement). One step further on is the useful primitive: *for this
symbol in region A, what is the region-B counterpart and how do they differ?*

## The decision this ticket exists to make
The field session proposed seeding relation 1 from a hand-maintained mapping (~4,300 entries,
`legacy path → unified path(s)`, CI-enforced) that the anchor repo already keeps.

**Adopted in principle; rejected as proposed.** Ingesting a specific repo's mapping file is
sample-over-standard (**R2**) — the exact thing CI gates. What the core may learn is **one generic
relation**: *this file/symbol corresponds to that file/symbol*, with a **source** and a
**confidence**, supplied by configuration and never by adapter knowledge. Under that primitive,
legacy↔unified and region-A↔region-B are the **same** relation with different sources, and so is any
fork/vendor/variant pair in any language.

The design must answer, in this order:
1. **Is a correspondence an edge, or its own table?** It is not a call, an include, or an
   inheritance; it relates *files* as often as symbols, and it can be many-to-many.
2. **What are the admissible sources, and how does the core stay ignorant of their format?** A
   declared config source (path pairs the repo supplies) is the baseline. Weigh, and either adopt or
   reject with reasons: a **basename/path-shape** source computed from rows the core already holds
   — *N files share a basename across different roots* — which needs no adapter and no language
   knowledge at all, and which the same session shows is the shape behind its highest-value defect of
   the day (a shared front-end asset that was one region's lineage).
3. **What does a stale correspondence look like?** The strongest argument for holding this at all:
   *a mapping that nothing verifies is a mapping that is quietly wrong.* If the graph holds both
   sides, it can report that an entry points at a file that no longer defines what it claims.
4. **What does it refuse to answer?** Correspondence is asserted, not inferred. The tier and the
   source must ride on every hit so nobody mistakes a config assertion for a resolved edge.

## Evidence (field interview, 2026-08-14, §8.2 — opinion, explicitly flagged as such by its author)
- §1 Moment 2: the region-split decision was made by reading 1,196 + 717 lines end to end and
  counting columns by eye. A correspondence query would have answered *"region A defines 7 top-level
  functions, region B defines 6, 4 names differ"* in one call.
- §8.2 (2): the anchor project keeps a dedicated pattern file for one defect class — *"A and B
  diverged and someone assumed they hadn't."* That is this relation, unheld.
- §8.2 (3): two confirmed instances in three days of a shared asset being one region's lineage,
  silently disabling the other region's UI with **nothing in any server log**.
- §6.5 / §8.2 (1): the one genuine win of the session — *"has this been ported, and under what
  name?"* — was answered by name similarity, and the interview downgraded it precisely because
  similarity is not correspondence.

## Scope / Deliverables
- **Design first, and expect the design to be most of the ticket.** Answer the four questions above
  with a written verdict each; a rejected alternative is a deliverable here, not a footnote.
- **A storage shape** for correspondences with `source` and `confidence`, and a migration verdict
  (schema bump ⇒ [050](050_schema-version-mismatch-recovery.md)'s recovery path must handle it).
- **One config-fed source**, format-declared by the core, populated by the repo. No repo's file
  format is hardcoded.
- **A query surface** — decide between extending an existing tool and adding one, against
  [061](061_payload-weight.md) and the interview's own §5 warning that the surface is already wider
  than one session can hold.
- **A staleness check**: given a declared correspondence, report when one side no longer holds what
  the other claims.
- **Explicitly out of scope:** inferring correspondences by similarity heuristics. That is an LLM-shaped
  judgement and would break **R4**; if the design wants it, it belongs in Phase 3 behind the
  Summarizer seam, not here.

## Constraints
- **R2 (CI-gated)** — no repo's names, paths, or mapping-file format in `code_atlas/` or any adapter.
  The anchor's mapping is a *test fixture at most*, never a dependency.
- **R1.1** — zero language branches; correspondence is language-agnostic by construction.
- **R4** — deterministic: asserted pairs in, identical rows out. No ranking, no fuzzy matching.
- **R1.2 / YAGNI** — one seam, one source to start. Do not build a plugin system for sources.
- Scale: the anchor holds 18,926 indexed files; a many-to-many table over that must not slow status
  or nav answers. Measure.

## Acceptance criteria
- A written design verdict on each of the four questions, with rejected alternatives.
- A fixture repo with declared correspondences produces queryable pairs carrying `source` and
  `confidence`, pinned by tests.
- The staleness check reports a deliberately rotted correspondence in a fixture.
- A grep-gate (or an extension of the existing R2 gate) proves no repo-specific mapping format leaked
  into the core.
- Payload weight and query latency measured before/after on a large synthetic index.

## References
Field interview (round-5 companion, 2026-08-14) §1 Moment 2, §6.5, §8.1 ("fit to this repo's dominant
work type — 35 %"), §8.2 (1)(2)(3), §8.4 item 1, §8.5. Related:
[078](078_ambiguous-payload-still-picks-one-definition.md) (the refusal this builds past),
[030](030_alias-indirection-edges.md) (precedent for a non-call relation),
[003](003_config-and-ignore.md) (where a declared source would live),
[050](050_schema-version-mismatch-recovery.md) (schema migration),
[094](094_class-constant-in-array-literal-is-not-an-edge.md) (the other unheld relation from round 5).
