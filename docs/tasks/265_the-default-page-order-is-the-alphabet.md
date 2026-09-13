---
id: 265
slug: the-default-page-order-is-the-alphabet
title: 'Page 1 of every caller and reference answer is ordered by qualified name, so what an agent sees first is an accident of spelling — a correct, cheap, unrepresentative page that terminates the reasoning which would have reached the truth; make tier the default order, and let a page that is a partition return a census with no rows at all'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [251, 252, 067, 259]
---

## Why this exists

`_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"` (`store.py:170`). Every paged edge answer is alphabetical by source name. Three independent records of the damage:

- [067](067_first-page-not-representative.md): a **fully correct 23-of-23** `find_callers` page that steered the session off `src/` — page 1 was 100 % of the tree it must not touch. The session *"briefly read that page as no `src/` callers"* before grep contradicted it.
- [251](251_the-resolved-caller-can-be-off-the-page.md): on a common method name the one `RESOLVED` caller sat on page 12 while page 1 was vendor `build()` noise.
- [074](074_does-the-index-harm-mechanism-questions.md): the mechanism question that was **right when the index was denied and wrong when it was granted** — still at n = 1, still the only datapoint suggesting the index costs accuracy.

251 shipped `confidence_tier` as a *filter the agent must know to pass*. Agents terminate on page 1; a knob nobody discovers is not a fix.

**Ordering before [259](259_one-knob-sets-both-index-size-and-page-truthfulness.md) is cosmetic**: the anchor's page cap is 10 because one knob also sets index size. 259 lands first.

## Scope / Deliverables

- **Tier-first default order** for caller/reference edge reads: `RESOLVED` before `HEURISTIC` before `DYNAMIC`, then today's stable keys. In SQL, **before truncation**, never a post-filter over a truncated page.
- **`confidence_tier` keeps its filter role**, unchanged. This ticket changes the default *order*, not the default *set*.
- **A page that is a partition of a differently-tiered set** returns `authoritative: false` plus a tier census, and **is permitted to return zero rows**. Uglier and more honest than ten plausible wrong callers.
- **Bound the class-level union to the page** — `252`'s `_member_caller_union` issues one `edges_by_target` per `CONTAINS` child and collects every hit before `cap`/`offset` apply, so cost scales with the class's total inbound set. A tool that looks cheap and is not is an honesty defect, not a performance note.
- **Write PLAN §19 first, before any code in this ticket**: that [074](074_does-the-index-harm-mechanism-questions.md) will be measured **after** this fix, that the baseline is the 2026-08-08 cell plus 067, and why — 074's "do not change a tool to make the number come out" governs tuning during a run, not shipping an already-named mechanism before measuring whether it closed.

## Constraints

- R4.2: the new order must be total and stable — identical input, identical rows, identical order.
- No unnamed ranking. Tier is the stated basis; nothing heuristic, nothing learned. (181's `ranked_by: "path"` is the anti-pattern.)
- Do not raise the page cap here — that is 259's knob.

## Acceptance criteria

- A fixture where the sole `RESOLVED` caller sorts last alphabetically returns it **on page 1**.
- A test pins the ordering is applied in the store query, not after truncation.
- A partition page returns `authoritative: false` + census; a test covers the zero-row arm.
- Class-level union: a test pins that cost scales with the page, not with the class's whole inbound set.
- PLAN §19 carries the 074-ordering decision, committed **before** the code change.

## References
`code_atlas/store.py:170`, [067](067_first-page-not-representative.md), [251](251_the-resolved-caller-can-be-off-the-page.md), [252](252_a-class-reference-question-costs-n-plus-one-calls.md), [074](074_does-the-index-harm-mechanism-questions.md), [259](259_one-knob-sets-both-index-size-and-page-truthfulness.md).
