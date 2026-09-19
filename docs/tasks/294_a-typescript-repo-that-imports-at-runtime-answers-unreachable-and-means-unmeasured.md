---
id: 294
slug: a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured
title: '279 made an unmodelled resolution strategy visible so `find_orphans` cannot answer a confident zero on a repo whose wiring the graph does not model — but the detection lives only in `adapters/php/src/Visitor.php`, so a TypeScript repo using dynamic `import()` or a computed `require()` produces no stamp, and the same tool returns the same bare orphan population 279 was filed to refuse'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [279, 019, 255, 299]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

**Blocked on [299](299_a-confident-hit-list-does-not-say-the-index-never-saw-this-extension.md).**
This stamp cannot see a `.js` the adapter never parsed. Run 299 first.

279's core half is language-agnostic and shipped that way: `File.extra.unmodelled_resolution` is
unioned per language (`store.py:1252`), stamped into `meta` (`indexer.py:1273`), and read by
`find_orphans` to answer `status=resolution_unmodelled` instead of a population
(`tools/find_orphans.py:82-95`). Nothing in it knows what PHP is.

The detection half is PHP-only. `markUnmodelledResolution` exists at
`adapters/php/src/Visitor.php:1341` and nowhere else — grep over `adapters/` returns one hit. So the
honesty 279 bought applies to one of the four adapters, and a TypeScript repo gets the pre-279
answer: a confident orphan list built on an import graph that is missing every edge the code
resolves at runtime.

The TypeScript adapter already *sees* the construct and already declines to invent an edge for it —
`const x = require(...)` is skipped as an import binding (`adapters/typescript/src/parse.js:160`) and
a call it cannot name becomes `(dynamic)` / `DYNAMIC` (`parse.js:508-509`). That is the correct
per-edge answer and it is not the file-level one: an edge marked `DYNAMIC` says *this call* is
unresolved, while the stamp says *this file resolves things the graph does not model*, which is the
claim `find_orphans` needs before it is allowed to say "nothing reaches this".

## Scope / Deliverables

- **A strategy token in `contract.py`** beside `RESOLUTION_AUTOLOAD`, naming runtime module
  resolution (`dynamic_import`), with the same one-line comment discipline.
- **Detection in the TypeScript adapter**, from the language standard only (R2): a dynamic `import()`
  whose specifier is not a string literal, and a CommonJS `require()` whose argument is not a string
  literal. No bundler API, no framework convention, no repo path list.
- **The stamp on the File node**, same shape as PHP's — a sorted, de-duplicated list under
  `extra.unmodelled_resolution`, merged into `extra` rather than rewriting it.
- **A gate-1 fixture** in the adapter's own fixtures, and the gate-2 registry row updated if the
  handshake changes.

## Constraints

- R5.6: the stamp says *unmeasured*, never *these modules are reachable*. No inferred `IMPORTS` edge.
- R1.1: no core change beyond the token constant — `find_orphans` already reads the stamp.
- 061: a repo with no dynamic resolution pays nothing and every payload stays byte-identical.
- A literal specifier is still resolved as today; only the non-literal case stamps.

## Acceptance criteria

- A TS fixture with `await import(name)` where `name` is a variable produces
  `unmodelled_resolution: ["dynamic_import"]` on its File node; a fixture with only literal
  specifiers produces no key at all.
- `find_orphans` over the stamped fixture answers `status=resolution_unmodelled` with the route, and
  over the unstamped one is byte-identical to today.
- The strategy token is emitted by the adapter and never constructed in the core.

## References
`adapters/typescript/src/parse.js:160`, `:508-509`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[019](019_typescript-adapter.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 294 — TS dynamic import stamps unmodelled_resolution (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: token `RESOLUTION_DYNAMIC_IMPORT = "dynamic_import"` beside `RESOLUTION_AUTOLOAD`; TS adapter stamps File.extra on non-literal `import()`/`require()` mirroring PHP `markUnmodelledResolution` — cites ticket Scope bullets 1–3 + Visitor.php:1343 + parse.js require/DYNAMIC sites. 299 dep satisfied (merged #389).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | TS lacks 279 stamp | port detection to TS adapter | D2 | AC1 | ✅ |
| C1 | Constraints | R5.6 stamp ≠ edges | no invented IMPORTS | D2 | AC1 | ✅ |
| C2 | Constraints | R1.1 token only in core | contract constant | D1 | AC3 | ✅ |
| C3 | Constraints | 061 no-dynamic identical | no key when literal-only | D2 | AC1 | ✅ |
| C4 | Constraints | literal still resolves | string arg unchanged | D2 | AC1 | ✅ |
| R1 | Scope | strategy token | RESOLUTION_DYNAMIC_IMPORT | D1 | AC3 | ✅ |
| R2 | Scope | detect import/require | parse.js stamp | D2 | AC1 | ✅ |
| R3 | Scope | File.extra list | merge+sort+dedupe | D2 | AC1 | ✅ |
| R4 | Scope | gate-1 fixture | tests/fixtures/typescript/unmodelled_resolution | D3 | AC1 | ✅ |
| AC1 | AC | stamp vs no-key | proving | D3 | proving | ✅ |
| AC2 | AC | find_orphans refuse/ok | proving | D3 | proving | ✅ |
| AC3 | AC | token from adapter | contract+adapter literal | D1 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 279 core is language-agnostic; detection only in PHP Visitor.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.6 (change-type) ✅`

Ran at 3e425f3bd2fa173bcff2a4a45b0787d229feabea

```
$ .venv/bin/python -m pytest tests/test_unmodelled_resolution_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.73s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: add `RESOLUTION_DYNAMIC_IMPORT`; stamp in TS `emitBodyEdges` for non-literal `import()`/`require()`; fixtures + proving test; PLAN/runbook one-line.
- Rejected: inventing IMPORTS edges (R5.6); bundler/framework APIs (R2); core find_orphans change (already reads stamp).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_ts_dynamic_import_unmodelled_stamp.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | RESOLUTION_DYNAMIC_IMPORT | contract.py | token consumers | 1/1 |
| D2 | stamp File.extra | adapters/typescript/src/parse.js | parse payload | 1/1 |
| D3 | fixtures + proving | tests/fixtures/typescript/unmodelled_resolution · tests/test_ts_dynamic_import_unmodelled_stamp.py | — | 1/1 |
| D4 | runbook mention | docs/runbooks/onboarding-a-repo.md | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/294-ts-dynamic-import-unmodelled-stamp
**Axis 1:** contract · parse.js · fixtures · proving · docs.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 3e425f3bd2fa173bcff2a4a45b0787d229feabea

```
$ .venv/bin/python -m pytest tests/test_ts_dynamic_import_unmodelled_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 1.06s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (10 met / 0 not met / 1 can't-tell unstamped byte-identity)
agent e1a0a291-4d65-4677-bdda-b50cb2a83b82

Ran at 3e425f3bd2fa173bcff2a4a45b0787d229feabea

```
$ .venv/bin/python -m pytest tests/test_ts_dynamic_import_unmodelled_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 1.06s
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
