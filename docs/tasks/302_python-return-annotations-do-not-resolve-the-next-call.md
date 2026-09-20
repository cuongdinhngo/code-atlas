---
id: 302
slug: python-return-annotations-do-not-resolve-the-next-call
title: "Python records a callable's return annotation but drops it before the next member call, leaving factory-result receivers HEURISTIC"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [226, 227]
---

## Why this exists

[226](226_an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links.md)
qualified imported Python types, and [227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md)
used explicit parameter, attribute and constructor bindings to promote 199 calls on pinned `flask`.
The resulting `CALLS` HEURISTIC share is still **82.2%**. Task 227 deliberately excluded receivers
whose type comes from a function's return annotation.

Python already states that fact in source:

```python
def repository() -> UserRepository: ...
repository().save()
```

The adapter reads the annotation and records declared function/method return types, but its local
type table does not carry the returned class onto the call result. This ticket measures and closes
the same-file, explicit-annotation subset without introducing runtime inference or Jedi.

## Scope / Deliverables

1. Extend the committed edge-health reporter with a Python receiver-shape census. Separate
   same-file explicit return annotations from imported callables, unresolved/ambiguous annotations,
   unions, `Any`, unannotated calls and dynamic attribute access.
2. Build a same-file callable-return map from declarations the adapter already walks, using the
   import/FQN rules shipped by 226 for the annotation itself.
3. Cover `x = factory(); x.method()`, `factory().method()` and a same-file method whose declared
   return class is concrete.
4. Promote only calls whose callable target and class-like return annotation are unique and
   indexable. Everything else retains today's bare `HEURISTIC` edge.
5. Measure the before/after HEURISTIC share and promoted-site count on pinned `flask`.

## Constraints

- Standard-library `ast` only: no Jedi, runtime imports, execution, network or third-party
  dependency.
- File-at-a-time remains the adapter contract. Imported callable bodies and whole-program return
  inference are not reconstructed in the core.
- No core language branch, schema change, contract field or `CONTRACT_VERSION` bump.
- `Any`, unions with more than one concrete class, unresolved forward references and unknown
  reassignments are never upgraded to `RESOLVED`.
- Identical input yields identical rows; sample-specific names influence tests and measurement only.

## Acceptance criteria

- **AC1 — evidence gate.** Before implementation, the committed reporter classifies every
  HEURISTIC `CALLS` edge on pinned `flask` and reports a non-zero explicit-return, indexed-target
  ceiling. A zero ceiling closes the ticket with evidence rather than code.
- **AC2 — red first.** A fixture with assigned and direct same-file annotated return receivers is
  bare `HEURISTIC` before the change and qualified `RESOLVED` after it.
- **AC3 — honesty.** Unannotated, `Any`, ambiguous union, external callable and unknown reassignment
  fixtures remain `HEURISTIC`; no guessed qname is emitted.
- **AC4 — measured result.** The promoted count equals the safely classifiable reporter population,
  or every difference is itemised by cause. The pinned `flask` HEURISTIC share does not increase.
- **AC5 — determinism and compatibility.** Two builds produce byte-identical stable rows;
  `code_atlas/`, `contract.py`, `CONTRACT_VERSION` and unaffected Python fixtures remain unchanged.


## Measurement (AC1 evidence gate — 2026-09-20)

Pinned `flask` @ `d318b68` via `scripts/edge_health_report.py --only flask` after the
flow-sensitive Python receiver-shape census landed:

| Metric | Value |
|--------|-------|
| HEURISTIC edges | 2213 / 7300 (30.3%) |
| bare HEURISTIC CALLS | 2213 |
| `identifier_receiver` | 1694 (76.5%) |
| `property_receiver` | 381 (17.2%) |
| `call_unannotated_or_foreign` | 86 (3.9%) |
| `explicit_return_unindexed` | 8 (0.4%) |
| other shapes | 44 |
| **explicit-return, indexed-target ceiling** | **0 / 2213 (ZERO)** |

Per AC1: a zero ceiling closes this ticket with the measurement — **no callable-return map** was
added under `adapters/python/src/parse.py` or `types.py`. The census scores both
`factory().m()` and `x = factory(); x.m()` (assigned form). Eight unindexed explicit returns
are not promote candidates.

