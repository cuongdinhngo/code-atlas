---
id: 049
slug: call-site-argument-selectivity
title: Select call sites by argument shape — "which of the 5,261 callers pass `null` here?"
phase: 1.5b
milestone: Agent-fit
status: in-progress
depends_on: [013, 037, 002]
---

## Goal
A real decision in the first external session (retro round 1) turned on this question: *of the call sites
of one shared DB helper, which pass a literal `null` as argument 2?* The answer decides where a fix
belongs — a nullable value that most callers pass is part of the contract (fix the shared method, helping
everyone); one passed by five callers out of thousands is caller pollution (fix the five).

code-atlas could not answer it, and the agent knew that in advance, so it never called `find_callers` at
all. It used a regex over call syntax, got **5 of 5,261**, and acted on that ratio — while recording in
the retro that this is precisely the kind of measurement it does not trust. A load-bearing architectural
decision rested on a grep the decider considered unreliable, with a name-resolved graph of the same call
sites sitting unused beside it.

Note what the gap is *not*. [037](037_compound-nav-responses.md) already added `include_source`, which
returns each hit's own call-site line (`tools/call_site.py`), so a returned row does show its arguments.
The gap is **selection and counting, not display**: with `total_count: 5261` and `max_results: 10` you
cannot enumerate the sites, so you cannot find the five, and you cannot state the ratio. Display scales
with what you can already see; this question needs the graph to filter.

There is also a second, cheaper question in the same family, from the same session: **arity**. "Which
callers omit argument 2 entirely" is a distinct case from "pass it as `null`", and the fix differs.

## Scope / Deliverables
This ticket is **design-first**; the deliverable of its analysis phase is a decision between the two
shapes below, not an implementation of both.

- **Option A — record it at index time.** The adapter emits per-call-site argument facts into the edge
  (arity always; literal arguments where they are literals — `null`, `true`, a string, a number — and a
  marker otherwise). `find_callers` then gains a filter. This makes the question a real graph query, but
  it is a **contract change**: new edge fields ⇒ `contract_version` bumps and the conformance suite moves
  (R3). Cost must be measured, not assumed — the anchor repo has ~1.77M edges and the edge table is
  already the whole index (823 MB); an `extra` payload per CALLS edge is not free, and 046 exists
  precisely because edge-table bloat is expensive.
- **Option B — resolve it at query time.** The graph gives the call sites; a bounded pass reads those
  lines (the `call_site` machinery already reads and caches per file) and filters on them. No contract
  change, no index growth, exact only to the precision of a line-level regex — but scoped to *known call
  sites of a known qname*, which is a far narrower and more honest filter than a repo-wide grep. Cost is
  O(sites), and 5,261 sites is a lot of file reads.
- **Whichever wins, the answer must be a count, not just rows.** The session needed "5 of 5,261". A
  filtered `total_count` alongside the returned rows is the actual deliverable; ten matching rows without
  a denominator would not have answered the question.
- **Arity first if the two separate.** If Option A proves too costly for full literal capture, arity
  alone is much cheaper (one integer) and answers the "omits the argument" half. Ship the half that pays.

## Constraints
- **No language branch in the core (R1.1).** "Literal argument" is a language notion, so any structured
  capture is emitted by the adapter and stays vocabulary-neutral in `contract.py`. The core must not learn
  what a PHP `null` looks like.
- **Contract discipline (R3).** Option A bumps `contract_version` and updates `tests/contract/`; adapter
  #2 does not exist yet, so a field the PHP adapter alone can fill must still be *specified* so another
  language can fill it. If it cannot be, that is an argument for Option B.
- **Measure before choosing (§19).** Index-size and build-time deltas on the anchor repo for Option A;
  wall-clock for Option B at ~5k sites. A decision without both numbers is a guess.
- **Determinism (R4)** and **no promotion of tiers (R5.2)** — filtering must never change a hit's
  confidence tier. A HEURISTIC call site that matches an argument filter is still HEURISTIC.
- **Truthful counting.** `total_count` on `find_callers` is already documented as exact at depth 1 and a
  floor beyond it (`tools/find_callers.py:47-60`); a filtered count must state which it is, and must not
  silently become "matches within the first page".
- **YAGNI on the filter language (R7.1).** One question drove this ticket. Ship a predicate narrow enough
  to answer it (argument position + literal/absent), not a query DSL.

## Acceptance criteria
- The analysis phase records measured index-size, build-time and query-time numbers for both options and
  states the choice with its reason. **Approval gate before implementation.**
- Given a qname with N call sites of which K pass a literal `null` at position *p*, the tool returns those
  K sites and a count of K, with N still available (asserted on a fixture, K ≥ 2, N > `max_results`, so the
  truncation path is exercised).
- Callers that omit the argument are distinguishable from callers that pass it as `null` (asserted) — the
  two were different fixes in the session that motivated this.
