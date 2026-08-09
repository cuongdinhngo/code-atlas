---
id: 063
slug: view-databag-array-keys
title: 'The data-bag setter takes an array, not a key — 062 emits nothing on the anchor repo'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [062, 002, 049]
---

## Goal
[062](062_view-databag-producer.md) models a publish as **setter + `key_arg`**, where the key is a
string literal in a named argument position — `assign('items', $items)`. The anchor repo publishes
with an **array literal** instead — `setData(['items' => $items])` — so the keys live in the array's
own keys, not in an argument of their own. Rules written against that repo produce **zero** edges, and
no `key_arg` value can fix it. Close the gap so the shape 059 was filed for is actually reachable in
the repo 059 was filed from.

## Evidence (anchor repo, index built 2026-08-08, contract v4)
- The view class merges an array into its bag and `extract()`s it into the included template — the
  string-keyed handler→template flow field retro round 1 §6a.1 described.
- `setData` carries **11,204** `CALLS` edges; **7,663** of them have `args = ["array"]`. None have a
  string in any position that could be a key.
- **0** call sites repo-wide match the `(key, value)` setter shape 062 assumes (`assign` / `with` /
  `setVar` / `render`). The only setters that *do* match it are request-parameter helpers (67 sites),
  not the view bag.
- Even if a rule could name the array argument, the key is not in the index: `args` records the
  argument **category** only, never the value (`contract.py:101`). `"array"` is one token; the keys
  inside it are not emitted by the adapter at all.

So this is not a rules-authoring gap. The adapter never captured the information a rule would need.

## Scope / Deliverables
- **Count first, as 059 did.** Before any code, count the two publish shapes across the fixture corpus
  and the anchor repo: `(key, value)` setters vs array-literal setters. If the array shape is rare
  outside one repo, this ticket dies here and the finding is recorded. The count is the deliverable
  that can kill it.
- **Adapter — emit array-literal keys at the call site.** Extend what the PHP adapter records for a
  call argument so a top-level array literal contributes its **string keys**, in order. Keys only,
  never values (R4 determinism, and the same "category never content" discipline `args` already
  keeps for everything else). Non-literal keys (`$k => …`, spread, nested arrays) contribute nothing
  and must not shift the positions of the ones that do.
- **Contract (R3).** Decide where the keys ride — a sibling column/field beside `args`, or a widened
  `args` entry — and bump `contract_version` with `tests/contract/` updated in the **same** change.
  The vocabulary must keep an array-with-keys distinguishable from today's bare `"array"`, so an
  index built before this ticket is never mistaken for one that found no keys.
- **Rules shape.** Extend the 062 `view_data` rule so an operator can say "the keys of the array at
  argument N", not just "the string at argument N". Keep the existing form working unchanged — both
  shapes are real, and 062's is the one the fixtures already prove.
- **Same nav surface.** `find_view_data` answers identically whichever shape produced the edge; the
  caller must not have to know how the framework spells its bag.
- **Off by default.** No rules loaded ⇒ graph unchanged, exactly as 040/062.

## Constraints
- R2 absolute — no framework or repo names under `adapters/`; the adapter learns "array literal keys",
  a language fact, not "this view class".
- R1.1 — the core applies rules generically; no branch on which rule shape matched.
- R4 — same rules + same parse ⇒ same rows; edges stay HEURISTIC-or-documented, never silent RESOLVED.
- Consumer side stays out (059 rejected option 2; 062 held the line — this ticket does not reopen it).
- Nothing about a private repo enters this repository — fixtures only, and the counts above are
  aggregates.

## Acceptance criteria
- The publish-shape count lands in the working doc before the first line of adapter code, with the
  kill/proceed call recorded either way.
- A fixture handler publishing `['items' => $x, 'title' => $y]` yields two `PROVIDES_VIEW_DATA` edges
  with keys `items` and `title`; a `(key, value)` fixture keeps yielding exactly what 062 ships today.
- A non-literal key in the same array shifts nothing and emits nothing.
- `contract_version` bumped; `tests/contract/` updated in the same change; an index built at the
  previous version reads as "no keys captured", not "no keys found".
