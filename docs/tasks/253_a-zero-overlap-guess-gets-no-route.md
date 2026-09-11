---
id: 253
slug: a-zero-overlap-guess-gets-no-route
title: 'A guessed name sharing no substring with any declared symbol falls through both 245 and 249 and returns a bare `no_matches`, so "this codebase has no such concept" and "you guessed the name wrong" are byte-identical answers — and the field produced both, indistinguishably, in the same session'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [245, 249, 065]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 18)

The consuming agent guessed three symbol names from domain vocabulary and got three clean misses:

> **Name-guess misses** (`uploadMemberPhoto`, `savePhoto`, `newMemberTab`) returned `no_matches`.
> Correct — those symbols don't exist under those names (the upload is
> `UploadFiles`/`UploadPhotoController`; the tab is procedural routing). Not a tool failure, but a
> reminder that `search_symbol` only knows declared symbols, so **a guessed name that isn't a real
> symbol tells you nothing about whether the concept exists.**

Its own tally counts these four times as "honest miss, zero signal", and its third suggestion asks
for the nearest declared symbols so it could "distinguish 'the concept doesn't exist' from 'you
guessed the name wrong'."

The session settled it both ways and the payload could not tell them apart. Photo upload **exists**,
under `UploadFiles` / `UploadPhotoController` — a name the reader eventually found through an
unrelated query. `newMemberTab` **does not exist as a symbol at all**; it is a routing action
string in procedural dispatch, and no name would have found it. Two opposite facts, one payload.

## Root cause

245 and 249 built the near-miss route, and both require the guess to *overlap* the real name.
`search_symbol` attaches a route on exactly these conditions
(`code_atlas/tools/search_symbol.py:344-350`, `:356-360`):

```python
def _needs_narrowing_route(hits):
    if hits.reason in (REASON_SUBSTRING_MATCH, REASON_SEPARATOR_NORMALISED):
        return True
    return hits.truncated and hits.total_count > len(hits.results)
```

- `substring_match` (245) needs the query to be a trigram/substring near-miss of something declared —
  there must be a candidate set to attach to.
- `separator_normalised` (249) needs `contract.member_separator_variant(qname)` to be non-`None` and
  to hit **uniquely** — a spelling repair, not a search.
- the truncation arm needs hits.

A name invented from the domain satisfies none of them: `total_count` is 0, `truncated` is `False`,
there is no separator variant. The answer is a bare `no_matches` with no `try_instead` — the one miss
shape on the surface with no route, which is precisely the gap 245 was filed to close, one step
further out. 249 already found the first such step (a separator spelling scores 0 exact and 0
substring, so 245's route had no candidate set); this is the same discovery for a guess that shares
no characters at all.

## Scope

A candidate route for a zero-overlap miss: when a query matches nothing, decompose it into name
tokens (`uploadMemberPhoto` → `upload` / `resident` / `photo`) and offer declared symbols matching
the tokens as **explicitly labelled candidates**.

What this must establish, and the reason it is worth a ticket rather than a nicety: on the evidence
above, a reader can tell the two cases apart. `upload` + `photo` reaches `UploadPhotoController`;
`newMemberTab` reaches nothing, and a route that returns nothing *after looking* is a different and
much stronger answer than one that never looked.

## Constraints

- **R5.6 — candidates are not hits.** They never enter `results`, never count in `total_count`, and
  `reason` is never `ok`. The 249 precedent (`separator_normalised`, never `ok`) is the model.
- **R1.1 — no language branch.** camelCase / snake_case / PascalCase are naming conventions, not
  language facts; the splitter is keyed by the convention, and lives in the core without naming a
  language (R2: the standard, never a sample's vocabulary).
- **R4.2** — deterministic candidate set and order for a given index and query.
- **Bounded** — a fixed small `k`; a token like `get` must not drag the whole index back.
- **061** — nothing is added to an answer that has hits; this rides the empty-answer path only.
- **Not a text search.** This ranges over *declared symbol names*, not file contents. Literal strings
  and default parameter values are a different gap (BACKLOG follow-up), deliberately out of scope.

## Acceptance criteria

- **AC1** A zero-overlap guess whose tokens match declared symbols returns labelled candidates plus a
  `reason` distinct from a genuine zero. The proving pair is this session's: a query on the token
  shape of `uploadMemberPhoto` reaches the upload controller.
- **AC2** A guess whose tokens match nothing returns an empty answer that **says the candidate search
  ran and found none**, so AC1's case and this one are distinguishable — the whole point of the
  ticket.
- **AC3** Candidates are excluded from `results` and `total_count`; an existing `no_matches` consumer
  reading those two fields sees no change.
- **AC4** Deterministic across runs on a fixed index; bounded by a stated `k` on the widest token.
- **AC5** Every answer that has hits today is byte-identical (022 AC3).

## References

- `code_atlas/tools/search_symbol.py:344-360` — the three route conditions and `_needs_narrowing_route`.
- `code_atlas/contract.py` — `member_separator_variant` (249's repair), and where a name splitter
  would sit to stay language-agnostic.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) — the route this
  extends; its design note that *"the route must MAKE PROGRESS"* is the standard applied here.
- [249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md) — the first miss shape
  found outside 245's reach; this is the second, and the pair suggests the rule is *every* miss needs
  a route, not every *near* miss.
- [065](065_empty-answer-cannot-explain-itself.md) — the rule the bare `no_matches` still breaks.
