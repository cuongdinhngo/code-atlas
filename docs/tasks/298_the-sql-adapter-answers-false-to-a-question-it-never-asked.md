---
id: 298
slug: the-sql-adapter-answers-false-to-a-question-it-never-asked
title: '262 made `is_test` a read field with the path convention as its fallback, and wrote the fallback to yield to any adapter that emits the flag — but the T-SQL adapter writes `is_test: false` on every node it builds, which is not a decision, so the fallback never runs for SQL and a procedure whose only callers are test scripts is counted as production in the one census 262 exists to provide'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [262, 130, 231]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

262 chose the precedence deliberately: *"the adapter's `is_test` where an adapter emits it; the
existing path convention (130) where it does not"*, implemented as an early `continue` on a present
key (`code_atlas/symbol_role.py:32-36`). That is correct precedence and it assumes a present key means
a decided value.

The SQL adapter hardcodes the field on every node it constructs — `is_test: false` at
`adapters/sql/src/scan.js:327`, `:385`, `:435`, `:660`, `:694`, `:785`. It never reads a path, never
looks for a test convention, and never sets it true. So the key is always present and always false.
Measured against the shipped helper:

```
apply_test_role([{'file_path': 'tests/foo.sql', 'is_test': 0},
                 {'file_path': 'tests/foo.php'}])
-> [{'file_path': 'tests/foo.sql', 'is_test': 0},   # adapter "wins" — stays production
    {'file_path': 'tests/foo.php', 'is_test': 1}]   # path convention fills
```

php, python and typescript emit no `is_test` at all, so all three get 130's path convention and a
`test_role_source` of `path_convention`. SQL is the only adapter that opts out of the fallback, and
it opts out by accident. The consequence is the exact answer 262 was filed to stop: a procedure
called three times, all from test scripts, reports `production_count: 3` — *dead* presented as
*load-bearing*, which is the direction that blocks a deletion rather than permitting a wrong one.

This is the defect class [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md)
removed for the capability handshake — declaring a field the adapter does not fill — arriving through
the node payload instead of the handshake.

## Scope / Deliverables

- **The SQL adapter stops emitting `is_test`** on nodes it does not classify, so 130's path convention
  fills it exactly as it does for the other three adapters. Six sites, one construct.
- **`ADAPTER_PLAYBOOK.md` §3's `is_test` row is corrected** in the same commit: it reads *"skip —
  nothing reads it; `class_diagram.py:253` derives the role from the path"*, which 262 made false.
  The row must say what the field now decides and that emitting a constant is worse than omitting it.
- **A test that pins the rule for any adapter**: a node with no `is_test` under a test path is
  classified; the fallback is not silently defeated by a constant.

## Constraints

- **Do not invert the precedence.** An adapter that genuinely decides the flag must still win; the fix
  is to stop pretending, not to stop trusting (262 / R5.6).
- R2 / R2.2: no test-directory name list enters the SQL adapter. The path convention stays the only
  fallback and stays in the core.
- 061: a schema with no test-path files produces byte-identical payloads and counts.
- `class_diagram.py:279`'s comment ("`is_test` is unused by adapters today") is the same stale claim;
  correct it or point it at `symbol_role`.

## Acceptance criteria

- A SQL fixture under a test path reports `is_test` true with `test_role_source: path_convention`, and
  `find_callers` on a procedure called only from it returns `production_count: 0`.
- No `is_test:` literal remains in `adapters/sql/src/scan.js`.
- The playbook row and the `class_diagram.py` comment no longer state that nothing reads the field.
- 262's existing tests pass unchanged.

## References
`adapters/sql/src/scan.js:327`, `:385`, `:435`, `:660`, `:694`, `:785`,
`code_atlas/symbol_role.py:24-40`, `code_atlas/tools/class_diagram.py:279`,
[`ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §3,
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[130](130_web-entry-bucket-counts-test-controllers.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 298 — SQL omits undecided is_test (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: remove all `is_test: false` from scan.js so path convention fills; correct playbook + class_diagram comment — cites ticket Scope + Constraints (do not invert precedence).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | constant false opts out | omit field | D1 | AC1 | ✅ |
| C1 | Constraints | keep precedence | omit only | D1 | AC1 | ✅ |
| C2 | Constraints | R2 no path list in adapter | core only | D1 | — | ✅ |
| C3 | Constraints | 061 no-test-path identical | omit only | D1 | — | ✅ |
| C4 | Constraints | class_diagram comment | fix stale | D3 | AC3 | ✅ |
| R1 | Scope | stop emitting is_test | scan.js | D1 | AC2 | ✅ |
| R2 | Scope | playbook row | ADAPTER_PLAYBOOK | D2 | AC3 | ✅ |
| R3 | Scope | pin rule for any adapter | proving | D3 | proving | ✅ |
| AC1 | AC | test path + production_count 0 | proving | D3 | proving | ✅ |
| AC2 | AC | no is_test in scan.js | proving | D3 | proving | ✅ |
| AC3 | AC | playbook + comment | docs | D2 | AC3 | ✅ |
| AC4 | AC | 262 tests pass | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: SQL emits is_test:false constantly, defeating path fallback.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.6 (change-type) ✅`

Ran at 8c8d5ab5acd143f178fbd90407b6260dd5711b0d

```
$ .venv/bin/python -m pytest tests/test_sql_omit_is_test_constant.py tests/test_callers_test_role_census.py -q --tb=no
..........                                                               [100%]
10 passed in 1.80s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: delete is_test from all SQL node builds; update playbook + class_diagram docstring; proving tests.
- Rejected: invert precedence; add test-dir list to SQL adapter.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_sql_omit_is_test_constant.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | omit is_test | adapters/sql/src/scan.js | parse nodes | 1/1 |
| D2 | playbook row | docs/ADAPTER_PLAYBOOK.md | docs | 1/1 |
| D3 | comment + proving | class_diagram.py · test_sql_omit_is_test_constant.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/298-sql-omit-is-test-constant

**Verification sweep**

Ran at 8c8d5ab5acd143f178fbd90407b6260dd5711b0d

```
$ .venv/bin/python -m pytest tests/test_sql_omit_is_test_constant.py tests/test_callers_test_role_census.py -q --tb=no
..........                                                               [100%]
10 passed in 1.80s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round-1 NOT CLEAN (AC1); fixed; round-2 CLEAN (4/4 AC met)
agents d84de181-aa12-4ba2-9ebd-441d49b3d5f7 · d907f7ee-6a85-4e29-af16-5d7cc7f9a979

Ran at a5d35df72abe6a4dbdc77e17cb60205205253b35

```
$ .venv/bin/python -m pytest tests/test_sql_omit_is_test_constant.py tests/test_callers_test_role_census.py -q --tb=no
...........                                                              [100%]
11 passed in 0.72s
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
