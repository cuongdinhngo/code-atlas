---
id: 205
slug: a-module-page-per-node-budget-slot
title: "`generate_onboarding` writes exactly `impact_max_nodes` module pages — 500 on every repo, each headed `Stop N of 500` while the tour beside it has 15 steps, and the 107 filler gate never fires because one edge counts as a fact"
phase: 3
milestone: M11
status: todo
depends_on: [106, 107, 108, 109, 111, 118]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

A regenerated `docs/onboarding/` is **505 files — 3.0 MB of bytes, 6.1 MB on disk**, because 500 of
them are sub-kilobyte files each taking a 4 K block. `modules/` is 3.6 MB of that disk figure — and
holds exactly **500** pages. Not "about 500": 500, because that is
`DEFAULT_IMPACT_MAX_NODES` (`code_atlas/config.py:54`).

The count is a node budget that leaks into a file count through four hops, none of which mean to
decide how many pages a repo gets:

```
code_atlas/tools/generate_onboarding.py:99   subgraph = store.tour_subgraph(max_nodes=config.impact_max_nodes)
code_atlas/tools/generate_onboarding.py:114  tour_files = subgraph.files
code_atlas/onboarding/artifact.py:375        stops = ordered_stops(tour_files, tour_edges, entry_points)
code_atlas/onboarding/artifact.py:385-398    one ModulePage per stop
```

`impact_max_nodes` is the **`impact` tool's** traversal ceiling. Nothing about it is a statement
that a reader wants 500 pages, and no repo — 200 files or 24,535 — gets a different number.

### What the 500 pages actually contain

Measured over the emitted tree:

| | |
|---|---|
| pages | 500 |
| page size | min 323 B · median **893 B** · max 1,964 B |
| pages rendering `No leading doc comment above the indexed declaration in this file.` | **277** |
| pages rendering a docline that is a bare comment delimiter (`/**` ×186, `/*` ×8, `/*!` ×5, `*/` ×2) | **201** |
| pages carrying a sentence that describes the file | **~2** |
| pages with `incoming: (none)` | 125 |
| pages with **both** lists empty | **0** |

The median page is under 900 bytes and carries: the path (already in the filename), a Role, a Layer,
a "Stop N of 500" line, and a truncated neighbour list. For 277 the Summary line is a sentence saying
there is no summary; for 201 more it is a comment delimiter like `/**`, which is worse — it *looks*
like a summary. Across all 500 pages, roughly **two** carry a sentence that describes the file.

> **Measurement provenance.** Every figure above was read off an artifact generated from the anchor's
> **field index before [204](204_bare-name-resolution-has-no-language-predicate.md) landed**, which
> carries 343,131 JavaScript/TypeScript-declared `CALLS` edges resolving to PHP targets — 100 %
> HEURISTIC, 0 RESOLVED — verified directly against `.code-atlas/graph.db` on 2026-09-02. Anything
> derived from **degree** is therefore contaminated, and JS files are the contaminated side: they
> carry the false out-edges that bought them their rank. The structural findings below do not depend
> on any edge and stand as written.

> For this ticket that touches two rows only: `incoming: (none)` (125) and `both lists empty` (0) are
> edge-derived and must be re-counted post-204 before C1's replacement criterion is chosen — Scope 3
> already says so. The page **count** (500), the page **sizes**, the 277 missing doclines and the
> `Stop N of 500` header are structural and do not move.

### The 107 gate cannot fire

[107](107_a-page-with-no-neighbours-and-no-summary-is-filler.md) named the defect *"a page with no
neighbours and no summary is filler"* and [109](109_onboarding-artifact-quality-gate.md) made C1 the
guard. As implemented (`code_atlas/onboarding/quality_gate.py`):

```python
if not (page.docline or page.fan_in or page.fan_out):  # C1: the 107 filler rule.
    raise QualityGateError("C1", page.file, "page carries no fact beyond its own path")
```

The measured `both lists empty` count is **0**, so C1 raised zero times on a run in which no page
carries a usable summary at all. The rule is an `and` over three signals where the reader's question is a
judgment about one: *does this page tell me something I could not read off the path?* A single
inbound edge — including a HEURISTIC one — satisfies it. C1 is a non-emptiness check wearing 107's
name, and the ticket that closed 107 is therefore closed against a guard that does not implement it.

### `Stop N of 500` against a 15-step tour

[111](111_tour-is-narrative-steps.md) replaced the 500-stop tour with narrative steps, and the gate
holds it there (`MAX_TOUR_STEPS = 15`). Today's `tour.md` has exactly 15 numbered sections, and their
`Covers N module(s)` figures sum to 500 — the steps *group* the same 500 modules, so the artifact is
not internally inconsistent in its arithmetic.

