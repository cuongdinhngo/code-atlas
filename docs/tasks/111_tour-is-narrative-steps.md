---
id: 111
slug: tour-is-narrative-steps
title: Onboarding — the tour is one stop per module, so 500 modules is a 500-stop "tour" (M11)
phase: 3
milestone: M11
status: todo
depends_on: [087, 110]
---

## Why this exists (measured, anchor monorepo)

`guided_tour` and `generate_onboarding` emit **one stop per module in the budget**. On the anchor repo
that is 500 stops in a 6,312,632-byte `tour.md`, each line of the form
`path — reached from path`. Nobody reads 500 stops, and 332 of them are `cycle with …` lines where the
same SCC is re-listed per member.

A tour is a *reading order with a reason*, and the reference tool constrains it to **5–15 steps**, each
grouping 1–5 files with a 2–4 sentence explanation of what the reader learns there. Its own repo tour is
12 steps. The mockup's 12-step tour over the anchor repo covered: the two mirror trees, the web entry
surface, the bootstrap/error-handler path, the DB wrapper's three copies, the global helper bag, the
namespaced `src/` layer, Domain/Data, Views, the self-contained integration island, the vendored PDF
libraries, the test bootstrap being the largest hub, and the map's own limits.

Every number in those 12 steps is interpolated from the dataset; the prototype carries a regression
assertion that no number is hard-coded, so a regenerated tour cannot go stale.

## Scope

Deterministic step construction — **no LLM in this ticket** (prose is 117):

- Group the budgeted subgraph into steps by layer rank (110) crossed with BFS depth from the entry
  seeds, collapsing each SCC to **one** step contribution rather than one per member.
- Clamp to `[5, 15]` steps by merging the smallest adjacent same-layer groups; each step names 1–5
  modules chosen by fan-in within the group.
- A step carries `order`, `title`, `modules`, and a structural `why` line assembled from facts already
  in the dataset (layer description, degree, cycle membership) — the slot 117 replaces with prose.
- The 500-module subgraph remains the *substrate* for ranking. It stops being the deliverable.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with 60 modules across 4 layers yields between 5 and 15 steps — observed
   red against today's code, which yields 60.
2. **AC2.** An SCC of N modules contributes exactly one step entry, and the step says how many modules
   the cycle holds instead of listing all of them.
3. **AC3.** Byte-stability: same index → identical steps, titles and order (R4.2).
4. **AC4.** Every step names at least one module and no step is empty; 109's C4 becomes a real bound.
5. **AC5.** Measured on the anchor repo and two pinned public repos: step count, `tour.md` bytes before
   and after, and the module count each step covers. `tour.md` under 64 KB on the anchor repo.
6. **AC6.** No number in the rendered tour text is a literal — proven by a test that regenerates against
   a mutated dataset and asserts the rendered numbers moved.

## Out of scope

Prose quality and the per-step narrative sentences (117). Whether per-module pages survive at all (116).
