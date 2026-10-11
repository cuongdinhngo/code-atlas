---
id: 385
slug: route-table-as-data
title: 'A URL a tester reports cannot be asked about: a dispatcher route resolved at runtime has no subject in the graph'
phase: 2
milestone: Coverage
status: done
depends_on: []
---

**Reopened 2026-10-11 by the maintainer:** the anchor project runs this as soon as it ships; that consumer is the evidence the 2026-10-10 deferral waited for.

## Why this exists

Bug reports and test docs name **what the user did**: a URL (`index.php?module=orders&action=edit`),
a CLI command, a message type. A front-controller dispatcher maps that key to a handler at runtime
from request input, so the graph has no edge and no subject for it: `trace_capability` takes a
`qname`, a `path` or a `module`, never a route.

`keyed_calls` with `key_pattern` (361, `docs/TOOLS.md` §"Indirection rule files") covers a route
**spelled as a literal inside the code**. It cannot cover a route that only exists in the request,
which is the common case for front controllers (`$_GET['action']`, `argv[1]`, a queue message's
type field).

Many repos already hold the mapping as data — a route census measured by crawling the running app,
a framework's route dump. The anchor repo keeps one as a TSV and resolves URLs through its own
script, re-implementing outside the graph what a route subject would answer inside it. The table
stays in the consuming repo; code-atlas only reads it through the rule file the repo points at.

## Scope

1. A new indirection rule kind, data not adapter code (PLAN §1 non-goals): `routes`, a list of
   `{key, target}` where `key` is a route string or pattern (query-string keys order-insensitive)
   and `target` is a stored qname or a File. Loadable from JSON, and from a TSV via a named column
   map so a measured route census can be used as is.
2. Each route becomes an `Entry` subject with a `HEURISTIC` `ROUTES_TO` edge to its target (it is
   declared, not resolved) carrying `rule: true`.
3. `trace_capability` and `impact` accept `route` as a subject; `search_symbol` finds routes by
   key. An unmatched URL answers `no_such_symbol` with the nearest declared keys, not an empty list.
4. Build report counts `routes_unresolved` (a target naming no indexed symbol), like
   `rule_keys_unresolved`.

## Assumptions to prove at design

- Whether a route is a node or only a lookup table in front of existing subjects; a node makes it
  show up in `impact` answers ("which routes does this change reach"), which is the stronger case.
- Matching rule for query strings: which keys are significant (`module`, `action`) and which are
  noise (paging flags, ids) must be declared in the rule, not guessed.

## Acceptance criteria

- **AC1:** a fixture front controller with a two-row route TSV answers `trace_capability(route=...)`
  with a path starting at the declared target, tier `HEURISTIC`, `rule: true`.
- **AC2:** `impact` on the target's file lists the route among what it reaches.
- **AC3:** a route naming a missing target is counted in `routes_unresolved` and produces no edge.
- **AC4:** with no `routes` rule configured, `trace_capability(route=...)` answers
  `capability_not_configured`, not an empty result.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 385 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1 (no `Entry` node / `ROUTES_TO` edge) and merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 383 - 384 - 385 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/385-route-table-as-data`, on `main` after #68 merged (`92d5be9b`), carrying 384's four post-merge bookkeeping commits. Contract `.mango/run-contract-385.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 19 unresolved surfaced | 1 want-decision asked | 18 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `trace_capability`, `keyed_calls`/`key_pattern` (`docs/TOOLS.md` §"Indirection rule files"),
