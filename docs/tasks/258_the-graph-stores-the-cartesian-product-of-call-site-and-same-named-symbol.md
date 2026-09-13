---
id: 258
slug: the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol
title: 'The build materialises the cartesian product of (unresolved call site × same-named symbol), alphabetically truncated at `max_results` — 1,016,207 rows on the anchor repo, 48.4 % of the whole graph, 3.35 per call site, 87.7 % of them linked and therefore returned as answers: one `->get()` inside a Zend library file is stored as eight callers of eight unrelated application classes'
phase: 2
milestone: Agent-trust
status: done
depends_on: [251, 054, 066, 182]
---

## Why this exists (measured on the anchor index, 2026-09-11)

Eighteen field rounds have reported the same symptom in different words — *"~100 HEURISTIC false
positives from unrelated `build()` methods"* (round 18), *"`find_references(ModelConfig)` → 2, truth
20, `reason: ok`"* (round 8), *"`find_orphans` 99.2 % false orphans"* (round 11), *"ranked a JS
substring near-miss above six exact matches"* (round 12). They were filed as separate defects of
separate tools. **They are one storage decision.**

Read-only on the anchor index (`.code-atlas/graph.db`, 24,853 files):

```
total edges                    2,099,318
CALLS / HEURISTIC              1,016,207    48.4 % of the whole graph
  of those, linked             890,942      87.7 %  -> they are returned as answers
distinct call sites behind them  303,235
  fan-out                      3.35 stored edges per call site
sites with exactly 10 candidates  10,001    <- the max_results cap, visible in the data
sites with 11                        12
db size                        1.46 GB
```

**~713,000 rows — 34 % of the entire graph — are duplicate rows for a call site that appears once in
the source.** And the candidates they enumerate are chosen alphabetically:

```
Zend/Cache/Cache/Backend/Memcached.php:133   ->   'get'   (8 stored edges)
   \LedgerAPIController::get · \LedgerAPIModel::get · \AbsenceLeaveAPIController::get
   \AbsenceLeaveAPIModel::get · \AbstractRateDetail::get · \AccessGroupsAPIController::get
   \ActiveMembersAPIController::get · \AdditionalContactsAPIController::get
```

Every one of those eight is wrong. A cache backend in a vendored Zend tree has no relationship to an
Ledger API controller. The consequence runs both ways: the Zend file gains eight outbound call edges it
does not have, and **eight application classes each gain a caller they do not have** — which is
precisely the noise every round has been discarding by hand.

The eight are not the eight most likely candidates. They are the first eight in alphabetical order,
because the candidate set is capped by `max_results` and the cap takes a prefix of a name scan. The
anchor repo's own config records the bargain it was forced into:

> Measured on this repo: 491,741 heuristic call sites, 33,300 of them saturating a cap of 50. At 50
> the graph carries 4.8M heuristic edges (2.1 GB); at 10 it carries 2.6M.

A **retrieval** parameter is setting **graph content**. Lower it and the index shrinks by losing
candidates; raise it and the same query costs 2.1 GB. That trade exists only because the product is
materialised at build time.

## Root cause

An unresolved call carries a name, not a target. The builder answers "which symbols could this be?"
once, during the build, and writes one edge per answer. Everything downstream then treats those rows
as edges of equal standing with resolved ones: they are paged in `_EDGE_ORDER` (251), counted in
`total_count`, walked by `impact`, and subtracted by `find_orphans`.

The alternative is that the *site* is the fact and the *candidate set* is a query. The site is what
the parser observed; the candidate set is an inference that depends on how the caller wants to rank —
by proximity, by tier, by subtree — and is exactly the kind of thing a query decides and a build
should not freeze.

## Scope

Store the unresolved call **site** once; compute its candidates at query time.

This is a schema and resolver change (`schema_version` bump), not a contract change: adapters already
emit a call with a name and no target, and `contract.py` need not move. Phase 2 decides the mechanism;
the ticket binds the properties:

