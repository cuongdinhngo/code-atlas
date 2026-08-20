---
id: 114
slug: business-module-table
title: Onboarding — nothing bridges "fix screen X" to a file path (M11)
phase: 3
milestone: M11
status: todo
depends_on: [112]
---

## Why this exists

A first-day developer's only real question is *"I was told to fix the X screen — which file do I open?"*
The current artifact is organised by structure (files, symbols, edges) while the newcomer's head is
organised by business capability. Nothing connects the two, and the reviewer standing in as that
developer named this the single reason the page failed them.

The mockup added a table derived from **module directories in the code** — the segment after
`application/` or `modules/` — giving 24 modules on the anchor repo with, per module: file count, class
count, which top-level trees it appears under, and its highest-fan-in file. Examples measured:
`admin` (394 files, both region trees), `roster` (257, both), `reports` (252, both), `api` (205, both
regions plus the namespaced tree), `care` (111, all three), `catering` (106, one region only).

The single-tree rows are the finding: **a module present under one region tree and not the other is where
the two markets have diverged**, which is exactly what a newcomer must not assume away.

## The limit that must ship with it

Testing the reviewer's own example exposed the boundary: the screen they named is a **flat file directly
under the web root** and belongs to no module directory, so it is absent from the table. The table
therefore must state its own coverage — what fraction of indexed files it accounts for — and point at
search for the remainder. A table that looks exhaustive and isn't is worse than a smaller honest one.

## Scope

- Derive module candidates structurally: a directory one level under a `application`/`modules`-style
  container segment, with a minimum file count, excluding role words already claimed by 110's vocabulary
  and excluding region/container names.
- Per module: files, classes, which top-level trees contain it, its directories, and its top hub.
- Report **coverage**: files accounted for vs total indexed, in the dataset and in every renderer.
- Rank single-tree modules as a distinct signal (divergence), not just as a row.
- R2.2: no repo-specific module names in code — the names are *read from the tree*, never listed.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with `app/application/billing/…` and `app/application/audit/…` yields two
   modules with correct counts — observed red against today's code, which has no such concept.
2. **AC2.** Coverage is reported and correct: a fixture where half the files sit outside any module
   directory reports ~50 %, and the renderer shows it.
3. **AC3.** A module present under one tree and absent under a sibling tree is flagged; a module present
   under both is not.
4. **AC4.** Role words (`controller`, `model`, `view`, …) and container/region names never become modules.
5. **AC5.** Measured on the anchor repo and two pinned public repos: module count, coverage percentage,
   and single-tree count. A repo with no module-style layout reports zero modules and says so rather than
   inventing groups.
6. **AC6.** No module name is hard-coded anywhere in `code_atlas/`; R2.2 grep-gate covers the new code.

## Out of scope

Mapping modules to URLs or menu entries — that needs a repo's own route inventory, which is repo-specific
knowledge the core must not consume.
