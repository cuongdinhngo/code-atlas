---
id: 122
slug: exact-miss-shaping-discards-a-resolved-subject
title: '075 normalised the leading backslash for three tools; four `find_*` tools still decline over it — while holding the resolved qname in hand'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [075, 076, 065, 093]
---

## Why this exists (field retro round 6, 2026-08-21, 17-tool surface, anchor monorepo)

The evaluator asked `find_references` for a class using the same qname style that had just worked twice
on `read_symbol` — no leading `\`. It received:

```json
{"results": [], "reason": "name_not_qualified", "candidate_count": 1}
```

With the `\` prefixed, the same call returned **9 hits, 8 of them RESOLVED `EXTENDS`**. So the index
held the answer, knew there was exactly **one** candidate, and returned none of it.

**What it cost, and this is the number that matters.** After that one call the evaluator stopped
reaching for the index and used `grep` for every remaining question — **four tickets** of a five-ticket
session. One malformed subject, silently answered with an empty list, changed tool selection for the
rest of the session. The retro names it the most expensive thing that happened that round, above a
236 s index rebuild that cost nothing because it could be worked through.

## This is not a new defect class — it is [075](075_read-symbol-confident-zero-on-unnormalised-qname.md)'s scope, unfinished

075 is `done`, and its scope bullet reads:

> "**Normalise the subject qname before lookup.** A leading `\` is optional, everywhere a qname is
> accepted, **for every tool that takes one — not only `read_symbol`**. State the normalisation in one
> place; do not re-derive it per tool."
>
> "**Decide and record the sibling surface.** `read_symbol`, `file_outline`'s symbol arguments,
> `find_*` subjects, `impact`, `explain_path` — each gets an explicit verdict."

The shared place exists and works. `classify_missing_subject` (`nav_result.py:301`) returns four
statuses, and its own docstring states the intent verbatim:

> "a leading-anchor difference (`Ns\Sub\Enum` vs `\Ns\Sub\Enum`) resolves as one candidate"

That case returns `status="resolved_unique"` with **`resolution.qname` carrying the stored qname**.
Seven tools call the classifier. Three honour that status:

| Tool | Honours `resolved_unique` | Where |
|---|---|---|
| `read_symbol` | ✅ re-points and reads on | `read_symbol.py:190` |
| `explain_path` | ✅ | `explain_path.py:103` |
| `impact` | ✅ | `impact.py:148` |
| `find_references` | ❌ | `find_references.py:129` → `shape_exact_miss` |
| `find_callers` | ❌ | `find_callers.py:168` → `shape_exact_miss` |
| `find_implementations` | ❌ | `find_implementations.py:78` → `shape_exact_miss` |
| `find_view_data` | ❌ | `find_view_data.py:98` → `shape_exact_miss` |

The four failures share one function. `shape_exact_miss` (`nav_result.py:397`) has no
`resolved_unique` branch, so a uniquely-resolved subject falls into `if resolution.candidate_count:`
and is shaped as `name_not_qualified` — because `resolved_unique` also carries `candidate_count: 1`.
**The resolved qname is discarded by the payload shaper, one line before it would have been used.**

## Why the 3/4 split is the defect and not a design choice

075 predicted this exact failure mode and it happened anyway, two rounds later, in the sibling family
075 named: *"the forgiving tool teaches the habit that breaks the strict one"* (round 6 §8). An agent
trained by `read_symbol` reads `results: []` first and `reason` second. `candidate_count: 1` plus
`results: []` is the worst available shape — it proves the tool knows the unique answer and is
declining to give it.

## Scope

- **Give `shape_exact_miss` a `resolved_unique` verdict**, so the shared shaper can never again
  mis-file a resolved subject as under-qualified. One function, four callers.
- **Re-point the four `find_*` tools** onto `resolution.qname` and answer, matching `read_symbol`'s
  existing retry rather than inventing a second path (075's "state it in one place").
- **Make the re-point visible, not silent.** The answer is about a qname the caller did not type;
  disclose the normalisation the way 061 discloses every other conditional field, so a reader can tell
  a re-pointed answer from an exact hit.
- **Close 075's sibling-surface verdict as a test, not as prose.** An enumerating test over every tool
  that calls `classify_missing_subject` — the same shape 066 used for the clamp contract — so a new
  nav tool cannot join the family without an explicit verdict on this status.

### Not in scope

`ambiguous` (`candidate_count > 1`) stays a refusal with `try_instead: search_symbol`. Round 6
recorded that behaviour as **IMPROVED** over round 4 and it is correct: with six candidates the tool
genuinely does not know. This ticket is only about the case where it does.

## Acceptance criteria

1. **AC1.** For a namespaced subject that differs from the stored qname only by the leading anchor,
   all seven classifier callers return the same subject resolution — proven by one enumerating test
   over the tool list, so the count is the denominator and not a sample.
2. **AC2.** `find_references` on the round-6 subject shape returns the RESOLVED edges instead of
   `results: []`; the hit count and tiers match the leading-`\` form byte for byte.
3. **AC3.** A re-pointed answer names the qname it actually answered about; an exact hit is
   byte-identical to today (R4.2 — no payload churn on the common path).
4. **AC4.** `candidate_count: 1` with an empty `results` list is unreachable from any nav tool, and a
   test asserts the combination cannot be produced.
5. **AC5.** The `ambiguous` path is unchanged — same `reason`, same `candidate_count`, same
   `try_instead` — proven by a test that would fail if this change made ambiguity forgiving.
6. **AC6.** 075's sibling-surface bullet is marked closed in that ticket with the enumerating test as
   the evidence; a scope bullet that was recorded as done while three of seven tools honoured it is how
   this survived two field rounds.
