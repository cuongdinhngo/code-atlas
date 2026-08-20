---
id: 115
slug: mirror-subtree-detection
title: Onboarding — sibling subtrees duplicating 62% of their paths, and nothing says so (M11)
phase: 3
milestone: M11
status: todo
depends_on: [112, 098]
---

## Why this exists (measured, anchor monorepo)

Two sibling subtrees hold near-copies of the same application. Counted from the index by relative path:

| | Count |
|---|---:|
| relative paths present under **both** subtrees | **4,244** (62 %) |
| present under the first only | 1,522 |
| present under the second only | 1,134 |

Corroborating signals from the same index: the DB-access file exists three times with 4,050 / 4,041 /
3,926 dependents; the largest class in the repo is a vendored PDF library present in **four** copies;
the tour's SCC lines are dominated by pairs of same-named files across the two trees.

This is the highest-value fact the map produces, and the current artifact never states it. The reviewer's
verdict was that seeing it as three numbers is not enough — they need it **as a lookup**: paste a path,
get the parallel path, or get told there isn't one. The mockup does exactly that, and the absence case
(`no counterpart`) is the more useful answer, because it marks divergence.

## Relationship to task 098

[098](098_correspondence-relation-seam.md) asks whether the *graph* should hold a "this file is a copy or
port of that one" relation, and is **deferred pending evidence**. This ticket is that evidence: it
produces the correspondence set structurally, without a new edge kind, and measures how large and how
useful it is. If it proves out, 098 can decide about a real relation with numbers in hand. If it does not
generalise past one repo, 098 stays deferred and this stays a presentation-layer fact.

## Scope

- Detect candidate mirror subtrees structurally: sibling directories at the same depth whose relative
  path sets overlap above a threshold. No repo names, no configured pair (R2.2).
- Report `both / only-A / only-B` counts, the overlap fraction, and a bounded sample.
- Expose counterpart resolution over the dataset's path index (112) so a renderer can answer
  "given this path, what is its sibling?" — including the negative answer.
- Confidence caveat: identical *path* is not identical *content*. The output must say it compares paths,
  not bytes, and must not claim the files are copies.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with `a/x`, `a/y`, `b/x` reports one shared path and one on each side —
   observed red against today's code, which has no such concept.
2. **AC2.** Counterpart resolution is symmetric, and a path outside any mirror subtree returns a clean
   negative rather than a guess.
3. **AC3.** A repo with no mirrored subtrees reports none — proven on a pinned public repo, so the
   detector is not manufacturing structure.
4. **AC4.** The threshold is justified by measurement across the anchor repo plus at least two pinned
   public repos, and the chosen value is recorded with the numbers that chose it.
5. **AC5.** The output states that the comparison is path-based, and never asserts content equality.
6. **AC6.** Findings written into 098 so the deferred decision has evidence attached.

## Out of scope

Content hashing or similarity scoring, and any new edge kind or `contract_version` bump (that is 098's
question, not this ticket's).
