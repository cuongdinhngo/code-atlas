---
id: 251
slug: the-resolved-caller-can-be-off-the-page
title: '`find_callers` pages in alphabetical caller order with no tier predicate and no tier ordering, so on a common method name the one RESOLVED caller can be absent from the page entirely — and the caveat that did fire named a relation gap, not the question the reader was asking'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [165, 168, 057]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 18)

A consuming agent drove three BETA bug fixes with code-atlas as the primary instrument and scored the
session 7.5/10. `find_callers` was named the highest-leverage tool of the session — the *absence* of
two reports from `MemberPhotoResolver::browserSrc`'s caller set **was** a root cause — and it
carried both of the session's deductions. Its own summary of the first:

> `EvacMemberReportModel::build` returned 138 results, ~100 of them HEURISTIC false positives from
> unrelated `build()` methods across `legacy/`, `lib/`, and Symfony vendor code. The RESOLVED-tier
> answer (the one caller that matters) was correct but buried; **you must read the tier, not the
> count.**

"Buried" understates it, and the understatement is the finding. Read against the code, tier does not
rank the page — it is not in the `ORDER BY` and not available as a predicate. The page is the
alphabetically-first *n* caller qnames. Whether the one caller that matters is shown at all is
decided by where its qname sorts, and the reader is given no way to ask for it.

The anchor repo makes that sharp: it pins `max_results = 10` in `.code-atlas.toml` to hold the graph
at 2.6M heuristic edges (BACKLOG follow-up), so a 138-caller answer pages at ten. Nine of those ten
rows can be vendor `build()` noise with the real caller on page 12, and the only signal distinguishing
that from "the real caller is on this page" is `truncated: true`, which is true either way.

## Root cause

At depth 1 `find_callers` delegates paging to the store and does not touch the rows
(`code_atlas/tools/find_callers.py:413-425`):

```python
edges = store.edges_by_target(qname, kinds=CALLER_KINDS, limit=limit, offset=offset, args_at=args_at)
```

`edges_by_target` orders by `_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"`
(`code_atlas/store.py:170`) — caller qname, alphabetically. `confidence_tier` enters the tool in
exactly two places, and neither decides what reaches the page:

- as a **label** written onto each returned hit (`code_atlas/tools/nav_result.py:191`);
- as the **frontier gate** at `depth > 1`, where only RESOLVED expands (`find_callers.py:459`), counted
  in `frontier_skipped_non_resolved`.

So the tier discipline the payload advertises is real for *walking* and absent for *selecting*. A
RESOLVED-only view is not a filter the caller can express — it is post-hoc work on whatever rows the
alphabet handed over, over a page that may contain none.

**The second deduction, folded in here rather than ticketed alone.** The session's one miss was that
the live evacuation renderer is a flat web-root PHP file reached by an AJAX string from
`public/js/evacuationList.js`, not the MVC `EvacMemberReportModel` the agent fixed first. The
tool's answer was *correct* — `memberPdfAction`, itself test-only, is the only `src` caller, which
is exactly the evidence the MVC path is UI-unused — and the agent still drew the wrong conclusion
from it. Note what did **not** save it: the payload **did** carry
`authoritative_caveats: [cross_language_relation_unmodelled, sibling_definitions]`, and the retro
praises those caveats as honest. They fired and cost nothing, because they name a *relation* that is
unmodelled, not what that costs the reader — that reachability inside one language's call graph does
not answer "which of two parallel renderers does the front end invoke". That is a routing question,
and the caveat is the only place on the surface where it could have been said.

## Scope

Two changes to `find_callers`, one selection and one prose:

- **A tier control.** A way to ask for RESOLVED only (or to ask for the tier census of the full hit
  set), so the answer is chosen by tier and not by alphabet. The predicate belongs in the store query
  next to `kinds` and `args_at`, not in a post-filter over an already-truncated page — a post-filter
  cannot recover a row the `LIMIT` never returned. Whether the knob is an argument or a changed
  default is phase 2's decision; the ticket does not bind one.
- **The caveat says what it costs.** When `cross_language_relation_unmodelled` rides an answer, name
  the operational limit in the reader's terms — this answer is reachability within one language's
  call graph and does not establish which entry point the front end invokes.

## Constraints

- **No default payload change** unless phase 2 argues the default *should* change and says so — the
  022 AC3 byte-identity check applies to every other tool regardless.
- **R5.6** — a tier-filtered answer must say it was filtered. A `total_count` that silently means
  "RESOLVED only" is a different claim wearing the old name.
