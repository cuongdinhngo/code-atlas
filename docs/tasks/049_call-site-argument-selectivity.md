---
id: 049
slug: call-site-argument-selectivity
title: Select call sites by argument shape — "which of the 5,261 callers pass `null` here?"
phase: 1.5b
milestone: Agent-fit
status: todo
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

## References
`code_atlas/tools/find_callers.py:39-60` (signature, `include_source`, and the `total_count` contract),
`code_atlas/tools/call_site.py:18-40` (`annotate` — per-file read with a staleness guard, the machinery
Option B would reuse), `code_atlas/contract.py:83-110` (`EDGE_FIELDS` / required fields — what Option A
must extend), `code_atlas/store.py` edge table (why per-edge payload is not free at 1.77M rows).
[037](037_compound-nav-responses.md) (call-site lines — display, already shipped),
[046](046_resolver-qname-candidate-dedupe.md) (the precedent that edge-table growth is the expensive axis).
Origin: field retro round 1 (`v0.1.0`, commit `e117b47`) §6a.2 and §7 — nominated there as the single
highest-value change, and the only genuine graph question the session had.
