---
id: 262
slug: the-contract-marks-test-code-and-no-tool-reads-it
title: '`is_test` is in the contract and in the `nodes` table, and not one tool consults it — so "three callers" and "three callers, all in the unit-test file" are the same answer, though the first blocks a deletion and the second permits it'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [130, 255]
---

## Why this exists

`is_test` is a contract field (`contract.py:152`) with a column in `nodes` (`store.py:110`). The only place it is mentioned in the tool layer says it is unused: *"Path-segment test role (130) — `is_test` is unused by adapters today"* (`tools/class_diagram.py:279`), which derives the role from the path instead.

Field round 18 recorded the shape that makes this expensive: a symbol with **three callers, all in the unit-test file**. That is the difference between *dead* and *latent* — between a symbol an agent may delete and one it may not. Today the agent gets one number and must re-derive the distinction by reading each caller's path, which is the cost the graph exists to remove.

## Scope / Deliverables

- **A census, not only a filter.** `find_callers` (and `find_references`, same predicate) report `production_count` / `test_count` beside `total_count`, always. An agent that never passes an argument still gets the distinction.
- **`exclude_tests` argument** (default off) filtering in SQL, before truncation — not a post-filter over an already-truncated page, which is the defect [251](251_the-resolved-caller-can-be-off-the-page.md) named.
- **Source of the flag, in order:** the adapter's `is_test` where an adapter emits it; the existing path convention (130) where it does not. Which source decided is stated in the payload, never guessed silently.
- **No framework guessing.** Not a list of test-directory names per framework — R2.2. The path convention already in `class_diagram.py` is the fallback and it stays the only one.

## Constraints

- A census must not change what `total_count` means; it partitions it.
- The filter runs in the store query so paging cost is the page (the discipline [252](252_a-class-reference-question-costs-n-plus-one-calls.md) is about).
- R4.2: partition counts are derived from stored rows, byte-reproducible.

## Acceptance criteria

- `find_callers` / `find_references` payloads carry `production_count` + `test_count` summing to the hit set, with the deciding source named.
- `exclude_tests=true` filters in SQL: a test pins that the returned page is a page of the *filtered* set, not the filtered remainder of an unfiltered page.
- A fixture with callers only in test files returns `production_count: 0` and does **not** return `no_matches`.
- No adapter-side framework directory list is introduced.

## References
`code_atlas/contract.py:152`, `code_atlas/store.py:110`, `code_atlas/tools/class_diagram.py:279`, field retro round 18, [251](251_the-resolved-caller-can-be-off-the-page.md), [252](252_a-class-reference-question-costs-n-plus-one-calls.md).
