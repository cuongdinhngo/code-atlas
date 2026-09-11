---
id: 249
slug: a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route
title: 'A miss whose only defect is the separator spelling returns a clean no_matches, and 245''s near-miss route cannot fire because the guessed name is not a substring of the real one'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [245, 224]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 17)

A consuming agent guessed the qname form for a column as `IndividualSiteForms.ChangeDateTime` and
swept seven subjects in that shape. All seven returned a clean `no_matches`. The real form is
`dbo.IndividualSiteForms::ChangeDateTime` — the container keeps its native `.` separator and the
member joins on with `::` (CONVENTION §3). The retro's note: *"it knew it had a node matching under a
different separator and suggested nothing"*, and it scored the round a full turn lower for it.

The turn was lost to a **spelling of the separator**, not to a wrong name, a wrong table or a wrong
column. Both halves of the qname were exactly right.

## Root cause

[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) shipped the route
for a near-miss page — `reason=substring_match` now carries `try_instead: file_outline` and a
narrow-by-qname hint. It cannot fire here, and the reason is mechanical: **the guess is not a
substring of the truth.** Measured on the anchor index:

```
real column qname:   dbo.Benefit::psi_file
dotted spelling:     dbo.Benefit.psi_file
  exact matches:     0
  substring matches: 0
```

Replacing `::` with `.` breaks the substring relation in both directions, so FTS and the trigram
near-miss path both return an empty candidate set. With no candidates there is nothing to rank, so
the payload is a truthful, complete, useless `no_matches` — and 245's route, which is attached to a
*populated* near-miss page, has nothing to attach to.

The separator is also the one part of a qname an agent cannot infer. A container's separator is
native to its language (`\Ns\Class`, `module.Class`, `src/user.ts`, `dbo.Table`) while the member
join is always `contract.MEMBER_SEPARATOR`. An agent that knows the table and the column still has to
guess which of the two it is looking at, and `.` is the spelling every SQL tool in the world prints.

## Scope

Before a search declares `no_matches`, retry the query with member-separator normalisation, and if
that retry finds candidates, return them as the near-miss shape 245 already defined — with the route
245 already built.

Concretely: for a query containing a separator character, try the variant where the **last**
separator is `contract.MEMBER_SEPARATOR`. `dbo.Benefit.psi_file` → `dbo.Benefit::psi_file`. The
last one is the right one to move because the member join is always the final segment; moving every
separator would turn `\Ns\Class::method` into nonsense.

## Constraints

- **R1.1 — no language branch in the core.** Normalise on `contract.MEMBER_SEPARATOR`, which is
  contract vocabulary. No `if language == "sql"`, and no list of which languages use `.` — the fix is
  the same one for `module.Class.method` in Python as for `dbo.T.col` in T-SQL.
- **R5.6 / R5.2 — a retry result is not an exact hit.** A subject found only by normalising the
  separator is a **near-miss**: it keeps the `substring_match` register (or a sibling reason naming
  the normalisation), never `reason=ok`. The agent asked for a name that is not in the graph; what it
  gets back is a correction, and the payload must say which.
- **No second search per miss on the hot path.** This runs only where the answer is already empty, so
  it costs nothing on a hit. Do not add the retry ahead of the primary lookup.
- **Deterministic (R4.2).** Identical input, identical rows — the retry is a pure string transform
  plus the same store query, nothing heuristic about ranking.
- **One spelling of one piece of advice.** If the existing `TRY_INSTEAD_HINT_NARROW_BY_QNAME` already
  says what the agent should do next, reuse it; a separator correction is a different *finding* and
  may need its own hint, but not a second phrasing of the same re-ask (the 245 review's rule).

## Acceptance criteria

- **AC1** `search_symbol` for `dbo.T.col`, where `dbo.T::col` is indexed, returns that node as a
  near-miss with a reason naming the correction — not `no_matches`, and not `reason=ok`.
- **AC2** The same holds for `read_symbol`, which is where a qname guess most often lands.
- **AC3** A query that misses under both spellings still returns the unchanged `no_matches` payload,
  byte-identical to today — the retry adds nothing when it finds nothing.
- **AC4** A query with no separator at all runs exactly one lookup; no extra store round-trip.
- **AC5** A genuine `.`-separated qname that exists as indexed (a Python `module.Class`) is returned
  as an exact hit by the primary lookup and never reaches the retry.
- **AC6** No language name appears in the core diff (`tests/test_no_language_branches.py` stays
  green).

## References

- `code_atlas/contract.py` — `MEMBER_SEPARATOR` and the qname convention (CONVENTION §3).
- `code_atlas/tools/search_symbol.py` — `_search_one`, the `substring_match` near-miss path and
  `TRY_INSTEAD_HINT_NARROW_BY_QNAME`.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) — the route this
  reuses, and the reason it cannot fire on an empty candidate set.
