---
id: 287
slug: the-spelling-every-stack-trace-uses-is-a-near-miss
title: '`is_direct_match` bands a search hit on exact-or-prefix over name and qname, so `Class::method` — the spelling every stack trace, code review and ticket uses — is a qname *suffix* and lands in the substring band with `reason: substring_match`, while 249''s separator repair is gated on `no_matches` and can never reach the case that has hits'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [249, 167, 253]
---

## Why this exists (field retro — the anchor repo, round 25 §4, 2026-09-15)

`search_symbol(query="EntityPlan::getItem")` returns `reason: substring_match` with near-misses
ranked oddly. It still surfaced the right row, so nothing was lost — but the retro's objection is that
the query is not an odd spelling:

> *"`Class::method` is the most natural way to write a subject down, it is how every stack trace and
> every code review comment spells it, and the tool treats it as a trigram soup."*

The mechanism is one predicate. `is_direct_match` (`store.py:379-391`) is exact-or-prefix over `name`
and `qualified_name`; a stored qname is namespace-qualified, so `Class::method` is a **suffix** of it
and never a prefix. 167 made that predicate the single definition site for both the `reason` and the
ordering band (R6.7), so the miss is consistent — and consistently wrong for this one shape.

249 built the repair for the adjacent case (the member separator spelled with the wrong character) but
gated it on an *empty* answer: `if reason == REASON_NO_MATCHES and offset == 0`
(`search_symbol.py:283-284`). A `Class::method` query has hits, so the retry never runs. The two
half-measures do not compose: one handles a wrong separator with no results, the other handles a right
separator with results, and the gap between them is the spelling people actually type.

Same predicate, different complaint, worth separating so this ticket does not over-reach: round 26 §3
hit `substring_match` on a bare **class name** wanting one of its methods. That one is correct
behaviour with a correct route — the payload already says `try_instead: file_outline` — and is out of
scope here.

## Scope / Deliverables

- **A qname-suffix match on the member separator is a direct match.** When the query contains
  `MEMBER_SEPARATOR` and matches a stored qname on a component boundary, it bands with exact and
  prefix rather than with trigram near-misses — so `reason` and order both change, because 167 keeps
  them one predicate.
- **Boundary-anchored, not substring.** `getItem` must not become a direct match for
  `OtherClass::getItem` by accident; the match is on the separator-delimited tail, not on any
  substring ending the qname.
- **249's retry stays.** This ticket does not move the `no_matches` gate; it removes the case that
  needed it.

## Constraints

- R1.1: `MEMBER_SEPARATOR` is contract vocabulary (`contract.py:289` already derives the variant) —
  no language branch, no per-adapter spelling.
- R6.7: one definition site. Whatever changes must change `is_direct_match` (or a named helper beside
  it), never a copy in the ordering SQL — 167's whole point.
- 061: a query with no member separator is byte-identical to today, `reason` and order included.
- R4.2: deterministic ordering, unchanged tie-breaks inside the band.
- Cost: the predicate runs as a SQLite UDF per candidate row (`store.py:394-396`); no added query.

## Acceptance criteria

- `Class::method` against an indexed method returns `reason: ok`, with the exact member first.
- `method` alone is unchanged — still whatever band it earns today.
- `Class::method` does **not** direct-match a same-named method on another class.
- A query with no member separator produces a byte-identical payload.
- 249's separator retry and 167's banding tests still pass.

## References
`code_atlas/store.py:379-396`, `code_atlas/tools/search_symbol.py:118-128,279-284`,
`code_atlas/contract.py:289` (`member_separator_variant`),
[249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md),
[253](253_a-zero-overlap-guess-gets-no-route.md).
Origin: field retro round 25 §4 / §8.2, 2026-09-15 — "removes a recurring papercut with no downside".