`rule_keys_unresolved` (`indexer.py`), `capability_not_configured` and `contract.RULE_FLAG` resolve. Recall: no live
claim names a class this change touches.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 47,195 tokens) added H12–H19.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | rule shape | how | `{"routes": {significant, table, tsv, columns}}`, a block or a list; the TSV repo-relative, contained, digested with the rules — Scope 1 |
| H2 | canonical key | how | path (no leading `/`, scheme or host) + only the `significant` query keys, sorted; none listed = all; `*` matches any value — Scope 1, assumption 2 |
| H3 | target | how | a stored qname or an indexed File; the first row of a key wins — Scope 1 |
| H4 | which tools | how | `trace_capability(route=)`, `impact(routes=[…])` (a list beside `paths`/`qnames`), `search_symbol` adds `routes` — Scope 3 |
| H5 | the declared hop | how | the first flow step carries `HEURISTIC`, `rule: true`; the row carries `route` — AC1 |
| H6 | which routes an impact lists | how | a target that is a seed or result qname, sits in a named path, or a File target among result files — AC2 |
| H7 | an unmatched URL | how | `no_such_symbol` + `nearest_routes` (difflib, 5) — Scope 3 |
| H8 | no table | how | `capability_not_configured` + `try_instead_hint` (no registered tool declares one, R5.4 c) — AC4 |
| H9 | `routes_unresolved` | how | on the BuildReport beside `rule_keys_unresolved` — Scope 4 |
| H10 | when the table moves | how | it describes the build that stored it (R4.2): edit the TSV, rebuild |
| H11 | a File target's flow | how | seeded at the File node (qname = path) |
| H12 | an index built before the block | how | no meta key → `capability_not_configured`; a meta key is not a schema change (R1.7 sibling-key precedent) |
| H13 | surfaces without routes | how | the map, `find_callers`, `explain_path`, `reachable_from` — documented |
| H14 | key grammar | how | case-sensitive, percent-decoded, fragment dropped; a CLI command or message type is a path-only key — documented |
| H15 | shadowed and ambiguous keys | how | first row / first matching pattern in table order wins — documented |
| H16 | a dead-target row | how | counted, not stored: its URL answers `no_such_symbol` (AC3: "produces no edge") |
| H17 | bad TSV input | how | a missing column or an escaping path fails the build loudly (R5.3) |
| H18 | tier beyond the first hop | how | each later hop keeps its own edge tier; documented |
| H19 | a mixed call | how | `impact(qnames=…, routes=…)` unions the seeds, as `paths` + `qnames` already do |
| W1 | Scope 2's `Entry` node + `ROUTES_TO` edge | want | **ASSUMED (awaiting ratification):** a lookup table in the index's meta instead — the ticket's own design question names it. A new node or edge kind moves `contract_version`; a bump cuts a release (`test_release_discipline.py`), and a release is a pushed tag, the maintainer's act. The lookup meets AC1–AC4; what it costs is presence in the map and the graph-walking tools (H13) |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=4 G=1 AC=4`
`CLARIFICATION: 19 raised | 19 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/10 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

384's head, this branch's base: `scripts/gate.sh` on 384 (its working doc). Ran at 3a3167b2.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "A URL a tester reports cannot be asked about" | a route is a subject | ✅ |
| C1 | Why | "The table stays in the consuming repo; code-atlas only reads it" | read through the rule file | ✅ |
| R1 | Scope 1 | `routes` rule kind, JSON or TSV via a column map | H1–H3 | ✅ |
| R2 | Scope 2 | `Entry` subject, `HEURISTIC` `ROUTES_TO` edge, `rule: true` | **deviation W1**: a lookup; HEURISTIC + rule on the declared hop | ⚠ W1 |
| R3 | Scope 3 | `route` on trace_capability and impact; search_symbol by key; unmatched → nearest | H4, H7 | ✅ |
| R4 | Scope 4 | `routes_unresolved` | H9 | ✅ |
| AC1 | AC | two-row TSV, path from the target, HEURISTIC, rule | | ✅ |
| AC2 | AC | impact on the target's file lists the route | | ✅ |
| AC3 | AC | missing target counted, no edge | | ✅ |
| AC4 | AC | no rule → capability_not_configured | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — first step qname, tier, rule; a downstream hop present | a noisy, reordered URL |
| AC2 | yes — the route rows' targets | and not a route that only shares the file (found and fixed while writing the test) |
| AC3 | yes — `routes_unresolved == 1` against a clean build's 0; the URL answers `no_such_symbol` | |
| AC4 | yes — reason, hint, no `routes` on impact | |

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ routes.py names no language; the table is data · §R1.7 (change-type) ✅ the table is its own meta key · §R3.1 (change-type) ✅ no vocabulary moved — W1 records why; test_a_route_adds_no_vocabulary asserts it · §R5.2 (change-type) ✅ a declared hop is HEURISTIC, never RESOLVED · §R5.4 (change-type) ✅ capability_not_configured carries a hint and no route · §R6.5 (change-type) ✅ the new tests fail on 384 (no routes module)`

## Phase 2 — design

### Approach

1. `code_atlas/routes.py`: `read_blocks` (rule JSON + TSV), `canonical`, `resolve`, `dump`/`load`, `match`, `nearest`,
   `containing`, `reaching`.
2. `enrichment.py`: `RulesPayload.routes`; `publish_routes` stores the resolved table in meta or drops it; `indexer.py`
   counts `routes_unresolved`.
3. `flows_from_graph(seeds=…)`; `trace_capability(route=)`; `impact(routes=)` + `routes` in the answer;
   `search_symbol` `routes`.
4. Docs: TOOLS.md (rule kind, tool rows), CHANGELOG.

### Rejected alternatives

- **`Entry` node + `ROUTES_TO` edge (Scope 2)** — W1: a contract bump and a release tag the run may not push.
- **Read the TSV at query time** — the answer would describe a table the index never saw (R4.2).
- **Match by regex keys** — `significant` plus `*` covers the census shapes without a second key grammar.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a flow can be seeded at an arbitrary qname | verified | AC1 through `flows_from_graph(seeds=)` |
| a File node's qname seeds a flow | verified | `test_a_route_to_a_file_traces_from_the_file` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the table | `code_atlas/routes.py` (new core module) | module pins 100 → 101 (P5) | R1, R3 | 1/1 |
| 2 | build | `code_atlas/enrichment.py`, `code_atlas/indexer.py` | BuildReport consumers (one new field) | R1, R4 | 2/2 |
| 3 | tools | `trace_capability.py`, `impact.py`, `search_symbol.py`, `onboarding/flows.py` | their MCP schemas (new optional params); impact's claim `call` | R3, R2 | 4/4 |
| 4 | tests | `tests/test_route_table.py`, the two module pins | — | AC1–AC4 | 3/3 |
| 5 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — rule file, build, tool | a real build through the Python adapter | n/a | ✅ |
| AC2 | integration | impact on the handler file, by route, and through the radius | n/a | ✅ |
| AC3 | integration | a third row with a dead target vs a clean build | n/a | ✅ |
| AC4 | integration | a build with no rule file | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_route_table.py`.

