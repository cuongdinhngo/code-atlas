---
id: 210
slug: the-artifact-has-one-shape-for-every-reader
title: "`detail_level` on `generate_onboarding` changes the MCP response and not one byte of the written artifact, so a first-week developer and the engineer auditing coupling are handed the same 6.1 MB tree"
phase: 3
milestone: M12
status: todo
depends_on: [088, 112, 121, 205, 207, 209]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

`generate_onboarding` takes `detail_level: DetailLevel = "standard"`, and everything it gates lives
in `_payload` (`code_atlas/tools/generate_onboarding.py:291`):

```python
if detail_level == "standard":
    payload["cache"] = f"{CACHE_DIR}/{CACHE_NAME}"
    payload["isolated_modules"] = len(artifact.isolated)
    payload["prose_calls"] = prose.calls
    payload["prose_declined"] = prose.declined
```

Every one of those is a field of the **MCP response**, which the caller reads once and drops. The
**written artifact** — `overview.md`, `tour.md`, `flows.md`, `modules/`, `index.html`,
`manifest.json` — is byte-identical at `minimal` and at `standard`. The knob named for how much
detail the reader wants does not reach the thing the reader keeps.

So the artifact has exactly one shape, and on the anchor that shape is 6.1 MB across 505 files.

### The two readers want opposite artifacts

This was measured by reading the generated tree as each:

| | first-week developer | engineer auditing the system |
|---|---|---|
| wants | where my work lives, how to run it, ten files to open | coupling hotspots, mirror-subtree overlap, what is unreachable |
| the tour | 15 steps, none of them in the tree they will edit | irrelevant — they know the layout |
| `modules/` (3.6 MB, 500 pages) | median 893 B, mostly path restatement | irrelevant — they query the graph |
| `overview.md` aggregates | unreadable — 12 layers, 24,535 modules, a 99-row cross-layer table | **this is the whole value** |
| what is missing | run/test commands, entry-point names, domain vocabulary | confidence attribution on the aggregates |

The load-bearing content for one is noise for the other, and the artifact spends **3.6 MB of 6.1 MB**
on the section neither of them named as their primary need.

### Why a knob, and why not just cut

[205](205_a-module-page-per-node-budget-slot.md) removes filler and
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) narrows the population, and
both are right independently. Neither answers *who is this for*, and without that the page count is
being argued in the abstract: 500 is indefensible for both readers, but the right number for a
newcomer (a handful, deeply written) and for an auditor (zero) are different numbers, not one
compromise. **R5.8** — rank inside the statement that truncates — needs to know what the reader is
optimising for before it can rank.

The prior art is external: the reference implementation surveyed in the user's notes carries a
persona axis (non-technical / junior / experienced) through its viewer, and it changes what is shown
rather than only how much. The idea transfers; its architecture does not (see Constraints).

## Scope

1. **An audience setting that reaches the written artifact**, not only the response. Two named
   audiences to start (**R7.1**) — the newcomer and the maintainer — with the current output as one
   of them or as an explicit third.
2. **Each audience is a stated content contract, not a verbosity dial.** Write down, per audience,
   which sections are emitted and why that reader needs them. A newcomer artifact that is the
   maintainer's with fewer bytes has failed the ticket.
3. **The artifact says which audience it was written for**, beside 209's summarizer stamp — a
   committed tree that cannot say who it is for cannot be judged, or regenerated to match.
4. **Reconcile with `detail_level` rather than adding a second knob beside it.** Either
   `detail_level` grows to reach the artifact, or it stays a payload knob and the audience setting
   is separate and documented as such. One decision, written down (**R1.8**).
5. **Measure both artifacts against the 121 harness.** An audience that answers fewer questions of
   its own class than today's single artifact is not shipped.

### Explicitly not in scope

- **A viewer feature.** The reference implementation puts persona in a React store; this is about
  the committed Markdown, which is what code-atlas ships and what a consumer commits.
- **New content.** [207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md) owns the
  orientation section. This ticket routes existing and 207's content to a reader; it does not author
  any.
- **More than two audiences.** Three named personas with overlapping needs is the gold-plating
  **R7.1** exists to prevent.

## Constraints

- **R4.1 / R4.2** — the audience is a resolved setting, so output stays deterministic per audience.
  No inference of who is reading.
- **R1.8** — one place decides what an audience emits; the Markdown writer, the dataset and the
  viewer all read that decision rather than re-deriving it, which is
  [127](127_caveats-drop-at-the-artifact-layer.md)'s lesson.
- **R3.5** — the dataset carries the audience; bump `DATASET_VERSION`.
- **R7.4 — no dead abstractions.** Two audiences with one real difference between them is a
  configuration flag wearing a bigger name; if the content contracts in Scope 2 come out nearly
  identical, that is the finding, and the ticket closes as *not built* with the measurement recorded.
- **Do not adopt the reference implementation's shape.** Its pipeline is orchestrated by prompt files
  the host LLM executes, which trades **R4.2** for flexibility; borrow the axis, keep the
  deterministic core.

## Acceptance criteria

1. An audience setting changes which sections the written artifact contains, provably, on the anchor.
2. Each audience has a written content contract naming its sections and the reader need each serves.
3. The artifact states its audience, and regenerating with the same audience is byte-identical.
4. The existing `detail_level` behaviour is either extended or explicitly left alone, and `TOOLS.md`
   says which — with the superseded text deleted (**R7.6**).
5. The 121 harness scores each audience on its own question class; neither regresses against
   today's artifact.
6. If Scope 2's contracts prove near-identical, the ticket closes unbuilt with that comparison
   recorded, and the BACKLOG row says so.

## References

[088](088_generate-onboarding-markdown.md) (the written artifact),
[112](112_onboarding-dataset-contract.md) (where the audience field lives),
[121](121_onboarding-question-class-never-measured.md) (the harness that judges each audience),
[127](127_caveats-drop-at-the-artifact-layer.md) (three renderers, one decision),
[205](205_a-module-page-per-node-budget-slot.md) (how many pages — a question this reframes),
[207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md) (the newcomer content this
routes), [209](209_a-committed-artifact-cannot-say-which-summarizer-wrote-it.md) (the other stamp
the artifact should carry).