- Filtering changes no hit's `confidence_tier` (asserted).
- If Option A: `contract_version` bumped, `tests/contract/` updated, and the index-size delta on the
  anchor repo recorded in the ticket outcome.
- Unfiltered `find_callers` behaviour and payload are byte-identical to today (asserted) — the filter is
  opt-in.
- `pytest`, `ruff`, `mypy` green; tokens-to-answer fixture gate still passes.

## Analysis — measured, then decided

Both options were measured on the anchor repo (1,774,891 edges, 768.0 MB after `VACUUM`) against one
shared DB helper with **8,650 distinct call sites across 1,764 files**.

| | Option A — record at index time | Option B — resolve at query time |
|---|---|---|
| Storage | **+2.9 MB (+0.4 %)** arity only · **+22.5 MB (+2.9 %)** arity + per-argument payload | 0 |
| Query | one indexed `WHERE` over the target's edges | 0.01 s SQL + **0.08 s** reading 1,764 files (35 MB) |
| Call sites it can answer | **100 %** | **85.0 %** |
| Where the logic lives | the adapter, which has the AST | the core, which does not |

Two measurements overturned the assumptions in the scope above.

- **Option A is not expensive.** The fear came from [046](046_resolver-qname-candidate-dedupe.md), but
  046's lesson is about **row count**, not column width: 1.06 M redundant *rows* cost 310 MB, while a
  payload on every existing row costs 2.9 %.
- **Option B is not cheap where it counts.** It is fast (0.09 s), but **1,299 of 8,650 call sites
  (15.0 %) have an argument list that continues past the indexed line**, so a line-level view cannot see
  argument 2 at all — and that blind spot is *biased toward long argument lists*, which is exactly the
  population the motivating question is about. Worse, the scanner that produced these numbers is ~20
  lines of paren- and quote-aware PHP-specific parsing. In `code_atlas/` that is a language's syntax in
  the language-agnostic core (R1.1) and parsing outside an adapter (R1.4). It also cannot see PHP 8
  named arguments, which move a value away from its position entirely.

**Decision: Option A**, full literal capture rather than arity alone — the two questions the field
session actually had ("passes `null`" vs "omits it") are only separable with both, and the measured
population confirms they are different sets, not one shape seen twice (of the single-line calls: 1,316
omit argument 2, 9 pass a literal `null`).

## Outcome
Contract **v2 → v3**, schema **2 → 3**, one new optional edge field.

- **`args`** (`contract.py`): one entry per argument at a `CALLS`/`NEW` site, in source order. JSON
  `null` = "not a literal"; a string = the literal's **category** from `ARG_LITERALS`
  (`null true false number string array`). The *value* is never recorded — nobody asked to match a
  particular string, values would carry repo content into the index, and categories keep the field
  language-neutral for adapters #2–#4.
- **Omitted means unknown.** The PHP adapter drops `args` entirely for a spread (`...$rest`, the count
  is unknowable) and for named arguments (PHP 8.0, a value's position is free). Neither can be honestly
  positional, and a half-truth here would be worse than silence.
- **`find_callers(arg_position, arg_is)`**, depth 1 only — an argument filter describes a direct call,
  so allowing it on a BFS frontier would answer a question nobody asked. `arg_is` takes a literal
  category, `absent` (fewer arguments than the position) or `dynamic` (present, not a literal). A bad
  selector, a 0 position, one half of the pair, or `depth > 1` all raise (R5.3) rather than returning an
  empty result that reads like an answer.
- **`args_unrecorded`** rides along with every filtered response: how many of the target's call sites
  the filter could not judge. Without it the feature would reproduce the defect it exists to fix — a
  confident-looking count whose denominator hides what it could not see.

**Every existing index must be rebuilt.** `schema_version` is enforced loud on open, so an index built
before this change raises rather than answering from a table without the column. `build_or_update_index`
recovers by rebuilding; on a repo the size of the anchor that is ~17 minutes.

Deliberately left out: matching a literal's *value*, filtering on more than one position at once, and
argument shapes on `find_references`. Each is a separate question, and none of them was asked.

## References
`code_atlas/tools/find_callers.py:39-60` (signature, `include_source`, and the `total_count` contract),
`code_atlas/tools/call_site.py:18-40` (`annotate` — per-file read with a staleness guard, the machinery
Option B would reuse), `code_atlas/contract.py:83-110` (`EDGE_FIELDS` / required fields — what Option A
must extend), `code_atlas/store.py` edge table (why per-edge payload is not free at 1.77M rows).
[037](037_compound-nav-responses.md) (call-site lines — display, already shipped),
[046](046_resolver-qname-candidate-dedupe.md) (the precedent that edge-table growth is the expensive axis).
Origin: field retro round 1 (`v0.1.0`, commit `e117b47`) §6a.2 and §7 — nominated there as the single
highest-value change, and the only genuine graph question the session had.
