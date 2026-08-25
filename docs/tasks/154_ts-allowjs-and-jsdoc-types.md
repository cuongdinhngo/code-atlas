---
id: 154
slug: ts-allowjs-and-jsdoc-types
title: '`allowJs` breadth and JSDoc as a type source — the `.js` half of the adapter is parsed but never typed'
phase: 2
milestone: M7
status: todo
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