- With no rules file, no `PROVIDES_VIEW_DATA` edges exist.

## References
[062](062_view-databag-producer.md) (the rule shape this widens); [059](059_view-databag-edge.md)
(decision + original occurrence counts); [049](049_call-site-argument-selectivity.md) (`args`
categories, and why they carry no values); `code_atlas/enrichment.py` (`_view_data_edges`,
`_arg_is_string`); `code_atlas/contract.py` (`ARG_LITERALS`, `CONTRACT_VERSION`); R1.1, R2, R3, R4.
Origin: onboarding the anchor repo onto contract v4, 2026-08-08 — found while writing the 062 rules
file, not by a session using the tool.

## Outcome

### AC1 — Publish-shape count → **PROCEED**

Counted before adapter work (session 2026-08-09). Kill would leave the anchor permanently empty under 062.

| Corpus | (key,value) sites | array-literal setter sites | Notes |
|--------|------------------:|---------------------------:|-------|
| `tests/fixtures/**/*.php` (at count time, pre-array fixture) | **2** | **0** | Only 062 `assign` sites |
| Anchor repo (Evidence above; aggregates only) | **0** view-bag assign/with/setVar/render; 67 request-param helpers (not bag) | **7,663** of **11,204** `setData` CALLS with `args=["array"]` | Dominant shape 059 was filed for |

**Call:** **PROCEED** — implement adapter `arg_keys` + `key_from: "array_keys"`.

### Shipped
- **Contract v5 + schema 4:** `arg_keys` parallel to `args` (string keys of array literals).
- **Adapter:** top-level string keys only; non-literal keys do not shift.
- **Rules:** `key_from: "array_keys"` (default `"string"` unchanged for 062).
- **Suite:** 965 passed.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 063 — view-databag-array-keys (working doc)

- **Ticket:** 063 · local `docs/tasks/063_view-databag-array-keys.md`
- **Type:** enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full
- **BASELINE:** green — `964 passed` at tip `cb23db7` (untouched main, 2026-08-09)
- **work_doc_mode:** embed (plain local-file ticket)
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 0 unresolved | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**INPUT KIND:** ticket

**Exposure-checker:** [Challenger](2a4f003d-0a66-42df-9ee9-7c83c2c64dee) — `none (ready)`. HOW (sibling field vs widened `args`; rule encoding) → design.

## Requirements matrix

`SECTIONS: 5 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=5 R=6 G=1 AC=5`

Evidence section → support rows under G/R (counts inform kill gate), not separate IDs beyond R0.

| ID | Source | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|----------------|--------------|-----|-------|--------|
| G1 | Goal | Close array-literal publish gap so 059 shape is reachable where 062's key_arg alone yields 0 edges | ticket + anchor counts in Evidence | | | |
| R0 | Scope | **Count first** (fixture + anchor): (key,value) vs array-literal; kill/proceed recorded before adapter code | AC1; 059 precedent | | | |
| R1 | Scope | PHP adapter emits top-level array-literal **string keys** (order-preserving; non-literal/spread/nested contribute nothing, no shift) | Visitor `literalKind` Array_ → `"array"` only today | | | |
| R2 | Scope | Contract: place for keys; bump version + tests/contract; old `"array"` ≠ “keys found empty” | EDGE_FIELDS has `args` only; no edge `extra` | | | |
| R3 | Scope | Extend 062 `view_data` rule: “keys of array at arg N”; keep string `key_arg` working | enrichment `{setter,key_arg}` only | | | |
| R4 | Scope | Same `find_view_data` surface for both shapes | find_view_data.py | | | |
| R5 | Scope | Off by default — no rules ⇒ no PROVIDES_VIEW_DATA | 040/062 | | | |
| C1 | Constraints | R2 — language fact in adapter, no framework/repo names | R2.2 | | | |
| C2 | Constraints | R1.1 — core applies rules generically | enrichment | | | |
| C3 | Constraints | R4 — deterministic; HEURISTIC not silent RESOLVED | 062 | | | |
| C4 | Constraints | Consumer/option 2 stays out | 059/062 | | | |
| C5 | Constraints | Fixtures only; private aggregates only | Evidence already aggregate | | | |
| AC1 | AC | Count + kill/proceed in working doc before adapter code | falsifiable doc artifact | | | |
| AC2 | AC | Array fixture → items+title edges; (key,value) fixture unchanged from 062 | pytest | | | |
| AC3 | AC | Non-literal key emits nothing / no shift | pytest | | | |
| AC4 | AC | contract_version bump + tests/contract; prior index = no keys captured | contract tests | | | |
| AC5 | AC | No rules ⇒ no PROVIDES_VIEW_DATA | pytest | | | |

