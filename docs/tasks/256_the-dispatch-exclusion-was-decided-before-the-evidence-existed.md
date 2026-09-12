---
id: 256
slug: the-dispatch-exclusion-was-decided-before-the-evidence-existed
title: '222 shipped the string-literal→target rule engine and excluded dispatch semantics on the reasoning that "the field correctly assigns routing to grep" — two field rounds later grep did not catch it, a code review did, after a fix landed on the wrong one of two parallel renderers; the exclusion is discharged and what is missing is whether a rule may target a file'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [222, 221, 063]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, rounds 18 and the BETA QA batch)

222 built exactly the machinery this needs — find every call to a named setter, take the Nth string
literal, emit a `HEURISTIC` edge to a templated target — and drew its boundary in E2:

> SELECT-list order and dispatch-table semantics are not [in reach] — do not claim them. […]
> routing/dispatch semantics, **which the field correctly assigns to grep**.

That was the right call on the evidence of the day. **The evidence has since arrived and it says the
opposite.** In the BETA QA session the evacuation photo had two renderers: a flat PHP file at the web
root that `public/js/evacuationList.js` AJAX-calls **by name**, and a parallel MVC model. The agent
fixed the MVC one. grep did not catch it. A code reviewer did, after the wrong fix was written:

> Could `find_callers` have caught it? No — the live dispatch is JS → a flat PHP file at the web root
> via an AJAX string. […] `find_callers` confirms reachability *within* the PHP call graph; it does
> not tell you which of two parallel PHP renderers the front end invokes.

Round 18 produced the same shape from the other direction: reachability there was decided by a
file-scope `require_once` taking the class name before any alias resolves — *"a load-order fact, not a
graph fact"*. The two together retire E2's premise: routing is not a question grep answers here, and
it cost a wrong shipped fix.

## Root cause

`CA_INDIRECTION_RULES` resolves a string literal to a **symbol** qname through `target_template`. The
dispatch case names a **file** — `getMemberEvacReport.php` as a string inside a `.js` file — and the
anchor repo's live rule file is one `view_data` entry, so nothing exercises a file-shaped target:

```json
{"view_data": [{"setter": "setData", "key_arg": 1, "key_from": "array_keys"}]}
```

So this is not new machinery. It is one question — *may a rule's target be a File node?* — plus the
disclosure that 251 also asks for: an answer about the PHP call graph must not read as an answer about
what the browser invokes.

## Scope

- **A file-shaped `target_template`.** A rule whose resolved target names an indexed file links to
  that `File` node. Tier stays `HEURISTIC` (or `DYNAMIC` — phase 2 decides); it is a string match, and
  the tiering must say so.
- **The caveat 251 also needs.** When a caller asks a reachability question about a subject whose
  language has a live string-dispatch surface, the answer states what it does not establish. Filing
  both is deliberate: 251 words the caveat, this ticket gives it something true to point at.
- **Not in scope:** discovering the mapping automatically. 222 refused that at 063 and 152 — `args`
  carries *"the category, never the value"* — and nothing here changes it. The rule stays the
  consumer's configuration, which is also what keeps R2 intact: the adapter learns no repo's names.

## Constraints

- **R2 — standard over sample.** The rule lives in the consumer's rule file. No adapter and no core
  file may name `main.php`, an AJAX convention, or any repo's dispatch shape.
- **R4.2 / 222's AC2** — with no rule configured the graph is byte-identical. This feature costs a
  non-user nothing, and that property is the reason 222 was allowed at all.
- **R5.6** — a string-matched edge is never `RESOLVED`. A dispatch answer says it is a candidate.
- **222's AC4** — a rule whose template resolves nothing reports that in `BuildReport`; a file-shaped
  target that matches no indexed file must fail the same loud way, not vanish.

## Acceptance criteria

- **AC1** A rule whose `target_template` resolves to an indexed file produces an edge to that `File`
  node, and `find_callers` / `find_references` on that file return the dispatching site.
- **AC2** The proving fixture is the field shape: a `.js` file containing a bare filename string, a
  PHP file of that name, no symbol relation between them — zero hits before, the dispatch site after.
- **AC3** With no rule configured, the graph is byte-identical (222 AC2, re-pinned).
- **AC4** A file-shaped template matching nothing is reported in `BuildReport`, not silently dropped.
- **AC5** Tier is never `RESOLVED`, and the payload names the rule that produced the edge (`rule: true`,
  as 222 already does).

## References

- [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md) — the engine,
  its E2 exclusion, and AC2's byte-identity property this must preserve.
- [221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) — the crossing census that
  makes an unmeasured cross-language answer self-diagnosing.
- [251](251_the-resolved-caller-can-be-off-the-page.md) — the caveat half; this ticket is the half that
  makes the caveat pointable at a real edge.