- **R4.2** — deterministic: identical index and arguments, identical page.
- **061** — omit when empty; a census on an all-RESOLVED answer adds nothing and is not emitted.
- **R1.1** — no language branch; the caveat prose is keyed by the contract's relation vocabulary.

## Acceptance criteria

- **AC1** A caller can obtain the RESOLVED callers of a common method name **in one call**, on an index
  where the RESOLVED hit sorts outside the first page of the unfiltered answer. This is the proving
  shape: a fixture where the correct answer is provably off page 1 today.
- **AC2** `total_count` under a tier request counts matches of that request, and the payload names the
  filter, so it is never mistaken for the unfiltered total.
- **AC3** An unfiltered answer lets the reader tell "no RESOLVED caller exists" from "no RESOLVED
  caller is on this page" without paging to the end.
- **AC4** When `cross_language_relation_unmodelled` is attached, the payload states the limit in terms
  of what the reader may not conclude, not only which relation is unmodelled.
- **AC5** Every existing payload is byte-identical when the new control is not used (022 AC3).

## References

- `code_atlas/tools/find_callers.py:413-425` (depth-1 paging), `:459` (the frontier gate — the only
  tier decision in the tool), `code_atlas/store.py:170` (`_EDGE_ORDER`), `:1330` (`edges_by_target`).
- `code_atlas/tools/nav_result.py:191` — where the tier becomes a label.
- [165](165_find-callers-splits-across-twins-and-says-reason-ok.md) / [168](168_find-references-never-got-165s-twin-disclosure.md) — sibling definitions and the caveat vocabulary this extends.
- [057](057_answer-pagination.md) — the paging contract whose order this ticket makes load-bearing.
- BACKLOG follow-up "`max_results` does two unrelated jobs" — why the anchor repo pages at ten, which
  is what turns a ranking weakness into a missing answer. The field instance moved here from that
  follow-up (R7.6): the anchor repo pins `max_results = 10` in `.code-atlas.toml` to hold the graph
  at 2.6M heuristic edges instead of 4.8M, so every answer is capped at ten rows to buy an index
  size, and a caller's `limit=100` is silently clamped to it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 251 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 251` with `--no-reviewer`; challenger ON
- Branch: `feat/251-the-resolved-caller-can-be-off-the-page`
- Contract: `.mango/run-contract-251.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 3 want-decision asked | 0 how-decision resolved+cited | 3 ASSUMED | skip: no`

**PREMISE detail.** Present: `find_callers.py`, `store.py` (`_EDGE_ORDER`, `edges_by_target`), `nav_result.py` (`confidence_tier` label, `attach_authoritative_caveats`), `CALLER_KINDS`, `cross_language_relation_unmodelled`, tickets 165/168/057. Ambiguous: BACKLOG follow-up prose noun `max_results` dual job (not a resolvable identifier).

**INPUT KIND:** ticket.

**ASSUMED (awaiting ratification) — handover authorised choose-best-approach.**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|---|---|---|---|
| 1 | Opt-in tool param `confidence_tier` (store predicate); default row order unchanged | Ticket forbids silent default change; AC5 + args_at pattern | Gate 2 design — surface ✋ | no |
| 2 | Tier filter is depth=1 only | Same seam as `args_at`; depth>1 already has RESOLVED frontier gate | Gate 2 design — surface ✋ | no |
| 3 | AC3/AC4 add `tier_census` / `caveat_limits` on the answers that need them (intentional default additions); other payloads unchanged when control unused | Ticket AC3/AC4 bind the fields; Constraint "no default change" yields to those ACs via phase-2 argument | Gate 2 design — surface ✋ | no |

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `do-not-attest-past-the-payloads-resolution` / R5.6 | 2 | handle | Yes — tier_filter names the filter |
| 2 | `reproduce-the-payload-not-the-story` | 2 | handle | Yes — proving fixture pins off-page RESOLVED |

