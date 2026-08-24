---
id: 139
slug: map-is-a-snapshot-so-nothing-shows-architectural-drift
title: The map is a snapshot, so nothing tells a reviewer what the agent changed about the architecture
phase: 3
milestone: Supervision
status: done
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
  deltas (113's populations, not one number).
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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `feat/139-map-is-a-snapshot-so-nothing-shows-architectural-drift`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M

## PREMISE / REFINE

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`refine skipped: 0 unresolved product-decisions`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

## Design

- Pure `code_atlas/onboarding/architecture_diff.py` over two dataset/manifest JSON snapshots
- Tool `diff_architecture(before, after)` — markdown + structured `diff`; refusals for `index_root` /
  schema mismatch (direction-aware)
- `manifest.json` stamps `index_root` + `last_ref` (operational envelope; no `DATASET_VERSION` bump)
- AC6 **deferred** to 142 — same ordering as 138's AC7

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | `tests/test_architecture_diff.py` + fixtures |
| AC2 | ✅ | waived | explicit no-change sentence |
| AC3 | ✅ | waived | `index_root_mismatch` refusal |
| AC4 | ✅ | waived | one-sided caveats |
| AC5 | ✅ | waived | `before_older_than_after` |
| AC6 | deferred | — | 142 |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| explore | dataset surface | unmeasured (host does not surface usage) |

## Review of PR #167 — three defects fixed in-branch

1. **Phantom entry-point drift.** `_entry_points` read the `web_entry` **sample** and ignored the
   `sample_truncated` flag published beside it. Two cappings of one unchanged bucket differ, so on
   any repo past the sample cap the report invented entry points. Probed on the fixture: count
   50 → 50, `reachability_deltas: ()`, yet **5 added and 5 removed** with `unchanged: False`. A
   truncated sample now suppresses the set delta, sets `entry_points_sampled`, and the markdown says
   the comparison was skipped and why — a dropped section otherwise reads as *nothing moved*.
   `count > len(sample)` counts as truncated too, so a snapshot that omits the flag still says so.
2. **`int(snapshot["version"])` raised instead of refusing.** `diff_architecture` promises refusals
   are returned, never raised; a non-numeric version escaped as `ValueError`. The `TypeError` guard
   in `_dataset_direction` could never fire (both sides were already `int`), so
   `DIRECTION_UNRECOGNISED` was dead code. Version parsing now returns the refusal that branch
   was written for.
3. **Forked reason vocabulary, again (see #166).** Five private `REASON_*` plus a bare
   `"snapshot_not_found"` literal, none in the pinned `NAV_REASONS`. All five joined the pinned
   tuple; the module keeps `REFUSAL_*` names, since onboarding never imports a tool, and
   `test_every_refusal_reason_is_in_the_pinned_nav_vocabulary` is the R6.7 pin that stops them
   drifting apart.

The AC1–AC5 fixtures publish untruncated samples and integer versions, so none of the above was
reachable through them. Five tests added; #1 and #2 are red without the fixes.

**Not fixed, noted:** `_file_layers` merges `hubs` and `classes` into one dict, so a file in both
with different labels takes the `classes` value silently — and both are bounded top-N lists, so
`layer_reassignments` and `hub_movements` only cover their intersection: a file entering or leaving
the published hub list is invisible to the diff. Same sampling family as #1, but the ticket's Scope
names *hub rank movement*, which the intersection does answer; widening it is a design call.
