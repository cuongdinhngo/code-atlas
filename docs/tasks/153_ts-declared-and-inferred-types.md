---
id: 153
slug: ts-declared-and-inferred-types
title: The TS adapter announces no `semantic_types` — inferred receivers need 137's type table, not a tsc Program
phase: 2
milestone: M7
status: done
depends_on: [019, 151, 137]
---

## Why this exists

`semantic_types` is the one entry in `contract.KNOWN_CAPABILITIES` (`code_atlas/contract.py:156`) and
the TS adapter announces `capabilities: {}` (`adapters/typescript/index.js` META). Declared types
already ride on a node's `extra.type` (019), so what is missing is exactly the **inferred** half: the
class an expression evaluates to, so `obj.method()` can resolve to `<Class>::method` instead of a bare
name.

019 settled that this needs **no** protocol change and no tsc `Program`. Task 019's finding #4 is the
route: [137](137_php-local-type-table.md) shipped that machinery for PHP — `TypeTable.php`,
`MemberTypes.php`, `TypeName.php` — per-function local variable types plus the class an expression
evaluates to, syntactic and file-at-a-time. A TS equivalent is a port of a proven shape, and PLAN §4.4's
`open_project`/two-pass options stay unneeded (019 resolved that gate; the one-program-per-worker cost
in 019's finding #5 is what made them expensive anyway).

**Sequencing.** [151](151_ts-member-calls-emit-no-edge.md) must land first: today `obj.method()` emits
*nothing*, so there is no edge for a type table to upgrade. 151 makes the edge exist at `HEURISTIC`;
this ticket promotes it to `RESOLVED`.

## Scope / Deliverables

- A TS/JS local type table in 137's shape: `const x = new Foo()`, an annotated parameter/property, a
  `let` narrowed by assignment — the syntactic cases, no checker.
- Promote a member call whose receiver the table names to `<Class>::method`, leaving the rest at the
  tier 151 set. The **measured HEURISTIC share** before and after is the deliverable, as 137 did.
- Announce `semantic_types` in the handshake once — and only once — the table actually backs it, with
  the core's meaning of the capability unchanged (R1.6: data the adapter announces, no core branch).
- A written verdict on the tsc-checker question: whether anything real still wants a `Program`, given
  019's answer and this table.

## Acceptance criteria

1. A named target HEURISTIC share on a pinned TS sample, met and reported by a committed reporter, in
   the shape 137 used (R6.3's reporter half) — not a session number.
2. `semantic_types` is announced only when the table is in place, and the core still has zero language
   branches (R1.1, CI-gated).
3. No `contract_version` bump. If one turns out to be needed, that reopens §4.4 and is a finding, not
   a quiet edit (R3).
4. Red run recorded per new guard (R6.5).

## Out of scope

- Cross-file type flow (a type that only a whole-program view could know). File-at-a-time is the
  contract; anything beyond it is a finding to write down, not to build here.
- `allowJs`/JSDoc as a *type source* — [154](154_ts-allowjs-and-jsdoc-types.md).

## References

PLAN §4.4, §8.2; `code_atlas/contract.py:156`; `adapters/php/src/TypeTable.php`; ENGINEERING_RULES
R1.1, R1.6, R3, R6.3, R6.5; tasks 137, 019, 151.

---

## Session status

- **KEY:** 153 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** the TS adapter announced `capabilities: {}` and every member call was bare/HEURISTIC; delta-green + the HEURISTIC-share measurement via Docker (node adapter + resolver + `fcntl`).

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

References resolve: `contract.py:156` (`KNOWN_CAPABILITIES = ("semantic_types",)`), `TypeTable.php` (137's shape to port), PLAN §4.4/§8.2. The one open question — does anything still want a tsc `Program`? — is the ticket's own "written verdict"; resolved as a HOW by 019's finding + this table (verdict below), not a want-decision.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** L · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ · §R1.6 (change-type) ✅ · §R3 (change-type) ✅ · §R6.3 (change-type) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — no member call resolves via a receiver type today; the RESOLVED promotion test is the guard. Delta-green + committed HEURISTIC-share reporter via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | announce `semantic_types`: infer the class an expression evaluates to | A local type table promotes `obj.method()` to `<Class>::method` | open |
| R1 | Scope 1 | TS/JS local type table in 137's shape (new / annotation / let-assignment) | `src/types.js` + flow-sensitive threading in `parse.js` | open |
| R2 | Scope 2 | promote a typed-receiver member call to `<Class>::method`; measure HEURISTIC share | RESOLVED emission + committed reporter, before/after | open |
| R3 | Scope 3 | announce `semantic_types` only once the table backs it (R1.6, no core branch) | META capability; core untouched (R1.1) | open |
| R4 | Scope 4 | a written tsc-checker verdict | README: no `Program` needed; the residual is a file-at-a-time limit | open |
| AC1 | AC1 | named HEURISTIC-share target on a pinned sample via a committed reporter | Falsifiable: `edge_health_report --only ky` before/after | open |
| AC2 | AC2 | `semantic_types` announced only with the table; core zero language branches (R1.1) | Falsifiable: handshake test + R1.1 grep-gate | open |
| AC3 | AC3 | no `contract_version` bump (else reopens §4.4, a finding) | Falsifiable: no contract.py change | open |
| AC4 | AC4 | red run per guard (R6.5) | Falsifiable: recorded red-run | open |
| C1 | Out-of-scope | no cross-file / whole-program type flow | boundary — a finding to write, not build | binding |
| C2 | Out-of-scope | no `allowJs`/JSDoc type source (154) | boundary | binding |

### AC validation

All four ACs falsifiable (reporter before/after, handshake test, no-contract-change, recorded red-run). No want-decision. The tsc-`Program` question is a HOW settled by evidence (019 + the measured residual), not a user choice. **No `contract_version` bump was needed (AC3) — `semantic_types` was already a `KNOWN_CAPABILITY`; the adapter simply announces it now.**

### Root cause (taxonomy: logic)

The TS adapter emitted every member call at the bare method name (HEURISTIC, task 151) because it never inferred the receiver's class. `semantic_types` — the one `KNOWN_CAPABILITY` — was announced by no TS handshake. 137 shipped the PHP machinery (a syntactic per-function type table); the TS side was the missing port.

### Blast radius

`adapters/typescript/src/types.js` (new — the table), `src/parse.js` (thread `locals`/`selfProps`, seed at callable/class boundaries, promote the member call), `index.js` (announce the capability), `README.md`, `scripts/edge_health_report.py` (language-aware + `--only`), new fixture `resolve/typed.ts`, new test `test_ts_semantic_types.py`. No `code_atlas/`, no `contract.py` (AC3), no store.

## Phase 2 — design

### Approach

`src/types.js` provides pure helpers (`typeRefName`, `newExprClass`, `boundClass`, `paramTypeMap`,
`classPropTypeMap`). `parse.js`'s `walk` threads a mutable `locals` (Map var→class) and `selfProps`
(Map property→class); a function/method/constructor seeds fresh `locals` from its typed parameters,
an arrow/function expression inherits the enclosing scope's and adds its own, and a class seeds
`selfProps`. A `const/let x` binds from an annotation or an inferred `new Foo()`; an assignment
`x = new Foo()` re-binds and any other RHS **forgets** (flow-sensitive, per 137). At a member call
`recv.method()`, `receiverClass` reads `locals` (a bare `recv`) or `selfProps` (`this.prop`); when it
names a class, the edge is `member(resolve(cls), method)` with **no HEURISTIC cap**, so the core links
it RESOLVED. Everything else stays the tier-151 set.

`index.js` announces `capabilities: { semantic_types: true }` (R1.6 — announced data; the core reads
capabilities, it does not branch on the language, R1.1). No `contract_version` bump — the capability
was already known (AC3).

**Measurement (AC1, R6.3's reporter half).** `scripts/edge_health_report.py` (137's committed reporter)
is made language-aware (`index_root(language=…)`) with an `--only <id>` filter, and run on a pinned TS
sample before/after.

### The tsc-checker verdict (R4)

**No `ts.Program`/checker is warranted.** The receiver classes the graph can act on are the ones the
language spec writes into the file — `new`, annotations, assignments — which a syntactic pass reads
directly. What a checker would additionally give is the **return type of a call** (fluent `a().b()`
chains) and cross-file/whole-program type flow; those are the file-at-a-time limit (C1), the residual
the measured HEURISTIC share still carries — a candidate for its own ticket if a field round demands
it, not a reason to pay the one-`Program`-per-worker cost 019's finding #5 priced out. Recorded in the
README.

### Rejected alternatives

- **A `ts.Program` / type checker** — 019 already priced this out (finding #5: one program per fanned-out worker); the table reaches the spec-in-the-file cases without it. Rejected; verdict recorded.
- **A stateless per-call inference** — would re-walk the enclosing body per call (O(n²)); the threaded, flow-sensitive table is one pass.
- **Promote return-type-of-call chains now (137's `TYPE_OF`/`MemberTypes`)** — needs a same-file method-return-type map and a walk bound; larger, and its share is the documented residual. Deferred as a possible follow-up, not built here.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration + measurement | `edge_health_report --only ky` before/after (committed reporter) | ✅ |
| AC2 | integration + guard | `test_adapter_announces_semantic_types` + R1.1 grep-gate | ✅ |
| AC3 | logic | no `contract.py`/`contract_version` change in the diff | ✅ |
| AC4 | validation | recorded red-run (promotion disabled → the RESOLVED test fails) | ✅ |

### Proving test

`test_local_type_table_promotes_member_call_to_resolved` in `tests/test_ts_semantic_types.py`:
`const u = new User(); u.greet()` full-builds to a `CALLS` edge `src/typed.ts::build → src/models.ts::User::greet`
at RESOLVED (not the bare `greet`). Plus `test_adapter_announces_semantic_types` (handshake). Fails
pre-change (bare HEURISTIC) and — AC4 — if the promotion is disabled. Invocation:
`pytest tests/test_ts_semantic_types.py -q` (Docker: node adapter + resolver).

### SCOPE

`SCOPE: L` — a new type-table module, flow-sensitive threading through the whole `walk`, a capability announcement, a reporter change, fixtures/tests, README. No core, no contract (AC3). Branch `feat`.

## Phase 3 — execute

**Branch:** `feat/153-ts-type-table`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `src/types.js` helpers; `locals`/`selfProps` threaded, seeded at callable/class boundaries | implemented-as-approved |
| flow-sensitive/forgetful binding (new / annotation / param / property / let-assignment) | implemented-as-approved |
| typed-receiver member call → `<Class>::method` RESOLVED; rest stay tier-151 | implemented-as-approved |
| `semantic_types` announced; no contract bump; core untouched | implemented-as-approved |
| tsc-checker verdict + type table documented in README | implemented-as-approved |
| `edge_health_report` language-aware + `--only`; before/after measured | implemented-as-approved |

No deviations. `SCOPE: L` held.

### Verification sweep (Axis 1)

Diff = `adapters/typescript/src/{types.js,parse.js}`, `adapters/typescript/index.js`,
`adapters/typescript/README.md`, `scripts/edge_health_report.py`,
`tests/fixtures/typescript/resolve/typed.ts` (new), `tests/test_ts_semantic_types.py` (new),
`docs/tasks/153_*.md`, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`. No `code_atlas/`, no `contract.py`.

### Empirical outputs

Adapter promotion (adapter `--file`): `const local = new Foo(); local.m()` → `::Foo::m` RESOLVED;
typed param `p:Bar` → `::Bar::q`; `this.dep:Foo` → `::Foo::n`; `let v = new Foo(); v.m()` → `::Foo::m`,
then `v = makeSomething(); v.m()` → bare `m` HEURISTIC (forgetful); `unknown.z()` → HEURISTIC.

HEURISTIC share on pinned sample `ky` (committed reporter, AC1):
```
before (promotion off): all edges=7781  HEURISTIC=4434 (57.0%)  unknown_receiver=4424
after  (promotion on) : all edges=7777  HEURISTIC=4209 (54.1%)  unknown_receiver=4199
```
225 member calls promoted HEURISTIC→RESOLVED (57.0% → 54.1%). The residual is dominated by
return-type-of-call (fluent-chain) receivers — the file-at-a-time limit the verdict names, not a
checker gap.

AC4 red-run — promotion disabled (`receiverClass` forced null):
```
test_local_type_table_promotes_member_call_to_resolved FAILED — target_raw is bare `greet`, not RESOLVED
```
parse.js restored byte-identical (grep `const cls = receiverClass` = 1).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `edge_health_report --only ky` before/after (57.0% → 54.1%, 225 promoted) |
| AC2 | `test_adapter_announces_semantic_types` + the R1.1 grep-gate (core untouched) |
| AC3 | no `contract.py`/`contract_version` in the diff |
| AC4 | recorded red-run (promotion disabled → the RESOLVED test fails) |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

Porting a proven PHP shape (137's TypeTable) to TS produced no new durable lesson of its own; the residual-share finding is recorded in the README as the tsc-checker verdict.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: tsc gate green, promotion + handshake tests green in Docker, HEURISTIC-share measured (committed reporter), AC4 red-run recorded, no contract change, parse.js restored. Maintainer reviews on the PR.
