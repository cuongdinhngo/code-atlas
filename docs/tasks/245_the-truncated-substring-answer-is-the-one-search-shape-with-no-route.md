---
id: 245
slug: the-truncated-substring-answer-is-the-one-search-shape-with-no-route
title: '`search_symbol` attaches `try_instead` only when the answer is empty *and* `index_stale`, so the shape that measurably sends the reader to grep — `reason: substring_match` with `total_count` far above `max_results` — is the one answer in the payload that names no narrower query, while the two registry entries that would answer it already exist unused'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [167, 065, 093, 123]
---

## Why this exists (field retro rounds 16 and 17)

065 established the rule this project keeps re-learning: a refusal with no route is a trap. The
routes were built — `TRY_INSTEAD_*` for a callable tool, `TRY_INSTEAD_HINT_*` for prose naming the
qualifier (093), with the explicit design note that *"the route must MAKE PROGRESS"*.

`search_symbol` attaches one, at exactly one condition:

```
if hits.reason == REASON_INDEX_STALE and hits.total_count == 0:
    return attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE)
```

`code_atlas/tools/search_symbol.py:265-267`, and the same guard on the batch path at :281-283. So the
empty-and-stale case is routed and **every other partial answer is not** — including the one the
field keeps walking into:

```
search_symbol("QuickAccessModel", kind=Method)
→ reason: "substring_match", truncated: true, total_count: 80, 10 rows returned
```

Ten rows out of eighty, four of them from test doubles, and the wanted method not among them. The
answer is honest — 167's `substring_match` says *near-miss, not hit*, and `truncated` says the page
is short — but honesty without a route leaves the reader to invent the next query. Both rounds
invented the same one: **grep the file, read the qname off the hit, call `read_symbol` directly.**
Round 17 priced that detour at ~90 seconds and noted it was the second consecutive round to take it.

The narrowing advice is already written down. `TRY_INSTEAD_HINT_METHOD_QNAME` exists for a
neighbouring miss and says *"list the class's methods, then re-ask …"*; `TRY_INSTEAD_FILE_OUTLINE`
is the tool that lists them. Neither is reachable from this answer. The retro asked for a
`members_of(qname)` tool; `file_outline` already is one, which makes this a routing defect and not a
surface gap — the 24-tool count stays as it is.

## Scope

- **Route the truncated near-miss.** When `reason` is `substring_match`, or `truncated` is true with
  `total_count` above the returned page, attach the route and the hint that name a narrower query.
- **Make the hint say something true about *this* answer.** A class-name substring over-matching a
  class's own members is a different miss from a bare name colliding across namespaces; if one
  sentence cannot serve both, say which cases get which, and which get none (R5.4c: naming a tool
  that cannot answer is worse than naming none).
- **Reuse the registry.** `TRY_INSTEAD_FILE_OUTLINE` and `TRY_INSTEAD_HINT_METHOD_QNAME` exist; a
  third spelling of the same advice is the drift 093's two-register rule exists to stop.
- **Check the sibling tools for the same gap** and state the verdict: `file_outline`,
  `find_callers` and `find_references` each have a truncation path, and this ticket either fixes the
  class or says why `search_symbol` is the only instance.
- **Out of scope:** a `members_of` tool, changing the ranking (180 owns that), changing `max_results`
  or its double duty (a standing follow-up), and suppressing test-file rows — a separate question
  with its own trade-off.

## Constraints

- **093** — `TRY_INSTEAD_*` holds a registered tool name, `TRY_INSTEAD_HINT_*` holds prose. Neither
  carries the other's kind; the invariant test pins it.
- **R5.4c** — a route must make progress. Routing `search_symbol` back to itself loops for the
  mechanical reader the field exists for.
- **061** — omit when empty. A confident, complete answer gains no field.
- **123 / 067** — `result_kinds` already tells a one-page reader what the page omitted; the hint must
  not restate it.
- **R4.2** — deterministic: the same query returns the same route.

## Acceptance criteria

- A `substring_match` answer over a class with more methods than `max_results` carries a route and a
  hint naming the narrower query, pinned by a test built on the shape the field hit (a class name,
  `kind=Method`, test doubles present).
- The batch (`queries`) path carries it per subject, never on the envelope (101).
- A complete, confident answer is byte-identical to today — asserted.
- No new `TRY_INSTEAD_*` constant duplicates an existing one; the 093 invariant test still passes.
- A written verdict on `file_outline` / `find_callers` / `find_references`.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.2 and §5 asks 3 and 5; round 16 recorded the
same detour. Related: [065](065_empty-answer-cannot-explain-itself.md) (the rule),
[167](167_a-substring-near-miss-is-reported-as-reason-ok.md) (`substring_match`),
[093](093_try-instead-is-not-a-callable-tool-name.md) (the two registers),
[123](123_file-outline-total-count-is-the-page-length.md) (what the capped page already discloses),
[180](180_search-ranks-a-near-miss-above-exact-matches.md) (ranking, deliberately untouched),
[101](101_nav-tools-take-one-subject-at-a-time.md) (per-subject routes on the batch path).

## Token usage

| Phase | Tokens |
|---|---|
| — | not yet started |
