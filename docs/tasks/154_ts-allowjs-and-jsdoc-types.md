---
id: 154
slug: ts-allowjs-and-jsdoc-types
title: '`allowJs` breadth and JSDoc as a type source — the `.js` half of the adapter is parsed but never typed'
phase: 2
milestone: M7
status: done
depends_on: [019, 153]
---

## Why this exists

The adapter already accepts `.js/.jsx/.mjs/.cjs` (`index.js` META `extensions`) and picks the right
`ScriptKind` (`parse.js` `scriptKindFor`), so plain JS parses today. What it cannot do is *type* it:
a JS file carries its types in **JSDoc**, and nothing reads them — so a JS-heavy repo gets structure
with none of the type facts a `.ts` file contributes to `extra.type` or, after
[153](153_ts-declared-and-inferred-types.md), to receiver resolution.

`ts.createSourceFile` keeps JSDoc on the AST (`node.jsDoc`), so this stays syntactic — no
`Program`, no checker, consistent with 019's verdict.

## Scope / Deliverables

- `@param` / `@returns` / `@type` / `@typedef` read into the same `extra.type` slot a TS annotation
  fills, so a consumer sees one field regardless of language flavour.
- `@typedef`/`@callback` as declarations: which contract kind they map to (`Interface` is the likely
  answer, matching how a `type` alias is treated) — decided in design, justified by the spec.
- Feed the type table from 153 with JSDoc-declared types, so a JS receiver resolves the same way a TS
  one does.
- Fixtures for a JSDoc-typed `.js` module, `.mjs`/`.cjs`, and `.jsx`; each earns an R6.2 inventory
  entry or an explicit note that it is a flavour of an existing case, not a new construct.

## Acceptance criteria

1. A JSDoc-typed `.js` file yields the same `extra.type` facts an equivalent `.ts` file does.
2. Where 153's table is in place, a JSDoc-typed receiver resolves at the same tier a TS one does.
3. R6.2's named inventory covers whatever new cases this adds — the rulebook list and the registry
   case keys stay equal (that equality is already tested).
4. Red run recorded (R6.5).

## Out of scope

- Type-checking JS. Reading a declared type is not verifying it.
- `checkJs` as a *static-analysis gate on the adapter's own source* — that is
  [150](150_ts-adapter-has-no-gate-but-its-own-fixtures.md).

## References

`adapters/typescript/index.js`, `src/parse.js` `scriptKindFor`; ENGINEERING_RULES R6.2, R6.5; tasks
019, 153.

---

## Session status

- **KEY:** 154 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** a `.js` file parsed for structure but carried no type facts (JSDoc unread); delta-green via Docker (node adapter + `fcntl`).

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

References resolve: `index.js` META `extensions` (accepts `.js/.jsx/.mjs/.cjs`), `parse.js scriptKindFor`. The one open decision — which contract kind `@typedef`/`@callback` map to — is the ticket's own "decided in design"; resolved as a HOW: `Interface` (marked `type_alias`), matching how a `type` alias is already treated. Not a want-decision.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** M · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R6.2 (change-type) ✅ · §R6.5 (change-type) ✅ · §R1.1 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — no JSDoc type is read today; the jsdoc-types conformance case + the extra.type/receiver test are the guards. Delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | a JS file carries types in JSDoc, and nothing reads them | Read JSDoc into `extra.type` + 153's table | open |
| R1 | Scope 1 | `@param`/`@returns`/`@type`/`@typedef` → the same `extra.type` slot | `typeTextOf` reads JSDoc when no TS annotation | open |
| R2 | Scope 2 | `@typedef`/`@callback` as declarations → a contract kind | `Interface` (marked `type_alias`), like a `type` alias | open |
| R3 | Scope 3 | feed 153's table with JSDoc types → a JS receiver resolves | `typeNodeOf` falls back to `ts.getJSDocType` | open |
| R4 | Scope 4 | fixtures for JSDoc `.js`, `.mjs`/`.cjs`, `.jsx`; R6.2 entry or flavour note | one `jsdoc-types` case (.js); flavours noted + tested | open |
| AC1 | AC1 | a JSDoc-typed `.js` yields the same `extra.type` facts a `.ts` does | Falsifiable: `run` node `extra.type == "Service"` | open |
| AC2 | AC2 | a JSDoc-typed receiver resolves at the same tier a TS one does | Falsifiable: `svc.handle()` → Service::handle RESOLVED | open |
| AC3 | AC3 | R6.2 inventory covers new cases; list == registry keys | Falsifiable: `jsdoc-types` in both; set-equality test | open |
| AC4 | AC4 | red run recorded (R6.5) | Falsifiable: recorded red-run | open |
| C1 | Out-of-scope | no type-checking JS (reading ≠ verifying) | boundary | binding |
| C2 | Out-of-scope | `checkJs` gate on the adapter's own source is 150 | boundary — README note corrected | binding |

