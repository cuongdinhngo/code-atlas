---
id: 192
slug: coverage-note-suppressed-on-a-partial-answer
title: 'The coverage disclosure self-suppresses on any answer carrying results, so a partial answer is the one shape it never reaches'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [160, 173, 186]
---

## Why this exists (field retro 8-A, re-confirmed round 12 §14 row 6-C)

`attach_coverage_note` names the index's language-coverage gap on an empty answer. It returns early on
any answer that has results:

```python
    if payload.get("results"):
        return payload
```

`code_atlas/tools/coverage.py:119-120`. So the disclosure covers **absence** and never covers a
**partial** — which is the shape that has actually cost an answer, twice, measured:

- **Round 8 §4 (8-A).** `search_symbol("DialogueService")` returned **1** hit, a PHP test method.
  Ground truth: **281 `.js` files** reference it. The retro's words: *"`total_count: 1` on a symbol
  with 281 real sites is a false negative wearing a modelled zero's clothes"* — and *"nothing in any
  `no_matches` or low-`total_count` answer names the index's language coverage, while
  `get_index_status` holds `indexed_suffixes` one call away."*
- **Round 12 §14 row 6-C.** *"STILL INVERTED, now on JS… r9 showed completeness harming via
  `legacy/`; r12 shows the same shape with a new language added to it."*

**The trend is the argument.** The failure got worse when a language was added, both times, with no
code change. A third adapter ([184](184_tsql-source-adapter-tier-1a.md)) makes it worse a third time,
and that adapter cannot fix it — its AC3 forbids a `code_atlas/` diff.

**This is not the 186 census and not a new one.** 186 asks *"does the subject's language emit these
kinds?"*; that verdict is silent whenever the language does emit them, which is exactly the partial
case. The gap here is one condition in a function that already exists and already knows the answer.

## Scope

1. Let the coverage disclosure reach an answer that **carries results** and is nonetheless partial
   with respect to the index's coverage. The verdict stays a data question with no language name
   (R1.1) and reuses `attach_coverage_gap`; design records what makes an answer "partial" without
   re-deriving 186's or 173's existing predicates.
2. Keep it self-gating and idempotent, as the docstring promises for every return point — a confident
   exact answer must not grow a note (160's original carve-out survives).
3. Prove the no-false-alarm property: an answer complete with respect to the indexed languages gets
   **no** note. This is what makes the change safe to apply to non-empty payloads at all.

### Explicitly not in scope

- Any new node or edge vocabulary. Zero contract cost.
- The cross-language pair census, and per-subject unlinked-edge evidence — both were considered for
  184 and rejected: the first cannot separate a legitimately empty language pair from a gap, the
  second is inert until edges exist that never get emitted.
- Ranking. 6-C's other half is a ranking finding and belongs with 167/180.

## Constraints

- **R5.6** — silence is not evidence. Where the index cannot say, withhold the claim rather than
  inventing one; `relation_unmodelled_for_language` already answers `False` on every silence and this
  must not regress that.
- **R1.1** — the verdict reads the index's own stamps, never a language name.
- **R6.5** — the guard ships with a recorded red run: the note must be shown absent before the change
  on a payload that carries results.

## Acceptance criteria

1. An answer carrying results, partial with respect to the index's coverage, carries the disclosure —
   pinned by a test that fails before the change on the same payload.
2. An answer complete with respect to the indexed languages carries **no** note (no false alarm),
   pinned separately.
3. A confident exact/prefix answer is unchanged — 160's carve-out and 167's `substring_match` path
   both still behave as their tests assert.
4. No `contract_version` bump.

## References

Field retro round 8 §4 (8-A, the 1-vs-281 measurement), round 12 §14 row 6-C. `coverage.py:103-123`.
Related: [160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the note's origin and its own carve-out),
[186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (the per-language census this is **not**),
[184](184_tsql-source-adapter-tier-1a.md) (the third adapter that widens this, and whose AC3 bars it
from fixing it).
