---
id: 062
slug: view-databag-producer
title: 'Producer-side view data-bag edges — rules + enrichment (implements 059 Option 1)'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [030, 040, 059]
---

## Goal
Implement the [059](059_view-databag-edge.md) decision: **Option 1 — producer side only.** When a
handler publishes values into a view/data-bag under string keys, the graph records that publish so an
agent can ask “what keys does this handler put in scope?” without grepping. Consumer-side template
reads stay out of scope (059 rejected option 2 for now).

## Scope / Deliverables
- **Contract (R3).** Add a new edge kind for “handler symbol publishes view-scope key”
  (working name `PROVIDES_VIEW_DATA` — final name chosen at design) to `EDGE_KINDS` in
  `code_atlas/contract.py`. Bump `contract_version` and update `tests/contract/` in the **same**
  change.
- **How the key is addressed.** Prefer a synthetic target (e.g. a stable qname for the string key, or
  an edge `extra` / target_raw convention documented in CONVENTION) — pick the smallest shape that
  nav tools can query without a new node kind unless a node kind is clearly cheaper.
- **Rules-file shape (R2).** Extend the 040 indirection-rules channel (or a sibling JSON rules file
  outside `adapters/`, same `CA_*` opt-in pattern) so operators declare *how* their framework’s view
  setter looks (method/qname patterns → which argument holds the key). Framework names live only in
  operator/fixture data, never under `adapters/`. Core `enrichment.py` applies rules generically —
  no `if framework == …` (R1.1).
- **Nav answer.** A tool surface (extend an existing `find_*` or add a thin helper) that, given a
  handler method qname, returns the published keys + lines at `detail_level` appropriate to §19.
- **Off by default.** No rules loaded ⇒ graph unchanged (mirror 040).
- **Deterministic (R4).** Same rules + same parse ⇒ same rows; HEURISTIC (or documented) tier — never
  silent plain RESOLVED.

## Constraints
- R2 absolute — zero framework knowledge in adapters; CI grep-gate stays green.
- R3 — vocabulary change and conformance tests land together with the version bump.
- Do **not** widen the indexed file set to Twig/Blade in this ticket (041 stands); producer edges come
  from already-indexed PHP handlers + rules.
- Nothing about a private repo enters this repository — fixtures only.

## Acceptance criteria
- With a planted fixture + rules file, a handler that publishes `items` (or equivalent) yields a
  `PROVIDES_VIEW_DATA` (or final name) edge queryable by the nav surface; without rules, no such edges.
- `contract_version` bumped; `tests/contract/` updated in the same change.
- Rule-emitted edges are distinguishable by tier/provenance from adapter CALLS/ALIASES (040 precedent).
- PLAN §19 059 decision remains the scope authority; this ticket does not silently expand to option 2.

## References
[059](059_view-databag-edge.md) (decision + occurrence counts); [040](040_framework-indirection-data.md);
`code_atlas/enrichment.py`; `code_atlas/contract.py` (`EDGE_KINDS`, `CONTRACT_VERSION`); R2, R3, R4;
PLAN §19 data-bag decision.

## Outcome

- **Contract v4:** `PROVIDES_VIEW_DATA` + `viewdata:<key>` (`VIEW_DATA_PREFIX`); not in `FQN_EDGE_KINDS`.
- **Rules:** `CA_INDIRECTION_RULES` `view_data` `{setter, key_arg}` — scan CALLS, map `key_arg` via args categories to the Nth string literal on the call line; HEURISTIC edges on the indirection bookmark.
- **Nav:** `find_view_data(qname)` returns keys + call-site lines + `rule: true`.
- **Off by default:** no rules ⇒ no such edges.
- **Suite:** 962+ passed (proving 2/2).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 062 — view-databag-producer (working doc)

- **Ticket:** 062 · local `docs/tasks/062_view-databag-producer.md`
- **Type:** enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full
- **BASELINE:** green — `956 passed` at tip `8dae1f7` (untouched main, 2026-08-08)
- **work_doc_mode:** embed (plain local-file ticket)
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 0 unresolved | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**INPUT KIND:** ticket

