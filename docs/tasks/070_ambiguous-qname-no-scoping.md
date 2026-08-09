---
id: 070
slug: ambiguous-qname-no-scoping
title: 'One qname, five definitions, 23 callers merged — no way to ask about one of them'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [043, 013, 011]
---

## Goal
`\getActiveStatus` has **five** definitions in the anchor repo. `find_callers` merges all 23 call
sites under that one qname and offers no way to scope to a definition. The caller cannot ask "who
calls *this* one", and nothing in the payload warns that the question is ambiguous. On this index
**22,261 qnames have more than one definition** — this is the common case, not an edge case.

## Evidence (anchor repo, index built 2026-08-09, queried directly)
```
\getActiveStatus  Function  legacy/alpha/web/include/member_transaction.php:20
\getActiveStatus  Function  legacy/beta/web/ajax.php:3440
\getActiveStatus  Function  legacy/beta/web/include/member_transaction.php:18
\getActiveStatus  Function  src/Application/Common/MemberTab/tabs_common.php:332
\getActiveStatus  Function  src/Utilities/member_transaction_functions.php:117
```
- `find_callers("\getActiveStatus")` → `total_count: 23`, every site correct, **no partition**.
- Qnames with >1 definition in `nodes` (Function/Method/Class): **22,261**.
- Both `src/` definitions are wrapped in `if (!function_exists('getActiveStatus'))`, so which one a
  given call site binds to is **load-order dependent**. The round-3 session had to answer that by
  reading the `require_once` order by hand.
- `search_symbol` does report the definitions separately — the ambiguity is visible on the *search*
  side and invisible on the *navigation* side. The evaluator listed this under false positives:
  *"Each is correct individually, but the qname is not unique and `find_callers` offers no way to
  scope to one definition."*
- Note for the record: the retro says four definitions; the index holds five. The retro's list came
  from a `search_symbol` page, which is itself consistent with a paging cap.

This interacts with [067](067_first-page-not-representative.md): merged results from five definitions,
ordered lexically, capped at 10, means page 1 can be entirely one definition's callers with no
indication that four other definitions exist.

## Scope / Deliverables
- **Warn before scoping.** The cheapest useful change is a payload signal that the subject qname
  resolves to more than one definition, with their `file:line`s. Ship that first — it converts a
  silently wrong reading into a visibly ambiguous one, and it may be enough.
- **Then evaluate scoping.** A way to say "callers of the definition at `path:line`" — an optional
  `defined_in` argument, or accepting a `path:line` subject. Design it, cost it, and say whether the
  edges even carry enough information to answer it: the resolver links call sites to a **qname**, so
  per-definition attribution may not exist in the graph at all. If it does not, say so plainly —
  "cannot be answered with the current edge model" is a valid, useful outcome.
- **Do not invent a binding.** Where the language makes binding load-order dependent
  (`function_exists` guards, conditional definitions), the honest answer is *ambiguous*, never a
  guess. R4 forbids a heuristic that looks like a fact.
- **Check which tools inherit this.** `find_callers`, `find_references`, `impact`, `reachable_from`,
  `explain_path` and `read_symbol` all take a qname; each needs a stated verdict.
- **Relationship to 043.** [043](043_duplicate-decl-resilience.md) made duplicate declarations not
  break the index. This ticket is the next question: now that they survive, how does a caller ask
  about one of them?

## Constraints
- R2 — `function_exists`-guarded redefinition is a PHP language fact and belongs in the adapter's
  understanding, never a repo's name.
- R1.1 — the core sees "N nodes share this qname"; it must not reason about why.
- R4 — no probabilistic pick of a "most likely" definition.
- 061 — the ambiguity signal is conditional: absent when the qname is unique.

## Acceptance criteria
- A fixture with two same-qname definitions and callers of each produces a nav payload that states
  the subject is ambiguous and lists the definition sites.
- A unique qname's payload is byte-identical to today's.
- The scoping design decision is recorded either way, with the edge-model limitation stated if
  scoping cannot be answered.
- The 22,261-count style measurement is re-run on the fixture corpus so the fixture reflects a real
  distribution, not a hand-built pair.

## References
Field retro round 3 §3 (false positives table), §7 (the "which definition does this call site bind
to" question the session had to answer by reading). `code_atlas/store.py:113` (`_NODE_ORDER`),
`code_atlas/tools/find_callers.py`, `code_atlas/tools/search_symbol.py`.
Related: [043](043_duplicate-decl-resilience.md) (duplicate declarations survive indexing),
[046](046_resolver-qname-candidate-dedupe.md) (candidate dedupe),
[067](067_first-page-not-representative.md) (why merged results hide behind page 1),
[011](011_resolver.md) (what an edge's target actually identifies).