References: citation only.

## AC validation

| AC | Falsifiable? | Notes |
|----|--------------|-------|
| AC1 | yes (doc count + proceed/kill line) | Must precede adapter edits in execute |
| AC2–AC5 | yes (pytest / contract pins) | |

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (HOW→design) | 0 for human decision`

| # | Item | Resolution | Citation |
|---|------|------------|----------|
| 1 | Sibling field vs widened `args` | HOW → design (prefer sibling `arg_keys` parallel to `args` — safer for SQL filters + old indexes) | ticket Scope; store `_args_predicate` |
| 2 | Rule encoding for “keys of array at N” | HOW → design (e.g. `key_from: "array_keys"` + `key_arg`) | ticket |
| 3 | Count methodology “as 059” | HOW → design/execute (fixture corpus grep + record ticket Evidence as anchor aggregates; CODE_ATLAS_SCALE_SAMPLE if set) | ticket R0 |

**Gate 0:** none (`j=0`).

## Cause / blast radius

- **Cause:** adapter emits `"array"` category only; 062 enrichment requires `"string"` at `key_arg`.
- **Blast:** PHP `Visitor.php` args; `contract.py` v4→5 + EDGE_FIELDS; store insert/validate; enrichment view_data; fixtures/tests; CONVENTION/PLAN. Nav tool shape unchanged. No Twig/Blade.

## Scope / tier

`SCOPE: M` · `TIER: full` · `TRACK: backend`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| analysis | explore (args/enrichment map) | 1 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-09 | Standing (prior): best option + pass all gates incl. push/PR/merge when CI green |
| 2026-08-09 | refine skip: 0 unresolved; deps 062/002/049 done; baseline 964 @ cb23db7 |

## Decision log (delta)

| When | Decision |
|------|----------|
| 2026-08-09 | Gate 1 cleared (standing) |
| 2026-08-09 | Gate 2 cleared (standing) — approach below |
| 2026-08-09 | **AC1 count → PROCEED** (see Phase 2) |

## Phase 2 — Design

### AC1 — Publish-shape count (before adapter code)

| Corpus | (key,value) sites | array-literal setter sites | Notes |
|--------|------------------:|---------------------------:|-------|
| `tests/fixtures/**/*.php` (32 files) | **2** (`view_databag/handler.php` assign) | **0** | Fixture corpus is 062-shaped only today |
| Anchor repo (ticket Evidence, 2026-08-08, aggregates only) | **0** matching assign/with/setVar/render for view bag; 67 request-param helpers (not bag) | **7,663** of **11,204** `setData` CALLS are `args=["array"]` | Dominates the shape 059 was filed for |

**Kill/proceed:** **PROCEED.** Array-literal publish is rare in *this* fixture tree but is the dominant (and only) view-bag shape on the anchor; killing would leave 062 permanently empty there. Plant an array fixture in this ticket so both shapes are proven in-repo.

### Approach
1. **Contract v5 + schema 4:** optional edge field `arg_keys` (JSON list parallel to `args`: `null` for non-array args; list of string keys for array args — possibly empty). Absent field / null slot = keys not captured (old indexes). Empty list = captured, no string keys.
2. **PHP adapter:** for `Array_` args, emit top-level string keys in order; non-literal keys / unpack contribute nothing and do not insert placeholders.
3. **Rules:** `view_data` entries may set `key_from: "array_keys"` (default `"string"` = 062). Same `key_arg`. Enrichment reads `arg_keys[key_arg-1]` and emits one `PROVIDES_VIEW_DATA` per key.
4. **Nav:** unchanged `find_view_data`.
5. Handshake `contract_version: 5`.

### Rejected
| Alt | Why |
|-----|-----|
| Widen `args` entry to object | Breaks 049 `json_extract` filters / ARG_LITERALS |
| Line-regex parse of PHP arrays | Fragile; ticket wants adapter capture |
| Kill ticket (fixtures only rare) | Anchor evidence is the filing reason |

### Assumptions
| # | Assumption | Tag | Mitigation |
|---|------------|-----|------------|
| A1 | PHP-Parser exposes ArrayItem keys as String_ for `'k'=>` | verified-enough | proving fixture |
| A2 | Parallel `arg_keys` survives store JSON round-trip | novel-untested | proving + call-site tests |

### Change list
| # | Change | Area | Rows |
|---|--------|------|------|
| CL1 | `CONTRACT_VERSION=5`, `arg_keys` on `EDGE_FIELDS`, validate | `contract.py` | R2,AC4 |
| CL2 | `SCHEMA_VERSION=4`, edges.arg_keys column | `store.py` | R2,AC4 |
| CL3 | Emit `arg_keys` for array literals | `adapters/php/Visitor.php` | R1,C1 |
| CL4 | Handshake + fake adapter → 5 | php index + fake_adapter + version pins | AC4 |
| CL5 | `view_data.key_from` + enrichment array path | `enrichment.py` | R3,R5,AC2,AC5 |
| CL6 | Array fixture + tests (array + non-literal + 062 regression + off) | fixtures + tests | AC2,AC3,AC5 |
| CL7 | Docs CONVENTION/PLAN/README as needed | docs | G1 |
| CL8 | Proof collateral: EDGE_FIELDS pins, VOCABULARY len, schema tests | tests | AC4 |

### Verification
| AC | Layer | Proof |
|----|-------|-------|
| AC1 | doc | count table above |
| AC2 | integration | proving pytest |
| AC3 | integration | non-literal key fixture |
| AC4 | logic | contract + schema pins |
| AC5 | integration | no-rules test |

**Proving test:** `tests/test_view_databag_producer.py` (extend) / `test_view_databag_array_keys.py`

## Phase 3 — Execute

**Branch:** `feat/063-view-databag-array-keys`
**Suite:** 965 passed.

## Phase 4 — Review

- **Reviewed at** `1aeee235a02c6adb61af78e9d7b4b189f9d3fb9c`
- **Reviewer round 1:** [Reviewer](f7f56936-5a1a-4561-8f5c-c33b1e2ac9a3) — **LGTM**
- **Challenger round 1:** [Challenger](80979760-4593-4efc-afd6-4a3a6c4f78c3) — **11 met · 0 not met · 1 can't tell** (AC1 temporal) · Gate 4 **FAIL**
- **Reviewer round 2:** [Reviewer](9bec63ad-7a7c-47f2-bb3b-1331df80d70f) — **LGTM** (AC1 Outcome pin)
- **Challenger round 2:** [Challenger](99bfb3a9-0414-4c39-8da1-44adce8c1281) — **16 met · 0 not met · 0 can't tell** · Gate 4 **PASS**

### Reviewer detail — round 1 @ `e238144`
**LGTM.** Critical/Important: none. Contract v5 `arg_keys`, schema 4, PHP keys, `key_from`, 062 path, find_view_data unchanged, AC1 proceed recorded.

### Challenger detail — round 1 @ `e238144`
**FAIL** on AC1 process (single commit can't prove count-before-code). Product ACs met.

### Round 2 (@ `1aeee23`)
Outcome AC1 table above separator + `tests/test_view_databag_shape_count.py` + LESSONS → challenger **PASS**, reviewer still **LGTM**.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| analysis | explore | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 2 | unmeasured (blocking retrieval) |
| review | challenger | 2 | unmeasured (blocking retrieval) |

## Phase 5 — Finalise

Standing: push + PR + merge when CI green.

## Session status

- **Phase:** finalise
- **Reviewed at:** `1aeee235a02c6adb61af78e9d7b4b189f9d3fb9c`
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/063_view-databag-array-keys.md` (below separator)
