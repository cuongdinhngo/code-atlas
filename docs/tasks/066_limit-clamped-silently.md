---
id: 066
slug: limit-clamped-silently
title: '`limit: 30` returns 10 rows and nothing in the payload says it was clamped'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [057, 033]
---

## Goal
Every paging tool computes `cap = config.max_results if limit is None else min(limit, config.max_results)`.
A caller who asks for 30 and gets 10 receives **no field saying the request was reduced**. Make the
clamp visible in the answer.

## Evidence (field retro round 3, 2026-08-09)
- The session passed `limit: 30` to `find_callers` **twice** and got exactly **10** rows both times.
  Nothing in either payload named `max_results`, the clamp, or the requested value.
- `truncated: true` and `total_count: 23` were both present and correct — so the caller could tell
  *more exist*, but not *why this page stopped at 10 when 30 were asked for*. Those are different
  questions: the first is about the result set, the second is about whether the tool honoured the call.
- The anchor repo's `CLAUDE.md` already carries a hand-written warning — *"`max_results` is 10, so
  read `total_count` for the real number"*. **A previous reader was burned by this and patched it in
  prose, in a file the server does not control.** That is the signal worth acting on: the server is
  exporting a caveat into every consumer's documentation.
- The same expression appears in `find_references`, `find_callers`, `find_view_data`,
  `search_symbol`, `file_outline` and friends; `include_graph` and `impact` do not take `limit`
  at all and simply use `config.max_results`.
- Round 3 also recorded that `max_results` does double duty on the anchor repo — it caps returned
  rows **and** the resolver's candidate fan-out — and that the session learned this only from a
  comment in the repo's own config file, not from the server.

## Scope / Deliverables
- **Report the clamp where it happens.** When `limit > config.max_results`, the payload says so —
  the requested value, the effective value, or a boolean; pick one and use it everywhere. One field,
  present only when a clamp actually occurred (061 weight discipline).
- **Decide clamp vs error, and record why.** Silently reducing is one option; rejecting a
  `limit` above the ceiling with a loud error (R5.3, as [056](056_filter-values-fail-loud.md) did for
  unknown filter values) is the other. The ticket must choose deliberately and write the reason down,
  because "accept the argument and ignore it" is the one option field evidence rules out.
- **Every tool that takes `limit`, uniformly.** A caveat that holds for five tools and not the sixth
  is worse than none.
- **State the ceiling where the caller can read it.** `get_index_status` (or the tool description)
  should carry the effective `max_results`, so a caller can size requests without reading the
  server's config file. Include which meanings the knob governs — rows returned, and resolver
  candidate fan-out — since a caller who thinks it only trims output will mis-read `total_count`.

## Constraints
- R4 — behaviour is deterministic; the clamp must not become host- or timing-dependent.
- 061 — no field on payloads where nothing was clamped.
- 057 — paging semantics (`offset`, `truncated`, `total_count`) stay exactly as they are; this ticket
  adds a signal, it does not change what a page contains.
- Do not raise `max_results` as the fix. The cap exists for measured reasons on the anchor repo
  (at 50 the graph carries 4.8M heuristic edges / 2.1 GB; at 10, 2.6M).

## Acceptance criteria
- A call with `limit` above the ceiling produces a payload from which the caller can tell, without
  reading server config, that the request was reduced — or a loud error, if that is the option chosen.
- A call with `limit` at or below the ceiling is byte-identical to today's payload.
- All tools accepting `limit` behave the same way; a test enumerates them so a new tool cannot
  silently opt out.
- The effective `max_results` is discoverable from the server, and its double duty is stated there.

## References
Field retro round 3 §4 ("`limit` is silently clamped"), §8 (the clamp named as half of the one
question where the graph was a net loss). `code_atlas/tools/find_callers.py`,
`find_references.py`, `find_view_data.py` (the shared `min(limit, config.max_results)` expression);
`code_atlas/config.py` (`max_results`). Related: [057](057_answer-pagination.md) (paging and
`total_count` auditing), [056](056_filter-values-fail-loud.md) (the fail-loud precedent for an
argument the server will not honour), [061](061_payload-weight.md) (why this is one conditional field).