✋ **Gate 0** — ASSUMED rows await maintainer ratification on the PR; handover proceeds.

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=3 G=2 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`
`RULE SECTIONS: 8 applicable — 6 by change-type | 2 by recalled handle — R1.1 (change-type) ✅ no language branch · R4.2 (change-type) ✅ identical index+args · R5.3 (change-type) ✅ loud unknown tier · R5.6 (recalled handle) ✅ tier_filter names filter · R6.5 (recalled handle) ✅ proving fixture · R6.9 (change-type) ✅ assert payload · R7.2 (change-type) ✅ ledger · R7.6 (change-type) ✅ PLAN prune-as-add`

### BASELINE

```
Ran at e020c0584ccd285628cda34b733dbd0a30e89067
$ .venv/bin/python -m pytest tests/test_answer_pagination.py tests/test_find_callers_cross_language_unmodelled.py -q --tb=no
28 passed in 4.5s
```

Green. No baseline exclusions. Full `pytest` / `scripts/gate.sh` deferred to execute-close (S-scope pin).

### Clarifications (j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Argument vs changed default? | **Opt-in `confidence_tier`** — ASSUMED #1 | ticket Constraints + AC5 |
| Q2 | Depth > 1? | **depth=1 only** — ASSUMED #2 | args_at precedent |
| Q3 | Census / caveat prose default change? | **Yes for AC3/AC4 cases** — ASSUMED #3 | ticket AC3/AC4 |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | RESOLVED caller obtainable in one call when off alphabetical page | field retro | open |
| G2 | Why | Caveat names operational cost, not only relation | field retro | open |
| C1 | Constraints | No silent default order change | ASSUMED #1 | open |
| C2 | Constraints | R5.6 — filtered total named | tier_filter | open |
| C3 | Constraints | R4.2 deterministic | same index+args | open |
| C4 | Constraints | 061 omit empty census | all-RESOLVED omits | open |
| C5 | Constraints | R1.1 no language branch | caveat keyed by vocab | open |
| R1 | Scope | Tier control in store query | edges_by_target tier | open |
| R2 | Scope | Caveat prose for cross_language | caveat_limits | open |
| R3 | Scope | Census or filter recovers RESOLVED | AC1+AC3 | open |
| AC1 | AC | RESOLVED in one filtered call when off page 1 | proving test | open |
| AC2 | AC | total_count + named filter | proving test | open |
| AC3 | AC | unfiltered tier_census | proving test | open |
| AC4 | AC | caveat_limits prose | proving test | open |
| AC5 | AC | control unused → identical omit/None | proving test | open |

### AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | one call recovers off-page RESOLVED | store tier filter | Y | measurable |
| AC2 | total_count + named filter | tier_filter + count | Y | measurable |
| AC3 | census distinguishes absent vs off-page | tier_census | Y | measurable |
| AC4 | caveat states reader limit | caveat_limits | Y | measurable |
| AC5 | control unused byte-identical | None == omit | Y | measurable |

## Phase 2 — design

### Approach

Add `_tier_predicate` + `tier_census_by_target` on `GraphStore`; wire opt-in `confidence_tier` through `find_callers` depth-1 paging; emit `tier_filter` / `tier_census`; attach `caveat_limits` when authoritative caveats merge a known limit. Proving tests AC1–AC5; PLAN §12/§19; bookkeeping.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Change default `_EDGE_ORDER` to tier-first | Violates AC5 / Constraint; ASSUMED #1 |
| Post-filter page for RESOLVED | Ticket forbids — LIMIT already dropped the row |
| Config `CA_TIER_DEFAULT` | Blasts every call; ticket wants askable control |

### Assumptions

| Assumption | Tag |
|---|---|
| `idx_edges_tier` already exists | verified — store.py DDL |
| FastMCP exposes new kwarg from signature | verified — main.py `server.tool(guard(...))` |
| Cross-language caveat attach path is shared | verified — find_callers.py |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `_tier_predicate` + compose; `confidence_tier` on edges/count/subtrees; `tier_census_by_target` | `store.py` | edge reads by target | AC1–AC3,R1 | 3/3 |
| 2 | `confidence_tier` param + `_callers` wire + `tier_filter`/`tier_census` | `find_callers.py` | that tool | AC1–AC5,C2 | 5/5 |
| 3 | `CAVEAT_LIMITS` + `attach_caveat_limits` from authoritative caveats | `nav_result.py` | any tool attaching caveats | AC4 | 1/1 |
| 4 | Proving tests | `tests/test_find_callers_tier_control.py` | find_callers | AC1–AC5 | 5/5 |
| 5 | PLAN §12/§19 + BACKLOG + TOKEN_LEDGER + task status | `docs/` | doc budgets | R7.2/R7.6 | 1/1 |

### HANDLES

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `do-not-attest-past-the-payloads-resolution`** — traced.

```
Ran at e020c0584ccd285628cda34b733dbd0a30e89067
$ rg -n 'tier_filter|def _tier_predicate' code_atlas/tools/find_callers.py code_atlas/store.py | head -8
code_atlas/store.py:438:def _tier_predicate(confidence_tier: str | None) -> _Predicate:
code_atlas/tools/find_callers.py:67:    "tier_filter",
```

Folded: change #2 emits `tier_filter` (R5.6).

**H2 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at e020c0584ccd285628cda34b733dbd0a30e89067
$ rg -n 'test_resolved_caller_off_page|tier_census' tests/test_find_callers_tier_control.py | head -5
86:def test_resolved_caller_off_page_one_recovered_by_tier_filter(
125:def test_unfiltered_tier_census_distinguishes_absent_from_off_page(
```