**Exposure-checker:** [Challenger](b5aef290-5bac-4efb-8c2f-cadf44b5fa8e) — `none (ready)`. HOW items (edge name, key address, rules channel, nav surface, tier) deferred to design.

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=6 G=1 AC=4`

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|-------------------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Option 1 producer only; record publish keys; consumer OOS | Ship producer-side view data-bag edges per PLAN §19 / 059; no template reader | PLAN §19; 059 done | | | |
| R1 | Scope | New edge kind + bump `contract_version` + `tests/contract/` same change | Add kind to `EDGE_KINDS`; `CONTRACT_VERSION` 3→4; update contract tests | `contract.py:21,39-50` v3 / 10 kinds | | | |
| R2 | Scope | Prefer synthetic target / target_raw / extra — smallest shape, avoid new node kind | Address published key without new NODE_KINDS unless cheaper | Edges have `target_raw`, no edge `extra` | | | |
| R3 | Scope | Extend 040 rules channel or sibling JSON + CA_* ; enrichment generic | Rules declare setter patterns → key arg; no framework in adapters | `enrichment.py` aliases/calls only today | | | |
| R4 | Scope | Nav: handler method qname → published keys + lines at detail_level | Thin tool or extend find_*; §19 detail_level | find_* are inbound-only; `edges_by_source` exists | | | |
| R5 | Scope | Off by default — no rules ⇒ graph unchanged | Mirror 040 when knob unset | `load_indirection_rules` None path | | | |
| R6 | Scope | Deterministic; HEURISTIC (or documented) — never silent RESOLVED | Rule edges HEURISTIC + rule provenance | 040 uses HEURISTIC + `INDIRECTION_FILE` + `rule` flag | | | |
| C1 | Constraints | R2 absolute; CI grep-gate green | Zero framework knowledge under adapters/ | R2.2 | | | |
| C2 | Constraints | R3 vocab + conformance together | Same PR as version bump | R3.1 | | | |
| C3 | Constraints | Do not widen indexed set to Twig/Blade | 041 stands; PHP handlers only | 041 | | | |
| C4 | Constraints | No private-repo identifiers in this repo | Fixtures only | R2.3 | | | |
| AC1 | AC | Fixture+rules ⇒ queryable publish edge; no rules ⇒ none | Falsifiable pytest | planted fixture | | | |
| AC2 | AC | contract_version bumped; tests/contract updated same change | Grep CONTRACT_VERSION + EDGE_KINDS tests | `test_contract_schema.py` | | | |
| AC3 | AC | Rule edges distinguishable by tier/provenance from adapter CALLS/ALIASES | HEURISTIC + synthetic path / `rule` flag (040) | nav_result RULE_FLAG | | | |
| AC4 | AC | PLAN §19 059 remains scope; no silent option 2 | No template parse / Twig-Blade index widen in this PR | diff review | | | |

References section: citation only — not a requirement row.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | fixture+rules → edge; no rules → none | Binary presence/absence of named edge kind from handler | Y | yes — pytest |
| AC2 | version bump + contract tests same change | CONTRACT_VERSION must be 4; EDGE_KINDS includes new kind; schema tests updated | Y | yes — grep/pytest |
| AC3 | distinguishable tier/provenance | Must not be silent RESOLVED; 040 pattern: HEURISTIC + rule path/`rule` | Y | yes — assert tier + rule flag |
| AC4 | no option 2 | No new template adapter / no Twig-Blade in collect paths | Y | yes — diff + no new file suffixes |

## Inventory

- **Universal "no framework in adapters":** CI R2.2 grep-gate is the denominator (existing gate) — no new inventory.
- **No frontend surfaces** — TRACK backend; SURFACES N/A.

## Clarifications

`CLARIFICATION: 5 raised | 5 self-resolved (HOW→design) | 0 for human decision`

| # | Item | Resolution | Citation |
|---|------|------------|----------|
| 1 | Final edge kind name | HOW → design (working `PROVIDES_VIEW_DATA`) | ticket Scope |
| 2 | Key addressing shape | HOW → design (prefer `target_raw` synthetic convention; no edge `extra` field) | `EDGE_FIELDS`; ticket R2 |
| 3 | Extend 040 vs sibling file/knob | HOW → design (prefer extend same JSON + CA_INDIRECTION_RULES) | ticket; enrichment.py |
| 4 | Nav surface | HOW → design (thin outgoing helper; find_* inbound) | explore map |
| 5 | Pattern→arg extraction vs exact pairs | HOW → design (ticket requires patterns→key arg; 040 is exact FQN today) | ticket Scope; enrichment v1 limit |

**Gate 0:** none (`j=0`).

## Cause / blast radius

- **Cause:** missing edge vocabulary + rules for string-key view publish (059 Option 1).
- **Blast radius:** `contract.py` (+version), `tests/contract/`, `enrichment.py` (+rules schema), indexer path (already calls enrichment), new/extended nav tool + MCP register, CONVENTION/PLAN/README docs, fixtures under `tests/fixtures/`, enrichment tests. Adapters: **untouched** (R2).

## Scope / tier

`SCOPE: M` · `TIER: full` · `TRACK: backend`

Contract bump + enrichment extension + nav + fixtures — multi-file, not lite; single deliverable (not epic).

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass all gates (incl. push/PR/merge when CI green) |
| 2026-08-08 | refine skip: 0 unresolved product-decisions |
| 2026-08-08 | deps 030/040/059 done; baseline 956 passed @ 8dae1f7 |
| 2026-08-08 | Gate 1 cleared (standing) — HOW deferred to design |
| 2026-08-08 | Gate 2 cleared (standing) — approach below |

## Phase 2 — Design

### Approach
1. **Contract v4:** add edge kind `PROVIDES_VIEW_DATA` (not in `FQN_EDGE_KINDS`). Synthetic key address: `target_raw = viewdata:<key>` (`VIEW_DATA_PREFIX` in `contract.py`). No new node kind.
2. **Rules (extend 040 JSON / `CA_INDIRECTION_RULES`):** optional `view_data: [{ "setter": "<method or FQN>", "key_arg": <1-based> }]`. Enrichment scans existing adapter `CALLS` edges whose `target_raw` matches the setter (exact, or `::<name>` suffix when setter is a bare method name). When `args[key_arg-1] == "string"`, extract the string literal from the call site source line; emit `PROVIDES_VIEW_DATA` with the **real** `file_path`/`line` of that CALLS edge, tier **HEURISTIC**. Wipe prior `PROVIDES_VIEW_DATA` each apply. Off rules ⇒ wipe + unchanged otherwise.
3. **Provenance:** adapter never emits this kind; nav stamps `rule: true` for `kind == PROVIDES_VIEW_DATA` (and keeps path-based rule flag for 040).
4. **Nav:** new thin tool `find_view_data(qname, detail_level, limit, offset)` → outgoing `PROVIDES_VIEW_DATA` via `edges_by_source`; hits expose `key` (strip prefix), file, line, tier, `rule`.
5. **PHP handshake** + fake_adapter + hard-coded version tests → 4.

### Rejected alternatives
| Alt | Why rejected |
|-----|----------------|
| Hand-list `{source,key,line}` only (040-calls clone) | Misses ticket’s pattern→`key_arg` requirement |
| New `ViewKey` node kind | Heavier than `target_raw` convention; YAGNI |
| Put string *values* in `args` | Breaks v3 “category not value”; larger contract blast |
| Sibling `CA_VIEW_DATA_RULES` knob | Second opt-in; ticket allows extend-or-sibling — same channel is smaller |

### Assumptions
| # | Assumption | Tag | Mitigation |
|---|------------|-----|------------|
| A1 | Planted `$view->assign('items', …)` yields a CALLS edge with string at `key_arg` | novel-untested | Proving fixture fails if adapter shape differs |
| A2 | Nth string literal on the call line is extractable deterministically for one-line calls | novel-untested | Proving test; multi-line OOS v1 |
| A3 | `PROVIDES_VIEW_DATA` never emitted by adapters | verified | adapters don’t list the kind; contract opt-in only |

### Change list (approved)

| # | Change | Area | Rows | k/N |
|---|--------|------|------|-----|
| CL1 | `CONTRACT_VERSION=4`, `PROVIDES_VIEW_DATA`, `VIEW_DATA_PREFIX` | `code_atlas/contract.py` | R1,R2,AC2 | 1/1 |
| CL2 | Update EDGE_KINDS / version assertions | `tests/contract/test_contract_schema.py` | R1,AC2 | 1/1 |
| CL3 | PHP + fake handshake `contract_version: 4` | `adapters/php/index.php`, `tests/fixtures/adapter/fake_adapter.py`, version-locked tests | R1,C2 | 1/1 |
| CL4 | Parse/apply `view_data` rules; extract keys; emit/wipe edges | `code_atlas/enrichment.py` (+ tiny key-extract helper) | R3,R5,R6,G1,AC1,AC3 | 1/1 |
| CL5 | `delete_edges_by_kind` (or equiv.) for wipe | `code_atlas/store.py` | R3,R5 | 1/1 |
| CL6 | `rule` flag for this kind when file:line real | `code_atlas/tools/nav_result.py` | AC3,R6 | 1/1 |
| CL7 | `find_view_data` tool + register in `TOOL_NAMES` | `code_atlas/tools/find_view_data.py`, `main.py` | R4,AC1 | 1/1 |
| CL8 | Fixture + proving tests (on/off rules) | `tests/fixtures/view_databag/`, `tests/test_view_databag_producer.py` | AC1,AC3,R5 | 1/1 |
| CL9 | Docs: EDGE_KINDS + `viewdata:` + tool; PLAN §19 062 done note | `docs/CONVENTION.md`, `docs/PLAN.md`, README tool list if present | R2,AC4,G1 | 1/1 |
| CL10 | Proof collateral: `test_mcp_server` TOOL_NAMES; `test_alias_indirection` version; `test_php_adapter_server` handshake | those tests | R1 | 1/1 |

**Out of list:** template/Twig/Blade indexing (AC4); consumer-side edges; multi-line call extraction; glob setter patterns beyond exact/`::suffix`.

### Rule compliance
- R1.1 — generic enrichment, no framework branch
- R2 — rules/fixtures only outside adapters; adapter version bump only
- R3 — vocab + conformance + adapter handshake same change
- R4 — deterministic extract; HEURISTIC only
- R5.3 — malformed rules fail loud (040 path)

### Verification plan

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 | integration | `tests/test_view_databag_producer.py` — rules on ⇒ `find_view_data` returns `items`; rules off ⇒ none | ✅ |
| AC2 | logic | contract schema tests + handshake asserts version 4 | ✅ |
| AC3 | integration | assert HEURISTIC + `rule: true` on hits | ✅ |
| AC4 | review/diff | no Twig/Blade collect widen; no template adapter | ✅ |

**Named proving test:** `tests/test_view_databag_producer.py::test_handler_publish_keys_queryable_with_rules`

## Phase 3 — Execute

**Branch:** `feat/062-view-databag-producer`

**Deviation:** CL5 (`delete_edges_by_kind`) dropped — `PROVIDES_VIEW_DATA` rows live on `INDIRECTION_FILE` and are replaced with aliases/calls (survives per-file reparse). Nav resolves `file` from the subject Method node; edge `line` is the call-site line. Approach still matches Gate 2 intent.

**Proving test:** `tests/test_view_databag_producer.py::test_handler_publish_keys_queryable_with_rules` — green.

**Suite:** `962 passed`; ruff/mypy clean on touched paths.

## Phase 4 — Review

- **Reviewed at** `35c99e8ace554c2d6fc215cfddd7be46c7ab8eff`
- **Reviewed files:** `code_atlas/contract.py`, `enrichment.py`, `store.py`, `tools/find_view_data.py`, `tools/nav_result.py`, `main.py`, `adapters/php/index.php`, fixtures + `tests/test_view_databag_producer.py`, `tests/contract/`, CONVENTION/PLAN/README/ENGINEERING_RULES, BACKLOG + task frontmatter, proof-collateral tests
- **Reviewer round 1:** [Reviewer](ed9063d9-c4a2-4640-b8e4-b2dd47519f9f) — **CHANGES REQUESTED** (3 Important)
- **Challenger round 1:** [Challenger](dc28f36c-0f7e-4259-975b-475a671d27d3) — **14 met · 0 not met · 1 partial can't-tell** · Gate 4 **PASS**
- **Reviewer round 2:** [Reviewer](8f2620dd-a9ae-40a6-a25e-73f91b6b5ec8) — **LGTM** (all round-1 findings closed)
- **Challenger round 2:** [Challenger](725a110a-5a1f-4c8f-b2df-d659e06c3c33) — **16 met · 0 not met · 0 can't tell** · Gate 4 **PASS**
- **Gate 4:** clean @ `35c99e8` · **PR:** [#73](https://github.com/cuongdinhngo/code-atlas/pull/73)

### Reviewer detail — round 1 ([Reviewer](ed9063d9-c4a2-4640-b8e4-b2dd47519f9f)) @ `5ef1c25`

**Verdict: CHANGES REQUESTED** (conditional LGTM after findings 1–3). Critical: none. Diff ⊆ approved list (CL5 drop → `INDIRECTION_FILE` recorded). Suite **962 passed**; proving 2/2 green.

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | Enrichment reads call-site source while R1.4 / PLAN §2 still said “never parses source” | Important | Fixed in `35c99e8` — R1.4 + PLAN §2 carve-out: may read one already-indexed line for `view_data`; never runs a language parser |
| 2 | PLAN said “Implemented in 062” while BACKLOG + frontmatter stayed `todo` (R7.2) | Important | Fixed in `35c99e8` — `in-progress` (then `done` at finalise) |
| 3 | `key_arg` treated as string-literal ordinal, not argument index (`put($bag,'extra')` with `key_arg: 2` would miss) | Important | Fixed in `35c99e8` — map via `args` categories to Nth string literal; fixture `put` + `key_arg: 2` |

**Verified (no finding):** contract v4 + `PROVIDES_VIEW_DATA` + `VIEW_DATA_PREFIX`; not in `FQN_EDGE_KINDS`; handshake bumps; R1.1/R2.2; off-by-default; HEURISTIC + `rule` + `INDIRECTION_FILE`; `find_view_data` + `TOOL_NAMES`; SQL confined to `store.py`.

### Challenger detail — round 1 ([Challenger](dc28f36c-0f7e-4259-975b-475a671d27d3)) — ticket-blind @ `5ef1c25`

**14 met · 0 not met · 1 partial can't-tell** (CI R2.2 gate not re-run; adapter/enrichment inspection supports met). Independence: raw ticket + `git diff main...HEAD` only.

| # | Requirement | Verdict |
|---|-------------|---------|
| 1 | Producer-only (059 Option 1); consumer OOS | **met** |
| 2 | `PROVIDES_VIEW_DATA` + contract bump + `tests/contract` | **met** |
| 3 | Synthetic key address (`viewdata:<key>`) | **met** |
| 4 | Extend 040 rules (setter → key_arg); no framework in core | **met** |
| 5 | Nav: handler qname → keys + lines | **met** — `find_view_data` |
| 6 | Off by default | **met** |
| 7 | HEURISTIC, not silent RESOLVED | **met** |
| 8 | R2 adapters clean | **met** / can't-tell on live CI grep |
| 9 | No Twig/Blade widen | **met** |
| 10 | Fixtures only (no private repo) | **met** |
| 11–14 | AC1–AC4 | **met** |

### Reviewer detail — round 2 ([Reviewer](8f2620dd-a9ae-40a6-a25e-73f91b6b5ec8)) @ `35c99e8`

**Verdict: LGTM.** Critical / Important: none. Round-1 findings 1–3 verified closed (SRP carve-out, `in-progress` status, `key_arg` ordinal + `put($bag,'extra',1)` fixture). Proving 2/2; related contract/MCP scan 202 passed.

### Challenger detail — round 2 ([Challenger](725a110a-5a1f-4c8f-b2df-d659e06c3c33)) — ticket-blind @ `35c99e8`

**16 met · 0 not met · 0 can't tell.** Gate 4 **PASS**. Proving + contract schema **43 passed**. Same independence note as round 1.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| analysis | explore (enrichment/040 map) | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 2 | unmeasured (blocking retrieval) |
| review | challenger | 2 | unmeasured (blocking retrieval) |

## Durable lesson

`key_arg` is an **argument** index; map through `args` categories to the Nth string literal on the line — never treat `key_arg` as a raw literal ordinal.

## Phase 5 — Finalise

Push + PR + merge approved (standing). Opened and merged [#73](https://github.com/cuongdinhngo/code-atlas/pull/73).
Cost summary: **6** subagent dispatches, all `unmeasured (blocking retrieval)`; top driver = review pairs.

## Session status

- **Phase:** done — PR [#73](https://github.com/cuongdinhngo/code-atlas/pull/73)
- **Reviewed at:** `35c99e8ace554c2d6fc215cfddd7be46c7ab8eff`
- **Reviewed files:** contract/enrichment/store/nav/find_view_data/main, PHP handshake, fixtures+proving tests, CONVENTION/PLAN/README/ENGINEERING_RULES, BACKLOG + task frontmatter, proof-collateral tests
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/062_view-databag-producer.md` (below separator)
