---
id: 279
slug: an-autoloaded-repo-answers-unreachable-and-means-unmeasured
title: 'A repo that loads classes through a registered autoloader emits no include edge for any of them, so "not reached by an include" is close to "a file" — and the tools that answer reachability say `no_inbound` / `unreachable_from_roots` in the same shape and with the same confidence as a real one, though the indexer parsed the autoloader registration and could have said the resolution strategy is unmodelled'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [031, 255, 264]
---

## Why this exists (field retro — a PHP 5.6 monolith, 2026-09-13, round 19 §2.5 / §6.1)

A P0 architecture decision, twelve queries, one of them:

```
own-ish php files never INCLUDEd: 4,507      (of ~6,310 indexed)
```

Read plainly: **71% of the application is dead code** — in a document about how much work an upgrade
is. It is meaningless. The bootstrap does `spl_autoload_register('Core::loadClass')`, so class
loading emits **no include edge at all**, and 572 top-level files are web entry points nothing
includes by design. The query measured *files not reached by a literal include statement*, which in
that codebase is nearly *files*.

That session ran raw SQL, so no honesty layer was in play — but the shipped tools answer the same
question. `find_orphans` refuses carefully on the two failures it knows (`roots_matched_nothing`,
`walk_budget_exhausted` — `find_orphans.py:44–53`, 182) and has nothing to say about a **resolution
strategy the graph does not model**. On an autoloaded repo its `no_inbound` population is the same
4,507, in a payload whose other refusals teach the reader that a refusal is what absence looks like.

The retro's first ask is the cheap half:

> *"A `meta` key declaring the loading strategies the graph does not model… the indexer saw
> `spl_autoload_register(…)` while parsing. It knows. It just does not say."*

Related and separate: the same round found `INCLUDES.target_qname` is frequently NULL with the literal
only in `target_raw` (§2.4), so a reachability query written against one column silently loses rows and
returns a clean zero. Inside the tools that is already handled; it is a trap for anyone reading the
database, and §6.2's `edges_resolved` coalescing view is the standing suggestion.

## Scope / Deliverables

- **A build-time stamp naming unmodelled resolution, per language**, set from evidence the parse
  already produced — a registered autoloader, a dynamic include — never from a guess or a file name.
- **The reachability answers read it.** `find_orphans` (and any tool whose claim is "nothing reaches
  this") states that the population is unmeasured where the stamp is set, with the 255/264 wording
  that already exists for an unmeasured inbound relation. A stamped repo cannot return a bare
  orphan population.
- **Evidence, per R2, is the language's own standard** — its autoload registration API, its package
  manager's autoload declaration — not a framework list and not a repo's bootstrap path.
- **A `meta` key a raw-SQL reader can find**, since the retro's whole class of failure happens outside
  the tools; the runbook names it.

## Constraints

- R5.6: the stamp says *unmeasured*, never *these files are reachable*. No inferred edges.
- R2 / R2.2: no framework or sample-repo names in core or adapter.
- R1.1: the core reads a stamp; the detection is the adapter's, expressed in the contract.
- 061: a repo with no such evidence pays nothing and every payload is unchanged.
- Not a resolver ticket. PSR-4 / autoload-aware include *resolution* stays the separate follow-up
  BACKLOG already carries; this one only makes the silence visible.

## Acceptance criteria

- An adapter fixture registering an autoloader produces the stamp; one without it does not.
- `find_orphans` on the stamped fixture carries the unmeasured statement and a route; on the unstamped
  fixture its payload is byte-identical to today's.
- The stamp is readable from `meta` and named in `docs/runbooks/onboarding-a-repo.md`.
- A documented note that `INCLUDES.target_qname` is nullable and `target_raw` carries the literal,
  wherever the repo tells a reader how to query the database directly.

## References
`code_atlas/tools/find_orphans.py:37–53`, `code_atlas/tools/reach_shared.py`,
field retro round 19 §2.4 / §2.5 / §6.1 / §6.2, [031](031_reachability-orphans.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[264](264_the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name.md),
BACKLOG follow-up *PSR-4 / autoload-aware include resolution*.