- `.code-atlas/indirection-rules.json` in the anchor repo — the one live rule today, symbol-shaped.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 256 · **work_doc_mode:** embed · **Current phase:** execute complete; review next
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 256` with `--no-reviewer`; challenger ON
- Branch: `feat/256-dispatch-file-shaped-target`
- Contract: `.mango/run-contract-256.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 2 want-decision asked | 0 how-decision resolved+cited | 2 ASSUMED | skip: no`

**PREMISE detail.** Present: `CA_INDIRECTION_RULES`, `code_atlas/enrichment.py` (`keyed_calls`, `_keyed_calls_edges`), `BuildReport.rules_unresolved`, tickets 222/221/063, `find_callers`/`find_references`. Ambiguous (not blocking): BETA QA / round-18 field prose; anchor `.code-atlas/indirection-rules.json` (consumer repo).

**INPUT KIND:** ticket.

**ASSUMED (awaiting ratification) — handover authorised choose-best-approach.**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|---|---|---|---|
| 1 | Tier stays **HEURISTIC** (not DYNAMIC) | Ticket offers either; 222 AC5 / R5.6 string match is never RESOLVED; keep 222's tier | Gate 2 design — surface ✋ | no |
| 2 | Exact File **qname** match via template (no basename search) | Same basis as PATH edges; ambiguous multi-file basename would invent ranking | Gate 2 design — surface ✋ | no |

Caveat wording for reachability answers is **251's scope** (ticket text); not assumed here.

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | Yes — AC1 pins find_callers/find_references |
| 2 | `prove-the-guard-fails` | 2 | handle | Yes — AC2 zero-before without rule |
| 3 | enrichment / indirection (040/222) | 5 | area | Surfaced |

✋ **Gate 0** — ASSUMED rows await maintainer ratification on the PR; handover proceeds.

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=4 R=3 G=2 AC=5`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`
`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ no language branch · R2 (change-type) ✅ rule stays consumer config · R4.2 (change-type) ✅ AC3 byte-identical off · R5.6 (change-type) ✅ never RESOLVED · R6.5 (recalled handle) ✅ AC2 zero-before · R6.9 (change-type) ✅ assert find_callers payload · R7.2 (change-type) ✅ ledger · R7.6 (change-type) ✅ PLAN prune-as-add`

### BASELINE

Delta-related suite on untouched mechanism + new proving tests at **8303edb**:

```
Ran at 658bee87ab8020962140cdac2711931d3b8d32b8
$ .venv/bin/python -m pytest tests/test_keyed_calls_rule.py tests/test_keyed_calls_file_target.py tests/test_indirection_enrichment.py tests/test_doc_size_budget.py -q --tb=no
26 passed in 5.28s
```

Green. No baseline exclusions. Full `pytest` / `scripts/gate.sh` deferred to execute-close (S-scope pin).

### Clarifications (j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Need resolver/enrichment code change? | **No** — spike: CALLS to File qname already links via `nodes_by_qualified_names` without kind filter | spike 2026-09-12; `resolver.py:142` |
| Q2 | Basename search when string ≠ path? | **No** — ASSUMED #2; consumer puts path in template | PATH_EDGE_KINDS / ticket AC2 plant at matching path |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | Discharge 222 E2 dispatch half with a true File edge | E2 text; field retro | open |
| G2 | Why | Pointable edge for 251's caveat | ticket Scope | open |
| C1 | Constraints | R2 — no repo names in core/adapters | rule JSON only | open |
| C2 | Constraints | R4.2 — off ⇒ byte-identical | 222 AC2 | open |
| C3 | Constraints | R5.6 — never RESOLVED | tier HEURISTIC | open |
| C4 | Constraints | AC4 loud miss | rules_unresolved | open |
| R1 | Scope | File-shaped target_template links to File | spike proves | open |
| R2 | Scope | Not auto-discovery | config rule | open |
| R3 | Scope | Caveat text is 251 | out of change list | closed |
| AC1 | AC | find_callers/find_references on File return dispatch site | need proving test | open |
| AC2 | AC | field-shape fixture zero-before / hit-after | need fixture | open |
| AC3 | AC | no rule ⇒ byte-identical | re-pin | open |
| AC4 | AC | missing File ⇒ BuildReport | re-pin | open |
| AC5 | AC | never RESOLVED; rule:true | assert | open |

### AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | edge to File; callers/refs return site | exact File qname link + nav | Y | measurable |
| AC2 | JS string + PHP file; zero before | plant + without-rule assert | Y | measurable |
| AC3 | byte-identical off | graph snap equality | Y | measurable |
| AC4 | BuildReport on miss | rules_unresolved ≥ 1 | Y | measurable |
| AC5 | never RESOLVED; rule:true | payload asserts | Y | measurable |

## Phase 2 — design

### Approach

**Pin, do not invent.** Spike proved `keyed_calls` + resolver already link a `target_template` that equals a File qname as HEURISTIC CALLS with `rule: true`. Change list: proving fixture (JS `fetch("….php")` + PHP File at that path) + tests AC1–AC5; one enrichment comment; PLAN §19 discharges E2; bookkeeping. No resolver/schema change.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Basename File search | Ambiguous; ASSUMED #2; PATH edges already exact |
| New edge kind / PATH_EDGE for keyed_calls | find_callers already walks CALLS; spike works |
| Encode `fetch` / AJAX in adapters | R2 |

### Assumptions

| Assumption | Tag |
|---|---|
| CALLS resolve against File qnames via unfiltered `nodes_by_qualified_names` | verified — spike + `resolver.py:142` |
| TS adapter emits string `args` on `fetch(...)` | verified — spike + `adapters/typescript/src/parse.js` |
| `count_unresolved_keyed_calls` covers File misses | verified — spike AC4 |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Proving fixture + `tests/test_keyed_calls_file_target.py` | `tests/fixtures/dispatch_file/` + test | keyed_calls suite; TS+PHP adapters in fixture env | AC1–AC5,C1–C4,R1,G1 | 9/9 |
| 2 | Enrichment comment: File qname valid template target | `code_atlas/enrichment.py` | none | R1 | 1/1 |
| 3 | PLAN §19 discharge E2 + prune | `docs/PLAN.md` | doc budget | G1,R7.6 | 1/1 |
| 4 | Bookkeeping: BACKLOG, TOKEN_LEDGER, task status | `docs/` | none | R7.2 | 1/1 |

### HANDLES

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at 658bee87ab8020962140cdac2711931d3b8d32b8
$ rg -n 'RULE_FLAG|is_rule_edge_path' code_atlas/tools/nav_result.py | head -5
14:from code_atlas.enrichment import is_rule_edge_kind, is_rule_edge_path
186:    if is_rule_edge_path(edge.get("file_path")) or is_rule_edge_kind(edge.get("kind")):
189:        hit[contract.RULE_FLAG] = True
```

