---
id: 301
slug: typescript-return-types-do-not-resolve-the-next-call
title: "TypeScript reads a callable's return type but drops it before the next member call, leaving fluent and factory-result receivers HEURISTIC"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [153]
---

## Why this exists

[153](153_ts-declared-and-inferred-types.md) added the TypeScript local type table and promoted
225 calls on pinned `ky`, but measured `CALLS` HEURISTIC share still at **54.1%**. Its written
verdict names the dominant residual: the receiver is the return value of a call, so annotations,
constructor bindings and assignments cannot name its class. The adapter already records declared
function and method return types in node `extra.type`; it does not carry that fact from
`makeClient()` to `makeClient().send()` or from `const c = makeClient()` to `c.send()`.

This is a narrower claim than "use the TypeScript checker". Before buying a `ts.Program`, measure
how many residual sites have a same-file callable target with an explicit return type—the subset the
existing file-at-a-time adapter can settle without changing the protocol.

## Scope / Deliverables

1. Extend the committed edge-health reporter with a TypeScript receiver-shape census that separates
   explicit same-file return types from unknown, imported, union/ambiguous and genuinely dynamic
   receivers. The census names the maximum number this ticket can safely promote.
2. Build a same-file callable-return map from declarations the adapter already walks. A call result
   enters the local type table only when its target and single class-like return type are explicit.
3. Cover both forms: `const x = factory(); x.method()` and `factory().method()`, including a
   same-file method returning another class.
4. Promote only those member calls to `<ReturnedClass>::method` at `RESOLVED`. Every missing,
   ambiguous, union, generic-without-a-concrete-binding, external or unindexed target keeps today's
   bare `HEURISTIC` edge.
5. Record the before/after HEURISTIC share and promoted-site count on pinned `ky` using the committed
   reporter.

## Constraints

- File-at-a-time remains the contract. No `ts.Program`, type checker, project lifecycle, second pass
  or new adapter capability.
- No core language branch, contract field, qname change or `CONTRACT_VERSION` bump.
- Return annotations are evidence; inferred library types and runtime values are not.
- Flow is forgetful: assigning an unknown result after a known one must reopen the receiver rather
  than preserve a stale `RESOLVED` target.
- Sample data sets the measured ceiling and validates the result; it never changes adapter semantics
  (R2, R6.3).

## Acceptance criteria

- **AC1 — evidence gate.** Before implementation, the committed reporter classifies every
  HEURISTIC `CALLS` edge on pinned `ky` into a derived receiver-shape cause and reports a non-zero
  explicit-return, indexed-target ceiling. If the ceiling is zero, close this ticket with the
  measurement instead of adding machinery.
- **AC2 — red first.** A fixture with assigned and direct same-file return-value receivers produces
  bare `HEURISTIC` edges before the change and the expected qualified `RESOLVED` edges after it.
- **AC3 — no false promotion.** Fixtures for union, unresolved import, unknown return and reassigned
  receiver remain `HEURISTIC`; none gains a guessed `target_qname`.
- **AC4 — measured result.** The post-change promoted count equals the reporter's safely
  classifiable population, or every difference is itemised by cause. The `ky` HEURISTIC share does
  not increase.
- **AC5 — boundary stability.** `code_atlas/`, `contract.py`, `CONTRACT_VERSION` and existing
  unaffected TypeScript fixture rows remain byte-identical.


## Measurement (AC1 evidence gate — 2026-09-20)

Pinned `ky` @ `0bda554` via `scripts/edge_health_report.py --only ky` after the receiver-shape
census landed:

| Metric | Value |
|--------|-------|
| HEURISTIC edges | 4170 / 7960 (52.4%) |
| bare HEURISTIC CALLS | 4170 |
| `identifier_receiver` | 3386 (81.2%) |
| `call_imported_or_unknown_method` | 343 (8.2%) |
| `call_imported_or_unindexed_callee` | 244 (5.9%) |
| `property_receiver` | 130 (3.1%) |
| `explicit_return_unindexed` | 2 (0.0%) |
| other shapes | 65 |
| **explicit-return, indexed-target ceiling** | **0 / 4170 (ZERO)** |

The census is flow-sensitive: both `factory().m()` and `const x = factory(); x.m()` score
toward the ceiling when the callable's return is an explicit same-file class-like type (challenger
finding on the first census draft). The two `explicit_return_unindexed` sites name a return type
the index does not hold as Class/Interface+method, so they are not promote candidates.

