---
id: 058
slug: list-parse-failures
title: '`parse_failures: 29` — nobody can find out which 29 files the index cannot see'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [009, 028]
---

## Goal
`get_index_status` reports `failed: 29` / `parse_failures: 29` on the anchor repo. It reported the same
29 in field retro round 1 and again in round 2, on a tree that moved by several commits in between —
stable, with no attrition. **No tool lists them.**

Those 29 files are a hole in every answer the index gives: nothing in them is searchable, no symbol they
declare can be a caller, an implementor, or a target. A nav tool that returns nothing because the
declaring file failed to parse reports the same empty answer as one where the symbol truly has no
callers — the same false-absence family as [054](054_bare-name-callers-silent-drop.md) and
[056](056_filter-values-fail-loud.md), arriving by a different route.

29 out of 18,872 is 0.15%, which sounds ignorable until you cannot tell whether it is 29 generated
fixtures or 29 controllers. The round-2 session said exactly that and could go no further.

**The data already exists.** `files.parsed_ok` is a column in the schema (`store.py` DDL); the build
writes it and `counts()` aggregates it. Only the listing is missing.

## Scope / Deliverables
- **Expose the failing paths.** A store method over `files.parsed_ok = 0` and a way for an operator or
  agent to read it. Prefer extending an existing surface to adding a fourteenth tool — `detail_level`
  on `get_index_status` is the obvious candidate, but see the constraint below.
- **Bounded, and never on the cheap path.** The list must not ride on the `standard` status payload;
  `get_index_status` staying cheap is what both field retros named as the thing that must not break. A
  capped list behind an explicit request, or a separate lightweight call.
- **Say why, if the reason is already known.** The build knows whether a file failed on a syntax error,
  an encoding problem, or an adapter timeout — check whether that survives to the store, and record the
  answer. If it does not, listing paths alone is still the deliverable; do not grow the schema for it
  here (R3).
- **A note in the onboarding runbook** telling an operator to check the list after the first build, so
  a systematic failure (one directory, one encoding, one PHP version) is caught at onboarding rather
  than two field retros later.

## Constraints
- **`get_index_status` cost must not move for existing callers** — asserted, at both detail levels.
- **No schema change (R3)** unless the failure *reason* turns out to need a column, in which case that
  becomes its own ticket rather than riding along here.
- **SQL stays in the store (R1.4)**; no language branch in the core (R1.1).
- **Determinism (R4.2)** — the listing is ordered, so two runs return the same rows in the same order.
- **The list is bounded.** A repo where 40,000 files failed must not return 40,000 paths.

## Acceptance criteria
- On a fixture with at least one unparseable file, the failing path is retrievable, and the count
  matches `parse_failures`.
- The `standard` and `minimal` `get_index_status` payloads are unchanged for callers that do not ask
  for the list, asserted.
- The listing is capped, and says so when it truncates.
- Ordering is stable across two runs (R4.2).
- The runbook tells an operator to check the list after the first build.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/store.py` — the `files` DDL (`parsed_ok INT DEFAULT 1`) and `counts()`, which already
aggregates it; `code_atlas/tools/get_index_status.py:121` (`parse_failures`, the count with no list
behind it); `code_atlas/indexer.py` `_parse_all` / `_write` (where `parsed_ok` is set).
Cheapness constraint: field retro round 1 §7 and round 2 §7 both name `get_index_status` as the thing
that must not break.
Origin: field retro round 2 §0 and §6a — the same 29 across both rounds, unlistable.