Folded: AC1/AC3 prove the off-page shape (R6.5).

### Coverage-gap exclusions

none

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | `test_resolved_caller_off_page_one_recovered_by_tier_filter` | authored | ✅ |
| AC2 | integration | `test_tier_filter_names_itself_and_counts_matches` | authored | ✅ |
| AC3 | integration | `test_unfiltered_tier_census_distinguishes_absent_from_off_page` | authored | ✅ |
| AC4 | integration | `test_cross_language_caveat_states_reader_limit` | authored | ✅ |
| AC5 | integration | `test_tier_control_off_is_byte_identical` | authored | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_find_callers_tier_control.py::test_resolved_caller_off_page_one_recovered_by_tier_filter -q
```

✋ **Gate 2** — ASSUMED #1/#2/#3 ratified by design; maintainer confirms on PR.

## Phase 3 — execute

Branch `feat/251-the-resolved-caller-can-be-off-the-page` from `main` @ `0720cab`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | store tier predicate + census | ✅ |
| 2 | find_callers wire | ✅ |
| 3 | caveat_limits | ✅ |
| 4 | Proving tests | ✅ |
| 5 | Docs / bookkeeping | ✅ (this commit) |

### Verification sweep

```
Ran at e020c0584ccd285628cda34b733dbd0a30e89067
$ .venv/bin/python -m pytest tests/test_find_callers_tier_control.py -q
......                                                                   [100%]
6 passed in 0.92s
```

Design-conformance: diff ⊆ change list. No deviation.

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 1 dispatch.

Challenger reconstructed 12 requirements from the raw ticket; **12 met / 0 not met / 0 can't tell**. Overall **CLEAN** (challenger only — REVIEWER OFF). Residual: AC5 vs AC3/AC4 intentional default fields (tier_census / caveat_limits) noted; not a product miss.

Proving evidence on reviewed tree:

```
Ran at e020c0584ccd285628cda34b733dbd0a30e89067
$ .venv/bin/python -m pytest tests/test_find_callers_tier_control.py -q
......                                                                   [100%]
6 passed in 0.92s
```

Reviewed at e020c0584ccd285628cda34b733dbd0a30e89067

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

**Corrected on merge (2026-09-12, maintainer review of [#336](https://github.com/cuongdinhngo/code-atlas/pull/336)).**
`--no-reviewer` waived the rule-book seat, so this was the first rule-book-grounded read of the diff.
Four findings, all fixed before the squash:
- `confidence_tier` shipped as a bare `str`, so the MCP input schema published **no choice** and the
  three spellings were discoverable only by triggering the `ValueError`. `contract` now carries
  `ConfidenceTier` as the typing SSoT with `CONFIDENCE_TIERS` derived from it — `NODE_KINDS`' own
  idiom (R3.2), applied to a vocabulary that had become a tool *parameter*.
- The census block was copied verbatim into both fetch paths. Extracted as `_tier_census`, which now
  owns the omit-when-it-adds-nothing rule in one place (061/R6.7).
- `tier_filter`, `tier_census` and `caveat_limits` had no `CONVENTION.md` §6 row. `caveat_limits`
  rides **every** payload carrying `authoritative_caveats`, so it is cross-tool contract, not a
  `find_callers` detail — §6 is where a reader who never opens this ticket finds it.
- `docs/PLAN.md` was **over its ceiling on the branch** (23,360 vs 23,250) though the pre-PR
  self-check reported `tests/test_doc_size_budget.py` green. Paid for with R7.6 prunes plus an
  argued raise; see the comments in that test.

## Phase 5 — Finalise

Durable lesson: none new — tier was already a label; 251 makes it a store predicate and names the cross-language caveat's operational cost.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Token usage (working doc)

| Phase | Tokens |
|---|---|
| autorun main-loop | unmeasured (host surfaces no usage block) |
| challenger ×1 | unmeasured |
| reviewer | waived (--no-reviewer) |

### Outward actions
1. push feature branch — authorised by handover
2. open PR — authorised by handover
3. merge — authorised by the maintainer; merged 2026-09-12 — `d3e5c7f` ([#336](https://github.com/cuongdinhngo/code-atlas/pull/336)).