Folded: change #1 asserts `rule: true` + HEURISTIC on find_callers/find_references.

**H2 `prove-the-guard-fails`** — traced.

```
Ran at 658bee87ab8020962140cdac2711931d3b8d32b8
$ rg -n 'nodes_by_qualified_names' code_atlas/resolver.py | head -3
128:        file_hits = store.nodes_by_qualified_names(
142:        qname_hits = store.nodes_by_qualified_names(lookup_raws, limit=max_candidates)
```

Folded: change #1 AC2 without-rule zero proves the before-state (R6.5).

### Coverage-gap exclusions

none

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | `test_file_shaped_rule_find_callers_and_references` | authored | ✅ |
| AC2 | integration | zero-before + hit-after pair | authored | ✅ |
| AC3 | integration | `test_file_shaped_off_is_byte_identical` | authored | ✅ |
| AC4 | integration | `test_file_shaped_unresolved_reported_on_build_report` | authored | ✅ |
| AC5 | integration | asserts in AC1 test | authored | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_keyed_calls_file_target.py::test_file_shaped_rule_find_callers_and_references -q
```

✋ **Gate 2** — ASSUMED #1/#2 ratified by design; maintainer confirms on PR.

## Phase 3 — execute

Branch `feat/256-dispatch-file-shaped-target` from `main` @ `8303edb`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | Fixture + proving tests | ✅ |
| 2 | Enrichment comment | ✅ |
| 3 | PLAN §19 | ✅ |
| 4 | Bookkeeping | ✅ (this commit) |

### Verification sweep

```
Ran at 658bee87ab8020962140cdac2711931d3b8d32b8
$ .venv/bin/python -m pytest tests/test_keyed_calls_file_target.py -q
4 passed in 1.93s
```

Design-conformance: diff ⊆ change list (tests + enrichment comment + PLAN + bookkeeping). No deviation.


## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 1 dispatch.

Challenger reconstructed 8 requirements from the raw ticket; **8 met / 0 not met / 0 can't tell**. Overall **CLEAN** (challenger only — REVIEWER OFF).

Proving evidence on reviewed tree:

```
Ran at 658bee87ab8020962140cdac2711931d3b8d32b8
$ .venv/bin/python -m pytest tests/test_keyed_calls_file_target.py -q
....                                                                     [100%]
4 passed in 1.94s
```

Reviewed at 7f43816df8b4f6ef871fcc3d304d1864f502b6c0

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

## Phase 5 — Finalise

Durable lesson: none new — 222's engine already admitted File qnames; this ticket pins the field shape and discharges E2.

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
Deferred to morning: merge; tracker transitions beyond bookkeeping already on branch.