Per AC1: a zero ceiling closes this ticket with the measurement — **no callable-return map and no
promotion machinery** were added under `adapters/typescript/src/parse.js` or `types.js`. The
committed reporter now prints the census so a later sample can re-open the claim if the ceiling
moves.

## Out of scope

- Return types available only from an imported declaration, `.d.ts`, conditional/generic
  instantiation or whole-program inference.
- Expanding `semantic_types`; task 153 already announces it.
- Deeper JavaScript/JSDoc inference beyond return declarations already captured by the adapter.

## References

[153](153_ts-declared-and-inferred-types.md), [137](137_php-local-type-table.md),
`adapters/typescript/src/types.js`, `scripts/edge_health_report.py`,
`scripts/cross_repo_samples.json`, ENGINEERING_RULES R1.1, R2, R3, R5.2, R6.3 and R6.5.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 301 — TypeScript return types do not resolve the next call (working doc)

- **Ticket:** 301
- **Type:** enhancement (measurement-first; zero-ceiling close)
- **Repo(s) / Porting:** app (.)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed · path: `docs/tasks/301_typescript-return-types-do-not-resolve-the-next-call.md`

## Session status
- **status:** in-progress (autorun)
- **branch:** feat/301-typescript-return-types-do-not-resolve-the-next-call
- **reviewer:** off · **challenger:** on

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
- checked existing: `adapters/typescript/src/types.js`, `adapters/typescript/src/parse.js`, `scripts/edge_health_report.py`, `scripts/cross_repo_samples.json`, `docs/tasks/153_ts-declared-and-inferred-types.md`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket.

**Settled wants:** none.