**Batch note:** 301 landed the TypeScript census first (#405); this ticket reuses its reporter
scaffolding — `_census_payload` / `_run_census` / `format_receiver_census` are shared, and
`_RECEIVER_CENSUS` names each language's runner as data.

## Out of scope

- Return annotations that can only be discovered by opening an imported callable's declaration.
- Runtime protocols, duck typing, data-flow inference, generic substitution and library stubs.
- Constructor/parameter/property bindings already owned by task 227.

## References

[226](226_an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links.md),
[227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md),
`adapters/python/src/types.py`, `adapters/python/src/parse.py`,
`scripts/edge_health_report.py`, `scripts/cross_repo_samples.json`,
ENGINEERING_RULES R1.1, R2, R3, R4.2, R5.2, R6.3 and R6.5.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 302 — Python return annotations do not resolve the next call (working doc)

- **Ticket:** 302
- **Type:** enhancement (measurement-first; zero-ceiling close)
- **Repo(s):** app (.)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed

## Session status
- **status:** in-progress (autorun)
- **branch:** feat/302-python-return-annotations-do-not-resolve-the-next-call
- **reviewer:** off · **challenger:** on

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
- `adapters/python/src/types.py`, `adapters/python/src/parse.py`, `scripts/edge_health_report.py`, `scripts/cross_repo_samples.json`, `docs/tasks/227_*.md`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket.

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Zero flask ceiling → ship what? | Close without adapter promotion; ship census + measurement (AC1). | ticket AC1 |
| H2 | Census location | `adapters/python/src/receiver_census.py` + reporter wire; stdlib ast only. | ticket Constraints; R1.1 |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | Carry return annotation onto next member call when safe | Measure first; promote only if ceiling > 0 | ticket | D1–D2 | AC1 | ✅ |
| C1 | Constraints | stdlib ast only | census uses ast | Constraints | D1 | review | ✅ |
| C2 | Constraints | File-at-a-time | no whole-program | Constraints | D1 | review | ✅ |
| C3 | Constraints | No core/contract bump | reporter + py helper only | Constraints | D1 | diff | ✅ |
| C4 | Constraints | Any/unions/reassign stay HEURISTIC | N/A — no promote | Constraints | — | AC1 | ✅ |
| C5 | Constraints | Deterministic; sample measures only | flask measures | Constraints | D2 | AC1 | ✅ |
| R1 | Scope | Reporter Python census | shapes + ceiling | Scope 1 | D1 | proving | ✅ |
| R2–R4 | Scope | callable-return map / promote | Deferred by AC1 zero | Scope 2–4 | — | AC1 | ✅ |
| R5 | Scope | Measure flask before/after | Measurement section | Scope 5 | D2 | AC1 | ✅ |
| AC1 | AC | Non-zero ceiling or close with measurement | **ZERO → close** | AC1 | D1–D2 | flask report | ✅ |
| AC2–AC4 | AC | promotion fixtures / counts | N/A under AC1 zero | AC | — | AC1 | ✅ |
| AC5 | AC | core/contract unchanged | no those paths | AC5 | D1 | git diff | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | non-zero or close | flask ceiling **0/2213** | Y | greppable ZERO | — |
| AC2–AC4 | promotion | N/A under AC1 zero | Y | AC1 branch | — |
| AC5 | core unchanged | no code_atlas/contract edits | Y | git diff | — |

---

## Phase 1 — Analysis

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R2 (change-type) ✅ · R6.3 (change-type) ✅ · R7.2 (change-type) ✅`

### BASELINE

Proving suite: `pytest tests/test_edge_health_report.py -q` → 12 passed.

`BASELINE: green`

---

## Phase 2 — Design

**Approach.** Census first (flow-sensitive assigned + direct). Measure flask. Zero ceiling → close without parse/types promotion (AC1). Lesson from 301 challenger: score assigned form from day one.

**Rejected alternatives.** Ship promotion anyway for fixtures — violates AC1. Jedi — Constraints.

### Smallest change-list

| # | Change | File/area | Ph2 | k/N |
|---|--------|-----------|-----|-----|
| D1 | `receiver_census.py` + reporter wire + tests/fixture | adapters/python/src/, scripts/, tests/ | R1,AC1 | 4/11 |
| D2 | Measurement + bookkeeping | ticket, BACKLOG, TOKEN_LEDGER | R5,AC1 | 2/11 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_edge_health_report.py -q`

**SCOPE:** S

---

## Phase 3 — Execute

**Diff ⊆ approved list:** D1 census · D2 measurement/bookkeeping · no parse/types promotion.

**Verification sweep**

`pytest tests/test_edge_health_report.py -q` → 12 passed; `scripts/edge_health_report.py --only flask` → ceiling 0/2213 (ZERO).

---

## Phase 4 — Review

`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent 0eac3691). Gate 4: challenger CLEAN; reviewer waived.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (census + challenger)`

## Phase 5 — Finalise

Outward actions authorised: (1) push feature branch (2) open PR.
