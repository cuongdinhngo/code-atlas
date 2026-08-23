---
id: 138
slug: architecture-rules-are-never-asked-of-the-graph
title: The architecture rules are prose plus a regex sweep — nothing asks the graph whether they hold
phase: 3
milestone: Supervision
status: todo
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
