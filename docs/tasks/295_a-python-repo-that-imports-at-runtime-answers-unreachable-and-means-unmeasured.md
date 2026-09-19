---
id: 295
slug: a-python-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured
title: '`importlib.import_module` and `__import__` are the stdlib way a Python codebase loads a module the source never names, and the adapter emits `IMPORTS` from `import` / `from` statements only — so the resolution the graph does not model leaves no trace, no `unmodelled_resolution` stamp is set, and `find_orphans` returns the confident orphan population 279 taught it to refuse'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [279, 020, 255, 299]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

**Blocked on [299](299_a-confident-hit-list-does-not-say-the-index-never-saw-this-extension.md).**
This stamp cannot see an extension the adapter never parsed. Run 299 first.

Same gap as [294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md),
different language standard. 279 shipped the core mechanism language-agnostically — the per-language
union in `store.py:1252`, the `meta` stamp in `indexer.py:1273`, the `resolution_unmodelled` status in
`tools/find_orphans.py:82-95` — and the detection only in `adapters/php/src/Visitor.php:1341`.

The Python adapter emits `IMPORTS` from exactly three sites, all of them `ast.Import` /
`ast.ImportFrom` (`adapters/python/src/parse.py:645`, `:667`, `:672`). `importlib.import_module(name)`
and `__import__(name)` are ordinary calls: they get a `CALLS` edge, `(dynamic)` where the callee
cannot be named (`parse.py:740`), and no import relation at all. That is correct — the adapter must
not invent the edge — and it is invisible, which is the half 279 exists to fix.

The population this matters for is not exotic: plugin registries, entry-point loading, settings
modules named by string, and any `importlib` call in a bootstrap path. On such a repo every
"nothing reaches this" answer is a claim about an import graph that is missing by construction.

## Scope / Deliverables

- **A strategy token in `contract.py`** naming runtime module resolution for Python (reuse
  `dynamic_import` from [294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md)
  if the shape matches; a second token only if the two are genuinely different claims).
- **Detection in the Python adapter**, stdlib only (R2): `importlib.import_module`, `__import__`, and
  `importlib.util.spec_from_file_location`. Not a framework list, not a settings-module convention.
- **The stamp on the File node** — sorted, de-duplicated, merged into `extra`, same shape as PHP's.
- **A gate-1 fixture**, plus the gate-2 registry row if the handshake moves.

## Constraints

- R5.6: unmeasured, never reachable. No inferred `IMPORTS` edge from a call.
- R1.1: no core change beyond the token constant.
- 061: a repo with no runtime import pays nothing; byte-identical payloads.
- A call whose module argument *is* a literal still gets no `IMPORTS` edge in this ticket — modelling
  that resolution is a different ticket, and stamping it is this one.

## Acceptance criteria

- A Python fixture calling `importlib.import_module(name)` stamps `unmodelled_resolution` on its File
  node; a fixture with only statement imports does not.
- `find_orphans` answers `status=resolution_unmodelled` over the stamped fixture and is byte-identical
  over the unstamped one.
- No new `IMPORTS` edge is emitted by this ticket.

## References
`adapters/python/src/parse.py:645`, `:667`, `:672`, `:740`, `adapters/php/src/Visitor.php:1341`,
`code_atlas/contract.py:234-237`, `code_atlas/tools/find_orphans.py:82-95`,
[279](279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md),
[020](020_python-adapter.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 295 — Python importlib stamps unmodelled_resolution (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: reuse `RESOLUTION_DYNAMIC_IMPORT` (same runtime-module-load claim as 294 Scope bullet 1); detect `importlib.import_module`, `__import__`, `importlib.util.spec_from_file_location` — cites ticket Scope + Constraints (stamp even for literal args). 294 PR #395 still open — both branches may introduce the constant.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | Python lacks 279 stamp | port detection | D2 | AC1 | ✅ |
| C1 | Constraints | R5.6 no IMPORTS | stamp only | D2 | AC3 | ✅ |
| C2 | Constraints | R1.1 token only | contract | D1 | — | ✅ |
| C3 | Constraints | 061 no-runtime identical | statement-only | D2 | AC1 | ✅ |
| C4 | Constraints | literal still stamps | any call | D2 | AC1 | ✅ |
| R1 | Scope | reuse dynamic_import | RESOLUTION_DYNAMIC_IMPORT | D1 | AC1 | ✅ |
| R2 | Scope | three stdlib APIs | parse.py | D2 | AC1 | ✅ |
| R3 | Scope | File.extra stamp | merge+sort | D2 | AC1 | ✅ |
| R4 | Scope | gate-1 fixture | fixtures/python/unmodelled_resolution | D3 | AC1 | ✅ |
| AC1 | AC | stamp vs no-key | proving | D3 | proving | ✅ |
| AC2 | AC | find_orphans | proving | D3 | proving | ✅ |
| AC3 | AC | no new IMPORTS | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 279 detection PHP-only; Python runtime imports invisible.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.6 (change-type) ✅`

Ran at ee3e21c740cfb0886ad7681c190f7c9d24d8c5de

```
$ .venv/bin/python -m pytest tests/test_unmodelled_resolution_stamp.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.73s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: reuse `dynamic_import`; stamp on three stdlib call forms; fixtures + proving; runbook note.
- Rejected: inventing IMPORTS for literal args (out of scope); second token (same claim as 294).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_py_dynamic_import_unmodelled_stamp.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | RESOLUTION_DYNAMIC_IMPORT | contract.py | token | 1/1 |
| D2 | stamp on three APIs | adapters/python/src/parse.py | parse | 1/1 |
| D3 | fixtures + proving | tests/fixtures/python/unmodelled_resolution · tests/test_py_dynamic_import_unmodelled_stamp.py | — | 1/1 |
| D4 | runbook | docs/runbooks/onboarding-a-repo.md | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/295-python-dynamic-import-unmodelled-stamp
**Axis 1:** contract · parse.py · fixtures · proving · runbook.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at ee3e21c740cfb0886ad7681c190f7c9d24d8c5de

```
$ .venv/bin/python -m pytest tests/test_py_dynamic_import_unmodelled_stamp.py -q --tb=no
.......                                                                  [100%]
7 passed in 0.74s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (11 met / 0 not met / 0 can't-tell)
agent 96b69985-fa26-45c1-96c8-c65cfeaf0b98

Ran at ee3e21c740cfb0886ad7681c190f7c9d24d8c5de

```
$ .venv/bin/python -m pytest tests/test_py_dynamic_import_unmodelled_stamp.py -q --tb=no
.......                                                                  [100%]
7 passed in 0.74s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

## Phase 5 — Finalise

Outward: push + PR. Never merge. Depends: 294 #395 open (shared token).

## Cost ledger

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
