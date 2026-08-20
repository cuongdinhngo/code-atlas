---
id: 110
slug: layers-named-by-responsibility
title: Onboarding — layers are directory names, not architecture; name them by responsibility (M10)
phase: 3
milestone: M10
status: todo
depends_on: [084, 105, 109]
---

## Why this exists (measured, anchor monorepo)

084/103/104/105 group modules by directory, so the layer names on a real repo are the top-level
directory names. On the anchor monorepo the emitted layers are the two region directories, the shared
`src`, a vendor directory, `tests`, `scripts`, `public`, `config`, and `(root)`. None of those tell a
newcomer what code in the layer *does*, and two of them are the same application twice.

The mockup instead matched a **responsibility vocabulary** against directory segments and produced 12
layers with plausible mass:

| Layer | Files | Class | Method |
|---|---:|---:|---:|
| Shared Library | 4,950 | 4,114 | 37,542 |
| Views | 3,694 | 734 | 3,058 |
| Uncategorised | 2,740 | 1,363 | 8,719 |
| Domain / Data | 2,478 | 2,461 | 19,223 |
| Vendor / Framework | 1,302 | 795 | 5,817 |
| Integration / Reporting | 1,048 | 1,019 | 2,586 |
| HTTP / Entry | 1,027 | 1,036 | 7,272 |
| Services | 870 | 875 | 5,073 |
| Middleware / Auth | 343 | 351 | 1,808 |
| Tests | 343 | 408 | 4,046 |
| Config / Migration | 97 | 78 | 404 |
| Background Jobs | 37 | 21 | 63 |

The distribution is itself the insight: `Views` holds 3,694 files but only 734 classes — that layer is
procedural script, and a newcomer should know before opening it.

**The deepest segment must win.** Matching *any* segment (the reference tool's order) let one container
directory absorb **11,540 files** into a single layer. Deepest-wins puts
`…/asset/controller/x` in HTTP and `…/asset/model/x` in Domain/Data, which is the useful answer.

## The rule judgment this ticket needs (✋ maintainer)

The vocabulary is `controller · handler · route · endpoint · api · service · usecase · model · entity ·
repository · view · template · page · form · middleware · filter · auth · session · job · cron · queue ·
worker · report · export · integration · lib · util · helper · common · system · test · spec · mock ·
config · migration · vendor`.

**Is that a standard or a sample (R2.2)?** This ticket argues **standard**: every word is an industry
architectural convention, none names a repo, product or framework, and the same table would apply
unchanged to a Laravel, Rails or Spring tree. The maintainer decides before implementation; if the
judgment is *sample*, the fallback is to keep directory names and carry only the mandatory
`description` field, and this ticket shrinks accordingly.

## Scope

- A responsibility vocabulary in `onboarding/layers.py`, deepest-segment-wins, with a documented
  `Uncategorised` fallback that is **reported, not hidden** (2,740 files is a naming-debt signal worth
  surfacing).
- Every layer carries a mandatory `description` (structural default now, LLM prose in 117).
- Keep 105's graph-mass ordering for layer *rank*; this ticket changes naming and grouping only.
- `architecture_overview` and the artifact both read the new names; no language branch (R1.1).

## Acceptance criteria

1. **AC1.** A fixture with `app/x/controller/a`, `app/x/model/b`, `app/x/view/c` yields three layers,
   not one — observed red against today's code (R6.5).
2. **AC2.** Deepest-wins is proven by a fixture where an outer segment also matches the vocabulary, and
   the outer match loses.
3. **AC3.** Every layer has a non-empty description; 109's C3 becomes green for real rather than by
   default.
4. **AC4.** Re-measured on the anchor repo and on at least two pinned public repos: layer counts and the
   `Uncategorised` share reported in the working doc. A pinned repo whose layer set changes shape is
   discussed, not silently accepted.
5. **AC5.** R2.2 grep-gate still passes; the vocabulary contains no repo, product or framework name.

## Out of scope

Re-grouping *modules* across layers (091 already refuses to), and the tour's use of layers (111).