It is inconsistent in its **unit**. `artifact.py:720` renders every page header as:

```
## In the tour   Stop 65 of 500. entry point (zero inbound)
```

A reader who has just read a 15-step tour is told this file is stop 65 of 500. "Stop" means a tour
step in `tour.md` and a module slot in `modules/`, and nothing in either file says so. 111 moved the
tour off stops and left `pages` still enumerating them.

## Scope

1. **Decouple the page count from `impact_max_nodes`.** Whatever decides how many pages an artifact
   emits is its own resolved setting with its own name and default, not a borrowed traversal
   ceiling. `impact`'s budget stays where it is and keeps its current default.
2. **One meaning for "stop."** Either the page header cites the tour step it belongs to (`Step 9 of
   15 — Uncategorised (2/3)`), or it cites no tour position at all. Not a second numbering.
3. **Make C1 enforce what 107 specified.** A page earns emission by carrying a fact a reader could
   not get from the path. Pick the criterion deliberately and write it down — a docline, or a
   RESOLVED edge, or a named role that is not the default — and let the gate fail the run that
   violates it, per [109](109_onboarding-artifact-quality-gate.md)'s contract that `build_artifact`
   raises rather than writing a bad tree.
4. **A way to emit no pages at all.** `detail_level: minimal` currently omits the cache path and
   keeps all 500 pages. A reader who wants `overview.md` + `tour.md` + `flows.md` and no
   `modules/` tree has no way to ask.
5. **A size budget on the emitted tree**, asserted the way the repo already budgets its own docs
   (`tests/test_doc_size_budget.py`). 6.1 MB of generated Markdown landing in a consumer's repo is a
   number someone should have had to argue for.

### Explicitly not in scope

- **The aggregates.** `overview.md`'s mirror-subtree table, business-module table and reachability
  split are the artifact's load-bearing content and must come out byte-identical (R4.2). This
  ticket removes filler; it does not re-derive a single figure.
- **Which files are chosen.** Scoping the artifact to the tree a reader works in is
  [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md). If 206 lands first,
  re-measure before setting a default here: the two tickets both move the page count and neither
  should be tuned against the other's stale number.
- **Re-tiering edges.** [204](204_bare-name-resolution-has-no-language-predicate.md) already did
  that. Note that 204 will change what the neighbour lists say and therefore what C1 sees, which is
  a reason to re-measure the docline/125/0 figures on a post-204 index before choosing C1's criterion —
  not a reason to wait.

## Constraints

- **R7.1** — the smallest useful thing. The defect is "a knob's default became a content decision";
  the fix is a knob of its own, not a new page format.
- **R6.5** — C1's replacement ships only once it has been **observed failing** on a page the current
  gate passes. On the anchor every one of the 500 is a candidate; commit one of each failure shape —
  the honest sentence and the bare `/**` — as fixtures.
- **R6.8** — AC3 below is phrased as a failure mode, so it needs a guard that can exhibit it.
- **R6.9** — assert at the consumer: the guard reads the **emitted tree**, not `ModulePage` objects.
- **R4.2** — identical input, identical output. A page-count change is a change to committed files
  in every downstream repo; the conformance tests and any golden artifact move with it.

## Acceptance criteria

1. The number of module pages is set by a named onboarding setting; changing `impact_max_nodes`
   alone changes no page count, and a test pins that independence.
2. No emitted page cites a tour position in a unit `tour.md` does not use.
3. A page carrying no fact beyond its own path fails the gate — demonstrated by a committed fixture
   that the pre-change gate passes and the post-change gate rejects.
4. A caller can request an artifact with no `modules/` tree, and the quality gate still runs over
   what is emitted.
5. `overview.md`, `tour.md` and `flows.md` are byte-identical to the pre-change run on the same
   index, except where AC2 changed a page header.
6. The emitted tree has an asserted size ceiling, and the number is argued in the test, not merely
   recorded.
7. `TOOLS.md` and the `generate_onboarding` docstring describe the new setting; per **R7.6** the
   text they supersede is deleted, not stacked on.

## References

[106](106_tour-budget-buys-500-alphabetical-isolated-files.md) (the budget first bought 500 files),
[107](107_a-page-with-no-neighbours-and-no-summary-is-filler.md) (the filler rule this closes for
real), [108](108_module-page-neighbour-list-is-unbounded.md) (the neighbour cap the pages already
carry), [109](109_onboarding-artifact-quality-gate.md) (the gate contract),
[111](111_tour-is-narrative-steps.md) (15 steps, and the `pages` reader it did not move),
[118](118_module-summary-seam-gets-empty-facts.md) (why the doclines are empty or are delimiters),
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (which files, as opposed
to how many).
