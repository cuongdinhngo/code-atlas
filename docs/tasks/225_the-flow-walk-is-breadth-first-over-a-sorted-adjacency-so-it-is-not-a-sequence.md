---
id: 225
slug: the-flow-walk-is-breadth-first-over-a-sorted-adjacency-so-it-is-not-a-sequence
title: 'A sequence view over `flows.py` would assert an order the walk never established — `_adjacency` drops `edges.line` and sorts alphabetically, and `_trace` is breadth-first, so today''s step order is deterministic but is not call order'
phase: 3
milestone: Comprehension
status: todo
depends_on: [197, 144, 112]
---

## Why this exists

197 built the one onboarding surface that follows a single capability *running* rather than
aggregating: `flows.md`, one trace per capability, every hop an edge carrying a confidence tier, a
hop that cannot be proven **terminating** the trace instead of being bridged. It renders as
`flowchart LR` (`artifact.py:856-860`).

The obvious next step — render the same trace as a mermaid `sequenceDiagram` — **is not a renderer
swap, and treating it as one would ship a false claim.** A flowchart asserts only *reaches*; a
sequence diagram asserts *this happened, then this*. The data behind `flows.md` does not carry that,
for two independent reasons found by reading the module:

| | What it does | Why it blocks a sequence |
|---|---|---|
| `_adjacency` (`flows.py:237-244`) | takes `(source, target, kind, tier)` 4-tuples and returns `source -> ((target, kind, tier), …)`, **`tuple(sorted(set(rows)))`** | `edges.line` is not in the tuple at all, so call order never enters the module. The sort is alphabetical by target — its docstring says *"sorted so the walk is order-stable (R4.2)"*, which is determinism, not chronology |
| `_trace` (`flows.py:253`) | **BFS** from the seed | breadth-first visits every hop at depth 1 before any at depth 2. That is the right shape for *what does this reach*; it is the wrong shape for *what does this do first* |

`FlowStep` (`flows.py:99-115`) carries `qname · file · layer · kind · tier` — no line, and no
container, so there is also nothing to name a participant with yet.

**`edges.line` exists and is populated** (`store.py:116`), so the ordering fact is in the graph and
has simply never been carried into this module. That is the whole ticket: two small widenings, and
one honesty decision about what to do when the order is genuinely unknowable.

## Scope

1. **Carry `line` into the trace.** Widen the adjacency tuple to include it, order a source's
   outgoing hops by `(line, target)` — `target` breaks ties so R4.2 still holds when two calls share
   a line — and put it on `FlowStep`.
2. **Walk in call order within a frame.** Order the hops *out of one source* by line; the walk's
   overall shape stays 197's and its termination rules are untouched. Whether the walk becomes
   depth-first is a design decision this ticket must **state and justify**, not assume: DFS follows
   one call to its end before the next, which is what a sequence diagram draws.
3. **Name participants.** `contract.split_qname` already yields `(container, member)`, so a hop in
   `App\\Foo::bar` participates as `App\\Foo`. A hop with no container participates as itself.
   No new vocabulary.
4. **Render `sequenceDiagram`,** with the `class_diagram.py` pattern: deterministic renderer plus a
   `validate_mermaid_*` guard, no LLM, no language branch. `flowchart LR` stays — the two answer
   different questions and 197's is not superseded.
5. **Say when the order is not known.** Two hops on the same line, a hop reached through a
   `HEURISTIC` or `DYNAMIC` edge, or a `walk_truncated` trace cannot claim ordering. The diagram
   discloses that rather than drawing a confident arrow (R5.6 / 108's rule that a cap is stated).

**Not in scope:** conditionals, loops and `alt`/`opt` blocks — control flow is not in the graph, and
a sequence diagram that invents branches is worse than one that draws a straight line. Cross-request
sequences. Any change to `flows.md`'s termination or ranking rules (197 owns them).

## Acceptance criteria

- **AC1 (R6.5).** A fixture whose call order differs from its alphabetical order proves today's
  module returns the alphabetical one. Without that row the change cannot be shown to have done
  anything, because both orders are deterministic and a green test proves nothing on its own.
- **AC2** The same fixture then traces in source order, and its `sequenceDiagram` messages appear in
  that order.
- **AC3** Ordering is disclosed, not assumed: a trace containing a same-line pair, an unproven hop
  or a truncation renders with that stated. A reviewer must be able to see which arrows are claims
  and which are proven.
- **AC4** Identical input yields byte-identical mermaid and byte-identical `flows.md` payload fields
  other than the new ones (R4.2). **If `flows.md`'s existing step order changes, that is a visible
  output change and the PR says so** — it is a fix, but it is not silent.
- **AC5** `flowchart LR` output for an existing fixture is unchanged unless AC4's reordering touches
  it, and the manifest stays valid against 112's schema.

## Exclusions

- **E1** Whether a sequence view is *worth* the surface is unproven. The maintainer asked for it
  after finding onboarding *"not really impressive"* on a real project, which is a demand signal, not
  a measurement. The honest artifact is the diagram plus its cost in the token ledger; if the
  rendered result reads as noise on a real trace, recording that and closing as *declined on
  evidence* is a legitimate outcome.

## Notes

**The `line` widening has value independent of the diagram.** Any answer that lists several call
sites in one function currently presents them in whatever order the query returned. `edges.line` is
already stored; carrying it through the trace is the first place it becomes visible.

**Why this is filed separately from 224.** Both came from the same question — the maintainer's read
that onboarding is missing a sequence view and an ER view — but they share no code: 224 is a T-SQL
DDL reader and a Column → Column edge, this is a walk order and a renderer. Filing them as one
ticket would have coupled a parser change to a diagram decision.

**The destination worth stating.** A trace that begins at a real HTTP route rather than a configured
entry point, runs through a controller, reaches a procedure through 222's cross-language link and
ends at a table 224 can relate to another table, is one continuous picture. None of the three
tickets delivers it alone, and none of them depends on the others to be worth shipping.
