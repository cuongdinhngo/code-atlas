---
id: 211
slug: the-tour-population-is-ranked-but-never-grouped
title: "The tour ranks 24,535 modules by degree and then labels the top 500 by path vocabulary, so three-quarters of the anchor's tour lands in `Uncategorised` — the graph's own community structure is never asked"
phase: 3
milestone: M11
status: todo
depends_on: [084, 105, 110, 131, 204, 206]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

The tour picks its population by out-degree and then assigns each module a layer from **path
vocabulary** — a keyword match on the file path. On the anchor, the result is that the largest
category is the one that means *"no keyword matched"*:

| tour step | layer | modules covered |
|---|---|---|
| 2, 9, 10 | **`Uncategorised`** | **371** |
| 11 | Domain / Data | 52 |
| 1 | Views | 28 |
| 15 | Shared Library | 15 |
| 3, 4 | HTTP / Entry | 15 |
| 8 | Middleware / Auth | 7 |
| others | Tests, Config, Integration | 12 |

**371 of 500 — 74 %.** `overview.md` describes the bucket honestly as *"Modules whose path matched no
responsibility keyword — a naming-debt signal"*, and on a repo with genuine naming debt that reading
is fair. But a tour that spends three of its fifteen steps saying *"here are 371 files we could not
characterise"* has not oriented anyone, and the honesty of the label does not repair the step.

### The signal that was never asked

Layer assignment reads the **path**. Ranking reads the **degree**. Neither reads the one thing the
graph is actually good at: **which modules import each other.** Files that call into each other form
communities whether or not anyone named the directory well, and community membership is exactly the
fact that survives bad naming.

Nothing in `code_atlas/` computes one — no community detection, no clustering, no modularity, and
the runtime dependency list is one line (`fastmcp>=3,<4`). The reference implementation surveyed in
the user's notes uses Louvain community detection over the import graph to batch files into coherent
modules before anything else looks at them, and reports it as the change that made its per-module
analysis coherent.

### Why grouping and scoping are different tickets

[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) lets a reader **declare**
which tree is theirs — intent, supplied from outside. This ticket derives structure **from the
graph** — no declaration needed. They compose: scope narrows the population, grouping organises what
is left, and on a repo where nobody declares anything, grouping alone still beats
`Uncategorised × 371`.

## Scope

1. **Compute module communities from the edge graph** and use them where the tour currently uses
   path vocabulary alone. A community with no vocabulary hit is still a group with a shape — the
   files that call each other — and can be named after its own most-connected member rather than
   after nothing.
2. **Deterministically.** See Constraints: this is the whole engineering difficulty and it is not
   optional.
3. **Path vocabulary stays, and wins where it fires.** `Domain / Data` is a better label than
   `community-7` whenever the path says so. The community answers the case where vocabulary is
   silent, which today is 74 % of the tour.
4. **Report the disagreement.** Where a community straddles two vocabulary layers, that is either a
   layering violation or a mis-labelled directory, and it is more interesting than either signal
   alone. Surface it as a finding, bounded (**R5.8**).
5. **Measure against the current tour** on the anchor: the `Uncategorised` share, and whether the
   115 mirror-subtree finding (`legacy/alpha` ↔ `legacy/beta`, 4,575 shared paths) falls out as two
   communities or one. That second question is a real test of whether the grouping means anything.

### Explicitly not in scope

- **Adding a graph library.** **R8.2** — dependencies are `fastmcp` and stdlib. Louvain is a few
  dozen lines against an adjacency map already in memory; if it cannot be written that way, the
  finding is that it does not belong here.
- **Replacing the layer model.** [084](084_onboarding-layer-assignment.md), [110](110_layers-named-by-responsibility.md)
  and [105](105_dominant-subtree-loses-to-a-config-dir.md) settled how layers are named and ranked.
  This adds a signal to a layer that has none; it does not re-open the taxonomy.
- **Communities as a tool surface.** Whether an agent should query them is a separate measurement
  under [121](121_onboarding-question-class-never-measured.md).

## Constraints

- **R4.2 — identical input, identical output. This is the hard constraint.** Louvain as usually
  implemented depends on node iteration order and on random tie-breaking; the reference
  implementation falls back to alphabetical batching precisely because of this. A non-deterministic
  community assignment would make every regeneration a diff, so the implementation fixes the
  iteration order and every tie-break rule explicitly, and a test asserts that two runs over one
  index agree byte-for-byte. **Ship nothing that cannot pass that test.**
- **Sequence after [204](204_bare-name-resolution-has-no-language-predicate.md).** Community
  detection over an edge set carrying 186,417 false cross-language edges would merge the JavaScript
  and PHP subgraphs into one community and the result would look plausible. Do not measure this
  before 204 is on `main`.
- **Weight by confidence.** A HEURISTIC edge is weaker evidence of community membership than a
  RESOLVED one (**R5.2**), and treating them alike hands the grouping to the least reliable edges.
- **R8.2** — no new runtime dependency. **R1.1** — no language branches in the core.
- **R7.1** — the smallest thing that moves the 74 %. Not a clustering framework.

## Acceptance criteria

1. Two runs over one unchanged index produce identical community assignments, asserted by a test.
2. The `Uncategorised` share of the anchor's tour falls materially, and the before/after numbers are
   recorded — including the case where it does not, which is a valid outcome honestly reported.
3. A community with no vocabulary hit is presented with a name derived from its own members, never
   as a bare identifier.
4. Path vocabulary still wins where it fires; a fixture pins one such module.
5. Edge confidence weights the grouping, and a fixture shows a HEURISTIC-only cluster not being
   treated as a resolved community.
6. No runtime dependency is added.
7. The `legacy/alpha` ↔ `legacy/beta` question from Scope 5 is answered in the close-out either way.

## References

[084](084_onboarding-layer-assignment.md), [105](105_dominant-subtree-loses-to-a-config-dir.md),
[110](110_layers-named-by-responsibility.md) and
[131](131_tour-ranks-configuration-ahead-of-the-front-controller.md) (four passes at the tour's
population and labels, all of them ranking or vocabulary, none of them structure),
[115](115_mirror-subtree-detection.md) (the mirror finding this must reproduce or contradict),
[204](204_bare-name-resolution-has-no-language-predicate.md) (why this cannot be measured first),
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (declared scope, the
complement to derived structure).
