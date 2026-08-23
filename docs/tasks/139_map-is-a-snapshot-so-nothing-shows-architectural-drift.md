---
id: 139
slug: map-is-a-snapshot-so-nothing-shows-architectural-drift
title: The map is a snapshot, so nothing tells a reviewer what the agent changed about the architecture
phase: 3
milestone: Supervision
status: todo
depends_on: [112, 077, 127]
---

## Why this exists

Provenance: the same architecture review of [PLAN §1](../PLAN.md#1-goals--non-goals) on 2026-08-23. The
gap is verified in the tree; no session has been measured asking for it.

PILLAR 2's supervision half reads: *"the rules and the architecture are given to the agent up front, and
the agent still drifts; the map shows what was actually generated, so a human can see where it went."*
The emitted artifact is a **single-revision rendering** — [112](112_onboarding-dataset-contract.md)'s
dataset plus [116](116_dashboard-viewer.md)'s map. **Drift is a two-revision fact**, and nothing compares
two.

`git diff` is not the answer: it reports lines. It does not say *a new layer appeared*, *`Domain` now
depends on `Http`*, *the hub gained 40 inbound edges*, *two entry points became four*. Those are the
statements a reviewer signs off on, and each one is a field 112 already publishes.

The pieces are present and the work is cheap, which is most of the argument for doing it:
[112](112_onboarding-dataset-contract.md) made one compact dataset the contract behind every renderer,
[077](077_index-cannot-name-the-revision-it-describes.md) gave the index the revision it describes, and
[127](127_caveats-drop-at-the-artifact-layer.md) made caveats survive into the artifact. A diff is a
**pure function over two datasets** — no second pipeline, which is the constraint PLAN §1 puts on
everything in this pillar.

## Scope

- A deterministic diff of two 112 datasets: modules added/removed, layer reassignments, **new
  cross-layer dependency pairs**, hub rank movement, entry-point set changes, reachability-bucket
  deltas (113's four populations, not one number).
- Both sides name their revision in the 077 vocabulary (`last_ref`), and the output states which side is
  which.
- Caveats are carried from both sides and never merged silently (127's family).
- Rendering: a markdown table. Deterministic ordering throughout (R4.2).

## Acceptance criteria

- **AC1** A→B diff over two committed dataset fixtures with a known delta, red first (R6.5).
- **AC2** Identical revisions produce an explicit *no architectural change* statement, not an empty
  file — an empty artifact reads as a failed run.
- **AC3** Both revisions are named; two sides from different `index_root`s are **refused**, not
  rendered (071's rule: an answer states the tree it describes).
- **AC4** A caveat present on one side only is reported as one-sided.
- **AC5** A dataset-schema difference is detected and refused rather than diffed field-blind — the 050
  lesson: a version mismatch must be direction-aware, not read as corruption.
- **AC6** Cost row through the question class [142](142_supervision-question-class-has-no-baseline.md)
  owns.

## Out of scope

- **Rendering the diff inside the HTML map** (116) — a follow-up once the diff exists.
- **LLM narration of the diff.** 117's seams already own prose, opt-in and outside the core (R4.1).
- **Diffing two different repositories.** AC3 refuses it on purpose.
- **Judging whether a drift is bad.** The diff states what moved; the rule check
  ([138](138_architecture-rules-are-never-asked-of-the-graph.md)) is where a verdict belongs.
