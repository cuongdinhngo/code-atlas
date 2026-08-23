---
id: 141
slug: extractability-cut-edges-and-the-cycles-that-block-it
title: '"Can this module be split out?" — the cut edges and the cycles that block it, composed — evidence-gated'
phase: 1.5b
milestone: Coverage
status: deferred
depends_on: [120, 087, 140]
---

> **Status: proposed with its gate attached, not scheduled.** Same discipline as
> [098](098_correspondence-relation-seam.md): the mechanism is clear and the demand is **n = 0**.
> Provenance is an architecture review of [PLAN §1](../PLAN.md#1-goals--non-goals) on 2026-08-23, not a
> session. What is *not* in doubt is the gap this ticket documents.

## Why this exists

[120](120_subtree-dependency-attribution.md) shipped `subtree_dependencies` — tree→tree crossing with
duplicate-declaration attribution. That is the cut **cost** at path grain, and it is the larger half of
an extraction question already answered.

Extraction needs one fact 120 does not report: whether the boundary is **cyclic**. A subtree the rest
depends on *and* which depends back cannot be lifted without breaking the cycle first, and the direction
split is what says which. The machinery exists but is scoped elsewhere:

- Tarjan SCCs, iterative and deterministic — `code_atlas/onboarding/tour.py:29`, built for the tour's
  reading order (087).
- `code_atlas/onboarding/metrics.py:125` records cycle membership as **explicitly out of scope** for the
  metrics layer.
- `code_atlas/onboarding/layers.py:80` collapses cycles into a `mixed` bucket — *"Modules with
  dependencies both ways, including cycles"* — which names the condition without locating it.

So the graph knows about the cycles and nothing answers the question with them.

**Why deletion is not this question.** 120's evidence was `git rm -r legacy/` on the anchor monorepo:
deletion needs the **inbound** direction only. Extraction needs both directions plus the cycle. Reusing
120's evidence to license this ticket would be exactly the n = 1 slide 098 is held back for.

## Evidence gate — all three, in writing, before this is scheduled

1. **A named repo with the extraction decision actually pending**, the question asked in a real session,
   and what it cost to answer without a tool.
2. **A second, independent repo.** One repo is a shape, not a demand (098's rule).
3. **The cheap alternative rejected in writing:** specifically why `subtree_dependencies` plus
   `guided_tour`'s SCC output, composed by hand, is not enough. If it is enough, this ticket closes as a
   runbook entry instead.

## Scope — if the gate opens

- Direction-split crossing counts (inbound vs outbound) over 120's existing report.
- Module-level SCC over the same graph, reusing `tour.py`'s Tarjan — not a second implementation.
- The edge set whose removal makes the boundary acyclic, **or an honest refusal**: if the minimum set is
  intractable at repo scale, state the bound and report the cycles instead. No silent approximation
  presented as a minimum.
- Tier partition per [136](136_heuristic-share-has-no-owner.md): a cycle that exists only through
  heuristic edges is a candidate, not a blocker.

## Acceptance criteria

Written when the gate opens. **The gate is this ticket's only current deliverable** — an AC list drafted
now would read as a scheduled commitment.

## Out of scope

- **Recommending an extraction, or performing one.** The core never mutates code (§1 non-goal).
- **A cost model for the refactor** (effort, risk, ordering). Not derivable from the graph.
