---
id: 056
slug: filter-values-fail-loud
title: An unknown filter value returns an empty result instead of an error
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [014, 033]
---

## Goal
`search_symbol(query=…, kind="class")` returns `total_count: 0, reason: "no_matches"`. The class
exists. The stored kind is `"Class"` — `contract.NODE_KINDS` is capitalised — and `store.py`'s search
clause compares with `nodes.kind = ?` (`_fts_search_clause` → `_narrow(…, "nodes.kind = ?")`), an exact,
case-sensitive match. A value that can never match any row produces the same payload as a query that
genuinely found nothing.

Two things make this worse than a typo trap:

- **The vocabulary is not discoverable.** `kind` is typed `str | None` in the tool signature, so the
  published MCP schema offers no enum. The only way to learn the accepted spellings is to run the query
  *without* the filter and read the casing off the results — the filter is discoverable only by not
  using it.
- **It violates R5.3.** An unknown filter value is a caller error, and the rule is to fail loud rather
  than degrade quietly. `find_callers` already does exactly this for its own selectors: a bad `arg_is`,
  a zero `arg_position`, or one half of the pair raises ([049](049_call-site-argument-selectivity.md)).
  The two tools disagree about the same class of mistake.

Observed in field retro round 2 §3d — one of three ways that session received an empty result that read
as proof of absence. It cost one wasted call; the other two cost more
([054](054_bare-name-callers-silent-drop.md)).

## Scope / Deliverables
- **Reject an unknown `kind`** with a message naming the accepted values (R5.3), rather than returning
  zero rows. `find_callers`'s selector validation is the shape to copy.
- **Publish the vocabulary in the schema.** Type the parameter so the MCP client sees the allowed
  values, as `detail_level` already does with a `Literal`. `contract.NODE_KINDS` is the single source of
  truth (R3) — the tool must not restate the list.
- **Sweep the other filters for the same defect.** `namespace` on `search_symbol`, and any other
  free-string narrowing parameter: decide per parameter whether an unmatchable value is an error or a
  legitimate empty, and write down which and why. `namespace` is plausibly the latter — it is
  matched case-insensitively today — so this is a survey, not a blanket change.
- **Decide the case policy explicitly.** Either accept `"class"` and normalise, or reject it and say so.
  Do not do both, and do not leave it implicit. Recommendation: reject, because normalising invents a
  second spelling of a frozen vocabulary (R3) for the sake of one typo.

## Constraints
- **No contract change (R3).** `NODE_KINDS` is already the vocabulary; this exposes it, it does not
  extend it.
- **No language branch in the core (R1.1).**
- **Backward-compatible for correct callers** — a request that works today must be unchanged.
- **Cost stays at zero on the hot path**: validation is a set membership test before any SQL.

## Acceptance criteria
- `search_symbol(kind="class")` raises, and the message names the accepted values.
- `search_symbol(kind="Class")` is unchanged.
- The published input schema enumerates the accepted kinds, asserted through a `list_tools` call in the
  same style as `test_the_guard_leaves_the_published_input_schema_alone`.
- The kind list in the schema derives from `contract.NODE_KINDS`, asserted — a hand-copied list cannot
  drift.
- The filter survey is recorded in the Outcome, with a decision per parameter.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/tools/search_symbol.py` (the `kind: str | None` parameter, and the `detail_level` `Literal`
that shows the shape to follow); `code_atlas/store.py` `_fts_search_clause` / `_narrow`
(`nodes.kind = ?`), `_search_short`; `code_atlas/contract.py:22` (`NODE_KINDS`).
`code_atlas/tools/find_callers.py` `_args_at` — the existing loud-rejection precedent (049).
Rule: R5.3 (fail loud on caller/config errors), R3 (frozen vocabulary).
Origin: field retro round 2 §3d, mode 3.
