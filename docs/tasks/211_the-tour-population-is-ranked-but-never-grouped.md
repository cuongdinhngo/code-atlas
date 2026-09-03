---
id: 211
slug: the-tour-population-is-ranked-but-never-grouped
title: "The tour ranks 24,535 modules by degree and then labels the top 500 by path vocabulary, so three-quarters of the anchor's tour lands in `Uncategorised` — the graph's own community structure is never asked"
phase: 3
milestone: M11
status: done
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

---

## Working doc (autorun 2026-09-03)

**KEY:** 211 · **work_doc_mode:** embed · **Current phase:** 5 finalise

### Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Refine skipped: all scopes, constraints and ACs are product-decided. No want-decisions remain open.

In-repo refs resolved (`tour.py`, `steps.py`, `layers.py` UNCATEGORISED, `artifact.py` build_artifact, `generate_onboarding.py` edge_tiers, `test_onboarding_steps.py`, `test_artifact_contract.py`, R4.2, R3.5, R8.2, R5.2, R1.1, tickets 084/110/131). Ambiguous: the anchor monorepo's live `graph.db` and generated `tour.md` — not this checkout.

Recalled (advisory): `one-rule-for-every-subject-slot` (R1.8 — community label derivation must be one site), `version-the-document-that-moved` (R3.5 — `community_crossings` is a new artifact summary key), `prove-the-guard-fails` (R6.5 — prove the HEURISTIC guard changes community membership).

### Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists / Scope, Constraints, Acceptance criteria, References) | 4 decomposed | ROWS: C=3 R=5 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (no language branch) ✅ · §R3.5 (new artifact summary key → ARTIFACT_VERSION bump) ✅ · §R4.2 (determinism) ✅ · §R5.2 (edge confidence weighting) ✅ · §R5.8 (rank inside truncation) ✅ · §R7.1 (smallest useful) ✅ · §R8.2 (no new dep) ✅`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

| ID | Type | Statement |
|---|---|---|
| G | G | Reduce Uncategorised tour share using graph community structure |
| R1 | R | Compute communities from import edges; substitute where path vocabulary is silent |
| R2 | R | Deterministic — fixed sort order, explicit tie-breaking (R4.2) |
| R3 | R | Path vocabulary wins where it fires; communities only fill the silent case |
| R4 | R | Report community-straddles-two-vocabulary-layers as a finding (R5.8) |
| R5 | R | Measure Uncategorised share before/after; answer legacy/alpha↔legacy/beta question |
| C1 | C | No new runtime dependency (R8.2) |
| C2 | C | RESOLVED edges outrank HEURISTIC edges in community formation (R5.2) |
| C3 | C | No language branches (R1.1) |
| AC1 | AC | Two runs, identical community assignments — asserted by test |
| AC2 | AC | Uncategorised share measured and recorded (E1 for anchor-scale) |
| AC3 | AC | No-vocabulary-hit community named from members, not bare identifier |
| AC4 | AC | Path vocabulary wins — fixture |
| AC5 | AC | HEURISTIC-only cluster treated differently from RESOLVED — fixture |
| AC6 | AC | No new runtime dep |
| AC7 | AC | legacy/alpha↔legacy/beta answered in close-out |

`HANDLES: 7 recalled | 7 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**E1**: AC2 anchor-scale Uncategorised measurement (before/after on 24,535 files). Expiry: `real_corpus_path` set in `.harness.json`. The fixture proves the mechanism; the anchor number is a reporting exercise requiring a live rebuild.

### Phase 2 — design

`HANDLES: 7 recalled | 7 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Approach:** Three-module change — new `community.py`, modify `steps.py`, modify `artifact.py`.

**1. `code_atlas/onboarding/community.py`** (new):
- `assign_communities(files, edge_tiers)` → `dict[str, str]` — `{file: community_label}`
- Two-pass union-find: pass 1 unions RESOLVED edges; pass 2 unions HEURISTIC-only files (C2/AC5)
- Label = `"Community/" + representative` where representative = alphabetically-first file in the component (R4.2)
- AC3: label is a path-derived name, never a bare integer identifier

**2. `code_atlas/onboarding/steps.py`** — `build_steps`:
- Add `community_of: Mapping[str, str] | None = None`
- In `_initial_buckets`: when `layer_of.get(file, "") == UNCATEGORISED`, override with `community_of.get(file)` when set (AC4: vocabulary wins — override only fires on UNCATEGORISED)

**3. `code_atlas/onboarding/artifact.py`** — `build_artifact`:
- Compute `community_of = assign_communities(tour_files, tour_edge_tiers)` — tour-scoped (filter inside community.py)
- Pass to `build_steps`
- Add `"community_crossings"` to `artifact.summary` — sorted list of `{community, layers}` dicts for communities straddling ≥2 named layers (R4/R5.8)
- `ARTIFACT_VERSION` bump: 3 → 4 (R3.5)

**Proving test:** `tests/test_community.py::test_two_runs_are_byte_identical`

**Rejected alternative:** Full Louvain (non-deterministic without seeding; union-find on RESOLVED is sufficient and simpler per R7.1).

### Phase 3 — execute

What landed: union-find communities over tour edges (`community.py`); `build_steps` substitutes the community label only when the layer is `Uncategorised` and buckets by `(rank, layer, depth)`; `artifact.summary.community_crossings` records communities that straddle ≥2 named layers (bounded, rendered); `ARTIFACT_VERSION` 3→4.

Proving test: `tests/test_community.py::test_two_runs_are_byte_identical` — green.

Verification: `.venv/bin/python -m pytest -q` on this Linux host — **2813 passed, 1 bookkeeping red (BACKLOG status), fixed in finalise**. Core module count 78→79. No runtime dependency added.

`diff ⊆` approved list: `community.py` (new), `steps.py`, `artifact.py`, `test_community.py` (new), `test_artifact_contract.py`, `test_sql_confinement.py`, `test_core_is_language_agnostic.py`, this working doc, BACKLOG, TOKEN_LEDGER.

AC2/AC7 (anchor Uncategorised share; `legacy/alpha`↔`legacy/beta`): **E1** — not measured; `.harness.json` `real_corpus_path` is null. Close-out answer: **cannot measure on this checkout**; deferred until a live corpus path is configured.

### Phase 4 — review

`reviewer`: OFF (`--no-reviewer`) — no rule-book-grounded review.
`challenger`: ON — round 1 **BLOCK** (qname edges vs file universe; alphabetical naming; crossings unrendered/unbounded; HEURISTIC pass treated all non-RESOLVED). Round 2 after fix: **LGTM**.

### Phase 5 — finalise

PR opened under handover authorisation (push + open PR only). Merge deferred to the operator.

---

## References

[084](084_onboarding-layer-assignment.md), [105](105_dominant-subtree-loses-to-a-config-dir.md),
[110](110_layers-named-by-responsibility.md) and
[131](131_tour-ranks-configuration-ahead-of-the-front-controller.md) (four passes at the tour's
population and labels, all of them ranking or vocabulary, none of them structure),
[115](115_mirror-subtree-detection.md) (the mirror finding this must reproduce or contradict),
[204](204_bare-name-resolution-has-no-language-predicate.md) (why this cannot be measured first),
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (declared scope, the
complement to derived structure).
