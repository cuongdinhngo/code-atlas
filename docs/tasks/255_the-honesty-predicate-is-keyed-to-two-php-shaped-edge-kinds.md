---
id: 255
slug: the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds
title: 'The predicate that decides whether an empty `find_references` is a genuine zero counts unlinked `REFERENCES`/`IMPORTS` only — the two kinds a PHP class subject has — so a T-SQL `Table` with 76 unlinked edges against it, 34 of them `WRITES`, returns a bare `no_matches`: the honesty layer is keyed to one language''s shape inside a core that forbids language branches'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [221, 232, 186, 065]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 18, verified live)

Round 18 recorded the session's one damaging answer and named it precisely:

> `find_references` on a **Table** returns a bare `no_matches` while `find_callers` on a **Function**
> in the same T-SQL file self-diagnoses as unmeasured. Same index, same language, two different
> honesty levels — and **the quiet one is the one I would have believed.** […] "What else touches
> `dbo.UserNotes`?" is exactly the question I asked before re-pointing two of its default
> constraints. If I had not had a prior note telling me T-SQL call edges are unreliable here,
> `no_matches` is a green light to change a column that three procs and a legacy view depend on.

Its ask was a caveat. **Measured against the anchor index read-only, the caveat is not the fix and
the size of the hazard is larger than the retro could see:**

```sql
-- .code-atlas/graph.db (the anchor repo, 2026-09-11), read-only
select count(*) from nodes  where qualified_name = 'dbo.UserNotes';      -- 1
select count(*) from edges  where target_qname   = 'dbo.UserNotes';      -- 0   <- the answer given
select kind, count(*) from edges where target_raw like '%UserNotes%';
--   CALLS 2 · CONTAINS 40 · WRITES 34                                    -- 76  <- what exists
```

**Thirty-four `WRITES` edges target this table and the tool reports nothing touches it.** `WRITES` is
the one relation in the contract that means *this changes the table's contents* — the exact relation a
reader asks about before re-pointing a default constraint.

## Root cause

`find_references` decides a zero is *unmeasured* rather than *genuine* by counting unlinked inbound
edges — but only of two kinds (`code_atlas/tools/find_references.py:223-233`):

```python
unlinked = store.count_unlinked_by_target_raw((lookup, name), kinds=UNMODELLED_REFERENCE_KINDS)
if unlinked > 0:
    reason = REASON_RELATIONSHIP_NOT_MODELLED
```

and `UNMODELLED_REFERENCE_KINDS = ("REFERENCES", "IMPORTS")` (`code_atlas/contract.py:106`).

A PHP `Class` subject is referenced by exactly those two kinds, so the predicate reads as general. A
T-SQL `Table` subject is reached by `WRITES`, `CALLS` and `CONTAINS`, none of which the predicate
counts — so `unlinked == 0`, the `relation_unmodelled_for_language` arm (which only asks about
`REFERENCES`) also declines, and the answer falls through to a bare `no_matches`.

**This is a language branch wearing a constant's name.** R1.1 forbids `if language == …` in the core;
the rule's purpose is that the core must not encode one language's shape. A tuple of the two edge
kinds PHP happens to use, consulted as though it were the set of all inbound relations, is that same
defect expressed as data instead of as an `if`. 232 found the mirror image one level down — one
emitted kind in a set masking a never-emitted sibling — and widened the reader per kind; the set
itself was never questioned.

## Scope

Two parts, and the second is the one that stops this recurring:

- **Key the predicate to the subject, not to PHP.** The kinds that can carry an inbound relation to a
  subject are derivable from the contract and from what this index actually holds — a `Table`'s are
  `WRITES`/`CALLS`/`CONTAINS`, a `Class`'s are `REFERENCES`/`IMPORTS`. Whether `find_references` should
  *return* `WRITES` hits, or only stop claiming a zero over them, is phase 2's decision; the ticket
  binds only that a bare `no_matches` over 76 unlinked edges must become impossible.
- **A conformance matrix, so the next kind does not repeat this.** This is the sixth instance of one
  class: 065 (an empty answer cannot explain itself) → 093 (the route must be callable) → 245 (the
  truncated substring shape) → 249 (the separator spelling) → 253 (the zero-overlap guess) → this.
  Each was fixed as one cell. A test over **(subject kind × relation × language present in the
  fixture index)** that fails when any cell can return an empty answer carrying neither a measured
  `reason` nor a route turns a recurring class into a gate.

## Constraints

- **R5.6** — derive the kind set from the contract and the index; an adapter must not *declare* which
  relations reach its kinds, or this repeats 231's failure one level down.
- **R1.1** — the fix is keyed by contract kind. A second hardcoded tuple, however well chosen, is the
  same defect.
- **R4.2 / 061** — deterministic; nothing added to an answer that has hits.
- **The matrix must fail on today's code.** A gate that passes before the fix proves nothing (R6.5).
- **022 AC3** — every payload that has hits today is byte-identical.

## Acceptance criteria

- **AC1** `find_references` on a `Table` with unlinked `WRITES`/`CALLS` against it no longer returns a
  bare `no_matches`; the answer names the relation it could not measure. The proving fixture mirrors
  `dbo.UserNotes`: one `Table` node, zero linked inbound edges, unlinked `WRITES` present.
- **AC2** The `Function` path's existing self-diagnosis (221/214) is unchanged — this ticket removes an
  asymmetry, it does not move the honest side.
- **AC3** A `Table` genuinely untouched by anything returns a zero distinguishable from AC1's answer.
- **AC4** The matrix test enumerates every contract kind against every inbound relation for the
  languages in the fixture index, and **fails on the pre-fix tree** at the `Table` × `WRITES` cell.
- **AC5** No payload with hits changes shape (022 AC3).

## References

- `code_atlas/tools/find_references.py:223-233`; `code_atlas/contract.py:106`
  (`UNMODELLED_REFERENCE_KINDS`), `:76`/`:124` (`WRITES` in the vocabulary since 022).
- [221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) — the same class on the
  `find_callers` side, fixed there; this is why the two tools disagree.
- [232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md) — widened
  the reader per kind and left the kind *set* unexamined.
- [065](065_empty-answer-cannot-explain-itself.md) — the rule this violates, and the first of the six.