### AC validation

All four ACs falsifiable (extra.type value, RESOLVED tier, set-equality, recorded red-run). The `@typedef`→`Interface` decision is a HOW cited to the existing `type`-alias treatment, not a want-decision. No `contract_version` change (an Interface node + `extra.type` are existing vocabulary).

### Root cause (taxonomy: logic)

`typeTextOf`/the 153 type table read only `node.type` (a TS annotation). A `.js` file's types live in JSDoc (`node.jsDoc`), which `ts.createSourceFile` keeps on the AST but the adapter never consulted — so a JS-heavy repo got structure with no type facts and no receiver resolution.

### Blast radius

`adapters/typescript/src/types.js` (`typeNodeOf` JSDoc fallback), `src/parse.js` (`typeTextOf` JSDoc + `emitJsDocDeclarations` for `@typedef`/`@callback`), `README.md` (+ the 150 `noImplicitAny` note corrected), new fixture `jsdoc_types.js`, `tests/contract/adapter_registry.py` (the `jsdoc-types` case), `docs/ENGINEERING_RULES.md` (R6.2 list), `docs/tasks/149` (inventory + count 14→15), new test `test_ts_jsdoc_types.py`. No `code_atlas/`, no contract.

## Phase 2 — design

### Approach

JSDoc rides the AST (`node.jsDoc`), so this stays syntactic — no `Program` (019's verdict, confirmed
by 153). `types.js` gains `typeNodeOf(node) = node.type || ts.getJSDocType(node)`, used by
`paramTypeMap`/`classPropTypeMap`/`boundClass`, so a `@param {Foo}` / `@type {Foo}` types the receiver
exactly as a TS annotation does (feeds 153's table → RESOLVED). `typeTextOf` gains the same fallback
plus `ts.getJSDocReturnType`, so `@returns`/`@param`/`@type` fill `extra.type` (AC1). `@typedef` /
`@callback` tags (scanned off each node's `.jsDoc[].tags`) emit an `Interface` node marked
`type_alias` — the `.js` analogue of a `type` alias (the design decision, R2). The `.mjs`/`.cjs`/`.jsx`
flavours are the same construct at a different `ScriptKind`, so the R6.2 inventory carries one
`jsdoc-types` entry and the flavours are covered by a test, not new cases (R4/AC3).

### Rejected alternatives

- **A `ts.Program`/checker to read JS types** — unnecessary (JSDoc is on the syntactic AST) and priced out by 019 finding #5. Not used.
- **`@typedef` → a new contract node kind** — the contract already has `Interface`, and a `type` alias is treated as one; a typedef is the same shape. No `contract_version` bump (R3).
- **A separate R6.2 case per `.mjs`/`.cjs`/`.jsx`** — they are the same construct at a different ScriptKind, not new constructs; one `jsdoc-types` case + a flavours test, noted in the README (R6.2's "flavour" allowance).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | logic | `test_jsdoc_fills_extra_type_and_resolves_the_receiver` (`extra.type == "Service"`) | ✅ |
| AC2 | logic | same test — `svc.handle()` → Service::handle RESOLVED; `jsdoc-types` conformance CALLS shape | ✅ |
| AC3 | validation | `jsdoc-types` in `TS_R62_CASES`/`TS_CASES`; inventory-is-named-set test | ✅ |
| AC4 | validation | recorded red-run (JSDoc source disabled → the receiver tests fail) | ✅ |

### Proving test

`test_jsdoc_fills_extra_type_and_resolves_the_receiver` (`extra.type` + RESOLVED receiver on
`jsdoc_types.js`) + `test_jsdoc_types_resolve_across_js_flavours` (`.mjs`/`.cjs`/`.jsx`) +
`test_adapter_conforms[typescript:jsdoc-types]`. Fail pre-change (JSDoc unread) and — AC4 — if the
JSDoc type source is disabled. Invocation: `pytest tests/test_ts_jsdoc_types.py -q` (Docker: node).

### Known limit (recorded)

An *inline* class-field JSDoc (`/** @type {Foo} */ field`) is not attached to the field node by
`ts.getJSDocType` in JS mode, so that one placement is not typed. Recorded in the README; a
`@param`/`@returns`/`@type`-on-a-variable is typed. Reading a type is not verifying it (C1).

### SCOPE

`SCOPE: M` — a JSDoc fallback in two type readers, a typedef emitter, one conformance case + fixture, tests, doc updates. No core, no contract. Branch `feat`.

## Phase 3 — execute

**Branch:** `feat/154-allowjs-jsdoc-types`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `typeNodeOf` JSDoc fallback feeds `paramTypeMap`/`classPropTypeMap`/`boundClass` | implemented-as-approved |
| `typeTextOf` reads `@type`/`@param`/`@returns` into `extra.type` | implemented-as-approved |
| `@typedef`/`@callback` → `Interface` (`type_alias`) via `emitJsDocDeclarations` | implemented-as-approved |
| one `jsdoc-types` R6.2 case; `.mjs`/`.cjs`/`.jsx` flavours tested + noted | implemented-as-approved |
| README JSDoc section + corrected 150 `noImplicitAny` note | implemented-as-approved |

No deviations. `SCOPE: M` held.

### Verification sweep (Axis 1)

Diff = `adapters/typescript/src/{types.js,parse.js}`, `adapters/typescript/README.md`,
`tests/fixtures/typescript/jsdoc_types.js` (new), `tests/contract/adapter_registry.py`,
`tests/test_ts_jsdoc_types.py` (new), `docs/ENGINEERING_RULES.md`, `docs/tasks/{149,154}_*.md`,
`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`. No `code_atlas/`, no contract.

### Empirical outputs

Adapter `--file` on a JSDoc `.js`: `@typedef Point` → `Interface Point`; `function build`
`@returns {Foo}` → `extra.type = "Foo"`; `@param {Foo} p` → `p.m()` = `<file>::Foo::m` RESOLVED;
`const local = new Foo(); local.m()` → RESOLVED. `.mjs`/`.cjs`/`.jsx` behave the same.

AC4 red-run — JSDoc type source disabled (`typeNodeOf` ignores `getJSDocType`):
```
test_jsdoc_fills_extra_type_and_resolves_the_receiver FAILED (svc.handle no longer RESOLVED)
test_jsdoc_types_resolve_across_js_flavours FAILED
```
types.js restored byte-identical (grep `ts.getJSDocType(node)` = 1).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_jsdoc_fills_extra_type_and_resolves_the_receiver` (`extra.type == "Service"`) |
| AC2 | same test (RESOLVED receiver) + `jsdoc-types` conformance CALLS shape |
| AC3 | `jsdoc-types` in `TS_R62_CASES`/`TS_CASES` + `test_the_conformance_inventory_is_the_named_set` |
| AC4 | recorded red-run (JSDoc source disabled → receiver tests fail) |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

Extending 153's type table with a second syntactic source (JSDoc) produced no new durable lesson; the inline-field-JSDoc limit is recorded in the README.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: tsc gate green, jsdoc + conformance + inventory tests green in Docker, AC4 red-run recorded, no contract change, types.js restored. Maintainer reviews on the PR.
