---
id: 138
slug: architecture-rules-are-never-asked-of-the-graph
title: The architecture rules are prose plus a regex sweep — nothing asks the graph whether they hold
phase: 3
milestone: Supervision
status: done
depends_on: [040, 110, 112, 136]
---

## Why this exists

**The gap is verified in this repo. The user demand is not** — provenance is an architecture-perspective
review of [PLAN §1](../PLAN.md#1-goals--non-goals)'s two pillars on 2026-08-23, not a field retro. The
evidence gate below is what stands in for a session.

This project's own structural rules are enforced two ways today, and **neither reads the graph the
project builds**:

- four grep gates in `scripts/gate.sh:176-207` — R1.1 (`if language ==`), R2.2 (repo/framework names),
  R4.1 (LLM imports), and the commit-trailer sweep;
- regex-over-source tests — `tests/test_sql_confinement.py` for the storage boundary,
  `tests/test_core_is_language_agnostic.py` for the language branch.

A regex sees **a token in a file**. A dependency rule is a statement about **edges**: "nothing under
`code_atlas/` except `store.py` reaches SQLite" holds only if nothing reaches it *transitively* either.
`test_sql_confinement.py` asserts the direct case and cannot state the indirect one — it says so by what
it matches (`SQL` regex over each module's own text).

PILLAR 2's supervision half is the reason this matters: the rules and the architecture are given to the
agent up front, and the agent still drifts. The map shows **what was generated**; it does not say
**which rule was broken**. Between those two sits the artifact a reviewer actually wants — a violation
list, each row a rule id plus `file:line`.

## Scope

1. **Rules as data, not code** — the [040](040_framework-indirection-data.md) precedent
   (`CA_INDIRECTION_RULES`): a declarative file naming, per rule, a source path set, a forbidden target
   path set, edge kinds, direction, and whether transitive closure counts. No rule text inside
   `code_atlas/` (R2.2 — a rule file that names a framework belongs to the user, not the server).
2. **One checker over the existing graph.** No second traversal: reuse the store's reachability
   (031 / `reach_shared`) and [112](112_onboarding-dataset-contract.md)'s path→module/layer assignment,
   so a violation names the same module the map names (PLAN §1 SHARED CONSTRAINT).
3. **A tool that obeys CONVENTION §6** — `index_root`, `detail_level`, `total_count` over the violation
   *population* (not the page length, 124), per-page `truncated` (057), and reason codes on the empty
   answer (065). An empty rule-check must separate *no violation* from *the rule matched no source file
   at all*: that second case is 130's family — honest signal, dishonest population.
4. **Tier partition, non-negotiable.** [136](136_heuristic-share-has-no-owner.md) measured ≥99 % of the
   HEURISTIC share as local-type causes. A violation whose only evidence is a HEURISTIC edge is a
   **candidate**, carried in its own bucket with its own count, and may never be the reason a gate
   fails. A rule engine over a two-thirds-heuristic graph that hides the tier is a false-violation
   machine.
5. **The proving case is a committed pin, not this repo.** `symfony/demo`: `src/Entity` must not depend
   on `src/Controller`. This repo cannot prove it — the core is Python and no Python adapter exists
   ([020](020_python-adapter.md), deferred).

## Evidence gate

Before implementation, in writing: **one rule, on a repo that is not this one, whose violation the
existing regex gates demonstrably cannot see** (transitive, or through an alias edge 030 already
models). If the only expressible rules are ones grep already catches, this ticket is closed as
unnecessary rather than shipped.

## Acceptance criteria

- **AC1** A rule file expressing "no edge from set A to set B, transitively", with a red-first fixture
  where the violating edge exists (R6.5).
- **AC2** Confirmed and candidate violations are separate counts at the payload level; a HEURISTIC-only
  violation never reads as confirmed.
- **AC3** An empty answer names its cause — no violation / rule matched no files / not indexed — and
  `total_count` is the population.
- **AC4** Every reported violation is reproducible through an existing tool at the same commit
  (`find_callers` / `find_references` / `include_graph`), asserted on at least one violation. The
  map-and-tool agreement is a test, not a claim.
- **AC5** Identical index → byte-identical violation list, ordering included (R4.2).
- **AC6** No repo, framework or rule name inside `code_atlas/` (R2, CI-gated); the vocabulary is
  generic — path sets, edge kinds, direction.
- **AC7** Cost measured, not assumed: one row through the harness question class
  [142](142_supervision-question-class-has-no-baseline.md) owns.

## Out of scope

- **Replacing the four grep gates or `test_sql_confinement.py`.** A token rule is a text rule and grep
  is the right tool for it. This ticket takes the *edge* rules only, and deletes no working gate.
- **Enforcing rules in this repo's CI** — needs a Python adapter (020, deferred).
- **Any fix, or any suggested fix.** The core never mutates code (§1 non-goal, permanently ceded).
- **Deciding which rules a project should have.** That is a human ratification step (mango's `codify`
  territory); this ticket only checks rules it is handed.

---

<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `feat/138-architecture-rules-are-never-asked-of-the-graph`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed

## Evidence gate (pre-implementation)

**One rule regex cannot see:** `domain/**` must not reach `http/**` transitively. Fixture
`tests/fixtures/architecture_rules/` + planted CALLS chain `domain/Model → service/Bridge →
http/Front`. Grep over `domain/Model.aa` never names `Front` or `http`; the graph closure does.
The pin case on a public app (`src/Entity` ↛ `src/Controller`) is the same shape; this repo has no
Python adapter, so the committed fixture is the proving pin (ticket Scope §5).

## Design

- `CA_ARCHITECTURE_RULES` → JSON `{rules:[{id, sources, forbidden, kinds?, direction?, transitive?}]}`
- Tool `check_architecture_rules`: confirmed (`results`/`total_count`) vs `candidates`/`candidate_count`
- Reuses `reachable_from` (kinds subset) / `impact_radius`; no second graph load
- AC7 **deferred** to 142 — BACKLOG orders the supervision baseline first; inventing a class here
  would repeat 121

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | `test_ac1_transitive_violation_is_confirmed` |
| AC2 | ✅ | waived | `test_ac2_heuristic_only_path_is_candidate_not_confirmed` |
| AC3 | ✅ | waived | `test_ac3_empty_answers_name_their_cause` |
| AC4 | ✅ | waived | `test_ac4_violation_reproducible_via_find_callers` |
| AC5 | ✅ | waived | `test_ac5_identical_index_is_byte_identical` |
| AC6 | ✅ | waived | R2.2 gate; generic vocabulary only |
| AC7 | deferred | — | owned by 142 |

## Cost ledger

| Phase | Dispatch | Tokens |
|---|---|---|
| execute | — | main-loop only |
| review/challenger | waived | — |

## Review of PR #166 — five defects fixed in-branch

The AC1–AC5 fixture is outgoing + transitive + all-kinds, so three quarters of Scope §1's own rule
vocabulary shipped unexercised. What that hid:

1. **`direction: "incoming"` ignored `kinds`** — `impact_radius` had no `kinds` parameter, so an
   incoming rule declaring `["EXTENDS"]` reported a **confirmed** violation off a `CALLS` edge. A
   false positive is the one failure mode a supervision tool may not have. `kinds` now threads
   through `impact_radius` exactly as 138 already threaded it through `reachable_from`.
2. **An absent `confidence_tier` on an incoming row defaulted to `RESOLVED`** — the unsafe side of
   the partition this module's own docstring calls non-negotiable. Now defaults to the candidate side.
3. **A rule whose `forbidden` set matched no file reported `status: "checked"`** — a vacuous pass
   labelled as a check. Both sides empty now report `rule_matched_no_files`; the two counts say which.
4. **An unknown `rule_id` returned `reason: "ok"`** — a typo read as *your rules hold*. Now
   `no_matches`.
5. **`candidates` was always the first page and never flagged short** — `[:cap]` ignored `offset`.
   Now paged like `results`, with `candidates_truncated`.

Also: the module had forked the reason vocabulary (three private `REASON_*`, one value outside the
pinned `NAV_REASONS`). `rule_matched_no_files` joined `nav_result`'s pinned tuple; the module keeps
only its own `STATUS_*` rule-status names, so the core still never imports a tool.

Tests added: `test_incoming_direction_honours_the_declared_edge_kinds`,
`test_non_transitive_rule_sees_the_direct_hop_only`,
`test_unknown_rule_id_is_not_reported_as_a_clean_pass`,
`test_a_rule_whose_forbidden_set_matched_nothing_never_reads_as_checked` — the first and last are
red without the fixes above.

**Not fixed, noted:** `_incoming_hits` runs one `impact_radius` per seed where `_outgoing_hits` runs
one `reachable_from` per file. Batching would cost coverage under the `max_nodes` prune, so the
asymmetry is deliberate; it is a per-symbol query count on a rule with a large source set.
