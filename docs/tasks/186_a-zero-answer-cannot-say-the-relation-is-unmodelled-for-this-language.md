---
id: 186
slug: a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language
title: 'A zero answer still cannot say "this relation is not modelled for this file''s language" — 160 recorded the carve-out, and a second language turned it into a confident false negative'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [160, 183, 185]
---

## Why this exists

160 shipped the language-coverage note and **wrote its own limit down**
(`tests/test_zero_answer_coverage.py` docstring):

> *"The note names what the index does not cover, **never the subject's own language** (160 out of
> scope)."*

On a single-language index that carve-out costs nothing. On a two-language index it produces a
**confident false negative**:

`include_graph(path="…/thing.ts", direction="imported_by")` returns `reason: "no_matches"` — a
genuine zero, meaning *"nothing imports this file"*. The truth is *"TypeScript does not use
`include`; this relation is `IMPORTS` here, and this tool does not read it."*

The mechanism is visible at `include_graph.py:76`: the honest arm
(`relationship_not_modelled`) fires only when `count_unlinked_includes_mentioning(...) > 0` — it needs
**unlinked `INCLUDES` edges as evidence**. The TS adapter emits no `INCLUDES` at all, not even
unlinked, so the evidence is zero and the tool falls through to the confident zero. **The better the
adapter, the more confident the wrong answer** — that is the inversion worth fixing.

This is 102's class (*absent subject ≠ modelled zero*) applied to a **relation kind** instead of a
subject, and it is the one honesty gap that only appears once the product stops being single-language.

## Why the obvious fix is forbidden, and what replaces it

The obvious fix — *"if the file's language is typescript, `include_graph` does not apply"* — is a
language branch in the core and **R1.1 forbids it, CI-gated.** That is presumably why 160 carved it
out rather than solving it.

**But the honest answer is a data question, not a language condition.** *"Has this edge kind ever
been emitted for this file's language in this index?"* is a join — `edges ⋈ files.language` — and the
core may ask it without knowing what any language is. **183 builds exactly that table**, which is why
this ticket depends on it rather than duplicating the query.

## Scope

1. A nav answer that is empty **because the relation kind has no presence for the subject file's
   language in this index** says so, distinctly from a genuine zero and distinctly from
   `relationship_not_modelled`'s existing unlinked-evidence meaning. Design fixes the reason code and
   states whether it extends `NavReason` or reuses one (R3: nav vocabulary vs contract vocabulary).
2. The verdict is derived from **index data**, never from a language name in the core (R1.1). Design
   records the source — 183's per-build per-language stamp, or a bounded query — and why the other
   was rejected.
3. It reaches the tools where the gap is provable today: `include_graph`, `find_references`. Design
   records whether every nav tool needs it or only the vocabulary-gated ones, and why.
4. `try_instead` is honest where an equivalent exists: for `include_graph` on a language whose
   dependency edge is `IMPORTS`, the route is `find_references` — a hint that names a **callable
   tool** (the 093 rule), not a language.

### Explicitly not in scope

- Teaching `include_graph` to read `IMPORTS`. Merging two relation kinds into one tool is a contract
  and naming decision (069's territory), not a honesty fix, and it must not be smuggled in here.
- Making any adapter emit more vocabulary.
- The declared-state matrix — [185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md)
  owns that, and this ticket is what makes 185's `empty_relation_not_modelled` state observable in a
  payload rather than only in a test.
- `not_applicable_by_language` as a *language* fact (TS has no traits). The index cannot know that; it
  can only report absence. Design must state this limit rather than blur it — an absent relation and an
  impossible relation are different claims, and only the first is derivable here.

## Constraints

- **R1.1** — no `if language == …` under `code_atlas/`. The verdict comes from rows.
- **R5.6 / 102** — an index that cannot support the claim says nothing rather than guessing. A
  pre-183 index must not silently report "not modelled" for everything.
- **061** — a single-language index is byte-identical to today, and so is every confident non-empty
  answer (160 AC3 already pins the second half).
- **R5.2** — the reason must be sourced from the computation, not inferred from an empty list.
- **Cost** — the verdict is a meta/stamp read on the answer path, never a `GROUP BY` per call (183's
  constraint, inherited).
- **R6.7** — one definition site shared with 185's state vocabulary if both need it.

## Acceptance criteria

1. `include_graph(imported_by)` on a file whose language emits no `INCLUDES` returns the new reason,
   **not** `no_matches` — pinned, and failing on today's code.
2. The same call on a PHP file with genuinely no inbound includes still returns `no_matches` — the
   two are not collapsed, pinned.
3. `relationship_not_modelled`'s existing unlinked-evidence arm is unchanged, pinned (160/065).
4. A single-language index and every confident non-empty answer are byte-identical (061), pinned.
5. An index built before the per-language stamp existed says nothing rather than guessing (R5.6),
   pinned.
6. `try_instead` names a callable tool, verified by the existing `test_try_instead_is_a_callable_tool_name`
   guard.
7. No language branch under `code_atlas/` — R1.1 grep-gate green.

## References

`tests/test_zero_answer_coverage.py` docstring (160's recorded carve-out, quoted above);
`code_atlas/tools/include_graph.py:28,76` (`_INCLUDE`, the unlinked-evidence arm);
`code_atlas/store.py:1062` (`count_unlinked_includes_mentioning` — the evidence a second language
never produces); `code_atlas/contract.py:78` (`UNMODELLED_REFERENCE_KINDS`);
`code_atlas/tools/nav_result.py:26,45,87` (the reason vocabulary and the `try_instead` routes).
Verified 2026-08-28: the TS adapter's sources contain no `INCLUDES` literal. Related:
[160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the carve-out's owner),
[183](183_edge-health-has-no-per-language-breakdown.md) (the per-language data this needs),
[185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md) (the matrix that would
have caught this).