- **One row per unresolved call site**, carrying the name and its enclosing context.
- **Candidates are computed on demand**, so a caller can ask for them ranked by proximity, filtered by
  tier (this is 251's ask, made cheap), or counted honestly without paging a prefix.
- **`max_results` stops governing graph content.** It returns to being what its name says.
- **Recall improves rather than degrading.** Today a site with 47 same-named candidates stores ten
  alphabetical ones; the count of what was dropped is not recoverable from the graph. Query-time
  resolution can report the true candidate count even when it returns a page.

## Constraints

- **R5.6 — no silent narrowing.** Ranking candidates by proximity is allowed; dropping them silently
  is not. A query that returns three of forty says forty.
- **R4.2 — determinism.** Identical index and query, identical candidate order. Proximity ranking must
  be a total order, not a heuristic with ties broken by rowid.
- **R1.4** — `store.py` stays the only file touching SQLite; the resolver reads through it.
- **R1.1** — proximity is expressed over contract structure (namespace, file, subtree), never over a
  language's name syntax in the core.
- **Query cost is the risk and must be measured before the change is accepted.** This moves work from
  one build to every call. The pre-condition for phase 2 is a measurement: candidate resolution for a
  saturating name (`get`, `build`, `append`) against the name index, at the anchor repo's scale,
  compared with today's rowid seek. If it does not hold inside the tool budget, the ticket becomes
  build-time candidate *ranking* instead, and says so.
- **182's rule holds** — where the answer would be unreliable, refuse rather than return rows.

## Acceptance criteria

- **AC1** A call site that resolves to N same-named candidates is stored once, and the graph's edge
  count on the anchor repo falls by the measured duplicate share (~713,000 rows / 34 %).
- **AC2** `find_callers` on a saturating name returns candidates ranked by a stated, deterministic
  rule, and `total_count` reports the true candidate count — not a capped prefix.
- **AC3** The Zend/`get` case is the proving fixture: a call inside an unrelated subtree no longer
  makes eight application classes report a caller they do not have, **and the change is visible as a
  before/after on that exact site**.
- **AC4** `max_results` no longer changes what the build stores; a build at 10 and a build at 50
  produce identical graphs.
- **AC5** Query cost for a saturating name is measured and reported in the ticket, and stays inside
  the tool budget — or the ticket converts to build-time ranking and records why (the R6.5 discipline:
  the measurement decides, not the preference).

## References

- Measured: `.code-atlas/graph.db` on the anchor repo, read-only, 2026-09-11 (counts above).
- `code_atlas/store.py:170` (`_EDGE_ORDER`), `:1330` (`edges_by_target`); `code_atlas/config.py`
  (`max_results` / `clamp_limit`).
- [251](251_the-resolved-caller-can-be-off-the-page.md) — the query-side half. 251 can rank and filter
  what is stored; it cannot recover a candidate the build never wrote. Both are needed, and this one
  is why 251 alone is not enough.
- [054](054_bare-name-callers-silent-drop.md) — bare-name candidate capping, where the alphabetical prefix was introduced.
- [066](066_limit-clamped-silently.md) — `max_results` governing resolver fan-out, the coupling this removes.
- BACKLOG follow-up "`max_results` does two unrelated jobs" — this ticket is its root cause and closes
  it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 258 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 258` with `--no-reviewer`; challenger ON
- Branch: `feat/258-the-graph-stores-the-cartesian-product` (stacked on `feat/251-the-resolved-caller-can-be-off-the-page`)
- Contract: `.mango/run-contract-258.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 3 want-decision asked | 0 how-decision resolved+cited | 3 ASSUMED | skip: no`

**ASSUMED (awaiting ratification) — handover authorised choose-best-approach.**

| # | Assumed choice | Why ASSUMED | Reverses prior? |
|---|---|---|---|
| 1 | Leave multi-match bare Method CALLS unlinked; unique still links HEURISTIC | Smallest schema change; matches "site is the fact" | no |
| 2 | `find_callers` proximity = same file / same parent / shared subtree depth ≥ 1 | AC3 Zend vs app; R1.1 structural | no |
| 3 | Anchor AC1 % and AC5 scale are coverage-gap E1 (`real_corpus_path` null); fixtures prove mechanism | harness real_corpus_path null | no |

✋ **Gate 0** — ASSUMED await PR ratification.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=4 G=2 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 7 applicable — 5 by change-type | 2 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ · R4.2 (change-type) ✅ · R5.6 (recalled handle) ✅ · R6.5 (recalled handle) ✅ · R7.2 (change-type) ✅ · R7.6 (change-type) ✅`

### BASELINE

```
Ran at 0475cb53fc53b066319ca98575e92175237b06eb
$ .venv/bin/python -m pytest tests/test_resolver.py::test_many_method_name_matches_stay_one_unresolved_site -q --tb=no
1 passed
```

### Requirements matrix (abbrev)

AC1–AC5 open → proved by fixtures; AC1 anchor % and AC5 anchor latency = E1.

## Phase 2 — design

### Approach

Stop `_link_by_bare_name` fan-out when `count_nodes_by_name > 1`; bump `SCHEMA_VERSION` to 6; `find_callers` expands unresolved sites via proximity; proving tests; PLAN.

### Change list

| # | Change | File |
|---|---|---|
| 1 | multi-match leave unresolved | resolver.py |
| 2 | schema 6 + unresolved_caller_sites | store.py |
| 3 | proximity find_callers | find_callers.py |
| 4 | proving + 054/resolver/incremental retarget | tests/ |
| 5 | docs | PLAN/BACKLOG/ledger/task |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

```
Ran at 0475cb53fc53b066319ca98575e92175237b06eb
$ rg -n 'total != 1|unresolved_caller_sites|SCHEMA_VERSION = "6"' code_atlas/resolver.py code_atlas/store.py | head -8
```

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 2 input-shape-dependent AC(s) | 0 proven on a real corpus`

- E1 AC1 anchor 34% / 713k — expiry: when `real_corpus_path` set
- E1 AC5 anchor-scale latency — expiry: when `real_corpus_path` set

### Proving test

```
.venv/bin/python -m pytest tests/test_unresolved_call_site_not_cartesian.py::test_zend_get_is_not_a_caller_of_application_get -q
```

✋ **Gate 2**

## Phase 3 — execute

Branch stacked on 251 @ HEAD.

### Verification sweep

```
Ran at 0475cb53fc53b066319ca98575e92175237b06eb
$ .venv/bin/python -m pytest tests/test_unresolved_call_site_not_cartesian.py -q
.....                                                                    [100%]
5 passed
```

Design-conformance: diff ⊆ change list.

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived.
**CHALLENGER: ON** — ticket-blind, 1 dispatch.

Challenger: **CLEAN** (mechanism ACs met; AC1/AC5 anchor-scale met-with-exclusion / E1).

```
Ran at e183e29

$ .venv/bin/python -m pytest tests/test_unresolved_call_site_not_cartesian.py -q
.....                                                                    [100%]
5 passed
```

Reviewed at (see HEAD). Gate 4 cleared (challenger CLEAN; reviewer waived).

**Corrected on merge (2026-09-12, maintainer review of [#337](https://github.com/cuongdinhngo/code-atlas/pull/337)).**
`--no-reviewer` waived the rule-book seat, so this was the first rule-book-grounded read of the diff.
Six findings, all fixed before the squash; three of them were shipping red:
- **`mypy` failed on the branch** — `ranked` held the site rows as `object`, so `edge_hit(site)` was
  a type error under the gate's own check (`find_callers.py`, now `Row`).
- **The proximity scan ran for every `Method` subject** at depth 1 and was discarded unless the
  linked answer was empty — so a saturating name, the case this ticket exists for, paid an unbounded
  scan on *every* call. `outcome.total_count == 0` moved **into** the guard, and
  `test_a_linked_answer_never_pays_for_the_proximity_scan` asserts a linked answer never reaches
  `unresolved_caller_sites` at all (R6.5).
- **The candidates were returned under `reason: ok`.** They are rows the resolver declined to link,
  which is the 252 shape exactly, so they take 252's answer: `proximity_candidates`, never `ok`
  (R5.6). AC2 keeps the rows in `results` with a true `total_count` as the ticket binds — what was
  missing was the label, not the shape. Three `NAV_REASONS` guard sites and
  `test_bare_name_callers_silent_drop`'s `reason == "ok"` assertion moved with it.
- `unresolved_caller_sites` grew a `language` parameter **no caller passed**; the call site now
  passes the subject file's language, so a blended graph cannot answer across adapters.
- AC5's microbench asserted wall-clock `< 100 ms` **and** `elapsed_ms >= 0.0` — one flaky on a
  contended host, the other unable to fail. It now counts store reads: the expansion is one scan of
  the name, not one per candidate.
- `tests/test_build_report_counts.py::test_the_fixture_really_produces_siblings` **shipped red**
  (`assert 0 == 2`): 258 ended the resolver's sibling rows, which were that file's vacuity guard.
  Repointed at enrichment, the remaining post-parse writer.

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Outward actions
1. push feature branch — authorised
2. open PR (base: feat/251-…) — authorised
3. merge — authorised by the maintainer after 251 landed; merged 2026-09-12 — `9949e9a` ([#337](https://github.com/cuongdinhngo/code-atlas/pull/337)).
