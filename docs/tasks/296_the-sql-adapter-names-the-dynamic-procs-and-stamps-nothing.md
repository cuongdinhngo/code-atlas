---
id: 296
slug: the-sql-adapter-names-the-dynamic-procs-and-stamps-nothing
title: 'The T-SQL adapter already holds the set of procedures that execute a string as SQL, and uses it to mark the call `DYNAMIC` — the exact evidence 279 asks for, one level below the claim it protects — but it never stamps `unmodelled_resolution`, so a schema whose dispatch goes through `sp_executesql` still yields a confident orphan population'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [279, 184, 255, 299]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

**Blocked on [299](299_a-confident-hit-list-does-not-say-the-index-never-saw-this-extension.md).**
This stamp cannot see an extension the adapter never parsed. Run 299 first.

Of the three ports in this group this is the cheapest, because the detection already exists.
`DYNAMIC_PROCS` at `adapters/sql/src/scan.js:255` names `sp_executesql` and its siblings, and the
`EXEC` scan marks a call dynamic when the target is a variable or a parenthesised expression
(`scan.js:711`, `:720-723`). The adapter therefore already knows, per file, that some execution in it
resolves at runtime — and does nothing with the fact above the edge.

279's mechanism is language-agnostic and waiting: `File.extra.unmodelled_resolution` unioned per
language (`store.py:1252`), stamped into `meta` (`indexer.py:1273`), read by `find_orphans`
(`tools/find_orphans.py:82-95`). Only `adapters/php/src/Visitor.php:1341` sets it.

A dynamic-SQL schema is the strongest case of the three: a procedure called only by name assembled at
runtime has *no* inbound edge anywhere in the graph, so it is not merely under-linked, it is
indistinguishable from dead code. That is the shape 279's Why argues an agent must never be handed as
a bare population.

## Scope / Deliverables

- **A strategy token in `contract.py`** naming string-executed SQL (`dynamic_sql`), beside
  `RESOLUTION_AUTOLOAD`.
- **The stamp, from evidence the scan already produces** — the existing `DYNAMIC_PROCS` hit and the
  variable/parenthesised `EXEC` target. No new parsing, no new regex, no procedure-name list beyond
  the T-SQL standard set already there.
- **The File-node `extra` merge** in the SQL adapter's node emission, sorted and de-duplicated.
- **A gate-1 fixture** with an `EXEC(@sql)` and an `sp_executesql` call, and one without.

## Constraints

- R5.6: the stamp says the population is unmeasured; it never claims a target.
- R1.1: core change limited to the token constant.
- 061: a schema with no dynamic execution is byte-identical, including the `meta` stamp being absent.
- The per-edge `DYNAMIC` confidence tier stays exactly as it is — this adds a file-level fact, it does
  not reinterpret an edge.

## Acceptance criteria

- A T-SQL fixture executing `@sql` stamps `unmodelled_resolution: ["dynamic_sql"]`; a static fixture
  stamps nothing.
- `find_orphans` over the stamped fixture answers `status=resolution_unmodelled`; over the static one
  its payload is unchanged.
- No edge kind, confidence tier or node kind changes.

## References
`adapters/sql/src/scan.js:255`, `:711`, `:720-723`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[184](184_tsql-source-adapter-tier-1a.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 296 — SQL dynamic_sql stamp (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: token `RESOLUTION_DYNAMIC_SQL="dynamic_sql"`; stamp from existing `dynamic||dynamicProc` evidence in EXEC scan — cites ticket Scope bullets 1–3 + scan.js DYNAMIC_PROCS. Move exec_dynamic.sql under unmodelled_resolution/ so tool_parity corpus is not stamped (PHP pattern).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | DYNAMIC known, no stamp | file-level stamp | D2 | AC1 | ✅ |
| C1 | Constraints | R5.6 | stamp only | D2 | AC3 | ✅ |
| C2 | Constraints | R1.1 token | contract | D1 | — | ✅ |
| C3 | Constraints | 061 static identical | static fixture | D2 | AC1 | ✅ |
| C4 | Constraints | edge tiers unchanged | no edge edit | D2 | AC3 | ✅ |
| R1 | Scope | dynamic_sql token | RESOLUTION_DYNAMIC_SQL | D1 | AC1 | ✅ |
| R2 | Scope | existing evidence | DYNAMIC_PROCS + @/( | D2 | AC1 | ✅ |
| R3 | Scope | File.extra merge | fileExtra | D2 | AC1 | ✅ |
| R4 | Scope | fixtures | exec_dynamic + exec_static | D3 | AC1 | ✅ |
| AC1 | AC | stamp vs none | proving | D3 | proving | ✅ |
| AC2 | AC | find_orphans | proving | D3 | proving | ✅ |
| AC3 | AC | no edge/kind change | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: SQL already marks DYNAMIC edges; never stamps File.extra.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.6 (change-type) ✅`

Ran at a350afdbfc74d3d7e6b89bfa9688babf38165d03

```
$ .venv/bin/python -m pytest tests/test_unmodelled_resolution_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 2.10s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: set flag on dynamic/dynamicProc EXEC; File.extra.unmodelled_resolution=["dynamic_sql"]; token + fixtures + proving.
- Rejected: new regex/proc list; changing edge tiers.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_sql_dynamic_sql_unmodelled_stamp.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | RESOLUTION_DYNAMIC_SQL | contract.py | token | 1/1 |
| D2 | stamp from EXEC evidence | adapters/sql/src/scan.js | parse | 1/1 |
| D3 | fixtures + proving + registry path | unmodelled_resolution/ · adapter_registry · proving | — | 1/1 |
| D4 | runbook | docs/runbooks/onboarding-a-repo.md | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/296-sql-dynamic-sql-unmodelled-stamp

**Verification sweep**

Ran at a350afdbfc74d3d7e6b89bfa9688babf38165d03

```
$ .venv/bin/python -m pytest tests/test_sql_dynamic_sql_unmodelled_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.85s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (11 met / 0 not met / 0 can't-tell)
agent dd8cd9b7-15e1-40ed-805d-0750a95d6900

Ran at 512f5261bf4faa7a2875d9422dd414f30b2d1c96

```
$ .venv/bin/python -m pytest tests/test_sql_dynamic_sql_unmodelled_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.82s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

## Phase 5 — Finalise

Outward: push + PR. Never merge.

## Cost ledger

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
