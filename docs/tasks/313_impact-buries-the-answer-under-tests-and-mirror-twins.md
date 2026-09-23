---
id: 313
slug: impact-buries-the-answer-under-tests-and-mirror-twins
title: "`impact` returns every row at the same weight, so ten production callers arrive under fifty tests and mirror twins"
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [262, 265, 277, 282, 298]
---

## Why this exists

Two field rounds scored `impact` **5/10** for the same mechanism, and it is the only tool with a
repeated score that low. The finding, in the round's own words: *"It contains the right answer and
buries it."* Sixty nodes at depth 2 — roughly twenty mirror twins of the same file and another
fifteen tests — against ten production callers that `find_callers` had already named. The ask was
explicit: **give `impact` the production/test and outside-the-mirror split `find_callers` already
computes.**

The data is one file away and already stored:

- `find_callers._role_census` (`code_atlas/tools/find_callers.py:633`) reads `is_test` per row and
  labels the basis with `stored_test_source` (262, with 298's path-convention fallback).
  `impact.py` does not mention `is_test` once.
- The mirror side is stamped at build time by `mirror_search.py` — measured from external inbound
  edges, **no directory names** (277/282, R2-safe) — and only `search_symbol` and `read_symbol`
  read it.

So this is not new analysis. It is two stored facts reaching a third tool.

## Goal

Make `impact`'s page-one rows the ones a reader acts on: every row says whether it is test or
production and whether it sits on a mirrored subtree, and a caller can exclude tests **before**
paging rather than after.

## Scope / Deliverables

1. **Per-row role on `impact` results** — each row carries its test/production role and the basis
   that decided it, reusing `symbol_role` rather than a second classifier.
2. **`exclude_tests` on `impact`**, filtering as a **store predicate before paging** (R1.4), so
   page one is production rows and not the production rows that survived a page of tests. This is
   the `find_callers` contract, applied to the same question one hop out.
3. **Mirror labelling on `impact` rows** — a row on a stamped pair names its counterpart, or the
   honest negative when the twin is not indexed, exactly as `search_symbol` and `read_symbol` do.
   No stamp ⇒ no field and no cost (061).
4. **The same per-row role on `search_symbol`**, which the field round named beside `impact` and
   which also has zero `is_test` today.
5. Ranking may use the new labels, but only within today's bands — an ordering change is stated in
   the payload the way `search_order` already states the mirror rule (265/277).

## Constraints

- **No aggregate census above depth 1.** `find_callers` reports `production_count` / `test_count`
  at depth 1 only, because above it the answer is a BFS total a partition cannot add up to
  (165/262). `impact` is multi-hop by definition, so this ticket ships **row properties**, which
  are honest at any depth, and must not ship counts that imply a partition of the radius (R5.5).
- **`src/` vs `legacy/` is the stamped mirror pair, never a directory list.** Naming a repo's
  layout in the core is R2; the stamp is measured from external inbound edges and already exists.
- No language branch in the core (R1.1); only `store.py` touches SQLite (R1.4).
- Identical graph and change set produce byte-identical ordering (R4.2).
- `minimal` stays a subset: a new field is omitted there, never added (CONVENTION §6).
- Omit-when-empty (061) — an unmirrored, test-free repo pays nothing.

## Acceptance criteria

- **AC1** A fixture whose changed symbol is reached by both production and test callers returns
  rows labelled with their role, and the label names the basis (`adapter` vs `path_convention`).
- **AC2** `exclude_tests=true` returns a page whose production rows are the same ones a full page
  would have contained — proven by a fixture where tests outnumber the page limit, so a
  filter-after-paging implementation fails it (R6.8).
- **AC3** A fixture on a stamped mirror pair labels the counterpart, and a fixture whose twin is
  **not** indexed gets the honest negative rather than a path that does not exist (282).
- **AC4** No count, total or census is emitted that partitions a multi-hop radius; a test asserts
  the absence, so a later well-meant addition fails rather than ships (R5.5).
- **AC5** `search_symbol` carries the same per-row role, and the existing band order is unchanged
  unless the payload states the new rule.
- **AC6** `minimal` omits every new field; `standard` carries them — asserted on both tools.
- **AC7** A repo with no mirror stamp and no test-classified nodes produces byte-identical payloads
  to today, so the feature is free where it does not apply (061, R4.2).

## Out of scope

- Fixing `subject_ambiguous` on a name defined in two trees. That is the *other* half of the same
  field finding — `impact` answering nothing at all rather than answering noisily — and it needs a
  seed-disambiguation design, not a labelling one. Separate ticket.
- `impact_modules`, which already rolls up by module and splits by tier.
- Any adapter change. `is_test` is stored today (262/298); if a language classifies tests poorly
  that is a recorded cause and a separate ticket.
- Selective test execution of any kind — 308's report-only contract is untouched.

## References

`code_atlas/tools/impact.py`, `code_atlas/tools/find_callers.py:615-640`,
`code_atlas/tools/search_symbol.py`, `code_atlas/mirror_search.py`, `code_atlas/symbol_role.py`,
`code_atlas/store.py::inbound_test_rows`,
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[282](282_a-mirror-hit-names-a-counterpart-that-is-not-in-the-index.md),
[`docs/TOOLS.md`](../TOOLS.md), CONVENTION §6, ENGINEERING_RULES R1.1, R1.4, R2, R4.2, R5.5, R6.8.