**Resolved direction + citation (how-decision):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | If pinned `ky` explicit-return indexed ceiling is zero, ship what? | Close without adapter promotion machinery; ship the census + recorded measurement only (AC1). | ticket AC1 L52–55 |
| H2 | Where does the TS receiver-shape census live? | Committed reporter calls a file-at-a-time node helper under `adapters/typescript/src/receiver_census.js` (AST via adapter's `typescript`); not a core language branch. | ticket Scope L26–28; R1.1 (`scripts/` + adapter helper, not `code_atlas/`) |

**ASSUMED:** none.

**Constraints from scan:** R1.1, R2, R3, R5.2, R6.3, R6.5; no `CONTRACT_VERSION` bump; file-at-a-time.

**Exposure-checker:** no further WANT; H1–H2 exhaust forks that would block autorun.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | Carry return type from callable to next member call when safe | Same-file explicit return → RESOLVED, else measure | ticket L11–22 | D1–D2 | AC1 | ✅ |
| C1 | Constraints | File-at-a-time; no ts.Program | Census + any future map stay one-file | L41–42 | D1 | review | ✅ |
| C2 | Constraints | No core language branch / contract bump | Touch reporter + TS helper only | L43 | D1 | diff ⊆ | ✅ |
| C3 | Constraints | Return annotations are evidence; inferred not | Census keys explicit annotations only | L44 | D1 | census | ✅ |
| C4 | Constraints | Flow forgetful | N/A — no promotion map shipped | L45–46 | — | AC1 zero | ✅ |
| C5 | Constraints | Sample sets ceiling; never changes semantics (R2) | ky measures; fixture only tests census | L47–48 | D1–D2 | AC1 | ✅ |
| R1 | Scope | Extend reporter with TS receiver-shape census | shapes + ceiling line | L26–28 | D1 | proving | ✅ |
| R2 | Scope | Build same-file callable-return map | **Deferred by AC1 zero ceiling** | L29–30 | — | AC1 | ✅ |
| R3 | Scope | Cover assigned + direct forms | Deferred by AC1 | L31–32 | — | AC1 | ✅ |
| R4 | Scope | Promote only safe subset | Deferred by AC1 | L33–35 | — | AC1 | ✅ |
| R5 | Scope | Record before/after on ky | Measurement section; after = no adapter change | L36–37 | D2 | AC1 | ✅ |
| AC1 | AC | Non-zero ceiling or close with measurement | **ZERO → close with measurement** | L52–55 | D1–D2 | ky report | ✅ |
| AC2 | AC | Red-first fixture promotion | N/A — no promotion machinery | L56–57 | — | AC1 | ✅ |
| AC3 | AC | No false promotion fixtures | N/A — no promotion machinery | L58–59 | — | AC1 | ✅ |
| AC4 | AC | Promoted count equals population | N/A — population 0 | L60–62 | — | AC1 | ✅ |
| AC5 | AC | code_atlas/ contract unchanged | Diff excludes them | L63–64 | D1 | git diff | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | non-zero ceiling or close with measurement | ky census ceiling **0/4170** | Y | greppable ZERO line + Measurement section | — |
| AC2 | red-first promotion | N/A under AC1 zero path | Y | AC1 branch | — |
| AC3 | no false promotion | N/A under AC1 zero path | Y | AC1 branch | — |
| AC4 | promoted == population | population 0; no promote | Y | ceiling 0 | — |
| AC5 | core/contract byte-identical | `git diff main -- code_atlas/ contract` empty of those paths | Y | git diff | — |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
- Q1→H1, Q2→H2

---

## Phase 1 — Analysis

- Root question: can a same-file return-type table move residual HEURISTIC CALLS on ky?
- Evidence: receiver-shape census → ceiling 0; residual is identifier/imported receivers, not explicit same-file returns used as call receivers.
- depends_on: 153 done.
- TRACK: backend · SCOPE: S · TIER: full

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ no code_atlas/ language branch · R2 (change-type) ✅ sample measures only · R6.3 (change-type) ✅ pinned ky · R7.2 (change-type) ✅ TOKEN_LEDGER row`

### BASELINE

Proving suite: `pytest tests/test_edge_health_report.py -q` → 13 passed (re-run on tip before PR; no `$` fence — avoids self-referential Ran-at).

`BASELINE: green`

---

## Phase 2 — Design

**Approach.** Implement the TS receiver-shape census in the committed reporter first (AC1). Measure pinned ky. If the explicit-return indexed ceiling is zero, stop — record measurement, do not add parse/types promotion machinery (ticket AC1).

**Rejected alternatives.**
- Ship the callable-return map anyway "for fixtures" — violates AC1 close-without-machinery.
- Buy a `ts.Program` to recover imported returns — out of scope / Constraints.
- Fold census shapes into the PHP-oriented CAUSES taxonomy — would break `check()`; census is additive.

**Assumptions.**
- `node` + adapter `typescript` package available when running TS samples — verified (existing adapter tests). Tag: verified.
- Zero ceiling on ky is stable at pin 0bda554 — novel until report runs; proving re-runs report. Tag: novel-untested → Gate-2 proving covers it.

### Smallest change-list

| # | Change | File/area | Blast radius | Ph2 | k/N |
|---|--------|-----------|--------------|-----|-----|
| D1 | Add `receiver_census.js` + wire `edge_health_report.py` TS section | `adapters/typescript/src/receiver_census.js`, `scripts/edge_health_report.py`, `tests/test_edge_health_report.py`, fixture | reporter + TS helper only | R1,AC1,C1–C3,C5 | 5/16 |
| D2 | Record ky measurement; mark done; no parse/types change | ticket Measurement, BACKLOG, TOKEN_LEDGER | docs | R5,AC1,AC5 | 3/16 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | Layer | How proven | ❌? |
|----|-------|------------|-----|
| AC1 | integration | `edge_health_report.py --only ky` prints ZERO ceiling | — |
| AC2–AC4 | N/A | AC1 zero path | — |
| AC5 | review | no `code_atlas/` / `contract.py` edits | — |
| D1 | unit | `tests/test_edge_health_report.py` | — |

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_edge_health_report.py -q`

**SCOPE:** S

---

## Phase 3 — Execute

**Branch:** feat/301-typescript-return-types-do-not-resolve-the-next-call

**Diff ⊆ approved list:** D1 census + tests · D2 measurement/bookkeeping · no adapter parse/types promotion.

**Verification sweep**

`pytest tests/test_edge_health_report.py -q` → 13 passed; `scripts/edge_health_report.py --only ky` → explicit-return indexed ceiling 0/4170 (ZERO).

Design-conformance: AC1 zero path taken; core untouched.

---

## Phase 4 — Review

`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round 1 NOT CLEAN (agent e364682d): ceiling omitted assigned-form receivers.
Fix: flow-sensitive locals in `receiver_census.js` score `const x = factory(); x.m()`. Re-measured
ky: ceiling still **0/4170** indexed (2 explicit_return_unindexed). Round 2 CLEAN (agent d116fbf3).

Gate 4: challenger CLEAN; reviewer waived.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (census + challenger rounds)`

## Phase 5 — Finalise

Outward actions authorised: (1) push feature branch (2) open PR.
Deferred: merge, force-push, deploy, tracker transitions beyond PR create.
