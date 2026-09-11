---
id: 251
slug: the-resolved-caller-can-be-off-the-page
title: '`find_callers` pages in alphabetical caller order with no tier predicate and no tier ordering, so on a common method name the one RESOLVED caller can be absent from the page entirely — and the caveat that did fire named a relation gap, not the question the reader was asking'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [165, 168, 057]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 18)

A consuming agent drove three BETA bug fixes with code-atlas as the primary instrument and scored the
session 7.5/10. `find_callers` was named the highest-leverage tool of the session — the *absence* of
two reports from `MemberPhotoResolver::browserSrc`'s caller set **was** a root cause — and it
carried both of the session's deductions. Its own summary of the first:

> `EvacMemberReportModel::build` returned 138 results, ~100 of them HEURISTIC false positives from
> unrelated `build()` methods across `legacy/`, `lib/`, and Symfony vendor code. The RESOLVED-tier
> answer (the one caller that matters) was correct but buried; **you must read the tier, not the
> count.**

"Buried" understates it, and the understatement is the finding. Read against the code, tier does not
rank the page — it is not in the `ORDER BY` and not available as a predicate. The page is the
alphabetically-first *n* caller qnames. Whether the one caller that matters is shown at all is
decided by where its qname sorts, and the reader is given no way to ask for it.

The anchor repo makes that sharp: it pins `max_results = 10` in `.code-atlas.toml` to hold the graph
at 2.6M heuristic edges (BACKLOG follow-up), so a 138-caller answer pages at ten. Nine of those ten
rows can be vendor `build()` noise with the real caller on page 12, and the only signal distinguishing
that from "the real caller is on this page" is `truncated: true`, which is true either way.

## Root cause

At depth 1 `find_callers` delegates paging to the store and does not touch the rows
(`code_atlas/tools/find_callers.py:413-425`):

```python
edges = store.edges_by_target(qname, kinds=CALLER_KINDS, limit=limit, offset=offset, args_at=args_at)
```

`edges_by_target` orders by `_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"`
(`code_atlas/store.py:170`) — caller qname, alphabetically. `confidence_tier` enters the tool in
exactly two places, and neither decides what reaches the page:

- as a **label** written onto each returned hit (`code_atlas/tools/nav_result.py:191`);
- as the **frontier gate** at `depth > 1`, where only RESOLVED expands (`find_callers.py:459`), counted
  in `frontier_skipped_non_resolved`.

So the tier discipline the payload advertises is real for *walking* and absent for *selecting*. A
RESOLVED-only view is not a filter the caller can express — it is post-hoc work on whatever rows the
alphabet handed over, over a page that may contain none.

**The second deduction, folded in here rather than ticketed alone.** The session's one miss was that
the live evacuation renderer is a flat web-root PHP file reached by an AJAX string from
`public/js/evacuationList.js`, not the MVC `EvacMemberReportModel` the agent fixed first. The
tool's answer was *correct* — `memberPdfAction`, itself test-only, is the only `src` caller, which
is exactly the evidence the MVC path is UI-unused — and the agent still drew the wrong conclusion
from it. Note what did **not** save it: the payload **did** carry
`authoritative_caveats: [cross_language_relation_unmodelled, sibling_definitions]`, and the retro
praises those caveats as honest. They fired and cost nothing, because they name a *relation* that is
unmodelled, not what that costs the reader — that reachability inside one language's call graph does
not answer "which of two parallel renderers does the front end invoke". That is a routing question,
and the caveat is the only place on the surface where it could have been said.

## Scope

Two changes to `find_callers`, one selection and one prose:

- **A tier control.** A way to ask for RESOLVED only (or to ask for the tier census of the full hit
  set), so the answer is chosen by tier and not by alphabet. The predicate belongs in the store query
  next to `kinds` and `args_at`, not in a post-filter over an already-truncated page — a post-filter
  cannot recover a row the `LIMIT` never returned. Whether the knob is an argument or a changed
  default is phase 2's decision; the ticket does not bind one.
- **The caveat says what it costs.** When `cross_language_relation_unmodelled` rides an answer, name
  the operational limit in the reader's terms — this answer is reachability within one language's
  call graph and does not establish which entry point the front end invokes.

## Constraints

- **No default payload change** unless phase 2 argues the default *should* change and says so — the
  022 AC3 byte-identity check applies to every other tool regardless.
- **R5.6** — a tier-filtered answer must say it was filtered. A `total_count` that silently means
  "RESOLVED only" is a different claim wearing the old name.
- **R4.2** — deterministic: identical index and arguments, identical page.
- **061** — omit when empty; a census on an all-RESOLVED answer adds nothing and is not emitted.
- **R1.1** — no language branch; the caveat prose is keyed by the contract's relation vocabulary.

## Acceptance criteria

- **AC1** A caller can obtain the RESOLVED callers of a common method name **in one call**, on an index
  where the RESOLVED hit sorts outside the first page of the unfiltered answer. This is the proving
  shape: a fixture where the correct answer is provably off page 1 today.
- **AC2** `total_count` under a tier request counts matches of that request, and the payload names the
  filter, so it is never mistaken for the unfiltered total.
- **AC3** An unfiltered answer lets the reader tell "no RESOLVED caller exists" from "no RESOLVED
  caller is on this page" without paging to the end.
- **AC4** When `cross_language_relation_unmodelled` is attached, the payload states the limit in terms
  of what the reader may not conclude, not only which relation is unmodelled.
- **AC5** Every existing payload is byte-identical when the new control is not used (022 AC3).

## References

- `code_atlas/tools/find_callers.py:413-425` (depth-1 paging), `:459` (the frontier gate — the only
  tier decision in the tool), `code_atlas/store.py:170` (`_EDGE_ORDER`), `:1330` (`edges_by_target`).
- `code_atlas/tools/nav_result.py:191` — where the tier becomes a label.
- [165](165_find-callers-splits-across-twins-and-says-reason-ok.md) / [168](168_find-references-never-got-165s-twin-disclosure.md) — sibling definitions and the caveat vocabulary this extends.
- [057](057_answer-pagination.md) — the paging contract whose order this ticket makes load-bearing.
- BACKLOG follow-up "`max_results` does two unrelated jobs" — why the anchor repo pages at ten, which
  is what turns a ranking weakness into a missing answer. The field instance moved here from that
  follow-up (R7.6): the anchor repo pins `max_results = 10` in `.code-atlas.toml` to hold the graph
  at 2.6M heuristic edges instead of 4.8M, so every answer is capped at ten rows to buy an index
  size, and a caller's `limit=100` is silently clamped to it.