### Rollback

`git revert`; a stored table is one meta key, dropped by the next build without the block.

## Phase 3 — execute

Commits `cea5067c` (core, tools, tests), `fa3b31ad` (docs), `18b8521d` (File target, limits), and the challenger fix below. **Red first** (R6.5): on
384 the file fails at collection — `code_atlas.routes` does not exist. While writing AC2's test, impact listed a route
whose target only shared a file with a reached symbol; `routes.reaching` now matches a symbol target by qname.

**Deviation D1 (file axis).** The first gate run went red on `tests/test_agent_brief_usage_completeness.py`: it
lists every shipped tool parameter as taught or waived, and `routes` was neither. A listed-subset pin of the surface
this change extends, missed at Gate 2 — P5's own class. Both new parameters are waived as subject selectors.

```
$ scripts/gate.sh
  PASS pytest -q
21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
Ran at abd312a9
```

**The maintainer pushed `28f2cf7c`** during the run: `fnmatch` read a key's `?` and any `[...]` as patterns too, so
`i.php?page=*` matched `i.phpXpage=x`; a key is now escaped except for `*`, with a test. Inside the reviewed files; the
gate above re-ran on top of it.

**Verification sweep.** File axis: the diff is the change list plus D1; `ruff`, `mypy` (101 files) clean; 583 neighbouring
tests pass (trace_capability, impact, search_symbol, indirection, build report, query, claims, MCP server). Behaviour
axis: Approach 1–4 implemented as approved; Scope 2 deviates as W1 records.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at 18b8521d — files: `code_atlas/routes.py`,
`code_atlas/enrichment.py`, `code_atlas/indexer.py`, `code_atlas/onboarding/flows.py`, the three tools,
`tests/test_route_table.py`, the two module pins, `docs/TOOLS.md`, `CHANGELOG.md`; working doc: this file.

- **`challenger` round 1** (ticket-blind, 68,059 tokens): 10 met · 1 not met (Scope 2 — the recorded deviation W1;
  "a partial miss on the ticket's wording that needs human acceptance") · 0 can't tell. It confirmed a removed rule
  clears the table on an incremental build. Findings: a TSV with a byte-order mark failed the column lookup; a
  non-UTF-8 TSV raised a raw `UnicodeDecodeError`; `*` spans `&`; batch `search_symbol` reads no routes (documented
  single-query); `/` and `?a=1` share the empty key (first wins, documented); duplicates silent (noise). Fixed in the
  commit after `18b8521d`: `utf-8-sig` and a `ConfigError`, both tested; the glob documented.

- **`challenger` round 2** (44,702 tokens) — D1 touched a file outside the reviewed set, so a full re-dispatch: 4 met ·
  0 not met; the waivers add `route`/`routes` and weaken nothing; 384's four commits touch only its working doc.
  Reviewed at 0dd10f52 — round 1's files plus `tests/test_agent_brief_usage_completeness.py`.

Verdict: clean (challenger only — REVIEWER: OFF), with W1 standing for ratification. Matrix `Ph3/4 proven by`: R1, R3,
R4, AC1–AC4 → `tests/test_route_table.py`; R2 → W1 + `test_a_route_adds_no_vocabulary`; G1, C1 → the diff and TOOLS.md.

## Phase 5 — finalise

**Durable lesson.** None new — 384-C1 covers the per-row trap this run met; nothing here recurred.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/385-route-table-as-data`; open the PR against `main`.
Deferred to the maintainer: ratify W1; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 47,195 |
| 4 review | `challenger` (ticket-blind) | 1 | 68,059 |
| 4 review | `challenger` (D1 re-review) | 2 | 44,702 |

`LEDGER TOTAL: 159,956 · top cost driver: challenger`
