---
id: 331
slug: a-mirror-counterpart-is-named-for-a-symbol-it-lacks
title: "mirror_counterpart names the twin FILE on a function hit, so it reads as 'the other region has this function' when it does not — on the exact cross-region question the field asks daily"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [277, 282, 286]
---

## Why this exists (field retro, 2026-09-23 — FIELD-1621/1615 batch)

`search_symbol` on a page-file function returned it with `mirror_counterpart: <other-region page>`.
The session read that as *the other region has this function too*. It does not: a text search of
the counterpart file found **zero** occurrences. The retro: *"misleading on the exact region
question I was asking."*

**The field is file-level by construction.** 277 stamps mirrored **subtree** pairs; `decorate_mirror_hits`
and `label_mirror_rows` (`mirror_search.py:150-192`) call `resolve_counterpart(path, …)` on the hit's
file and attach the twin path when that file is indexed. The symbol is never consulted. On a File
hit that is the whole truth; on a Function / Method / Class hit it silently widens to a claim about
the symbol. 282 already refused to name a counterpart that is not indexed — this is the same
honesty one level down.

## Goal

On a symbol hit, a named counterpart means the symbol's twin exists there, or the payload says the
file exists and the symbol does not.

## Scope / Deliverables

1. **For non-File hits, check the counterpart file for a definition with the same name segment**
   (a `GraphStore` lookup scoped to that file; one batched query per page).
2. **Present ⇒ today's `mirror_counterpart`. Absent ⇒ a distinct field** (e.g. the file named plus
   a flag that the symbol is not in it) — the naming is the design call.
3. **Applies wherever 286/313 label mirrors**: `search_symbol`, `read_symbol`, nav rows.

## Constraints

- **061** — File hits, and symbol hits whose twin exists, are byte-identical.
- **R1.1** — match on the contract's name segment; no language or directory-name branch.
- **R1.4** — the lookup lives in `store.py`.
- Never assert which twin a request reaches (286's rule stands).

## Acceptance criteria

- **AC1** Fixture mirror pair; a function present only on one side → its hit does not carry a bare
  `mirror_counterpart`; red-arm on today's code.
- **AC2** A function present on both sides carries `mirror_counterpart` as today.
- **AC3** One query per page, not per hit (asserted by a query count or a store-call spy).

## References
`code_atlas/mirror_search.py:110-192`; `code_atlas/tools/search_symbol.py`; tickets 277, 282, 286, 313.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 331 — mirror counterpart symbol honesty (working doc)

- **Ticket:** 331 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR
- **Session status:** review clean → finalise

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW (field naming when file twin exists, symbol does not): use `mirror_counterpart_file` (path) + `mirror_symbol_absent: true`; omit bare `mirror_counterpart`. Citation: ticket Scope §2 ("the file named plus a flag"); parallels `mirror_no_counterpart` (286/282).

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | named counterpart ⇒ twin symbol exists, else say file-only | presence check + distinct fields | D1 D2 | AC1 AC2 | ✅ |
| R1 | Scope 1 | non-File: check counterpart file for same name segment; one batched query | `store.names_defined_in_files` | D1 | AC1 AC3 | ✅ |
| R2 | Scope 2 | Present ⇒ `mirror_counterpart`; Absent ⇒ `mirror_counterpart_file` + `mirror_symbol_absent` | decorate/label/read | D2 | AC1 AC2 | ✅ |
| R3 | Scope 3 | search_symbol, read_symbol, nav rows (286/313) | all three attach paths | D2 D3 | AC1 | ✅ |
| C1 | Constraints | 061 File + present-twin byte-identical | no new fields on those | D2 | AC2 | ✅ |
| C2 | Constraints | R1.1 name segment only | `nodes.name` match | D1 | review | ✅ |
| C3 | Constraints | R1.4 lookup in store.py | store method | D1 | AC3 | ✅ |
| C4 | Constraints | never assert which twin request reaches (286) | no new claim | D2 | review | ✅ |
| AC1 | AC | function one-sided → no bare mirror_counterpart; red-arm today | proving | D4 | proving | ✅ |
| AC2 | AC | both sides → mirror_counterpart as today | proving | D4 | proving | ✅ |
| AC3 | AC | one query per page (spy) | proving | D4 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

### AC validation

| AC | Ticket value | Recomputed | Match? |
|----|--------------|------------|--------|
| AC1 | no bare counterpart when twin lacks symbol | same | ✅ |
| AC2 | both sides keep mirror_counterpart | same | ✅ |
| AC3 | one query/page | store method once | ✅ |

## Phase 1 — Analysis

- Root cause (bug, `logic`): decorate/label/read attach file-level twin for every kind; symbol hits silently widen the claim.
- Blast radius: `mirror_search.py` decorate/label/read; `store.py` new batch; callers already pass store or can; search/read/impact.

`TRACK: backend — 0/4 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ name column only · R1.4 (change-type) ✅ store owns SQL · R4.2 (change-type) ✅ stored rows · R7.2 (change-type) ✅ ledger`

`BASELINE: green`

## Phase 2 — Design

- Approach: `GraphStore.names_defined_in_files(paths, names)` one DISTINCT query; decorate/label/read resolve twin then for non-File require `(twin, name)` in presence set; else `mirror_counterpart_file` + `mirror_symbol_absent`. Batch name lookup via existing `nodes_by_qualified_names` when hits lack `name`. Thread `store` into attach helpers.
- Rejected: per-hit `nodes_by_file` scan (AC3); language/qname-split match (R1.1); inventing a second mirror stamp.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | `names_defined_in_files` | code_atlas/store.py | SQL only | R1 C2 C3 AC3 | 1/1 |
| D2 | symbol-aware decorate/label/read + field consts | code_atlas/mirror_search.py | search/read/impact | G1 R2 C1 C4 | 1/1 |
| D3 | pass store into attach call sites | search_symbol / read_symbol / impact | callers | R3 | 1/1 |
| D4 | proving AC1–3 | tests/test_mirror_counterpart_symbol_honesty.py | — | AC* | 1/1 |
| D5 | bookkeeping | docs/tasks/331 · BACKLOG · TOKEN_LEDGER | — | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest | authored | ✅ |
| AC2 | integration | pytest | authored | ✅ |
| AC3 | integration | pytest spy | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_mirror_counterpart_symbol_honesty.py -q`

`SCOPE: S`

Rejected alternatives: synthesise twin qname via path rewrite (R1.1/language); mark absent with only a boolean and no path (ticket wants file named).

## Phase 3 — Execute

**Branch:** feat/331-mirror-counterpart-symbol-honesty

Implemented D1–D4: `names_defined_in_files`, symbol-aware decorate/label/read, store threaded at search/read/impact callers, proving tests.

```
$ .venv/bin/python -m pytest tests/test_mirror_counterpart_symbol_honesty.py -q
...
3 passed
```

`diff ⊆ approved list` — store.py · mirror_search.py · search_symbol.py · read_symbol.py · impact.py · proving test · working doc / BACKLOG / TOKEN_LEDGER.

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer) — waived at handover.
CHALLENGER: ON — CLEAN 10/0/0 (ticket-blind).
REVIEWER: OFF — waived.
