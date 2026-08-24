---
id: 140
slug: impact-answers-in-symbols-not-modules
title: '`impact` answers in symbols, and the decision is module-shaped — 500 rows at ~160 KB is the only answer today'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [017, 112, 114, 124]
---

## Why this exists

Two halves, one measured and one not.

**Measured, and already in BACKLOG's follow-up list:** `reachable_from` at `detail_level: standard` is
bounded by `impact_max_nodes` (500) and returns *~160 KB of JSON against a metric measured in tokens*.
[`runbooks/onboarding-a-repo.md`](../runbooks/onboarding-a-repo.md) §4 carries the workaround.

**Not measured — provenance is the architecture review of 2026-08-23:** the decision that consumes an
impact answer is module-shaped. *Which modules does this change reach, how many edges into each, and
which single edge do I read first?* Today that is a 500-row symbol list the reader aggregates by hand,
and the aggregation is the whole answer.

The rollup already exists in the tree and nothing joins it to impact:
[114](114_business-module-table.md) derives business modules from the path set and
[112](112_onboarding-dataset-contract.md) publishes the assignment. Deriving a *second* module notion
here would break PLAN §1's shared constraint, so the ticket is a join, not a new model.

## Scope

- An aggregation over the **existing** impact walk: module → edge count + one exemplar `file:line`,
  using 112's assignment verbatim. No new traversal, no second module definition.
- Honest bounds: a walk that hit `impact_max_nodes` says so and labels the rollup an **under-estimate**
  — 124's `walk_truncated` vocabulary, already in CONVENTION §6.
- Tier partition per [136](136_heuristic-share-has-no-owner.md): confirmed and heuristic edge counts are
  separate numbers, because a module that appears only through heuristic edges is a different fact.
- `minimal` = module names + counts; `standard` adds exemplars. `minimal` stays a subset (CONVENTION §6).
- A file the dataset does not assign goes to an explicit `unassigned` bucket — 113's lesson: never fold
  four populations into one number, and never invent a home for a file.

## Acceptance criteria

- **AC1** A subject whose impact spans ≥3 modules; the per-module counts sum to the symbol-level
  population, asserted (127's arithmetic guard).
- **AC2** A truncated walk is stated as truncated and the rollup is labelled an under-estimate.
- **AC3** The module names are byte-identical to the ones the map prints at the same commit — one
  assertion joining tool and map, so "same graph, no second pipeline" is tested.
- **AC4** A number, not a claim: the rollup at `standard` is measurably cheaper in tokens than the
  symbol answer it summarises, recorded in the benchmark file.
- **AC5** Deterministic ordering; identical index → identical rows (R4.2).
- **AC6** Red first (R6.5), and `unassigned` is exercised by a fixture that has one.

## Out of scope

- **Changing `impact`'s own payload.** 061 pruned it once; this is an additional answer, not a reshape.
- **A new or wider traversal.** If the walk bound is wrong, that is its own ticket with its own
  measurement.
- **Guessing a module for an unassigned file.**

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived per maintainer standing approval)
- **Branch:** `feat/140-impact-module-rollup`
- **CHALLENGER:** OFF (`with skipped review and challenge`)
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M

## Design

A **new tool**, not a reshape: the ticket puts changing `impact`'s payload out of scope, so this is
an additional answer over the same walk.

- `impact.py` publishes `subject_parts` / `resolve_seeds` / `explain_lost_subject` / `SeedSet`; the
  rollup imports them, so both tools answer about the same seeds by construction.
- `modules.py` publishes `directory_owners` + `module_of_path` — the assignment 114 already built,
  named so a consumer joins on it instead of deriving a lookalike (PLAN §1).
- `_owners()` calls `find_business_modules` exactly as the dataset does, with `fan_in={}`: it feeds
  only `hub`/`hub_fan_in`, which a rollup never reads, and computing it would mean a whole-graph
  metrics pass for fields nobody looks at.

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | counts sum to the symbol population, asserted against `impact` itself |
| AC2 | ✅ | waived | `walk_truncated` + `NOTE_UNDER_ESTIMATE`, proved at `impact_max_nodes=2` |
| AC3 | ✅ | waived | names asserted ⊆ what `find_business_modules` prints at the same commit |
| AC4 | ✅ | waived | 98.5 % / 58.9 % / 18.1 % — [benchmark](../benchmarks/140_module_rollup.md) |
| AC5 | ✅ | waived | `json.dumps` equality across two calls, not set equality |
| AC6 | ✅ | waived | fixture has `bootstrap.php` outside every module; 10 tests, red-first |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| execute | main loop | unmeasured (host does not surface usage; review/challenger waived) |

## What the measurement changed about the answer

The 7-row fixture made the rollup look 18 % cheaper, which is a weak case for a ticket whose
complaint is *500 rows at ~160 KB*. Measuring at real scale gave 98.5 %, and measuring on the pins
gave something the fixture could not: **both public pins roll up to a single `unassigned` bucket**,
because 114 refuses a role-organised layout and reports no modules rather than inventing them.

A lone `unassigned` row reads as a bug. So `NOTE_NO_MODULE_TABLE` was added — the answer names
which of the two it is and routes back to `impact`. That is not extra scope; it is the `unassigned`
bucket's honesty requirement (113) applied to the case where the bucket is *everything*, and it
only surfaced because the benchmark was run on repos rather than on the fixture built to pass.

## Two defects found by asking what the tool still cannot say

Both were found after the first green gate, by going back over the answer looking for a bound that
is real but silent — the same shape as the ticket's own complaint.

- **The second bound had no name.** `walk_truncated` covers the walk; nothing covered 114's table,
  which `find_business_modules` caps at `CA_MAX_RESULTS`. A file whose module was cut resolves to
  no owner and lands in `unassigned` — so the one bucket this tool promised never to guess into was
  silently absorbing modules that exist. Now `module_table_truncated` + `NOTE_TABLE_TRUNCATED` say
  it, and say the direction: the walk bound makes counts an **under**-estimate, the table bound
  makes `unassigned` an **over**-count. Proved at `max_results=2`, where `unassigned` goes 1 → 3.
- **AC3 was checking itself.** The first version re-derived the table with the same arguments the
  tool uses (`fan_in={}`) and compared the tool to that — circular, and it could not fail for the
  assumption actually in question. It now runs `generate_onboarding` and reads the module names out
  of the artifact it writes, which is built **with** real per-file fan-in. That turns `_owners()`'s
  "fan-in does not change the names" comment into a checked fact. Verified to have teeth by
  perturbing the tool's names and watching it go red.

## Ten registry guards, all correct

Adding a tool reddened 10 tests across 8 files — `TOOL_NAMES` pins, the core-module count, the
signed/unsigned and batched/unbatched README tables, the `which_tool` map and the recognition
probe. Every one was the repo refusing to let a tool exist without being accounted for. None was
worked around; each got its real row.
