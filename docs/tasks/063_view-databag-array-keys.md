---
id: 063
slug: view-databag-array-keys
title: 'The data-bag setter takes an array, not a key — 062 emits nothing on the anchor repo'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [062, 002, 049]
---

## Goal
[062](062_view-databag-producer.md) models a publish as **setter + `key_arg`**, where the key is a
string literal in a named argument position — `assign('items', $items)`. The anchor repo publishes
with an **array literal** instead — `setData(['items' => $items])` — so the keys live in the array's
own keys, not in an argument of their own. Rules written against that repo produce **zero** edges, and
no `key_arg` value can fix it. Close the gap so the shape 059 was filed for is actually reachable in
the repo 059 was filed from.

## Evidence (anchor repo, index built 2026-08-08, contract v4)
- The view class merges an array into its bag and `extract()`s it into the included template — the
  string-keyed handler→template flow field retro round 1 §6a.1 described.
- `setData` carries **11,204** `CALLS` edges; **7,663** of them have `args = ["array"]`. None have a
  string in any position that could be a key.
- **0** call sites repo-wide match the `(key, value)` setter shape 062 assumes (`assign` / `with` /
  `setVar` / `render`). The only setters that *do* match it are request-parameter helpers (67 sites),
  not the view bag.
- Even if a rule could name the array argument, the key is not in the index: `args` records the
  argument **category** only, never the value (`contract.py:101`). `"array"` is one token; the keys
  inside it are not emitted by the adapter at all.

So this is not a rules-authoring gap. The adapter never captured the information a rule would need.

## Scope / Deliverables
- **Count first, as 059 did.** Before any code, count the two publish shapes across the fixture corpus
  and the anchor repo: `(key, value)` setters vs array-literal setters. If the array shape is rare
  outside one repo, this ticket dies here and the finding is recorded. The count is the deliverable
  that can kill it.
- **Adapter — emit array-literal keys at the call site.** Extend what the PHP adapter records for a
  call argument so a top-level array literal contributes its **string keys**, in order. Keys only,
  never values (R4 determinism, and the same "category never content" discipline `args` already
  keeps for everything else). Non-literal keys (`$k => …`, spread, nested arrays) contribute nothing
  and must not shift the positions of the ones that do.
- **Contract (R3).** Decide where the keys ride — a sibling column/field beside `args`, or a widened
  `args` entry — and bump `contract_version` with `tests/contract/` updated in the **same** change.
  The vocabulary must keep an array-with-keys distinguishable from today's bare `"array"`, so an
  index built before this ticket is never mistaken for one that found no keys.
- **Rules shape.** Extend the 062 `view_data` rule so an operator can say "the keys of the array at
  argument N", not just "the string at argument N". Keep the existing form working unchanged — both
  shapes are real, and 062's is the one the fixtures already prove.
- **Same nav surface.** `find_view_data` answers identically whichever shape produced the edge; the
  caller must not have to know how the framework spells its bag.
- **Off by default.** No rules loaded ⇒ graph unchanged, exactly as 040/062.

## Constraints
- R2 absolute — no framework or repo names under `adapters/`; the adapter learns "array literal keys",
  a language fact, not "this view class".
- R1.1 — the core applies rules generically; no branch on which rule shape matched.
- R4 — same rules + same parse ⇒ same rows; edges stay HEURISTIC-or-documented, never silent RESOLVED.
- Consumer side stays out (059 rejected option 2; 062 held the line — this ticket does not reopen it).
- Nothing about a private repo enters this repository — fixtures only, and the counts above are
  aggregates.

## Acceptance criteria
- The publish-shape count lands in the working doc before the first line of adapter code, with the
  kill/proceed call recorded either way.
- A fixture handler publishing `['items' => $x, 'title' => $y]` yields two `PROVIDES_VIEW_DATA` edges
  with keys `items` and `title`; a `(key, value)` fixture keeps yielding exactly what 062 ships today.
- A non-literal key in the same array shifts nothing and emits nothing.
- `contract_version` bumped; `tests/contract/` updated in the same change; an index built at the
  previous version reads as "no keys captured", not "no keys found".
- With no rules file, no `PROVIDES_VIEW_DATA` edges exist.

## References
[062](062_view-databag-producer.md) (the rule shape this widens); [059](059_view-databag-edge.md)
(decision + original occurrence counts); [049](049_call-site-argument-selectivity.md) (`args`
categories, and why they carry no values); `code_atlas/enrichment.py` (`_view_data_edges`,
`_arg_is_string`); `code_atlas/contract.py` (`ARG_LITERALS`, `CONTRACT_VERSION`); R1.1, R2, R3, R4.
Origin: onboarding the anchor repo onto contract v4, 2026-08-08 — found while writing the 062 rules
file, not by a session using the tool.
